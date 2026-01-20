import { ethers } from "ethers";
import { config as dotenvConfig } from "dotenv";
import { resolve } from "path";

import { proxyFactoryAbi } from "../../src/abis";
import { 
    CONDITIONAL_TOKENS_FRAMEWORK_ADDRESS,
    NEG_RISK_ADAPTER_ADDRESS,
    PROXY_WALLET_FACTORY_ADDRESS,
    USDC_ADDRESS
} from "../../src/constants";
import { encodeRedeem, encodeRedeemNegRisk } from "../../src/encode";


dotenvConfig({ path: resolve(__dirname, "../../.env") });


async function main() {
    // Parse command line arguments
    const args = process.argv.slice(2);
    
    if (args.length < 1) {
        console.error("Usage: ts-node redeem.ts <conditionId> [negRisk] [yesAmount] [noAmount]");
        console.error("Example: ts-node redeem.ts 0x123...abc true 1 1");
        console.error("\nArguments:");
        console.error("  conditionId  - The market condition ID (required)");
        console.error("  negRisk      - Whether it's a neg risk market (default: false)");
        console.error("  yesAmount    - Amount of YES tokens to redeem for neg risk (default: 1)");
        console.error("  noAmount     - Amount of NO tokens to redeem for neg risk (default: 1)");
        process.exit(1);
    }
    
    const conditionId = args[0];
    const negRisk = args[1] === "true" || args[1] === "1";
    const redeemAmounts = [
        args[2] || "1",  // YES amount
        args[3] || "1"   // NO amount
    ];
    
    console.log(`Starting redeem...`);
    console.log(`Condition ID: ${conditionId}`);
    console.log(`Neg Risk: ${negRisk}`);
    if (negRisk) {
        console.log(`Redeem Amounts: YES=${redeemAmounts[0]}, NO=${redeemAmounts[1]}`);
    }
    console.log();
    
    const provider = new ethers.providers.JsonRpcProvider(`${process.env.RPC_URL}`);
    const pk = new ethers.Wallet(`${process.env.PK}`);
    const wallet = pk.connect(provider);
    console.log(`Address: ${wallet.address}`)

    // Proxy factory
    const factory = new ethers.Contract(PROXY_WALLET_FACTORY_ADDRESS, proxyFactoryAbi, wallet); 
    
    // Redeem
    const data = negRisk ? encodeRedeemNegRisk(conditionId, redeemAmounts) : encodeRedeem(USDC_ADDRESS, conditionId);
        
    const to = negRisk ? NEG_RISK_ADAPTER_ADDRESS: CONDITIONAL_TOKENS_FRAMEWORK_ADDRESS;

    const proxyTxn = {
        to: to,
        typeCode: "1",
        data: data,
        value: "0",
    };

    // Get current gas prices from the network
    const feeData = await provider.getFeeData();
    console.log(`Current baseFee: ${feeData.lastBaseFeePerGas?.toString()} wei`);
    console.log(`Suggested maxFeePerGas: ${feeData.maxFeePerGas?.toString()} wei`);
    console.log(`Suggested maxPriorityFeePerGas: ${feeData.maxPriorityFeePerGas?.toString()} wei`);

    // Polygon has minimum requirements for priority fee (25 Gwei)
    const MIN_PRIORITY_FEE = ethers.utils.parseUnits("25", "gwei");
    const MIN_MAX_FEE = ethers.utils.parseUnits("500", "gwei");
    
    // Use the max of: (suggested * 1.5) or minimum required
    let maxPriorityFeePerGas = feeData.maxPriorityFeePerGas?.mul(150).div(100) || MIN_PRIORITY_FEE;
    if (maxPriorityFeePerGas.lt(MIN_PRIORITY_FEE)) {
        maxPriorityFeePerGas = MIN_PRIORITY_FEE;
    }
    
    let maxFeePerGas = feeData.maxFeePerGas?.mul(150).div(100) || MIN_MAX_FEE;
    if (maxFeePerGas.lt(MIN_MAX_FEE)) {
        maxFeePerGas = MIN_MAX_FEE;
    }
    
    // Ensure maxFeePerGas >= maxPriorityFeePerGas + baseFee
    const baseFee = feeData.lastBaseFeePerGas || ethers.BigNumber.from(0);
    const minMaxFee = baseFee.mul(2).add(maxPriorityFeePerGas);
    if (maxFeePerGas.lt(minMaxFee)) {
        maxFeePerGas = minMaxFee;
    }
    
    console.log(`Using maxPriorityFeePerGas: ${ethers.utils.formatUnits(maxPriorityFeePerGas, "gwei")} Gwei`);
    console.log(`Using maxFeePerGas: ${ethers.utils.formatUnits(maxFeePerGas, "gwei")} Gwei`);

    const txn = await factory.proxy([proxyTxn], { 
        maxFeePerGas,
        maxPriorityFeePerGas
    });
    
    console.log(`Txn hash: ${txn.hash}`);
    await txn.wait();

    console.log(`Done!`)
}

main();