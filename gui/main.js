const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const fs = require('fs');
const log = require('electron-log');

// 개발 모드 확인
const isDev = process.argv.includes('--dev');

let mainWindow;
let pythonProcess = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    icon: path.join(__dirname, 'assets', 'icon.png'),
    title: 'Route Optimizer - 배송 경로 최적화',
    show: false
  });

  mainWindow.loadFile(path.join(__dirname, 'index.html'));

  // 개발 모드에서는 DevTools 열기
  if (isDev) {
    mainWindow.webContents.openDevTools();
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
    // Python 프로세스 종료
    if (pythonProcess) {
      pythonProcess.kill();
    }
  });
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// IPC 핸들러들

// 폴더 선택 다이얼로그
ipcMain.handle('select-folder', async (event, title) => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: title,
    properties: ['openDirectory']
  });

  if (!result.canceled && result.filePaths.length > 0) {
    return result.filePaths[0];
  }
  return null;
});

// 입력 폴더의 Excel 파일 목록 가져오기
ipcMain.handle('get-excel-files', async (event, folderPath) => {
  try {
    const files = fs.readdirSync(folderPath);
    const excelFiles = files.filter(file =>
      file.toLowerCase().endsWith('.xlsx') || file.toLowerCase().endsWith('.xls')
    );
    return excelFiles;
  } catch (error) {
    log.error('Excel 파일 목록 읽기 오류:', error);
    return [];
  }
});

// 배치 처리 시작
ipcMain.handle('start-batch-processing', async (event, { inputFolder, outputFolder, priority, apiKey }) => {
  return new Promise((resolve, reject) => {
    try {
      // Python 실행 경로 설정
      let pythonPath;
      let scriptPath;

      if (isDev) {
        // 개발 모드
        pythonPath = 'python';
        scriptPath = path.join(__dirname, '..', 'batch_process.py');
      } else {
        // 배포 모드
        pythonPath = 'python';
        scriptPath = path.join(process.resourcesPath, 'batch_process.py');
      }

      log.info(`Starting batch processing: ${inputFolder} -> ${outputFolder}`);

      const args = [
        scriptPath,
        '--input-folder', inputFolder,
        '--output-folder', outputFolder,
        '--priority', priority
      ];

      // API 키가 제공된 경우 추가
      if (apiKey) {
        args.push('--api-key', apiKey);
      }

      pythonProcess = spawn(pythonPath, args, {
        env: {
          ...process.env,
          PYTHONIOENCODING: 'utf-8',
          PYTHONLEGACYWINDOWSSTDIO: '1'
        },
        encoding: 'utf8'
      });

      let outputData = '';
      let errorData = '';

      pythonProcess.stdout.on('data', (data) => {
        const message = data.toString('utf8');
        outputData += message;
        log.info('Python stdout:', message);

        // 실시간 로그를 프론트엔드로 전송
        mainWindow.webContents.send('processing-log', {
          type: 'info',
          message: message.trim()
        });
      });

      pythonProcess.stderr.on('data', (data) => {
        const message = data.toString('utf8');
        errorData += message;
        log.error('Python stderr:', message);

        // 에러 로그도 프론트엔드로 전송
        mainWindow.webContents.send('processing-log', {
          type: 'error',
          message: message.trim()
        });
      });

      pythonProcess.on('close', (code) => {
        log.info(`Python process exited with code: ${code}`);
        pythonProcess = null;

        if (code === 0) {
          mainWindow.webContents.send('processing-complete', {
            success: true,
            message: '배치 처리가 성공적으로 완료되었습니다.'
          });
          resolve({ success: true, output: outputData });
        } else {
          mainWindow.webContents.send('processing-complete', {
            success: false,
            message: '배치 처리 중 오류가 발생했습니다.',
            error: errorData
          });
          reject(new Error(`Process failed with code ${code}: ${errorData}`));
        }
      });

      pythonProcess.on('error', (error) => {
        log.error('Python process error:', error);
        pythonProcess = null;

        mainWindow.webContents.send('processing-complete', {
          success: false,
          message: 'Python 프로세스 실행 중 오류가 발생했습니다.',
          error: error.message
        });
        reject(error);
      });

    } catch (error) {
      log.error('Batch processing start error:', error);
      reject(error);
    }
  });
});

// 처리 중단
ipcMain.handle('stop-processing', async () => {
  if (pythonProcess) {
    pythonProcess.kill();
    pythonProcess = null;

    mainWindow.webContents.send('processing-complete', {
      success: false,
      message: '사용자에 의해 처리가 중단되었습니다.'
    });

    return { success: true };
  }
  return { success: false, message: '실행 중인 프로세스가 없습니다.' };
});

// 에러 핸들링
process.on('uncaughtException', (error) => {
  log.error('Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  log.error('Unhandled Rejection at:', promise, 'reason:', reason);
});