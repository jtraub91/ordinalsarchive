from django.contrib import admin

# Register your models here.
from .models import Tx, TxIn, TxOut, Inscription, Block, ContextRevision

admin.site.register(Tx)
admin.site.register(TxIn)
admin.site.register(TxOut)
admin.site.register(Inscription)
admin.site.register(Block)
admin.site.register(ContextRevision)
