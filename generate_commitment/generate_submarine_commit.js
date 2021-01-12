const web3 = require('web3');
const Tx = require('ethereumjs-tx').Transaction;

const toHex = (n) => web3.utils.toHex(n);

const unlockFunctionSelector = web3.utils.hexToBytes("0xec9b5b3a");

module.exports = function generateAddressB(
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
    // let w = require("crypto").randomBytes(32);
    let w = Buffer.from("ce172ac25dfebdc35fd14939002f921e3975bec18f350c2969a0c2d99ab1f380", 'hex');
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
    commit = web3.utils.keccak256(commit);
    
    // We then create the TxUnlock transaction
    const tx = new Tx({
        nonce : nonce,
        to : addressC,
        value : toHex(sendAmount),
        gasPrice : toHex(gasPrice),
        gasLimit : toHex(gasLimit)
    })

    // And sign it with the generated private key
    tx.sign(w);
    const raw = '0x' + tx.serialize().toString('hex');

    //Before recovering addressB after the fact
    const addressB = tx.getSenderAddress();
    
    return toHex(addressB);
}

function parseAddress(address){
    address = address.toString();

    if(address.length !== 42){
        throw "Address is incorrect length";
    }
    if(address[0] != "0" || address[1] != "x"){
        throw "Address is formatted incorrectly";
    }

    return Buffer.from(web3.utils.hexToBytes(address));

}
function numberToBuffer(number) {
    // l0x0l
    const hex = web3.utils.toHex(number);
    return Buffer.from(web3.utils.hexToBytes(hex));
}


function RSfromCommit(commit) {
    let R, S;
}