import os
import time
import slicer
import logging
import requests

from typing import List
from pathlib import Path

from utils.gitlab_snippets import *
from utils import run_with_interval_forever


class LabelManager:

    def __init__(self):
        self._segment_labels: List[str] = None

        self._config_dir = Path(slicer.app.slicerUserSettingsFilePath).parent
        self._config_file_path = self._config_dir / 'labels.txt'

    @property
    def segment_labels(self) -> List[str]:
        if self._segment_labels is not None:
            return self._segment_labels

        with open(self._config_file_path, 'r') as f:
            lines = [line.strip() for line in f.readlines()]
            for line in lines:
                if len(line) > 100:
                    raise ValueError()
            self._segment_labels = list(sorted(lines))

        return self._segment_labels

    def fetch_labels(self) -> bool:
        try:
            response = requests.get(URL_LABEL_LIST, headers={'PRIVATE-TOKEN': API_KEY})
        except requests.exceptions.ConnectionError:
            self.create_empty_label_list_file()
            return False

        if response.status_code != 200:
            self.create_empty_label_list_file()
            logging.warning(f'Fetch labels error status code: {response.status_code}')
            logging.warning(response.content)
            return False

        labels = []
        content = response.content.decode('UTF-8')
        for line in content.split('\n'):
            parts = line.split(',')
            if len(parts) != 3:
                raise ValueError('Invalid row in downloaded label file.')
            if parts[2].strip() == 'TRUE':
                labels.append(parts[1] + '\n')

        with open(self._config_file_path, 'w') as f:
            f.writelines(sorted(labels))

        self._segment_labels = None
        return True

    def is_label_file_exist(self) -> bool:
        return os.path.isfile(self._config_file_path)

    def create_empty_label_list_file(self, truncate=False):
        if not self.is_label_file_exist() or truncate:
            open(self._config_file_path, 'w').close()

    def start_outdated_label_list_watcher(self, watch_interval=60, label_list_outdated=3600):
        def watch():
            if time.time() - os.path.getmtime(self._config_file_path) > label_list_outdated:
                logging.info('Clearing outdated label list file.')
                self.create_empty_label_list_file(truncate=True)

        run_with_interval_forever(watch, watch_interval)
