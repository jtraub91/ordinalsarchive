from django.db import models


class Block(models.Model):
    blockheight = models.IntegerField(primary_key=True)
    blockheaderhash = models.CharField(unique=True)
    version = models.IntegerField()
    prev_blockheaderhash = models.CharField()
    merkle_root = models.CharField()
    time = models.IntegerField()
    bits = models.CharField()
    nonce = models.BigIntegerField()

    coinbase_tx_scriptsig = models.CharField(
        max_length=200
    )  # hex-encoded max 100 bytes
    coinbase_tx_scriptsig_text = models.CharField(
        max_length=200
    )  # utf8 encoded ignoring other chars

    def dict(self):
        return {
            "blockheaderhash": self.blockheaderhash,
            "version": self.version,
            "prev_blockheaderhash": self.prev_blockheaderhash,
            "merkle_root_hash": self.merkle_root,
            "nTime": self.time,
            "nBits": self.bits,
            "nNonce": self.nonce,
        }

    def __str__(self):
        return f"<Block height={self.blockheight}, hash={self.blockheaderhash}>"


class Tx(models.Model):
    txid = models.CharField()
    wtxid = models.CharField()
    version = models.IntegerField()
    locktime = models.IntegerField()

    block = models.ForeignKey(Block, on_delete=models.CASCADE)

    def __str__(self):
        return f"<Tx txid={self.txid}>"


class OpReturn(models.Model):
    """Table for storing data from tx outputs with OP_RETURN"""

    # raw hex-encoded data from scriptpubkey of tx output with OP_RETURN
    # i.e. OP_RETURN <data>
    data = models.CharField(max_length=160)

    # utf8 encoded text of data
    text = models.CharField(max_length=80)

    txout_n = models.IntegerField()
    txout_value = models.IntegerField()

    tx = models.ForeignKey(Tx, on_delete=models.CASCADE)


class Content(models.Model):

    context = models.TextField()

    op_return = models.ForeignKey(OpReturn, on_delete=models.CASCADE, null=True)
    block = models.ForeignKey(Block, on_delete=models.CASCADE, null=True)
