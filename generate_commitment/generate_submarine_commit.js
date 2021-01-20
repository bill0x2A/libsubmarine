const Web3 = require('web3');
const rlp = require('rlp')
const Tx = require('ethereumjs-tx').Transaction;
const Trie = require('merkle-patricia-tree').BaseTrie

const web3 = new Web3(new Web3.providers.HttpProvider('https://mainnet.infura.io/v3/e607510aa3604e3e8daa17376f47379a'))

const toHex = (n) => Web3.utils.toHex(n);
const keccak256 = (n) => Web3.utils.keccak256(n);
const hexToBytes = (n) => Web3.utils.hexToBytes(n);

const unlockFunctionSelector = Buffer.from(hexToBytes("0xec9b5b3a"));

module.exports = {
    generateCommit : 
    function generateAddressB(
        addressA,   // Sender address
        addressC,   // Contract address
        sendAmount, // Bid amount in Wei
        auctionID,   // Data for contract
        gasPrice,   // UnlockTx gas price
        gasLimit,   // UnlockTx gas limit
        nonce=0,    // tx nonce
        v=27,        // No replay protection
    ){
        // First, we need to generate our random secret w
        let w = require("crypto").randomBytes(32);
        // w = Buffer.from("ce172ac25dfebdc35fd14939002f921e3975bec18f350c2969a0c2d99ab1f380", 'hex');
        // Test case, private key for 0xc3a0388acfcb18197D1753dd1e7961c93DFd5a82
    
        // Then we process all our other inputs to be in the same format
        addressABuffer = parseAddress(addressA);
        addressCBuffer = parseAddress(addressC);
        
        let sendAmountBuffer, auctionIdBuffer, gasPriceBuffer, gasLimitBuffer;
        sendAmountBuffer = numberToBuffer(sendAmount); 
        auctionIdBuffer = numberToBuffer(auctionID);
        gasPriceBuffer = numberToBuffer(gasPrice);
        gasLimitBuffer = numberToBuffer(gasLimit);
        
        // Then we can generate and hash our commit variable
        let commit = Buffer.concat([addressABuffer, addressCBuffer, sendAmountBuffer, w, gasPriceBuffer, gasLimitBuffer]);
        commit = keccak256(commit);
    
        hashedCommitBuffer = Buffer.from(hexToBytes(commit));
        const zero = Buffer.from([0])
        const one = Buffer.from([1])
    
        // Before using it to generate the other required values
        const r = keccak256(
            Buffer.concat([hashedCommitBuffer, zero])
        )
        const s = keccak256(
            Buffer.concat([hashedCommitBuffer, one])
        )
    
        const data = '0x' + Buffer.concat([unlockFunctionSelector, hashedCommitBuffer]).toString('hex')
        
        // We then create the TxUnlock transaction
    
        const tx = new Tx({
            nonce : nonce,
            to : addressC,
            value : toHex(sendAmount),
            gasPrice : toHex(gasPrice),
            gasLimit : toHex(gasLimit),
            data : data,
            r : r,
            s : s,
            v : toHex(v)
        })
    
        // Before recovering addressB after the fact
        let addressB
        try {
            addressB = tx.getSenderAddress();
        }
        catch(e) {
            if(e.name = "Invalid Signature"){
                console.log("Invalid signature, rerunning");
                return generateAddressB(addressA, addressC, sendAmount, auctionID, gasPrice, gasLimit)
            }
            else {
                console.log("OTHER ERROR:\n", e)
                return
            }
        }
        
        return toHex(addressB);
    },
    constructProofBlob : 
    async function constructProofBlob(transactionHash){
        const transaction = await web3.eth.getTransaction(transactionHash)
        const blockData = await web3.eth.getBlock(transaction.blockNumber)
        const { transactions, parentBlock, uncles, miner, stateRoot, transactionsRoot, receiptsRoot, logsBloom, difficulty, number, gasLimit, gasUsed, timestamp, extraData, mixHash, nonce } = blockData;

        let txPath
        // MPT Tree construction
        constructTxTree(transactions)
            .then(mpt => {
                console.log("MPT : \n", mpt)
                console.log("Transaction : \n", transaction)
                return mpt.findPath(rlpTx(transaction))
            })
            .then(path => console.log(path))
            .catch(e => {
                console.log(e)
            })

        const list = [
            1,
            [
              parentBlock,
              uncles,
              miner, 
              stateRoot,
              transactionsRoot,
              receiptsRoot,
              logsBloom,
              difficulty,
              number,
              gasLimit, 
              gasUsed,
              timestamp,
              extraData,
              mixHash,
              nonce
            ],
            transaction.transactionIndex,
            [
                // MPT nodes on way to transaction
            ]
        ]
        // return rlp.encode(rec_bin(list))
        return txPath
    }

} 

// Auxilliary functions

async function constructTxTree(transactions){

    let mpt = new Trie();

    for (const transaction of transactions){
        const tx = await web3.eth.getTransaction(transaction)
        await mpt.put(rlp.encode(tx.transactionIndex), rlpTx(tx))
    }

    return mpt
}

function rlpTx(tx){
    let transaction = new Tx({
            nonce : toHex(tx.nonce),
            to : addressC,
            value : toHex(parseInt(tx.value)),
            gasPrice : toHex(parseInt(gasPrice)),
            gasUsed : toHex(tx.gas),
            data : tx.input,
            r : tx.r,
            s : tx.s
        })
    return transaction.serialize(); // RLP encoded transaction data
}

function parseAddress(address){
    address = address.toString();

    if(address.length !== 42){
        throw "Address is incorrect length";
    }
    if(address[0] != "0" || address[1] != "x"){
        throw "Address is formatted incorrectly";
    }

    return Buffer.from(hexToBytes(address));

}
function numberToBuffer(number) {
    // l0x0l
    const hex = toHex(number);
    return Buffer.from(hexToBytes(hex));
}

function rec_bin(x){
    if(Array.isArray(x) && x.length > 1){
        let value = [];
        x.forEach(element => {
            value.push(rec_bin(element))
        })
    } else {
        let value;
        if(Array.isArray(x)){
            value = x[0]
        } else {
            value = x
        }
        if(typeof(x) == 'string' &&
           x[0] == '0' &&
           x[1] == 'x' &&
           x.length != 2
        ){
            return hexToBytes(x)
        }
    }
}