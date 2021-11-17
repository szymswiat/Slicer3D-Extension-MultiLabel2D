import logging
from pathlib import Path
from typing import List

import requests
import slicer

logger = logging.getLogger('LabelManager')


class LabelManager:
    URL = 'https://gitlab.com/api/v4/projects/cxrai%2Fcxrai-slicer/snippets/2178847/raw'
    API_KEY = 'CzsC8d_HeS-Z49Histce'

    def __init__(self):
        self._segment_labels: List[str] = None

        self._config_dir = Path(slicer.app.slicerUserSettingsFilePath).parent

    # TODO: should handle case when during first setup there is no internet connection
    @property
    def segment_labels(self) -> List[str]:
        if self._segment_labels is not None:
            return self._segment_labels

        labels_file_path = self._config_dir / 'labels.txt'

        with open(labels_file_path, 'r') as f:
            lines = [line.strip() for line in f.readlines()]
            for line in lines:
                if len(line) > 100:
                    raise ValueError()
            self._segment_labels = list(sorted(lines))

        return self._segment_labels

    def fetch_labels(self) -> bool:
        response = requests.get(self.URL, headers={'PRIVATE-TOKEN': self.API_KEY})

        if response.status_code != 200:
            return False

        labels = []
        content = response.content.decode('UTF-8')
        for line in content.split('\n'):
            parts = line.split(',')
            if len(parts) != 3:
                raise ValueError('Invalid row in downloaded label file.')
            if parts[2].strip() == 'TRUE':
                labels.append(parts[1] + '\n')

        with open(self._config_dir / 'labels.txt', 'w') as f:
            f.writelines(sorted(labels))

        self._segment_labels = None
        return True
