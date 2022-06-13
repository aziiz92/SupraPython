import os
import yaml


current_path = os.path.abspath(os.getcwd())

with open(current_path + '/histogram_config.yml') as f:
    try:
        config = yaml.safe_load(f)

    except yaml.YAMLError as e:
        print(e)


