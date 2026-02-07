/**
 * Chess Game WebSocket Client - Enhanced Version
 * Improvements:
 * - Automatic reconnection with exponential backoff
 * - Heartbeat/keepalive mechanism
 * - Better error handling and recovery
 * - Connection state management
 * - Message queue for offline support
 * 
 * Author: Renier Barnard (renier52147@gmail.com/ renierb@axxess.co.za)
 */

// ═══════════════════════════════════════════════════════════════════════════
// Global State
// ═══════════════════════════════════════════════════════════════════════════

let websocket = null;
let board = null;
let gameState = {
  gameId: null,
  playerColor: null,
  playerUsername: null,
  opponentUsername: null,
  currentTurn: 'white',
  fen: 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1',
  legalMoves: [],
  gameStatus: 'waiting',
  winner: null,
  moveHistory: []
};

// Connection state management
const connectionState = {
  isConnected: false,
  reconnectAttempts: 0,
  maxReconnectAttempts: 5,
  reconnectDelay: 1000, // Start with 1 second
  maxReconnectDelay: 30000, // Max 30 seconds
  heartbeatInterval: null,
  heartbeatTimeout: null,
  messageQueue: [],
  intentionalDisconnect: false
};

// ═══════════════════════════════════════════════════════════════════════════
// WebSocket Connection Management
// ═══════════════════════════════════════════════════════════════════════════

function connectWebSocket() {
  // Don't reconnect if intentionally disconnected
  if (connectionState.intentionalDisconnect) {
    console.log('Skipping reconnect - intentional disconnect');
    return;
  }

  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws`;
  
  console.log('Connecting to WebSocket:', wsUrl);
  updateStatus('Connecting to game server...', 'info');
  
  try {
    websocket = new WebSocket(wsUrl);
    
    websocket.onopen = handleWebSocketOpen;
    websocket.onmessage = handleWebSocketMessage;
    websocket.onerror = handleWebSocketError;
    websocket.onclose = handleWebSocketClose;
  } catch (error) {
    console.error('Failed to create WebSocket:', error);
    handleReconnect();
  }
}

function handleWebSocketOpen(event) {
  console.log('WebSocket connected');
  connectionState.isConnected = true;
  connectionState.reconnectAttempts = 0;
  connectionState.reconnectDelay = 1000; // Reset delay
  
  updateStatus('Connected - waiting for game to start...', 'success');
  
  // Send handshake
  sendWebSocketMessage({
    type: 'handshake',
    message: 'Client ready'
  });
  
  // Start heartbeat
  startHeartbeat();
  
  // Send any queued messages
  flushMessageQueue();
}

function handleWebSocketMessage(event) {
  // Reset heartbeat timeout on any message
  resetHeartbeatTimeout();
  
  try {
    const message = JSON.parse(event.data);
    console.log('Received:', message);
    
    switch (message.type) {
      case 'handshake_ack':
        console.log('Server acknowledged handshake');
        break;
        
      case 'game_start':
        handleGameStart(message);
        break;
        
      case 'game_state':
        // Legacy message type - treat as game start
        handleGameStart(message);
        break;
        
      case 'move_update':
        handleMoveUpdate(message);
        break;
        
      case 'game_over':
        handleGameOver(message);
        break;
        
      case 'game_end':
        // Legacy message type
        handleGameOver(message);
        break;
        
      case 'opponent_disconnected':
        handleOpponentDisconnected(message);
        break;
        
      case 'draw_offered':
        handleDrawOffer(message);
        break;
        
      case 'error':
        handleServerError(message);
        break;
        
      case 'ping':
        sendWebSocketMessage({ type: 'pong' });
        break;
        
      case 'pong':
        // Server responded to our ping
        console.log('Received pong from server');
        break;
        
      default:
        console.warn('Unknown message type:', message.type);
    }
  } catch (error) {
    console.error('Error parsing message:', error);
  }
}

function handleWebSocketError(event) {
  console.error('WebSocket error:', event);
  updateStatus('Connection error', 'error');
  connectionState.isConnected = false;
}

function handleWebSocketClose(event) {
  console.log('WebSocket closed:', event.code, event.reason);
  connectionState.isConnected = false;
  
  // Stop heartbeat
  stopHeartbeat();
  
  // Don't reconnect if intentionally closed
  if (connectionState.intentionalDisconnect) {
    updateStatus('Disconnected from server');
    return;
  }
  
  // Handle different close codes
  if (event.code === 1000 || event.code === 1001) {
    // Normal closure
    updateStatus('Connection closed');
  } else if (gameState.gameStatus === 'ongoing') {
    // Unexpected closure during game - attempt reconnect
    updateStatus('Connection lost. Reconnecting...', 'error');
    handleReconnect();
  } else {
    // Unexpected closure, but no game in progress
    updateStatus('Disconnected from server. Click to reconnect.', 'error');
    // Show reconnect button if available
    showReconnectOption();
  }
}

function handleReconnect() {
  if (connectionState.reconnectAttempts >= connectionState.maxReconnectAttempts) {
    updateStatus('Failed to reconnect. Please refresh the page.', 'error');
    showReconnectOption();
    return;
  }
  
  connectionState.reconnectAttempts++;
  
  // Exponential backoff
  const delay = Math.min(
    connectionState.reconnectDelay * Math.pow(2, connectionState.reconnectAttempts - 1),
    connectionState.maxReconnectDelay
  );
  
  console.log(`Reconnecting in ${delay}ms (attempt ${connectionState.reconnectAttempts}/${connectionState.maxReconnectAttempts})`);
  updateStatus(`Reconnecting in ${Math.ceil(delay/1000)}s... (${connectionState.reconnectAttempts}/${connectionState.maxReconnectAttempts})`, 'error');
  
  setTimeout(() => {
    connectWebSocket();
  }, delay);
}

function showReconnectOption() {
  // Add a manual reconnect button if it doesn't exist
  const statusElement = document.getElementById('game-status');
  if (statusElement && !document.getElementById('manual-reconnect-btn')) {
    const reconnectBtn = document.createElement('button');
    reconnectBtn.id = 'manual-reconnect-btn';
    reconnectBtn.className = 'button';
    reconnectBtn.textContent = 'Reconnect';
    reconnectBtn.onclick = () => {
      reconnectBtn.remove();
      connectionState.reconnectAttempts = 0;
      connectionState.intentionalDisconnect = false;
      connectWebSocket();
    };
    statusElement.parentNode.insertBefore(reconnectBtn, statusElement.nextSibling);
  }
}

function sendWebSocketMessage(message) {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.send(JSON.stringify(message));
    console.log('Sent:', message);
  } else {
    console.warn('WebSocket not connected, queuing message:', message);
    
    // Queue important messages (moves, etc.)
    if (['move', 'resign', 'offer_draw', 'draw_accept'].includes(message.type)) {
      connectionState.messageQueue.push(message);
    }
    
    updateStatus('Not connected to server - message queued', 'error');
  }
}

function flushMessageQueue() {
  if (connectionState.messageQueue.length === 0) return;
  
  console.log(`Flushing ${connectionState.messageQueue.length} queued messages`);
  
  while (connectionState.messageQueue.length > 0) {
    const message = connectionState.messageQueue.shift();
    sendWebSocketMessage(message);
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Heartbeat / Keepalive
// ═══════════════════════════════════════════════════════════════════════════

function startHeartbeat() {
  // Send ping every 25 seconds
  connectionState.heartbeatInterval = setInterval(() => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      sendWebSocketMessage({ type: 'ping' });
      
      // Set timeout for pong response
      connectionState.heartbeatTimeout = setTimeout(() => {
        console.warn('No pong received - connection may be dead');
        // Close and trigger reconnect
        if (websocket) {
          websocket.close();
        }
      }, 10000); // Wait 10 seconds for pong
    }
  }, 25000);
}

function stopHeartbeat() {
  if (connectionState.heartbeatInterval) {
    clearInterval(connectionState.heartbeatInterval);
    connectionState.heartbeatInterval = null;
  }
  
  if (connectionState.heartbeatTimeout) {
    clearTimeout(connectionState.heartbeatTimeout);
    connectionState.heartbeatTimeout = null;
  }
}

function resetHeartbeatTimeout() {
  if (connectionState.heartbeatTimeout) {
    clearTimeout(connectionState.heartbeatTimeout);
    connectionState.heartbeatTimeout = null;
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Game Event Handlers
// ═══════════════════════════════════════════════════════════════════════════

function handleGameStart(message) {
  // Handle both message formats
  gameState.gameId = message.game_id;
  gameState.playerColor = message.your_color;
  gameState.playerUsername = message.your_username;
  gameState.opponentUsername = message.opponent_username;
  gameState.currentTurn = message.current_turn || message.turn || 'white';
  gameState.fen = message.fen;
  gameState.legalMoves = message.legal_moves || [];
  gameState.gameStatus = 'ongoing';
  gameState.moveHistory = message.move_history || [];
  
  // Update UI
  updatePlayerInfo();
  updateStatus(
    gameState.playerColor === gameState.currentTurn 
      ? 'Your turn!' 
      : `${gameState.opponentUsername}'s turn`
  );
  
  // Initialize board
  if (!board) {
    initializeChessboard();
  } else {
    board.position(gameState.fen);
    board.orientation(gameState.playerColor);
  }
  
  // Update move history if provided
  if (gameState.moveHistory.length > 0) {
    updateMoveHistory();
  }
  
  console.log('Game started:', gameState);
}

function handleMoveUpdate(message) {
  gameState.fen = message.fen;
  gameState.currentTurn = message.next_turn || message.turn;
  gameState.legalMoves = message.legal_moves || [];
  
  // Update move history if provided
  if (message.move_history) {
    gameState.moveHistory = message.move_history;
  } else if (message.last_move) {
    gameState.moveHistory.push(message.last_move);
  }
  
  // Update board
  board.position(gameState.fen);
  
  // Update move history display
  updateMoveHistory();
  
  // Update status
  const isMyTurn = gameState.playerColor === gameState.currentTurn;
  updateStatus(
    isMyTurn 
      ? 'Your turn!' 
      : `${gameState.opponentUsername}'s turn`
  );
  
  console.log('Move update:', message);
}

function handleGameOver(message) {
  gameState.gameStatus = 'finished';
  gameState.winner = message.winner || message.result;
  
  let statusMessage = '';
  const winner = message.winner || message.result;
  
  if (winner === 'draw' || winner === 'stalemate') {
    statusMessage = 'Game ended in a draw';
  } else if (winner === gameState.playerColor) {
    statusMessage = 'You won! 🎉';
  } else {
    statusMessage = 'You lost';
  }
  
  if (message.reason) {
    statusMessage += ` (${message.reason})`;
  }
  
  updateStatus(statusMessage, winner === gameState.playerColor ? 'success' : 'error');
  
  // Show ELO changes if provided
  if (message.elo_changes) {
    const myChange = message.elo_changes[gameState.playerColor];
    if (myChange) {
      statusMessage += ` | ELO: ${myChange > 0 ? '+' : ''}${myChange}`;
      updateStatus(statusMessage, winner === gameState.playerColor ? 'success' : 'error');
    }
  }
  
  // Disable board
  if (board) {
    board.draggable = false;
  }
  
  // Show game over dialog
  showGameOverDialog(message);
  
  console.log('Game over:', message);
}

function handleOpponentDisconnected(message) {
  updateStatus('Opponent disconnected. You win by default!', 'success');
  gameState.gameStatus = 'finished';
  gameState.winner = gameState.playerColor;
  
  if (board) {
    board.draggable = false;
  }
  
  showGameOverDialog({
    winner: gameState.playerColor,
    reason: 'opponent disconnected'
  });
}

function handleDrawOffer(message) {
  const accept = confirm(`${message.message || 'Opponent offers a draw'}. Do you accept?`);
  if (accept) {
    sendWebSocketMessage({ type: 'draw_accept' });
  }
}

function handleServerError(message) {
  console.error('Server error:', message);
  updateStatus(message.message || 'Server error occurred', 'error');
}

// ═══════════════════════════════════════════════════════════════════════════
// Chessboard Integration
// ═══════════════════════════════════════════════════════════════════════════

function initializeChessboard() {
  const config = {
    draggable: true,
    position: gameState.fen,
    orientation: gameState.playerColor,
    pieceTheme: pieceTheme,
    onDragStart: onDragStart,
    onDrop: onDrop,
    onSnapEnd: onSnapEnd
  };
  
  board = Chessboard('board1', config);
  console.log('Chessboard initialized');
}

function pieceTheme(piece) {
  return 'static/game/game_depends/img/chesspieces/' + piece + '.png';
}

function onDragStart(source, piece, position, orientation) {
  if (gameState.gameStatus !== 'ongoing') return false;
  if (gameState.currentTurn !== gameState.playerColor) return false;
  
  const pieceColor = piece.charAt(0) === 'w' ? 'white' : 'black';
  if (pieceColor !== gameState.playerColor) return false;
  
  return true;
}

function onDrop(source, target) {
  // Construct move in UCI notation (e2e4)
  const move = source + target;
  
  // Check if move is legal
  if (!isMoveLegal(move, source, target)) {
    console.log('Illegal move:', move);
    return 'snapback';
  }
  
  // Send move to server
  sendMove(source, target);
}

function onSnapEnd() {
  board.position(gameState.fen);
}

function isMoveLegal(move, from, to) {
  // Check against legal moves list
  // Legal moves might be in format: e2e4, e2-e4, or e2e4q (with promotion)
  return gameState.legalMoves.some(legalMove => {
    const normalized = legalMove.replace('-', '');
    const moveBase = move.substring(0, 4);
    return normalized === move || normalized.startsWith(moveBase);
  });
}

function sendMove(from, to) {
  sendWebSocketMessage({
    type: 'move',
    from: from,
    to: to,
    move: from + to  // Also send UCI format
  });
  
  console.log('Move sent:', from, to);
}

// ═══════════════════════════════════════════════════════════════════════════
// UI Updates
// ═══════════════════════════════════════════════════════════════════════════

function updateStatus(message, type = 'info') {
  const statusElement = document.getElementById('game-status');
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = `game-status ${type}`;
  }
  console.log(`Status [${type}]:`, message);
}

function updatePlayerInfo() {
  const playerInfoElement = document.getElementById('player-info');
  if (playerInfoElement) {
    const opponentColor = gameState.playerColor === 'white' ? 'black' : 'white';
    playerInfoElement.innerHTML = `
      <div class="player you">
        <span class="color-indicator ${gameState.playerColor}"></span>
        <span class="player-name">${gameState.playerUsername} (You)</span>
        <span class="player-color">${capitalize(gameState.playerColor)}</span>
      </div>
      <div class="vs">VS</div>
      <div class="player opponent">
        <span class="color-indicator ${opponentColor}"></span>
        <span class="player-name">${gameState.opponentUsername}</span>
        <span class="player-color">${capitalize(opponentColor)}</span>
      </div>
    `;
  }
}

function updateMoveHistory() {
  const historyElement = document.getElementById('move-history');
  if (!historyElement) return;
  
  if (gameState.moveHistory.length === 0) {
    historyElement.innerHTML = '<p class="no-moves">No moves yet</p>';
    return;
  }
  
  let html = '<ol class="move-list">';
  for (let i = 0; i < gameState.moveHistory.length; i += 2) {
    const moveNumber = Math.floor(i / 2) + 1;
    const whiteMove = formatMove(gameState.moveHistory[i]);
    const blackMove = gameState.moveHistory[i + 1] ? formatMove(gameState.moveHistory[i + 1]) : '';
    
    html += `<li class="move-pair">
      <span class="move-number">${moveNumber}.</span>
      <span class="move white-move">${whiteMove}</span>
      ${blackMove ? `<span class="move black-move">${blackMove}</span>` : ''}
    </li>`;
  }
  html += '</ol>';
  
  historyElement.innerHTML = html;
  historyElement.scrollTop = historyElement.scrollHeight;
}

function formatMove(move) {
  // Remove hyphens for display (e2-e4 -> e2e4)
  return move.replace('-', '');
}

function showGameOverDialog(message) {
  const dialog = document.getElementById('game-over-dialog');
  if (!dialog) return;
  
  const titleElement = dialog.querySelector('.dialog-title');
  const messageElement = dialog.querySelector('.dialog-message');
  
  const winner = message.winner || message.result;
  
  if (winner === 'draw' || winner === 'stalemate') {
    titleElement.textContent = 'Draw';
    messageElement.textContent = message.reason || 'Game ended in a draw';
  } else if (winner === gameState.playerColor) {
    titleElement.textContent = 'Victory!';
    messageElement.textContent = message.reason || 'You won the game!';
  } else {
    titleElement.textContent = 'Defeat';
    messageElement.textContent = message.reason || 'You lost the game';
  }
  
  // Add ELO info if available
  if (message.elo_changes && message.elo_changes[gameState.playerColor]) {
    const change = message.elo_changes[gameState.playerColor];
    messageElement.textContent += `\n\nELO Change: ${change > 0 ? '+' : ''}${change}`;
  }
  
  dialog.style.display = 'flex';
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ═══════════════════════════════════════════════════════════════════════════
// Button Handlers
// ═══════════════════════════════════════════════════════════════════════════

function handleResign() {
  if (gameState.gameStatus !== 'ongoing') return;
  
  const confirmed = confirm('Are you sure you want to resign?');
  if (confirmed) {
    sendWebSocketMessage({ type: 'resign' });
  }
}

function handleOfferDraw() {
  if (gameState.gameStatus !== 'ongoing') return;
  
  sendWebSocketMessage({ type: 'offer_draw' });
  updateStatus('Draw offer sent to opponent');
}

function handleNewGame() {
  // Mark as intentional disconnect before navigating
  connectionState.intentionalDisconnect = true;
  if (websocket) {
    websocket.close();
  }
  window.location.href = '/home';
}

function closeGameOverDialog() {
  const dialog = document.getElementById('game-over-dialog');
  if (dialog) {
    dialog.style.display = 'none';
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Initialization
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
  console.log('Game page loaded');
  
  // Connect to WebSocket
  connectWebSocket();
  
  // Set up button event listeners
  const resignBtn = document.getElementById('resign-btn');
  if (resignBtn) {
    resignBtn.addEventListener('click', handleResign);
  }
  
  const drawBtn = document.getElementById('draw-btn');
  if (drawBtn) {
    drawBtn.addEventListener('click', handleOfferDraw);
  }
  
  const newGameBtn = document.getElementById('new-game-btn');
  if (newGameBtn) {
    newGameBtn.addEventListener('click', handleNewGame);
  }
  
  const closeDialogBtn = document.getElementById('close-dialog-btn');
  if (closeDialogBtn) {
    closeDialogBtn.addEventListener('click', closeGameOverDialog);
  }
  
  // Close dialog on outside click
  const gameOverDialog = document.getElementById('game-over-dialog');
  if (gameOverDialog) {
    gameOverDialog.addEventListener('click', (e) => {
      if (e.target === gameOverDialog) {
        closeGameOverDialog();
      }
    });
  }
  
  console.log('Game initialization complete');
});

// Handle page unload
window.addEventListener('beforeunload', () => {
  connectionState.intentionalDisconnect = true;
  stopHeartbeat();
  if (websocket) {
    websocket.close();
  }
});

// Handle page visibility changes (tab switching)
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    console.log('Page hidden - maintaining connection');
  } else {
    console.log('Page visible - checking connection');
    // Check if connection is still alive when user returns
    if (!connectionState.isConnected && gameState.gameStatus === 'ongoing') {
      console.log('Reconnecting after page became visible');
      connectWebSocket();
    }
  }
});
