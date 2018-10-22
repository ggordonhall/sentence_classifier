import spacy
from torchtext import data
from torchtext import vocab


nlp = spacy.load("en", disable=["parser", "tagger", "ner"])


class DataLoader:
    """Load, tokenise, vectorise and batch entries from a tabular dataset (csv, tsv).
    The Spacy tokeniser is used to split text fields into tokens. Tokens are matched
    with pretrained embeddings with the name `pretrained`, i.e. 'glove.6B.50d.txt',
    which are downloaded to `dir` if they are not already there locally.

    The `DataLoader.loader()` method returns a generator which yields (X, y) pairs
    which are ready to feed to a model. By default the `loader()` generates pairs
    from the training set, but if "test" is passed as an argument will generate from
    the test set.

    Arguments:
        dir {str} -- path to the data directory
        format {str} -- the format of the data table (tsv, csv)
        headings {List[str]} -- the column head names
        text_col {str} -- the input column name
        label_col {str} -- the output column name
        batch_sizes {Tuple[int]} -- batch dimensions
        pretrained {str} -- name of valid pretrained embedding
        pretrained_dir {str} -- path to embedding directory
    """

    def __init__(
        self,
        dir,
        format,
        headings,
        text_col,
        label_col,
        batch_sizes,
        pretrained,
        pretrained_dir,
    ):
        # Build text and label `data.Field`
        self._text = data.Field(
            sequential=True, tokenize=tokeniser, include_lengths=True, use_vocab=True
        )
        self._label = data.LabelField(use_vocab=True)
        # Match columns in the dataset with fields. If not used in the model
        #  column takes field value [col_name, None] and is ignored.
        field_dict = {text_col: self._text, label_col: self._label}
        fields = []
        for col in headings:
            if col in field_dict.keys():
                field = field_dict[col] if col in field_dict.keys() else None
                fields.append([col, field])
        # Load the dataset process according to fields
        train_splt, test_splt = data.TabularDataset.splits(
            path=dir,
            format=format,
            train="train.{}".format(format),
            test="test.{}".format(format),
            fields=tuple(fields),
            skip_header=True,
        )
        # Download pretrained embeddings to `pretrained_dir`, or
        #  load if they exist locally.
        vec = vocab.Vectors(pretrained, pretrained_dir)
        # Build vocabs and match with pretrained embeddings
        self._text.build_vocab(train_splt, test_splt, vectors=vec)
        self._label.build_vocab(train_splt)
        #  Split processed data into batches of dimensions `batch_sizes`
        train_it, test_it = data.BucketIterator.splits(
            datasets=(train_splt, test_splt),
            batch_sizes=batch_sizes,
            sort_key=lambda x: len(getattr(x, text_col)),
            sort_within_batch=True,
            repeat=False,
        )
        self._iter_dict = {"train": train_it, "test": test_it}

    def load(self, mode="train"):
        """Load input, output pairs from a
        data iterator. Default train, but can
        also load test set.

        Keyword Arguments:
            mode {str} -- [train/test split] (default: {"train"})
        """

        iterator = self._iter_dict[mode]
        for batch in iterator:
            X = getattr(batch, self._text)
            y = getattr(batch, self._label)
            yield (X, y)

    @property
    def vocab(self):
        return self._text.vocab

    @property
    def label_map(self):
        return self._label.vocab.itos


def tokeniser(sentence):
    """Tokenise sentence with Spacy
    tokeniser.

    Arguments:
        sentence {str}

    Returns:
        List[str] -- list of token strings
    """

    return [word.text.lower() for word in nlp.pipe(sentence)]