# tptp-features
Extract features from TPTP problems for machine learning

# Notes

Install antlr:
```
brew install antlr
pip3 install antlr4-python3-runtime
```

Generate Python3 parser using
```
antlr -Dlanguage=Python3 tptp_v7_0_0_0.g4
```