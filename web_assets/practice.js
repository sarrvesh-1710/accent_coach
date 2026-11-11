() => {
  // One delegated listener survives Gradio replacing sentence cards.
  if (window.accentCoachExamples) return;
  window.accentCoachExamples = true;
  let audio = null;
  let activeButton = null;
  const normalText = 'Synthetic English example. Listening only; not used for scoring.';
  const status = (button, text) => {
    const node = button?.closest('.sentence')?.querySelector('.example-status');
    if (node) node.textContent = text;
  };
  const reset = () => {
    if (audio) { audio.pause(); audio.removeAttribute('src'); audio.load(); }
    if (activeButton) {
      activeButton.setAttribute('aria-pressed', 'false');
      activeButton.setAttribute('aria-label', 'Listen to the synthetic English example');
      activeButton.querySelector('span').textContent = 'Listen';
      status(activeButton, normalText);
    }
    audio = null;
    activeButton = null;
  };
  const recordingActive = () => [...document.querySelectorAll(
    '#learner-audio .stop-button, #learner-audio .stop-button-paused'
  )].some(node => node.getClientRects().length > 0);
  document.addEventListener('click', async event => {
    if (!(event.target instanceof Element)) return;
    const button = event.target.closest('button.example-play');
    if (!button) {
      // Stop the example before microphone capture starts or input changes.
      if (event.target.closest('#learner-audio, #check-button, #retry-button, [role="combobox"]')) reset();
      return;
    }
    if (recordingActive()) {
      status(button, 'Finish recording before listening to the example.');
      return;
    }
    if (activeButton === button) { reset(); return; }
    reset();
    activeButton = button;
    const current = new Audio(button.dataset.example);
    audio = current;
    button.setAttribute('aria-pressed', 'true');
    button.setAttribute('aria-label', 'Stop the synthetic English example');
    button.querySelector('span').textContent = 'Stop';
    status(button, 'Playing synthetic English example. Not used for scoring.');
    current.addEventListener('ended', () => { if (audio === current) reset(); });
    try { await current.play(); }
    catch (_) {
      if (audio !== current) return;
      reset();
      status(button, 'Example audio could not play. Try Listen again or continue recording.');
    }
  }, true);
  new MutationObserver(() => {
    if (activeButton && (!activeButton.isConnected || recordingActive())) reset();
    const active = recordingActive();
    for (const button of document.querySelectorAll('.example-play')) {
      if (button.disabled !== active) button.disabled = active;
    }
  }).observe(document.body, {childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'style']});
  window.addEventListener('pagehide', reset);
}
