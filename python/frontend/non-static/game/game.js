/**
 * Chess Game WebSocket Client - Enhanced Version with Custom Dialogs
 * Improvements:
 * - Automatic reconnection with exponential backoff
 * - Heartbeat/keepalive mechanism
 * - Better error handling and recovery
 * - Connection state management
 * - Message queue for offline support
 * - Custom dialog system instead of confirm()
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
  currentTurn: "white",
  fen: "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
  legalMoves: [],
  gameStatus: "waiting",
  winner: null,
  moveHistory: [],
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
  intentionalDisconnect: false,
};

// ═══════════════════════════════════════════════════════════════════════════
// Custom Dialog System
// ═══════════════════════════════════════════════════════════════════════════

class CustomDialogManager {
  constructor() {
    this.drawOfferDialog = document.getElementById('draw-offer-dialog');
    this.drawSentDialog = document.getElementById('draw-sent-dialog');
    this.pendingDrawOffer = false;
    this.drawOfferSent = false;
  }

  // Show draw offer received from opponent
  showDrawOfferReceived() {
    if (this.pendingDrawOffer) return;
    this.pendingDrawOffer = true;
    
    if (this.drawOfferDialog) {
      this.drawOfferDialog.style.display = 'flex';
    }
  }

  // Show draw offer sent confirmation
  showDrawOfferSent() {
    if (this.drawOfferSent) return;
    this.drawOfferSent = true;
    
    if (this.drawSentDialog) {
      this.drawSentDialog.style.display = 'flex';
    }
    
    // Disable the draw button
    const drawBtn = document.getElementById('draw-btn');
    if (drawBtn) {
      drawBtn.disabled = true;
      drawBtn.textContent = 'Draw Offered';
    }
  }

  // Hide draw offer dialogs
  hideDrawOfferDialog() {
    if (this.drawOfferDialog) {
      this.drawOfferDialog.style.display = 'none';
    }
    this.pendingDrawOffer = false;
  }

  hideDrawSentDialog() {
    if (this.drawSentDialog) {
      this.drawSentDialog.style.display = 'none';
    }
    this.drawOfferSent = false;
    
    // Re-enable the draw button
    const drawBtn = document.getElementById('draw-btn');
    if (drawBtn) {
      drawBtn.disabled = false;
      drawBtn.textContent = 'Offer Draw';
    }
  }

  // Accept draw
  acceptDraw() {
    this.hideDrawOfferDialog();
    sendWebSocketMessage({
      type: 'accept_draw'
    });
  }

  // Decline draw
  declineDraw() {
    this.hideDrawOfferDialog();
    sendWebSocketMessage({
      type: 'decline_draw'
    });
    updateStatus('Draw offer declined', 'info');
  }

  // Cancel draw offer (by sender)
  cancelDrawOffer() {
    this.hideDrawSentDialog();
    sendWebSocketMessage({
      type: 'cancel_draw_offer'
    });
  }

  // Handle draw offer being declined
  onDrawDeclined() {
    this.hideDrawSentDialog();
    updateStatus('Your draw offer was declined', 'info');
  }
}

// Initialize dialog manager
let dialogManager;

// Custom confirm dialog (replaces browser confirm())
function customConfirm(message, onConfirm, onCancel) {
  // Create a custom confirmation dialog
  const dialog = document.createElement('div');
  dialog.className = 'modal';
  dialog.style.display = 'flex';
  
  dialog.innerHTML = `
    <div class="modal-content">
      <h2 class="dialog-title">Confirm Action</h2>
      <p class="dialog-message">${message}</p>
      <div class="button-row">
        <button class="button button-secondary" id="custom-cancel-btn">Cancel</button>
        <button class="button button-danger" id="custom-confirm-btn">Confirm</button>
      </div>
    </div>
  `;
  
  document.body.appendChild(dialog);
  
  const confirmBtn = dialog.querySelector('#custom-confirm-btn');
  const cancelBtn = dialog.querySelector('#custom-cancel-btn');
  
  const cleanup = () => {
    dialog.remove();
  };
  
  confirmBtn.addEventListener('click', () => {
    cleanup();
    if (onConfirm) onConfirm();
  });
  
  cancelBtn.addEventListener('click', () => {
    cleanup();
    if (onCancel) onCancel();
  });
  
  // Close on outside click
  dialog.addEventListener('click', (e) => {
    if (e.target === dialog) {
      cleanup();
      if (onCancel) onCancel();
    }
  });
}

// ═══════════════════════════════════════════════════════════════════════════
// WebSocket Connection Management
// ═══════════════════════════════════════════════════════════════════════════

function connectWebSocket() {
  // Don't reconnect if intentionally disconnected
  if (connectionState.intentionalDisconnect) {
    console.log("Skipping reconnect - intentional disconnect");
    return;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const wsUrl = `${protocol}//${window.location.host}/ws`;

  console.log("Connecting to WebSocket:", wsUrl);
  updateStatus("Connecting to game server...", "info");

  try {
    websocket = new WebSocket(wsUrl);

    websocket.onopen = handleWebSocketOpen;
    websocket.onmessage = handleWebSocketMessage;
    websocket.onerror = handleWebSocketError;
    websocket.onclose = handleWebSocketClose;
  } catch (error) {
    console.error("Failed to create WebSocket:", error);
    handleReconnect();
  }
}

function handleWebSocketOpen(event) {
  console.log("WebSocket connected");
  connectionState.isConnected = true;
  connectionState.reconnectAttempts = 0;
  connectionState.reconnectDelay = 1000; // Reset delay

  updateStatus("Connected - waiting for game to start...", "success");

  // Send handshake
  sendWebSocketMessage({
    type: "handshake",
    message: "Client ready",
  });

  // Start heartbeat
  startHeartbeat();

  // Send any queued messages
  flushMessageQueue();
}

function handleWebSocketMessage(event) {
  // Reset heartbeat timeout on any message
  resetHeartbeatTimeout();

  // Check if message is JSON or plain text
  const data = event.data;

  // Try to detect if it's JSON (starts with { or [)
  const looksLikeJSON =
    typeof data === "string" &&
    (data.trim().startsWith("{") || data.trim().startsWith("["));

  if (!looksLikeJSON) {
    // Plain text message from server (e.g., "Hello from server")
    console.log("Server message (text):", data);
    return;
  }

  try {
    const message = JSON.parse(data);
    console.log("Received:", message);

    switch (message.type) {
      case "handshake_ack":
        console.log("Server acknowledged handshake");
        break;

      case "game_start":
        handleGameStart(message);
        break;

      case "game_state":
        // Legacy message type - treat as game start
        handleGameStart(message);
        break;

      case "move_update":
        handleMoveUpdate(message);
        break;

      case "game_over":
        handleGameOver(message);
        break;

      case "game_end":
        // Legacy message type
        handleGameOver(message);
        break;

      case "opponent_disconnected":
        handleOpponentDisconnected(message);
        break;

      case "draw_offer":
      case "draw_offered":
        handleDrawOffer(message);
        break;

      case "draw_accepted":
        handleDrawAccepted(message);
        break;

      case "draw_declined":
        handleDrawDeclined(message);
        break;

      case "error":
        handleServerError(message);
        break;

      case "ping":
        sendWebSocketMessage({ type: "pong" });
        break;

      case "pong":
        // Server responded to our ping
        console.log("Received pong from server");
        break;

      default:
        console.warn("Unknown message type:", message.type);
    }
  } catch (error) {
    console.error("Error parsing JSON message:", error);
    console.error("Raw message data:", data);
  }
}

function handleWebSocketError(event) {
  console.error("WebSocket error:", event);
  updateStatus("Connection error", "error");
  connectionState.isConnected = false;
}

function handleWebSocketClose(event) {
  console.log("WebSocket closed:", event.code, event.reason);
  connectionState.isConnected = false;

  // Stop heartbeat
  stopHeartbeat();

  // Don't reconnect if intentionally closed
  if (connectionState.intentionalDisconnect) {
    updateStatus("Disconnected from server");
    return;
  }

  // Handle different close codes
  if (event.code === 1000 || event.code === 1001) {
    // Normal closure
    updateStatus("Connection closed");
  } else if (gameState.gameStatus === "ongoing") {
    // Unexpected closure during game - attempt reconnect
    updateStatus("Connection lost. Reconnecting...", "error");
    handleReconnect();
  } else {
    // Unexpected closure, but no game in progress
    updateStatus("Disconnected from server. Click to reconnect.", "error");
    // Show reconnect button if available
    showReconnectOption();
  }
}

function handleReconnect() {
  if (
    connectionState.reconnectAttempts >= connectionState.maxReconnectAttempts
  ) {
    updateStatus("Failed to reconnect. Please refresh the page.", "error");
    showReconnectOption();
    return;
  }

  connectionState.reconnectAttempts++;

  // Exponential backoff
  const delay = Math.min(
    connectionState.reconnectDelay *
      Math.pow(2, connectionState.reconnectAttempts - 1),
    connectionState.maxReconnectDelay,
  );

  console.log(
    `Reconnecting in ${delay}ms (attempt ${connectionState.reconnectAttempts}/${connectionState.maxReconnectAttempts})`,
  );
  updateStatus(
    `Reconnecting in ${Math.ceil(delay / 1000)}s... (${connectionState.reconnectAttempts}/${connectionState.maxReconnectAttempts})`,
    "error",
  );

  setTimeout(() => {
    connectWebSocket();
  }, delay);
}

function showReconnectOption() {
  // Add a manual reconnect button if it doesn't exist
  const statusElement = document.getElementById("game-status");
  if (statusElement && !document.getElementById("manual-reconnect-btn")) {
    const reconnectBtn = document.createElement("button");
    reconnectBtn.id = "manual-reconnect-btn";
    reconnectBtn.className = "button";
    reconnectBtn.textContent = "Reconnect";
    reconnectBtn.onclick = () => {
      reconnectBtn.remove();
      connectionState.reconnectAttempts = 0;
      connectionState.intentionalDisconnect = false;
      connectWebSocket();
    };
    statusElement.parentNode.insertBefore(
      reconnectBtn,
      statusElement.nextSibling,
    );
  }
}

function sendWebSocketMessage(message) {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.send(JSON.stringify(message));
    console.log("Sent:", message);
  } else {
    console.warn("WebSocket not connected, queuing message:", message);

    // Queue important messages (moves, etc.)
    if (
      message.type === "move" ||
      message.type === "resign" ||
      message.type === "offer_draw"
    ) {
      connectionState.messageQueue.push(message);
    }
  }
}

function flushMessageQueue() {
  if (connectionState.messageQueue.length > 0) {
    console.log("Flushing message queue:", connectionState.messageQueue.length);
    connectionState.messageQueue.forEach((msg) => {
      sendWebSocketMessage(msg);
    });
    connectionState.messageQueue = [];
  }
}

// ═══════════════════════════════════════════════════════════════════════════
// Heartbeat/Keepalive
// ═══════════════════════════════════════════════════════════════════════════

function startHeartbeat() {
  stopHeartbeat(); // Clear any existing heartbeat

  // Send ping every 30 seconds
  connectionState.heartbeatInterval = setInterval(() => {
    if (websocket && websocket.readyState === WebSocket.OPEN) {
      sendWebSocketMessage({ type: "ping" });
    }
  }, 30000);

  // Set initial timeout
  resetHeartbeatTimeout();
}

function resetHeartbeatTimeout() {
  if (connectionState.heartbeatTimeout) {
    clearTimeout(connectionState.heartbeatTimeout);
  }

  // If no message received in 60 seconds, consider connection dead
  connectionState.heartbeatTimeout = setTimeout(() => {
    console.log("No heartbeat received, connection may be dead");
    if (websocket) {
      websocket.close();
    }
  }, 60000);
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

// ═══════════════════════════════════════════════════════════════════════════
// Game Event Handlers
// ═══════════════════════════════════════════════════════════════════════════

function handleGameStart(message) {
  console.log("Game starting:", message);

  gameState.gameId = message.game_id;
  gameState.playerColor = message.your_color || message.color;
  gameState.playerUsername = message.player_username || "You";
  gameState.opponentUsername = message.opponent_username || "Opponent";
  gameState.currentTurn = message.turn || "white";
  gameState.fen = message.fen || gameState.fen;
  gameState.legalMoves = message.legal_moves || [];
  gameState.gameStatus = "ongoing";

  // Initialize chessboard if not already done
  if (!board) {
    initializeBoard();
  }

  // Update board position
  board.position(gameState.fen, false);

  // Flip board if playing black
  if (gameState.playerColor === "black") {
    board.orientation("black");
  }

  // Update UI
  updatePlayerInfo();
  updateStatus(
    gameState.currentTurn === gameState.playerColor
      ? "Your turn"
      : "Opponent's turn",
    "info",
  );
}

function handleMoveUpdate(message) {
  console.log("Move update:", message);

  // Update game state
  gameState.fen = message.fen;
  gameState.currentTurn = message.turn || message.current_turn;
  gameState.legalMoves = message.legal_moves || [];

  // Add to move history
  if (message.move) {
    gameState.moveHistory.push(message.move);
  }

  // Update board position with animation
  board.position(gameState.fen, true);

  // Update UI
  updateMoveHistory();
  updateStatus(
    gameState.currentTurn === gameState.playerColor
      ? "Your turn"
      : "Opponent's turn",
    "info",
  );
}

function handleGameOver(message) {
  console.log("Game over:", message);

  gameState.gameStatus = "finished";
  gameState.winner = message.winner || message.result;

  showGameOverDialog(message);

  // Show new game button
  const newGameBtn = document.getElementById("new-game-btn");
  if (newGameBtn) {
    newGameBtn.style.display = "inline-block";
  }

  // Update status
  const winner = message.winner || message.result;
  if (winner === "draw" || winner === "stalemate") {
    updateStatus("Game ended in a draw", "info");
  } else if (winner === gameState.playerColor) {
    updateStatus("You won!", "success");
  } else {
    updateStatus("You lost", "error");
  }
}

function handleOpponentDisconnected(message) {
  console.log("Opponent disconnected:", message);
  updateStatus("Opponent disconnected. Waiting for reconnection...", "warning");
}

function handleDrawOffer(message) {
  console.log("Draw offer received:", message);
  if (dialogManager) {
    dialogManager.showDrawOfferReceived();
  }
}

function handleDrawAccepted(message) {
  console.log("Draw accepted:", message);
  
  // Hide draw sent dialog if it's open
  if (dialogManager) {
    dialogManager.hideDrawSentDialog();
  }
  
  // Show game over as draw
  handleGameOver({
    winner: 'draw',
    result: 'draw',
    reason: 'Draw accepted by agreement'
  });
}

function handleDrawDeclined(message) {
  console.log("Draw declined:", message);
  
  if (dialogManager) {
    dialogManager.onDrawDeclined();
  }
}

function handleServerError(message) {
  console.error("Server error:", message);
  updateStatus(`Error: ${message.message || "Unknown error"}`, "error");
}

// ═══════════════════════════════════════════════════════════════════════════
// Chessboard Initialization
// ═══════════════════════════════════════════════════════════════════════════

function initializeBoard() {
  const config = {
    draggable: true,
    position: gameState.fen,
    onDragStart: onDragStart,
    onDrop: onDrop,
    onSnapEnd: onSnapEnd,
  };

  board = Chessboard2("board1", config);
  console.log("Chessboard initialized");
}

function onDragStart(source, piece) {
  // In v2, source is a string (e.g., 'e2'), piece is a string (e.g., 'wP')
  if (gameState.gameStatus !== "ongoing") return false;
  if (gameState.currentTurn !== gameState.playerColor) return false;

  const pieceColor = piece.charAt(0) === "w" ? "white" : "black";
  if (pieceColor !== gameState.playerColor) return false;

  return true;
}

function onDrop(source) {
  // Chessboard.js v2 API: passes a single object with all properties
  let piece, fromSquare, toSquare;
  piece = source.piece;
  fromSquare = source.source;
  toSquare = source.target;

  // Validate we got valid squares
  if (!fromSquare || !toSquare) {
    console.error("Could not extract square names from:", { source });
    return "snapback";
  }

  console.log("Extracted squares:", fromSquare, "to", toSquare);

  // Move format: e2-e4 (consistent with backend)
  const move = fromSquare + "-" + toSquare;

  // Check if move is legal
  if (!isMoveLegal(move, fromSquare, toSquare)) {
    console.log("Illegal move:", move);
    return "snapback";
  }

  // Send move to server
  sendMove(fromSquare, toSquare);
}

function onSnapEnd() {
  // Don't update position here - it's already handled by handleMoveUpdate from the server
  // Just sync with current gameState to ensure visual consistency
  board.position(gameState.fen, false); // false = no animation
}

function isMoveLegal(move, from, to) {
  // Legal moves from backend are always in format: e2-e4
  return gameState.legalMoves.some((legalMove) => {
    // Direct comparison (e2-e4 === e2-e4)
    if (legalMove === move) return true;

    // Handle promotions (e7-e8q matches e7-e8)
    if (legalMove.startsWith(move)) return true;

    return false;
  });
}

function sendMove(from, to) {
  sendWebSocketMessage({
    type: "move",
    move: from + "-" + to,
  });

  console.log("Move sent:", from, to);
}

// ═══════════════════════════════════════════════════════════════════════════
// UI Updates
// ═══════════════════════════════════════════════════════════════════════════

function updateStatus(message, type = "info") {
  const statusElement = document.getElementById("game-status");
  if (statusElement) {
    statusElement.textContent = message;
    statusElement.className = `game-status ${type}`;
  }
  console.log(`Status [${type}]:`, message);
}

function updatePlayerInfo() {
  const playerInfoElement = document.getElementById("player-info");
  if (playerInfoElement) {
    const opponentColor = gameState.playerColor === "white" ? "black" : "white";
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
  const historyElement = document.getElementById("move-history");
  if (!historyElement) return;

  if (gameState.moveHistory.length === 0) {
    historyElement.innerHTML = '<p class="no-moves">No moves yet</p>';
    return;
  }

  let html = '<ol class="move-list">';
  for (let i = 0; i < gameState.moveHistory.length; i += 2) {
    const moveNumber = Math.floor(i / 2) + 1;
    const whiteMove = formatMove(gameState.moveHistory[i]);
    const blackMove = gameState.moveHistory[i + 1]
      ? formatMove(gameState.moveHistory[i + 1])
      : "";

    html += `<li class="move-pair">
      <span class="move-number">${moveNumber}.</span>
      <span class="move white-move">${whiteMove}</span>
      ${blackMove ? `<span class="move black-move">${blackMove}</span>` : ""}
    </li>`;
  }
  html += "</ol>";

  historyElement.innerHTML = html;
  historyElement.scrollTop = historyElement.scrollHeight;
}

function formatMove(move) {
  // Keep the hyphen format (e2-e4)
  return move;
}

function showGameOverDialog(message) {
  const dialog = document.getElementById("game-over-dialog");
  if (!dialog) return;

  const titleElement = dialog.querySelector(".dialog-title");
  const messageElement = dialog.querySelector(".dialog-message");

  const winner = message.winner || message.result;

  if (winner === "draw" || winner === "stalemate") {
    titleElement.textContent = "Draw";
    messageElement.textContent = message.reason || "Game ended in a draw";
  } else if (winner === gameState.playerColor) {
    titleElement.textContent = "Victory!";
    messageElement.textContent = message.reason || "You won the game!";
  } else {
    titleElement.textContent = "Defeat";
    messageElement.textContent = message.reason || "You lost the game";
  }

  // Add ELO info if available
  if (message.elo_changes && message.elo_changes[gameState.playerColor]) {
    const change = message.elo_changes[gameState.playerColor];
    messageElement.textContent += `\n\nELO Change: ${change > 0 ? "+" : ""}${change}`;
  }

  dialog.style.display = "flex";
}

function capitalize(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ═══════════════════════════════════════════════════════════════════════════
// Button Handlers
// ═══════════════════════════════════════════════════════════════════════════

function handleResign() {
  if (gameState.gameStatus !== "ongoing") return;

  customConfirm(
    "Are you sure you want to resign? This will end the game and count as a loss.",
    () => {
      // User confirmed
      sendWebSocketMessage({ type: "resign" });
      updateStatus("You resigned", "error");
    },
    () => {
      // User cancelled
      console.log("Resign cancelled");
    }
  );
}

function handleOfferDraw() {
  if (gameState.gameStatus !== "ongoing") return;

  // Show the draw sent dialog
  if (dialogManager) {
    dialogManager.showDrawOfferSent();
  }

  sendWebSocketMessage({ type: "offer_draw" });
  updateStatus("Draw offer sent to opponent", "info");
}

function handleNewGame() {
  // Mark as intentional disconnect before navigating
  connectionState.intentionalDisconnect = true;
  if (websocket) {
    websocket.close();
  }
  window.location.href = "/home";
}

function closeGameOverDialog() {
  // Mark as intentional disconnect before navigating
  connectionState.intentionalDisconnect = true;
  if (websocket) {
    websocket.close();
  }
  window.location.href = "/home";
}

// ═══════════════════════════════════════════════════════════════════════════
// Initialization
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener("DOMContentLoaded", () => {
  console.log("Game page loaded");

  // Initialize dialog manager
  dialogManager = new CustomDialogManager();
  window.dialogManager = dialogManager; // Make it globally accessible

  // Connect to WebSocket
  connectWebSocket();

  // Set up button event listeners
  const resignBtn = document.getElementById("resign-btn");
  if (resignBtn) {
    resignBtn.addEventListener("click", handleResign);
  }

  const drawBtn = document.getElementById("draw-btn");
  if (drawBtn) {
    drawBtn.addEventListener("click", handleOfferDraw);
  }

  const newGameBtn = document.getElementById("new-game-btn");
  if (newGameBtn) {
    newGameBtn.addEventListener("click", handleNewGame);
  }

  const closeDialogBtn = document.getElementById("close-dialog-btn");
  if (closeDialogBtn) {
    closeDialogBtn.addEventListener("click", closeGameOverDialog);
  }

  // Draw dialog buttons
  const acceptDrawBtn = document.getElementById("accept-draw-btn");
  if (acceptDrawBtn) {
    acceptDrawBtn.addEventListener("click", () => {
      dialogManager.acceptDraw();
    });
  }

  const declineDrawBtn = document.getElementById("decline-draw-btn");
  if (declineDrawBtn) {
    declineDrawBtn.addEventListener("click", () => {
      dialogManager.declineDraw();
    });
  }

  const cancelDrawBtn = document.getElementById("cancel-draw-btn");
  if (cancelDrawBtn) {
    cancelDrawBtn.addEventListener("click", () => {
      dialogManager.cancelDrawOffer();
    });
  }

  // Close dialog on outside click
  const gameOverDialog = document.getElementById("game-over-dialog");
  if (gameOverDialog) {
    gameOverDialog.addEventListener("click", (e) => {
      if (e.target === gameOverDialog) {
        closeGameOverDialog();
      }
    });
  }

  // Draw offer dialog outside click
  const drawOfferDialog = document.getElementById("draw-offer-dialog");
  if (drawOfferDialog) {
    drawOfferDialog.addEventListener("click", (e) => {
      if (e.target === drawOfferDialog) {
        dialogManager.declineDraw();
      }
    });
  }

  const drawSentDialog = document.getElementById("draw-sent-dialog");
  if (drawSentDialog) {
    drawSentDialog.addEventListener("click", (e) => {
      if (e.target === drawSentDialog) {
        dialogManager.cancelDrawOffer();
      }
    });
  }

  console.log("Game initialization complete");
});

// Handle page unload
window.addEventListener("beforeunload", () => {
  connectionState.intentionalDisconnect = true;
  stopHeartbeat();
  if (websocket) {
    websocket.close();
  }
});

// Handle page visibility changes (tab switching)
document.addEventListener("visibilitychange", () => {
  if (document.hidden) {
    console.log("Page hidden - maintaining connection");
  } else {
    console.log("Page visible - checking connection");
    // Check if connection is still alive when user returns
    if (!connectionState.isConnected && gameState.gameStatus === "ongoing") {
      console.log("Reconnecting after page became visible");
      connectWebSocket();
    }
  }
});
