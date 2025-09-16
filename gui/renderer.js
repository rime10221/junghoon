// DOM 요소들
const inputFolderInput = document.getElementById('inputFolder');
const outputFolderInput = document.getElementById('outputFolder');
const selectInputFolderBtn = document.getElementById('selectInputFolder');
const selectOutputFolderBtn = document.getElementById('selectOutputFolder');
const apiKeyInput = document.getElementById('apiKey');
const toggleApiKeyBtn = document.getElementById('toggleApiKey');
const prioritySelect = document.getElementById('priority');
const startProcessingBtn = document.getElementById('startProcessing');
const stopProcessingBtn = document.getElementById('stopProcessing');
const statusIndicator = document.getElementById('statusIndicator');
const currentFileDiv = document.getElementById('currentFile');
const progressFill = document.getElementById('progressFill');
const progressText = document.getElementById('progressText');
const logContainer = document.getElementById('logContainer');
const clearLogBtn = document.getElementById('clearLog');
const inputFilesDiv = document.getElementById('inputFiles');

// 상태 관리
let isProcessing = false;
let excelFiles = [];
let processedFiles = 0;

// 초기화
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    loadSavedApiKey();
    updateUIState();
    addLog('info', '애플리케이션이 시작되었습니다.');
});

// 이벤트 리스너 설정
function setupEventListeners() {
    // 폴더 선택 버튼들
    selectInputFolderBtn.addEventListener('click', () => selectFolder('input'));
    selectOutputFolderBtn.addEventListener('click', () => selectFolder('output'));

    // 처리 버튼들
    startProcessingBtn.addEventListener('click', startBatchProcessing);
    stopProcessingBtn.addEventListener('click', stopProcessing);

    // 로그 지우기 버튼
    clearLogBtn.addEventListener('click', clearLog);

    // API 키 관련
    toggleApiKeyBtn.addEventListener('click', toggleApiKeyVisibility);
    apiKeyInput.addEventListener('input', saveApiKey);

    // 폴더 입력 필드 변경 감지
    inputFolderInput.addEventListener('input', updateUIState);
    outputFolderInput.addEventListener('input', updateUIState);

    // Electron IPC 이벤트 리스너들
    window.electronAPI.onProcessingLog((data) => {
        handleProcessingLog(data);
    });

    window.electronAPI.onProcessingComplete((data) => {
        handleProcessingComplete(data);
    });
}

// 폴더 선택
async function selectFolder(type) {
    try {
        const title = type === 'input' ? '입력 폴더 선택 (Excel 파일들)' : '출력 폴더 선택';
        const folderPath = await window.electronAPI.selectFolder(title);

        if (folderPath) {
            if (type === 'input') {
                inputFolderInput.value = folderPath;
                await loadExcelFiles(folderPath);
                addLog('info', `입력 폴더 선택: ${folderPath}`);
            } else {
                outputFolderInput.value = folderPath;
                addLog('info', `출력 폴더 선택: ${folderPath}`);
            }
            updateUIState();
        }
    } catch (error) {
        addLog('error', `폴더 선택 오류: ${error.message}`);
        showNotification('폴더 선택 중 오류가 발생했습니다.', 'error');
    }
}

// Excel 파일 목록 로드
async function loadExcelFiles(folderPath) {
    try {
        excelFiles = await window.electronAPI.getExcelFiles(folderPath);
        displayExcelFiles();
    } catch (error) {
        addLog('error', `Excel 파일 목록 로드 오류: ${error.message}`);
        excelFiles = [];
        displayExcelFiles();
    }
}

// Excel 파일 목록 표시
function displayExcelFiles() {
    if (excelFiles.length === 0) {
        inputFilesDiv.innerHTML = '<div style="color: #999;">선택된 폴더에 Excel 파일이 없습니다.</div>';
        inputFilesDiv.classList.remove('has-files');
    } else {
        inputFilesDiv.innerHTML = excelFiles.map(file =>
            `<div class="file-item">📊 ${file}</div>`
        ).join('');
        inputFilesDiv.classList.add('has-files');
        addLog('info', `${excelFiles.length}개의 Excel 파일을 발견했습니다.`);
    }
}

// UI 상태 업데이트
function updateUIState() {
    const hasInputFolder = inputFolderInput.value.trim() !== '';
    const hasOutputFolder = outputFolderInput.value.trim() !== '';
    const hasExcelFiles = excelFiles.length > 0;

    startProcessingBtn.disabled = !hasInputFolder || !hasOutputFolder || !hasExcelFiles || isProcessing;
    stopProcessingBtn.disabled = !isProcessing;

    selectInputFolderBtn.disabled = isProcessing;
    selectOutputFolderBtn.disabled = isProcessing;
    prioritySelect.disabled = isProcessing;
}

// 배치 처리 시작
async function startBatchProcessing() {
    try {
        isProcessing = true;
        processedFiles = 0; // 카운터 초기화
        updateUIState();
        updateStatus('processing', '처리 중');
        updateProgress(0); // 진행률 초기화

        addLog('info', '='.repeat(50));
        addLog('info', '배치 처리를 시작합니다...');
        addLog('info', `입력 폴더: ${inputFolderInput.value}`);
        addLog('info', `출력 폴더: ${outputFolderInput.value}`);
        addLog('info', `처리할 파일 수: ${excelFiles.length}개`);
        addLog('info', `최적화 우선순위: ${prioritySelect.value}`);
        addLog('info', '='.repeat(50));

        const config = {
            inputFolder: inputFolderInput.value,
            outputFolder: outputFolderInput.value,
            priority: prioritySelect.value,
            apiKey: apiKeyInput.value.trim() || null
        };

        await window.electronAPI.startBatchProcessing(config);
    } catch (error) {
        addLog('error', `배치 처리 시작 오류: ${error.message}`);
        handleProcessingComplete({
            success: false,
            message: '배치 처리 시작 중 오류가 발생했습니다.',
            error: error.message
        });
    }
}

// 처리 중단
async function stopProcessing() {
    try {
        addLog('warning', '처리 중단 요청...');
        await window.electronAPI.stopProcessing();
    } catch (error) {
        addLog('error', `처리 중단 오류: ${error.message}`);
    }
}

// 처리 로그 핸들링
function handleProcessingLog(data) {
    const { type, message } = data;

    // 현재 처리 중인 파일 추출
    if (message.includes('시작:') || message.includes('📂')) {
        const fileName = extractFileName(message);
        if (fileName) {
            updateCurrentFile(`처리 중: ${fileName}`);
        }
    }

    // 파일별 완료 상태 추적
    if (message.includes('✅ 성공:') && message.includes('완료)')) {
        // "✅ 성공: filename.xlsx (3/5 완료)" 패턴에서 진행률 추출
        const progressMatch = message.match(/\((\d+)\/(\d+) 완료\)/);
        if (progressMatch) {
            const completed = parseInt(progressMatch[1]);
            const total = parseInt(progressMatch[2]);
            processedFiles = completed;
            updateProgress();
        }
    }

    // 전체 진행률 메시지 처리
    if (message.includes('📊 전체 진행률:')) {
        const percentMatch = message.match(/(\d+\.?\d*)%/);
        if (percentMatch) {
            const percent = parseFloat(percentMatch[1]);
            updateProgress(percent);
        }
    }

    addLog(type, message);
}

// 처리 완료 핸들링
function handleProcessingComplete(data) {
    isProcessing = false;
    updateUIState();

    if (data.success) {
        updateStatus('success', '완료');
        updateCurrentFile('모든 파일 처리 완료');
        updateProgress(100);
        addLog('success', data.message);
        showNotification('배치 처리가 성공적으로 완료되었습니다!', 'success');
    } else {
        updateStatus('error', '오류');
        updateCurrentFile('처리 중단됨');
        addLog('error', data.message);
        if (data.error) {
            addLog('error', `상세 오류: ${data.error}`);
        }
        showNotification('배치 처리 중 오류가 발생했습니다.', 'error');
    }

    addLog('info', '='.repeat(50));
}

// 상태 업데이트
function updateStatus(status, text) {
    statusIndicator.className = `status-indicator status-${status}`;
    statusIndicator.textContent = text;
}

// 현재 파일 업데이트
function updateCurrentFile(text) {
    currentFileDiv.textContent = text;
}

// 진행률 업데이트
function updateProgress(percentage = null) {
    if (percentage === null) {
        percentage = excelFiles.length > 0 ? Math.min((processedFiles / excelFiles.length) * 100, 100) : 0;
    }

    // 100%를 초과하지 않도록 제한
    percentage = Math.min(percentage, 100);

    progressFill.style.width = `${percentage}%`;
    progressText.textContent = `${Math.round(percentage)}% (${processedFiles}/${excelFiles.length})`;
}

// 로그 추가
function addLog(type, message) {
    const now = new Date();
    const timestamp = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    const logEntry = document.createElement('div');
    logEntry.className = `log-entry ${type}`;

    // 텍스트를 안전하게 처리하고 UTF-8 인코딩 보장
    const safeMessage = decodeMessage(message);

    logEntry.innerHTML = `
        <span class="timestamp">[${timestamp}]</span>
        <span class="message">${escapeHtml(safeMessage)}</span>
    `;

    logContainer.appendChild(logEntry);
    logContainer.scrollTop = logContainer.scrollHeight;

    // 로그 항목이 너무 많으면 오래된 것부터 제거
    const maxLogEntries = 1000;
    while (logContainer.children.length > maxLogEntries) {
        logContainer.removeChild(logContainer.firstChild);
    }
}

// 로그 지우기
function clearLog() {
    logContainer.innerHTML = '';
    addLog('info', '로그가 지워졌습니다.');
}

// 알림 표시
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;

    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in forwards';
        setTimeout(() => {
            document.body.removeChild(notification);
        }, 300);
    }, 3000);
}

// 유틸리티 함수들
function extractFileName(message) {
    // 메시지에서 파일명 추출
    const patterns = [
        /시작:\s*(.+\.xlsx?)/i,
        /처리 중:\s*(.+\.xlsx?)/i,
        /Processing:\s*(.+\.xlsx?)/i,
        /파일:\s*(.+\.xlsx?)/i,
        /성공:\s*(.+\.xlsx?)/i,
        /실패:\s*(.+\.xlsx?)/i
    ];

    for (const pattern of patterns) {
        const match = message.match(pattern);
        if (match) {
            return match[1].split(' ')[0]; // 파일명만 추출 (괄호 제거)
        }
    }
    return null;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function decodeMessage(message) {
    try {
        // 메시지가 이미 문자열이면 그대로 반환
        if (typeof message === 'string') {
            // UTF-8 바이트 시퀀스가 잘못 해석된 경우 복구 시도
            if (message.includes('�') || message.includes('\\x')) {
                // Python에서 오는 인코딩 문제 해결
                return message
                    .replace(/\\n/g, '\n')
                    .replace(/\\r/g, '\r')
                    .replace(/\\t/g, '\t');
            }
            return message;
        }

        // Buffer나 ArrayBuffer인 경우 UTF-8로 디코딩
        if (message instanceof ArrayBuffer || message instanceof Uint8Array) {
            const decoder = new TextDecoder('utf-8');
            return decoder.decode(message);
        }

        return String(message);
    } catch (error) {
        console.warn('Message decoding failed:', error);
        return String(message);
    }
}

// API 키 관련 함수들
function loadSavedApiKey() {
    try {
        const savedApiKey = localStorage.getItem('kakao_api_key');
        if (savedApiKey) {
            apiKeyInput.value = savedApiKey;
            addLog('info', 'API 키가 로드되었습니다.');
        }
    } catch (error) {
        console.warn('API 키 로드 실패:', error);
    }
}

function saveApiKey() {
    try {
        const apiKey = apiKeyInput.value.trim();
        if (apiKey) {
            localStorage.setItem('kakao_api_key', apiKey);
        } else {
            localStorage.removeItem('kakao_api_key');
        }
    } catch (error) {
        console.warn('API 키 저장 실패:', error);
    }
}

function toggleApiKeyVisibility() {
    const isPassword = apiKeyInput.type === 'password';
    apiKeyInput.type = isPassword ? 'text' : 'password';
    toggleApiKeyBtn.textContent = isPassword ? '🙈' : '👁️';
}

// CSS 애니메이션 추가
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);