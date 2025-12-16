import math

import torch
import torch.nn as nn
import torch.nn.functional as F

# Ref: https://pytorch.org/tutorials/beginner/translation_transformer.html


def _xavier_init_params(params):
    for p in params:
        if p.dim() > 1:
            torch.nn.init.xavier_uniform_(p)


class _PositionalEmbedding(nn.Module):
    def __init__(self, emb_dim, max_len=4096):
        super().__init__()
        den = torch.exp(-torch.arange(0, emb_dim, 2) * math.log(10000) / emb_dim)
        pos = torch.arange(0, max_len).reshape(max_len, 1)
        pos_embedding = torch.zeros((max_len, emb_dim))
        pos_embedding[:, 0::2] = torch.sin(pos * den)
        pos_embedding[:, 1::2] = torch.cos(pos * den)
        pos_embedding = pos_embedding.unsqueeze(-2)
        self.register_buffer("pos_embedding", pos_embedding)

    def forward(self, emb):
        return emb + self.pos_embedding[: emb.size(0), :]


class _TokenEmbedding(nn.Module):
    def __init__(self, vocab_size, emb_size):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, emb_size)
        self.emb_size = emb_size

    def forward(self, tokens):
        return self.embedding(tokens.long()) * math.sqrt(self.emb_size)


class Encoder(nn.Module):
    """
    Base class for encoders.
    """
    def __init__(self, src_emb_dim):
        """
        Args:
            src_emb_dim (int): Dimension of the source embeddings.
        """
        super().__init__()
        self.src_emb_dim = src_emb_dim

    def get_src_enc_dim(self):
        """
        Returns the output dimension of the encoder.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError()

    def _encode(self, src_emb, src_len):
        """
        Internal encode method to be implemented by subclasses.

        Args:
            src_emb (torch.Tensor): Source embeddings.
            src_len (torch.Tensor): Lengths of source sequences.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError()

    def forward(self, src_emb, src_len):
        """
        Encodes the source sequence.

        Args:
            src_emb (torch.Tensor): Source embeddings [max_len, batch_size, emb_dim].
            src_len (torch.Tensor): Lengths of source sequences [batch_size].

        Returns:
            torch.Tensor: Encoded sequence.

        Raises:
            ValueError: If sequence lengths are invalid or dimensions mismatch.
        """
        src_max_len, batch_size, _ = src_emb.shape
        if not (
            torch.all(0 <= src_len).item() and torch.all(src_len <= src_max_len).item()
        ):
            raise ValueError("Invalid sequence lengths")
        if src_emb.shape[-1] != self.src_emb_dim:
            raise ValueError()
        return self._encode(src_emb, src_len)


class IdentityEncoder(Encoder):
    """
    An encoder that returns the input embeddings unchanged.
    """
    def get_src_enc_dim(self):
        """Returns the source embedding dimension."""
        return self.src_emb_dim

    def _encode(self, src_emb, src_len):
        """Returns the input source embeddings."""
        return src_emb


class MLPEncoder(Encoder):
    """
    An encoder using a Multi-Layer Perceptron (MLP).
    """
    def __init__(self, src_emb_dim, hidden_layer_dims=[512], dropout_p=0.5):
        """
        Args:
            src_emb_dim (int): Source embedding dimension.
            hidden_layer_dims (list[int]): List of hidden layer dimensions.
            dropout_p (float): Dropout probability.
        """
        super().__init__(src_emb_dim)
        self.num_layers = len(hidden_layer_dims)
        d = self.src_emb_dim
        for i, ld in enumerate(hidden_layer_dims):
            setattr(self, f"hidden_{i}", nn.Linear(d, ld))
            d = ld
        self.output_dim = d
        self.dropout = nn.Dropout(p=dropout_p)

    def get_src_enc_dim(self):
        """Returns the output dimension of the MLP."""
        return self.output_dim

    def _encode(self, src_emb, src_len):
        """Encodes the source embeddings using the MLP."""
        src_max_len, batch_size, _ = src_emb.shape
        x = src_emb.reshape(src_max_len * batch_size, -1)
        for i in range(self.num_layers):
            x = getattr(self, f"hidden_{i}")(x)
            x = F.relu(x)
            x = self.dropout(x)
        x = x.reshape(src_max_len, batch_size, -1)
        return x


class TransformerEncoder(Encoder):
    """
    An encoder using the Transformer architecture.
    """
    def __init__(
        self,
        src_emb_dim,
        model_dim=512,
        num_heads=8,
        num_layers=6,
        feedforward_dim=2048,
        dropout_p=0.1,
        _legacy_for_unit_test=False,
    ):
        """
        Args:
            src_emb_dim (int): Source embedding dimension.
            model_dim (int): Model dimension (must match src_emb_dim).
            num_heads (int): Number of attention heads.
            num_layers (int): Number of transformer layers.
            feedforward_dim (int): Dimension of feedforward network.
            dropout_p (float): Dropout probability.
            _legacy_for_unit_test (bool): Internal flag for testing.

        Raises:
            ValueError: If src_emb_dim does not match model_dim.
        """
        if src_emb_dim != model_dim:
            raise ValueError()

        if not _legacy_for_unit_test:
            super().__init__(src_emb_dim)

        transformer_layer = nn.modules.TransformerEncoderLayer(
            model_dim,
            num_heads,
            dim_feedforward=feedforward_dim,
            dropout=dropout_p,
            activation="relu",
        )
        transformer_norm = nn.modules.normalization.LayerNorm(model_dim)
        self.transformer = nn.modules.TransformerEncoder(
            transformer_layer, num_layers, norm=transformer_norm
        )

        if not _legacy_for_unit_test:
            _xavier_init_params(self.parameters())

        self.model_dim = model_dim

    def get_src_enc_dim(self):
        """Returns the model dimension."""
        return self.model_dim

    def _encode(self, src_emb, src_len):
        """Encodes using the Transformer."""
        src_max_len, batch_size, _ = src_emb.shape

        # Create sequence mask
        seq_idxs = torch.arange(
            0, src_max_len, dtype=src_len.dtype, device=src_emb.device
        ).expand(batch_size, -1)
        # NOTE: True means *do* mask that position
        src_key_padding_mask = seq_idxs >= src_len.unsqueeze(1)

        return self.transformer(src_emb, src_key_padding_mask=src_key_padding_mask)


class Decoder(nn.Module):
    """
    Base class for decoders.
    """
    def __init__(self, src_enc_dim, tgt_emb_dim):
        """
        Args:
            src_enc_dim (int): Dimension of source encodings.
            tgt_emb_dim (int): Dimension of target embeddings.
        """
        super().__init__()
        self.src_enc_dim = src_enc_dim
        self.tgt_emb_dim = tgt_emb_dim

    def get_tgt_dec_dim(self):
        """
        Returns the output dimension of the decoder.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError()

    def _decode(self, src_enc, src_len, tgt_emb, tgt_len=None):
        """
        Internal decode method.

        Raises:
            NotImplementedError: Must be implemented by subclasses.
        """
        raise NotImplementedError()

    def forward(self, src_enc, src_len, tgt_emb, tgt_len=None):
        """
        Decodes the sequence.

        Args:
            src_enc (torch.Tensor): Source encodings.
            src_len (torch.Tensor): Source lengths.
            tgt_emb (torch.Tensor): Target embeddings.
            tgt_len (torch.Tensor, optional): Target lengths.

        Returns:
            torch.Tensor: Decoded sequence.

        Raises:
            ValueError: If dimensions mismatch or lengths are invalid.
        """
        if src_enc.shape[1] != tgt_emb.shape[1]:
            raise ValueError("Batch sizes must be the same")
        src_max_len, batch_size, _ = src_enc.shape
        tgt_max_len, _, _ = tgt_emb.shape
        if not (
            torch.all(0 <= src_len).item() and torch.all(src_len <= src_max_len).item()
        ):
            raise ValueError("Invalid sequence lengths")
        if tgt_len is not None:
            if not (
                torch.all(0 <= tgt_len).item()
                and torch.all(tgt_len <= tgt_max_len).item()
            ):
                raise ValueError("Invalid sequence lengths")
        if src_enc.shape[-1] != self.src_enc_dim:
            raise ValueError()
        if tgt_emb.shape[-1] != self.tgt_emb_dim:
            raise ValueError()
        return self._decode(src_enc, src_len, tgt_emb, tgt_len=tgt_len)


class IdentityDecoder(Decoder):
    """
    A decoder that returns the target embeddings unchanged.
    """
    def get_tgt_dec_dim(self):
        """Returns the target embedding dimension."""
        return self.tgt_emb_dim

    def _decode(self, src_enc, src_len, tgt_emb, tgt_len=None):
        """Returns the target embeddings."""
        return tgt_emb


class TransformerDecoder(Decoder):
    """
    A decoder using the Transformer architecture.
    """
    def __init__(
        self,
        src_enc_dim,
        tgt_emb_dim,
        model_dim=512,
        num_heads=8,
        num_layers=6,
        feedforward_dim=2048,
        dropout_p=0.1,
    ):
        """
        Args:
            src_enc_dim (int): Source encoding dimension.
            tgt_emb_dim (int): Target embedding dimension.
            model_dim (int): Model dimension (must match src and tgt dims).
            num_heads (int): Number of attention heads.
            num_layers (int): Number of transformer layers.
            feedforward_dim (int): Dimension of feedforward network.
            dropout_p (float): Dropout probability.

        Raises:
            ValueError: If dimensions mismatch.
        """
        if src_enc_dim != model_dim or tgt_emb_dim != model_dim:
            raise ValueError()

        super().__init__(src_enc_dim, tgt_emb_dim)

        transformer_layer = nn.modules.TransformerDecoderLayer(
            model_dim,
            num_heads,
            dim_feedforward=feedforward_dim,
            dropout=dropout_p,
            activation="relu",
        )
        transformer_norm = nn.modules.normalization.LayerNorm(model_dim)
        self.transformer = nn.modules.TransformerDecoder(
            transformer_layer, num_layers, norm=transformer_norm
        )

        _xavier_init_params(self.parameters())

        self.model_dim = model_dim

    def get_tgt_dec_dim(self):
        """Returns the model dimension."""
        return self.model_dim

    def _decode(self, src_enc, src_len, tgt_emb, tgt_len=None):
        """Decodes using the Transformer."""
        src_max_len, batch_size, _ = src_enc.shape
        tgt_max_len, _, _ = tgt_emb.shape

        # Create src mask (based on sequence length)
        seq_idxs = torch.arange(
            0, src_max_len, dtype=src_len.dtype, device=src_enc.device
        ).expand(batch_size, -1)
        # NOTE: True means *do* mask that position
        src_key_padding_mask = seq_idxs >= src_len.unsqueeze(1)

        # Create tgt mask (causal)
        tgt_mask = (
            torch.triu(
                torch.ones(
                    (tgt_max_len, tgt_max_len), dtype=torch.bool, device=tgt_emb.device
                )
            )
            == 1
        ).transpose(0, 1)
        tgt_mask = (
            tgt_mask.float()
            .masked_fill(tgt_mask == 0, float("-inf"))
            .masked_fill(tgt_mask == 1, float(0.0))
        )

        return self.transformer(
            tgt_emb,
            src_enc,
            tgt_mask=tgt_mask,
            memory_key_padding_mask=src_key_padding_mask,
        )


class _TransducerImpl(nn.Module):
    def __init__(
        self,
        src_emb_mode="identity",
        src_vocab_size=None,
        src_dim=None,
        src_emb_dim=None,
        src_pos_emb=False,
        src_dropout_p=0,
        enc_cls=IdentityEncoder,
        enc_kwargs={},
        tgt_emb_mode="identity",
        tgt_vocab_size=None,
        tgt_dim=None,
        tgt_emb_dim=None,
        tgt_pos_emb=False,
        tgt_dropout_p=0,
        dec_cls=None,
        dec_kwargs={},
    ):
        super().__init__()

        # Init src embed
        self.src_emb = None
        if src_emb_mode == "identity":
            src_emb_dim = src_dim
        elif src_emb_mode == "project":
            if src_dim is None or src_emb_dim is None:
                raise ValueError()
            self.src_emb = nn.Linear(src_dim, src_emb_dim)
        elif src_emb_mode == "embed":
            if src_vocab_size is None or src_emb_dim is None:
                raise ValueError()
            self.src_emb = _TokenEmbedding(src_vocab_size, src_emb_dim)
        else:
            raise ValueError()
        self.src_pos_emb = None
        if src_pos_emb:
            if src_emb_dim is None:
                raise ValueError()
            self.src_pos_emb = _PositionalEmbedding(src_emb_dim)
        self.src_dropout = None
        if src_dropout_p > 0:
            self.src_dropout = nn.Dropout(p=src_dropout_p)

        # Init encoder
        self.enc = enc_cls(src_emb_dim, **enc_kwargs)

        # Init tgt embed
        self.tgt_emb = None
        if tgt_emb_mode == "identity":
            tgt_emb_dim = tgt_dim
        elif tgt_emb_mode == "project":
            if tgt_dim is None or tgt_emb_dim is None:
                raise ValueError()
            self.tgt_emb = nn.Linear(tgt_dim, tgt_emb_dim)
        elif tgt_emb_mode == "embed":
            if tgt_vocab_size is None or tgt_emb_dim is None:
                raise ValueError()
            self.tgt_emb = _TokenEmbedding(tgt_vocab_size, tgt_emb_dim)
        else:
            raise ValueError()
        self.tgt_pos_emb = None
        if tgt_pos_emb:
            if tgt_emb_dim is None:
                raise ValueError()
            self.tgt_pos_emb = _PositionalEmbedding(tgt_emb_dim)
        self.tgt_dropout = None
        if tgt_dropout_p > 0:
            self.tgt_dropout = nn.Dropout(p=tgt_dropout_p)

        # Init decoder
        self.dec = None
        if dec_cls is not None:
            self.dec = dec_cls(self.enc.get_src_enc_dim(), tgt_emb_dim, **dec_kwargs)

    def encode(self, src, src_len):
        src_max_len, batch_size, _ = src.shape

        # Embed src
        src_emb = src
        if self.src_emb is not None:
            src_emb = src_emb.reshape(src_max_len * batch_size, -1)
            src_emb = self.src_emb(src_emb)
            src_emb = src_emb.reshape(src_max_len, batch_size, -1)
        if self.src_pos_emb is not None:
            src_emb = self.src_pos_emb(src_emb)
        if self.src_dropout is not None:
            src_emb = self.src_dropout(src_emb)

        return self.enc(src_emb, src_len)

    def decode(self, src_enc, src_len, tgt, tgt_len=None):
        if self.dec is None:
            raise Exception()

        tgt_max_len, batch_size = tgt.shape

        # Embed tgt
        tgt_emb = tgt
        if self.tgt_emb is not None:
            tgt_emb = tgt_emb.reshape(tgt_max_len * batch_size, -1)
            tgt_emb = self.tgt_emb(tgt_emb)
            tgt_emb = tgt_emb.reshape(tgt_max_len, batch_size, -1)
        if self.tgt_pos_emb is not None:
            tgt_emb = self.tgt_pos_emb(tgt_emb)
        if self.tgt_dropout is not None:
            tgt_emb = self.tgt_dropout(tgt_emb)

        return self.dec(src_enc, src_len, tgt_emb, tgt_len=tgt_len)

    def forward(self, src, src_len, tgt, tgt_len=None):
        raise NotImplementedError()


class EncOnlyTransducer(_TransducerImpl):
    """
    Encoder-only transducer for tasks like tagging.
    """
    def __init__(self, output_dim, **kwargs):
        """
        Args:
            output_dim (int): Output dimension.
            **kwargs: Arguments passed to _TransducerImpl.
        """
        super().__init__(
            tgt_emb_mode="identity",
            tgt_vocab_size=None,
            tgt_dim=None,
            tgt_emb_dim=None,
            tgt_pos_emb=False,
            dec_cls=None,
            dec_kwargs={},
            **kwargs,
        )
        self.output = nn.Linear(self.enc.get_src_enc_dim(), output_dim)

    def decode(self, src_enc, src_len, tgt, tgt_len=None):
        """
        Raises Exception as this model has no decoder.
        """
        raise Exception()

    def forward(self, src, src_len, tgt=None, tgt_len=None):
        """
        Forward pass.

        Args:
            src (torch.Tensor): Source input.
            src_len (torch.Tensor): Source lengths.
            tgt: Ignored.
            tgt_len: Ignored.

        Returns:
            torch.Tensor: Output logits.
        """
        src_max_len, batch_size, _ = src.shape

        src_enc = self.encode(src, src_len)

        out = src_enc
        out = out.reshape(src_max_len * batch_size, -1)
        out = self.output(out)
        out = out.reshape(src_max_len, batch_size, -1)

        return out


class S2STransducer(_TransducerImpl):
    """
    Sequence-to-sequence transducer using an encoder-decoder architecture.
    """
    def __init__(self, output_dim, **kwargs):
        """
        Args:
            output_dim (int): Output dimension (vocab size).
            **kwargs: Arguments passed to _TransducerImpl.
        """
        super().__init__(**kwargs)
        self.output = nn.Linear(self.dec.get_tgt_dec_dim(), output_dim)

    def forward(self, src, src_len, tgt, tgt_len=None):
        """
        Forward pass.

        Args:
            src (torch.Tensor): Source input.
            src_len (torch.Tensor): Source lengths.
            tgt (torch.Tensor): Target input.
            tgt_len (torch.Tensor, optional): Target lengths.

        Returns:
            torch.Tensor: Output logits.
        """
        src_max_len, batch_size, _ = src.shape
        if tgt.dim() == 2:
            tgt_max_len, batch_size = tgt.shape
        else:
            tgt_max_len, batch_size, _ = tgt.shape

        src_enc = self.encode(src, src_len)
        tgt_dec = self.decode(src_enc, src_len, tgt, tgt_len=tgt_len)

        out = tgt_dec
        out = out.reshape(tgt_max_len * batch_size, -1)
        out = self.output(out)
        out = out.reshape(tgt_max_len, batch_size, -1)

        return out


class CTCTransducer(_TransducerImpl):
    """
    Transducer trained with Connectionist Temporal Classification (CTC) loss.
    """
    def __init__(self, output_dim, **kwargs):
        """
        Args:
            output_dim (int): Output dimension (vocab size).
                              A blank token is automatically added (dim + 1).
            **kwargs: Arguments passed to _TransducerImpl.
        """
        super().__init__(
            tgt_emb_mode="identity",
            tgt_vocab_size=None,
            tgt_dim=None,
            tgt_emb_dim=None,
            tgt_pos_emb=False,
            dec_cls=None,
            dec_kwargs={},
            **kwargs,
        )
        self.output = nn.Linear(self.enc.get_src_enc_dim(), output_dim + 1)

    def decode(self, src_enc, src_len, tgt, tgt_len=None):
        """
        Raises Exception as this model uses CTC decoding logic, not an explicit decoder.
        """
        raise Exception()

    def forward(self, src, src_len, tgt=None, tgt_len=None):
        """
        Forward pass.

        Args:
            src (torch.Tensor): Source input.
            src_len (torch.Tensor): Source lengths.
            tgt: Ignored.
            tgt_len: Ignored.

        Returns:
            torch.Tensor: Output logits (including blank token).
        """
        src_max_len, batch_size, _ = src.shape

        src_enc = self.encode(src, src_len)

        out = src_enc
        out = out.reshape(src_max_len * batch_size, -1)
        out = self.output(out)
        out = out.reshape(src_max_len, batch_size, -1)

        return out
