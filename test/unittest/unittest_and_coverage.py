# Aus ~/projects ausführen (Ordnername "unittest" kollidiert sonst mit dem Standardmodul):
python3 -m unittest discover -s QGCR/test/unittest -t . -v
python3 -m pytest QGCR/test/pytest
QGCR_SITL=1 python3 -m unittest discover -s QGCR/test/unittest -t . -p "test_px4_*.py" -v
coverage run -m unittest discover -s QGCR/test/unittest -t .
coverage report -m
coverage html
