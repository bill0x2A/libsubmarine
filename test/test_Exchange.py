import logging
import os
import rlp
import sys
import unittest
from ethereum import config, transactions
from ethereum.tools import tester as t
from ethereum.utils import checksum_encode, normalize_address, sha3
from test_utils import rec_hex, rec_bin, deploy_solidity_contract_with_args

sys.path.append(
    os.path.join(os.path.dirname(__file__), '..', 'generate_commitment'))
import generate_submarine_commit

sys.path.append(
    os.path.join(os.path.dirname(__file__), '..', 'proveth', 'offchain'))
import proveth

root_repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

COMMIT_PERIOD_LENGTH = 3
REVEAL_PERIOD_LENGTH = 4
TOTAL_TOKEN_SUPPLY = 1000*10**18
TOKEN_AMOUNT_STARTING = 1337000000000000000
ETH_AMOUNT_STARTING = 5*10**18
OURGASLIMIT = 3712394
OURGASPRICE = 10**6
BASIC_SEND_GAS_LIMIT = 21000
extraTransactionFees = 100000000000000000
ACCOUNT_STARTING_BALANCE = 1000000000000000000000000
SOLIDITY_NULL_INITIALVAL = 0
ALICE_ADDRESS = t.a1
ALICE_PRIVATE_KEY = t.k1
BOB_STARTING_TOKEN_AMOUNT = 12 * 10**18
BOB_ADDRESS = t.a2
BOB_PRIVATE_KEY = t.k2
CHARLIE_ADDRESS = t.a3
CHARLIE_PRIVATE_KEY = t.k3
RANDO_ADDRESS = t.k6
RANDO_ADDRESS_PRIVATE_KEY = t.k6
CONTRACT_OWNER_ADDRESS = t.a7
CONTRACT_OWNER_PRIVATE_KEY = t.k7
ALICE_TRADE_AMOUNT = 2200000000000000000


log = logging.getLogger('TestExampleAuction')
LOGFORMAT = "%(levelname)s:%(filename)s:%(lineno)s:%(funcName)s(): %(message)s"
log.setLevel(logging.getLevelName('INFO'))
logHandler = logging.StreamHandler(stream=sys.stdout)
logHandler.setFormatter(logging.Formatter(LOGFORMAT))
log.addHandler(logHandler)


class TestExampleAuction(unittest.TestCase):
    def setUp(self):
        config.config_metropolis['BLOCK_GAS_LIMIT'] = 2**60
        self.chain = t.Chain(env=config.Env(config=config.config_metropolis))
        self.chain.mine(1)
        contract_dir = os.path.abspath(
            os.path.join(root_repo_dir, 'contracts/'))
        os.chdir(root_repo_dir)
        self.token_contract = deploy_solidity_contract_with_args(
            chain=self.chain,
            solc_config_sources={
            'examples/Exchange/ERC20Interface.sol': {
                'urls':
                [os.path.join(contract_dir, 'examples/Exchange/ERC20Interface.sol')]
            },
            'examples/Exchange/TestToken.sol': {
                'urls':
                [os.path.join(contract_dir, 'examples/Exchange/TestToken.sol')]
                },
                'SafeMath.sol': {
                    'urls': [os.path.join(contract_dir, 'SafeMath.sol')]
                },
            },
            allow_paths=root_repo_dir,
            contract_file='examples/Exchange/TestToken.sol',
            contract_name='TestToken',
            startgas=10**7,
            args=["TestToken", "TTT", 18],
            contractDeploySender=CONTRACT_OWNER_PRIVATE_KEY)
        self.token_contract.mint(CONTRACT_OWNER_ADDRESS, TOTAL_TOKEN_SUPPLY, sender=CONTRACT_OWNER_PRIVATE_KEY)
        self.exchange_contract = deploy_solidity_contract_with_args(
            chain=self.chain,
            solc_config_sources={
                'examples/Exchange/Exchange.sol': {
                    'urls':
                    [os.path.join(contract_dir, 'examples/Exchange/Exchange.sol')]
                },
                'examples/Exchange/ERC20Interface.sol': {
                    'urls':
                    [os.path.join(contract_dir, 'examples/Exchange/ERC20Interface.sol')]
                },
                'examples/Exchange/TestToken.sol': {
                    'urls':
                    [os.path.join(contract_dir, 'examples/Exchange/TestToken.sol')]
                },
                'LibSubmarineSimple.sol': {
                    'urls':
                    [os.path.join(contract_dir, 'LibSubmarineSimple.sol')]
                },
                'SafeMath.sol': {
                    'urls': [os.path.join(contract_dir, 'SafeMath.sol')]
                },
                'proveth/ProvethVerifier.sol': {
                    'urls': [
                        os.path.join(contract_dir,
                                     'proveth/ProvethVerifier.sol')
                    ]
                },
                'proveth/RLP.sol': {
                    'urls': [os.path.join(contract_dir, 'proveth/RLP.sol')]
                }
            },
            allow_paths=root_repo_dir,
            contract_file='examples/Exchange/Exchange.sol',
            contract_name='Exchange',
            startgas=10**7,
            args=[self.token_contract.address],
            contractDeploySender=CONTRACT_OWNER_PRIVATE_KEY)
        self.token_contract.approve(self.exchange_contract.address, TOKEN_AMOUNT_STARTING, sender=CONTRACT_OWNER_PRIVATE_KEY)
        self.exchange_contract.initializeExchange(TOKEN_AMOUNT_STARTING, value=ETH_AMOUNT_STARTING, sender=CONTRACT_OWNER_PRIVATE_KEY)
        self.token_contract.transfer(BOB_ADDRESS, BOB_STARTING_TOKEN_AMOUNT, sender=CONTRACT_OWNER_PRIVATE_KEY)


    def test_ExchangeWorkflowBuyTokensWithEth(self):
        ##
        ## STARTING STATE
        ##
        self.chain.mine(1)
        self.assertEqual(TOTAL_TOKEN_SUPPLY - TOKEN_AMOUNT_STARTING - BOB_STARTING_TOKEN_AMOUNT, self.token_contract.balanceOf(CONTRACT_OWNER_ADDRESS))
        self.assertEqual(TOKEN_AMOUNT_STARTING, self.token_contract.balanceOf(self.exchange_contract.address))
        self.assertEqual(ACCOUNT_STARTING_BALANCE - ETH_AMOUNT_STARTING, self.chain.head_state.get_balance(rec_hex(CONTRACT_OWNER_ADDRESS)))
        self.assertEqual(ETH_AMOUNT_STARTING, self.chain.head_state.get_balance(rec_hex(self.exchange_contract.address)))
        self.assertEqual(BOB_STARTING_TOKEN_AMOUNT, self.token_contract.balanceOf(BOB_ADDRESS))
        self.assertEqual(0, self.token_contract.balanceOf(ALICE_ADDRESS))
        self.assertEqual(ETH_AMOUNT_STARTING, self.exchange_contract.ethPool())
        self.assertEqual(TOKEN_AMOUNT_STARTING, self.exchange_contract.tokenPool())
        self.assertEqual(ETH_AMOUNT_STARTING * TOKEN_AMOUNT_STARTING ,self.exchange_contract.invariant())
        currentInvariant = ETH_AMOUNT_STARTING * TOKEN_AMOUNT_STARTING

        ##
        ## ALICE BUYS TOKENS WITH ETH
        ##
        timeout = self.chain.head_state.timestamp + 300
        self.exchange_contract.ethToTokenSwap(1, timeout, value=ALICE_TRADE_AMOUNT, sender=ALICE_PRIVATE_KEY)

        ##
        ## CHECK STATE AFTER TOKEN PURCHASE
        ##
        self.assertEqual(ETH_AMOUNT_STARTING+ALICE_TRADE_AMOUNT, self.exchange_contract.ethPool())
        self.assertEqual(ETH_AMOUNT_STARTING+ALICE_TRADE_AMOUNT, self.chain.head_state.get_balance(rec_hex(self.exchange_contract.address)))
        self.assertEqual(ACCOUNT_STARTING_BALANCE - ALICE_TRADE_AMOUNT, self.chain.head_state.get_balance(rec_hex(ALICE_ADDRESS)))
        tokens_out = int(TOKEN_AMOUNT_STARTING - (currentInvariant //(ETH_AMOUNT_STARTING + ALICE_TRADE_AMOUNT)))
        self.assertEqual(tokens_out, self.token_contract.balanceOf(ALICE_ADDRESS))
        self.assertEqual(TOKEN_AMOUNT_STARTING - tokens_out, self.token_contract.balanceOf(self.exchange_contract.address))
        self.assertEqual(TOKEN_AMOUNT_STARTING - tokens_out, self.exchange_contract.tokenPool())

    # def test_ExchangeWorkflowBuyEthWithTokens(self):
    #     ##
    #     ## STARTING STATE
    #     ##
    #     self.chain.mine(1)
    #     self.assertEqual(TOTAL_TOKEN_SUPPLY - TOKEN_AMOUNT_STARTING - BOB_STARTING_TOKEN_AMOUNT, self.token_contract.balanceOf(CONTRACT_OWNER_ADDRESS))
    #     self.assertEqual(TOKEN_AMOUNT_STARTING, self.token_contract.balanceOf(self.exchange_contract.address))
    #     self.assertEqual(ACCOUNT_STARTING_BALANCE - ETH_AMOUNT_STARTING, self.chain.head_state.get_balance(rec_hex(CONTRACT_OWNER_ADDRESS)))
    #     self.assertEqual(ETH_AMOUNT_STARTING, self.chain.head_state.get_balance(rec_hex(self.exchange_contract.address)))
    #     self.assertEqual(BOB_STARTING_TOKEN_AMOUNT, self.token_contract.balanceOf(BOB_ADDRESS))
    #     self.assertEqual(0, self.token_contract.balanceOf(ALICE_ADDRESS))
    #     self.assertEqual(ETH_AMOUNT_STARTING, self.exchange_contract.ethPool())
    #     self.assertEqual(TOKEN_AMOUNT_STARTING, self.exchange_contract.tokenPool())
    #     self.assertEqual(ETH_AMOUNT_STARTING * TOKEN_AMOUNT_STARTING ,self.exchange_contract.invariant())
    #     currentInvariant = ETH_AMOUNT_STARTING * TOKEN_AMOUNT_STARTING

if __name__ == "__main__":
    unittest.main()
