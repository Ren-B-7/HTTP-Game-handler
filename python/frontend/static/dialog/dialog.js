// Draw Dialog Manager
// Add this to your game.js file or create a separate draw-dialog.js

class DrawDialogManager {
  constructor() {
    this.drawOfferDialog = document.getElementById('draw-offer-dialog');
    this.drawSentDialog = document.getElementById('draw-sent-dialog');
    
    // Button references
    this.offerDrawBtn = document.getElementById('draw-btn');
    this.acceptDrawBtn = document.getElementById('accept-draw-btn');
    this.declineDrawBtn = document.getElementById('decline-draw-btn');
    this.cancelDrawBtn = document.getElementById('cancel-draw-btn');
    
    this.pendingDrawOffer = false;
    this.drawOfferSent = false;
    
    this.init();
  }
  
  init() {
    // Bind event listeners
    if (this.offerDrawBtn) {
      this.offerDrawBtn.addEventListener('click', () => this.sendDrawOffer());
    }
    
    if (this.acceptDrawBtn) {
      this.acceptDrawBtn.addEventListener('click', () => this.acceptDraw());
    }
    
    if (this.declineDrawBtn) {
      this.declineDrawBtn.addEventListener('click', () => this.declineDraw());
    }
    
    if (this.cancelDrawBtn) {
      this.cancelDrawBtn.addEventListener('click', () => this.cancelDrawOffer());
    }
    
    // Close modal when clicking outside
    this.drawOfferDialog?.addEventListener('click', (e) => {
      if (e.target === this.drawOfferDialog) {
        this.declineDraw();
      }
    });
    
    this.drawSentDialog?.addEventListener('click', (e) => {
      if (e.target === this.drawSentDialog) {
        this.cancelDrawOffer();
      }
    });
  }
  
  // Called when the current player offers a draw
  sendDrawOffer() {
    if (this.drawOfferSent) {
      console.log('Draw offer already sent');
      return;
    }
    
    // Show confirmation that draw offer was sent
    this.showDrawSentDialog();
    this.drawOfferSent = true;
    
    // Disable the draw button
    if (this.offerDrawBtn) {
      this.offerDrawBtn.disabled = true;
      this.offerDrawBtn.textContent = 'Draw Offered';
    }
    
    // Send draw offer to server/opponent
    // Replace this with your actual WebSocket/API call
    this.sendToServer({
      type: 'draw_offer',
      gameId: this.getCurrentGameId(), // Implement this based on your setup
      timestamp: Date.now()
    });
    
    console.log('Draw offer sent to opponent');
  }
  
  // Called when opponent offers a draw
  receiveDrawOffer(data) {
    if (this.pendingDrawOffer) {
      console.log('Already have a pending draw offer');
      return;
    }
    
    this.pendingDrawOffer = true;
    this.showDrawOfferDialog();
    
    // Optional: Play a notification sound
    this.playNotificationSound();
  }
  
  // Accept the draw offer
  acceptDraw() {
    this.hideDrawOfferDialog();
    this.pendingDrawOffer = false;
    
    // Send acceptance to server
    this.sendToServer({
      type: 'draw_accepted',
      gameId: this.getCurrentGameId(),
      timestamp: Date.now()
    });
    
    // Show game over dialog with draw result
    this.showGameOverDialog('Draw', 'Game ended by agreement');
    
    console.log('Draw accepted');
  }
  
  // Decline the draw offer
  declineDraw() {
    this.hideDrawOfferDialog();
    this.pendingDrawOffer = false;
    
    // Send decline to server
    this.sendToServer({
      type: 'draw_declined',
      gameId: this.getCurrentGameId(),
      timestamp: Date.now()
    });
    
    // Optional: Show brief notification
    this.showStatusMessage('Draw offer declined', 'info');
    
    console.log('Draw declined');
  }
  
  // Cancel the draw offer (by the player who sent it)
  cancelDrawOffer() {
    this.hideDrawSentDialog();
    this.drawOfferSent = false;
    
    // Re-enable the draw button
    if (this.offerDrawBtn) {
      this.offerDrawBtn.disabled = false;
      this.offerDrawBtn.textContent = 'Offer Draw';
    }
    
    // Send cancellation to server
    this.sendToServer({
      type: 'draw_cancelled',
      gameId: this.getCurrentGameId(),
      timestamp: Date.now()
    });
    
    console.log('Draw offer cancelled');
  }
  
  // Handle draw offer being declined by opponent
  onDrawDeclined() {
    this.hideDrawSentDialog();
    this.drawOfferSent = false;
    
    // Re-enable the draw button
    if (this.offerDrawBtn) {
      this.offerDrawBtn.disabled = false;
      this.offerDrawBtn.textContent = 'Offer Draw';
    }
    
    // Show notification
    this.showStatusMessage('Your draw offer was declined', 'info');
    
    console.log('Draw offer was declined by opponent');
  }
  
  // Show dialogs
  showDrawOfferDialog() {
    if (this.drawOfferDialog) {
      this.drawOfferDialog.style.display = 'flex';
      // Trigger reflow for animation
      void this.drawOfferDialog.offsetWidth;
    }
  }
  
  showDrawSentDialog() {
    if (this.drawSentDialog) {
      this.drawSentDialog.style.display = 'flex';
      void this.drawSentDialog.offsetWidth;
    }
  }
  
  // Hide dialogs
  hideDrawOfferDialog() {
    if (this.drawOfferDialog) {
      this.drawOfferDialog.style.display = 'none';
    }
  }
  
  hideDrawSentDialog() {
    if (this.drawSentDialog) {
      this.drawSentDialog.style.display = 'none';
    }
  }
  
  // Utility methods - implement these based on your actual game setup
  
  getCurrentGameId() {
    // Replace with your actual game ID retrieval logic
    return window.currentGameId || 'game-123';
  }
  
  sendToServer(data) {
    // Replace with your actual WebSocket or API call
    // Example:
    if (window.socket && window.socket.readyState === WebSocket.OPEN) {
      window.socket.send(JSON.stringify(data));
    } else {
      console.error('WebSocket not connected', data);
    }
  }
  
  showGameOverDialog(result, message) {
    // Replace with your actual game over dialog logic
    const dialog = document.getElementById('game-over-dialog');
    const titleEl = dialog?.querySelector('.dialog-title');
    const messageEl = dialog?.querySelector('.dialog-message');
    
    if (dialog && titleEl && messageEl) {
      titleEl.textContent = result;
      messageEl.textContent = message;
      dialog.style.display = 'flex';
    }
  }
  
  showStatusMessage(message, type = 'info') {
    // Replace with your actual status message logic
    const statusEl = document.getElementById('game-status');
    if (statusEl) {
      statusEl.textContent = message;
      statusEl.className = `game-status ${type}`;
      
      // Auto-hide after 3 seconds
      setTimeout(() => {
        statusEl.textContent = '';
        statusEl.className = 'game-status';
      }, 3000);
    }
  }
  
  playNotificationSound() {
    // Optional: Play a sound when receiving a draw offer
    // const audio = new Audio('/static/sounds/notification.mp3');
    // audio.play().catch(e => console.log('Could not play sound:', e));
  }
}

// Initialize the draw dialog manager when DOM is ready
let drawDialogManager;

function initDrawDialog() {
  drawDialogManager = new DrawDialogManager();
  
  // Expose globally for use in other parts of the code
  window.drawDialogManager = drawDialogManager;
}

// Auto-initialize
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initDrawDialog);
} else {
  initDrawDialog();
}

// Example usage in WebSocket message handler:
/*
socket.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  switch(data.type) {
    case 'draw_offer':
      window.drawDialogManager.receiveDrawOffer(data);
      break;
      
    case 'draw_accepted':
      // Handle draw acceptance
      window.drawDialogManager.hideDrawSentDialog();
      window.drawDialogManager.showGameOverDialog('Draw', 'Draw accepted by agreement');
      break;
      
    case 'draw_declined':
      window.drawDialogManager.onDrawDeclined();
      break;
      
    case 'draw_cancelled':
      // Opponent cancelled their draw offer
      window.drawDialogManager.hideDrawOfferDialog();
      break;
  }
};
*/
