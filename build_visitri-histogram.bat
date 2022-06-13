call "C:\ProgramData\Miniconda3\Scripts\activate.bat"
call activate visitri
pyinstaller --hidden-import=sqlalchemy.ext.baked --add-data ./histogram_config.yml;./ --add-data ./images/;./images/ -n visitri-histogram-customer-lot generate_histograms.py
