const { contextBridge, ipcRenderer } = require('electron');

// Electron API를 안전하게 노출
contextBridge.exposeInMainWorld('electronAPI', {
  // 폴더 선택
  selectFolder: (title) => ipcRenderer.invoke('select-folder', title),

  // Excel 파일 목록 가져오기
  getExcelFiles: (folderPath) => ipcRenderer.invoke('get-excel-files', folderPath),

  // 배치 처리 시작
  startBatchProcessing: (config) => ipcRenderer.invoke('start-batch-processing', config),

  // 처리 중단
  stopProcessing: () => ipcRenderer.invoke('stop-processing'),

  // 이벤트 리스너
  onProcessingLog: (callback) => {
    ipcRenderer.on('processing-log', (event, data) => callback(data));
  },

  onProcessingComplete: (callback) => {
    ipcRenderer.on('processing-complete', (event, data) => callback(data));
  },

  // 이벤트 리스너 제거
  removeAllListeners: (channel) => {
    ipcRenderer.removeAllListeners(channel);
  }
});