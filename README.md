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
cd tptp_features
antlr -Dlanguage=Python3 ../TPTP-ANTLR4-Grammar/tptp_v7_0_0_0.g4
mv -v ../TPTP-ANTLR4-Grammar/tptp_v7_*.{interp,tokens,py} .
```

If using pypy, may need to install numpy with openblas. See
https://stackoverflow.com/questions/64390138/init-dgelsd-failed-init-when-using-import-numpy-as-np