const { generateCommit, constructProofBlob } = require('./generate_commitment/generate_submarine_commit.js');


const testW = Buffer.from("ce172ac25dfebdc35fd14939002f921e3975bec18f350c2969a0c2d99ab1f380", 'hex')

const results = generateCommit(addressA = "0x0dE2d18d335EC5128204da6a0e2c37f1B1c563B3",
                                    addressC = "0x0dE2d18d335EC5128204da6a0e2c37f1B1c563B3",
                                    sendAmount = 200000000000000000000,
                                    auctionID = 3,
                                    gasPrice = 2333333333333440202,
                                    gasLimit = 2000000000000000000,
                                    w = testW
                                );

async function getProofBlob() {
    const result = await constructProofBlob('0x2f81c59fb4f0c3146483e72c1315833af79b6ea9323b647101645dc7ebe04074')
    console.log(result)
}

getProofBlob();