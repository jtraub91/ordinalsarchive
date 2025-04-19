from django.contrib.auth.models import User
from django.db import models


class ContextRevision(models.Model):
    text = models.TextField()
    prev_revision = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True
    )
    updated_at = models.DateTimeField(auto_now=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)


class Block(models.Model):
    blockheight = models.IntegerField()
    blockheaderhash = models.CharField(unique=True)
    version = models.IntegerField()
    prev_blockheaderhash = models.CharField()
    merkle_root = models.CharField()
    time = models.IntegerField()
    bits = models.CharField()
    nonce = models.BigIntegerField()

    context = models.ForeignKey(ContextRevision, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.context_id is None:
            self.context = ContextRevision()
            self.context.save()
        super().save(*args, **kwargs)

    def dict(self):
        return {
            "blockheight": self.blockheight,
            "blockheaderhash": self.blockheaderhash,
            "version": self.version,
            "prev_blockheaderhash": self.prev_blockheaderhash,
            "merkle_root": self.merkle_root,
            "time": self.time,
            "bits": self.bits,
            "nonce": self.nonce,
        }

    def __str__(self):
        return f"<Block height={self.blockheight}, hash={self.blockheaderhash}>"


class Tx(models.Model):
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    n = models.IntegerField()

    txid = models.CharField()
    wtxid = models.CharField()

    version = models.IntegerField()
    locktime = models.IntegerField()

    context = models.ForeignKey(ContextRevision, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.context_id is None:
            self.context = ContextRevision()
            self.context.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"<Tx txid={self.txid}>"


class TxIn(models.Model):
    tx = models.ForeignKey(Tx, on_delete=models.CASCADE)
    n = models.IntegerField()

    # outpoint
    txid = models.CharField()
    vout = models.BigIntegerField()

    scriptsig_text = models.CharField(null=True)
    sequence = models.BigIntegerField()

    context = models.ForeignKey(ContextRevision, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.context_id is None:
            self.context = ContextRevision()
            self.context.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"<TxIn n={self.n} txid={self.tx.txid}>"


class TxOut(models.Model):
    tx = models.ForeignKey(Tx, on_delete=models.CASCADE)
    n = models.IntegerField()

    scriptpubkey = models.BinaryField(null=True)
    scriptpubkey_text = models.CharField(null=True)
    value = models.BigIntegerField()

    context = models.ForeignKey(ContextRevision, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.context_id is None:
            self.context = ContextRevision()
            self.context.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"<TxOut n={self.n} txid={self.tx.txid}>"


class Inscription(models.Model):
    number = models.IntegerField()
    content_type = models.CharField()
    content_size = models.IntegerField()
    filename = models.CharField()

    txin = models.ForeignKey(TxIn, on_delete=models.CASCADE)

    context = models.ForeignKey(ContextRevision, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        if self.context_id is None:
            self.context = ContextRevision()
            self.context.save()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"<Inscription number={self.number}>"
