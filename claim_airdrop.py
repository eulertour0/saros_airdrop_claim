import http.client
import time
import json
import base64
from solana.rpc.api import Client, Pubkey, Keypair
from solana.rpc.commitment import Confirmed
from solana.transaction import Transaction, Instruction, AccountMeta
from spl.token.constants import TOKEN_PROGRAM_ID, ASSOCIATED_TOKEN_PROGRAM_ID
from spl.token.instructions import transfer, TransferParams

headers = {
    'Content-Type': "application/json",
    'User-Agent': "insomnia/8.6.0"
}

solana_rpc = "https://api.mainnet-beta.solana.com"
rpc_client = Client(solana_rpc, commitment=Confirmed)

def get_airdrop(
    funding_keypair: Keypair,
    schedule_index: int,
    proof,
    amount: int,
    schedule_address: Pubkey,
    receiver_keypair: Keypair,
):
    vault_address = Pubkey.from_string("43Yhpt3t5oCardXf236xikqDaVA71AAnLXPJdz8EyzxZ")
    token_mint = Pubkey.from_string("SarosY6Vscao718M4A778z4CGtvcwcGef5M9MEH1LGL")
    receiver_address = receiver_keypair.pubkey()
    receiver_token_address = Pubkey.find_program_address(
        seeds=[bytes(receiver_address), bytes(TOKEN_PROGRAM_ID), bytes(token_mint)], program_id=ASSOCIATED_TOKEN_PROGRAM_ID
    )[0]
    funding_address = funding_keypair.pubkey()
    funding_token_address = Pubkey.find_program_address(
        seeds=[bytes(funding_address), bytes(TOKEN_PROGRAM_ID), bytes(token_mint)], program_id=ASSOCIATED_TOKEN_PROGRAM_ID
    )[0]

    compute_budget_ix = Instruction(
        program_id=Pubkey.from_string("ComputeBudget111111111111111111111111111111"),
        accounts=[],
        data = bytes.fromhex('03') + int(100).to_bytes(8, 'little'),
    )
    create_wallet_ix = Instruction(
        accounts=[
            AccountMeta(pubkey=funding_address, is_signer=True, is_writable=True),
            AccountMeta(pubkey=receiver_token_address, is_signer=False, is_writable=True),
            AccountMeta(pubkey=receiver_address, is_signer=False, is_writable=False),
            AccountMeta(pubkey=token_mint, is_signer=False, is_writable=False),
            AccountMeta(pubkey=Pubkey.from_string("11111111111111111111111111111111"), is_signer=False, is_writable=False),
            AccountMeta(pubkey=TOKEN_PROGRAM_ID, is_signer=False, is_writable=False),
        ],
        program_id=ASSOCIATED_TOKEN_PROGRAM_ID,
        data=bytes.fromhex('01'),
    )
    claim_ix = Instruction(
        program_id=Pubkey.from_string("VAU1T98eWi9uxHbED9i6ueoTRLy1dGcNfDBwdCSNQ3e"),
        data=(
            bytes.fromhex('be555ab0c0da29d6') +
            schedule_index.to_bytes(2, 'little') +
            len(proof).to_bytes(4, 'little') +
            b''.join([bytes.fromhex(p[2:]) for p in proof]) +
            (amount * int(1e6)).to_bytes(8, 'little') +
            bytes.fromhex('0000000000000000')
        ),
        accounts=[
            AccountMeta(vault_address, False, False),
            AccountMeta(schedule_address, False, True),
            AccountMeta(Pubkey.from_string("DQiSLoagGRKF4qBzVCBG57gp8X8t5n6UoJoqXEf5xeS9"), False, True), # vault authority
            AccountMeta(Pubkey.from_string("FokM4xWWDqbtCBkfRam49TTkYva8vBmiEocMX2CFW4GU"), False, True), # vault token account
            AccountMeta(receiver_address, True, True), # receiver address
            AccountMeta(receiver_token_address, False, True), # receiver token account
            AccountMeta(TOKEN_PROGRAM_ID, False, False),
        ]
    )
    transfer_ix = transfer(
        TransferParams(
            TOKEN_PROGRAM_ID,
            receiver_token_address,
            funding_token_address,
            receiver_address,
            amount * int(1e6),
        )
    )
    tx = Transaction(
        recent_blockhash=rpc_client.get_latest_blockhash().value.blockhash,
        fee_payer=funding_address,
        instructions=[compute_budget_ix, create_wallet_ix, claim_ix, transfer_ix]
    )
    tx.sign(funding_keypair, receiver_keypair)
    print(base64.b64encode(tx.serialize()))
    signature = rpc_client.send_transaction(tx, funding_keypair, receiver_keypair)
    result = rpc_client.confirm_transaction(signature.value).value
    assert len(result) == 1
    result = result[0]
    if result is None:
        print("transaction droppped")
    else:
        if result.err is None:
            print(f"transaction success {signature}")
        else:
            print("transaction failed")

# funding wallet 
funding_keypair = Keypair.from_bytes(json.load(open("funding_wallet.json")))
# search wallets
wallets = [
    "wallet0.json",
    "wallet1.json",
    "wallet2.json",
]
for wallet in wallets:
    receiver_keypair = Keypair.from_bytes(json.load(open(wallet)))
    receiver_address = receiver_keypair.pubkey()
    payload = f"{{\"wallets\": [{{\"address\": \"{receiver_address}\",\"chain\": \"solana\"}}]}}"
    while True:
        time.sleep(1)
        conn = http.client.HTTPSConnection("api.coin98.com")
        conn.request("POST", "/adapters/eco/vault/schedule/multiple/v1", payload, headers)
        res = conn.getresponse()
        if res.status != 200:
            print(f"status:{res.status} error:{res.read()}")
            continue
        data = res.read()
        data = json.loads(data.decode("utf-8"))
        schedule = data['data']['schedule']
        if len(schedule) > 0:
            assert len(schedule) == 1
            schedule = schedule[0]['schedule']
            for schedule in schedule:
                rank = schedule['name']
                print(f"{receiver_address} {rank}")
                assert schedule['token'] == "SarosY6Vscao718M4A778z4CGtvcwcGef5M9MEH1LGL"
                assert schedule['vaultAddress'] == "43Yhpt3t5oCardXf236xikqDaVA71AAnLXPJdz8EyzxZ"
                schedule_index = int(schedule['scheduleIdx'])
                proof = schedule['proof']
                amount = int(float(schedule['amount']))
                schedule_address = Pubkey.from_string(schedule['scheduleAddress'])
                get_airdrop(funding_keypair, schedule_index, proof, amount, schedule_address, receiver_keypair)
        else:
            print(f"no airdrop for {receiver_address}")
        break
