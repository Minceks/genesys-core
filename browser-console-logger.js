/**
 * Browser Console Logger
 * Captures browser console messages and sends them to the Flask backend
 * 
 * Include this in your HTML: <script src="/browser-console-logger.js"></script>
 */

(function() {
  const configuredEndpoint =
    window.GENESYS_BROWSER_CONSOLE_ENDPOINT;
  const API_ENDPOINT =
    typeof configuredEndpoint === 'string' &&
    !configuredEndpoint.includes('%VITE_CLOUD_AGENT_URL%')
      ? configuredEndpoint
      : '/browser-console';
  const PROJECT_ID = new URLSearchParams(window.location.search).get('projectId') || 'genesys-project';
  
  // Store original console methods
  const originalLog = console.log;
  const originalError = console.error;
  const originalWarn = console.warn;
  const originalInfo = console.info;
  const originalDebug = console.debug;

  /**
   * Send console message to backend
   */
  function sendToBackend(level, message, args) {
    try {
      const payload = {
        level: level,
        message: message,
        url: window.location.href,
        userAgent: navigator.userAgent,
        timestamp: new Date().toISOString(),
        projectId: PROJECT_ID,
        args: args.map(arg => {
          try {
            return typeof arg === 'object' ? JSON.stringify(arg) : String(arg);
          } catch (e) {
            return String(arg);
          }
        })
      };

      // Send asynchronously to avoid blocking
      navigator.sendBeacon
        ? navigator.sendBeacon(
            API_ENDPOINT,
            new Blob(
              [JSON.stringify(payload)],
              { type: 'application/json' }
            )
          )
        : fetch(API_ENDPOINT, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            keepalive: true
          }).catch(() => {}); // Silently fail

    } catch (err) {
      // Don't break if something goes wrong
      originalError('[BrowserLogger Error]', err);
    }
  }

  /**
   * Wrap console methods
   */
  function wrapConsoleMethod(level, originalMethod) {
    return function(...args) {
      // Call original method first
      originalMethod.apply(console, args);
      
      // Send to backend
      const message = args.map(arg => {
        try {
          return typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg);
        } catch (e) {
          return String(arg);
        }
      }).join(' ');

      sendToBackend(level, message, args);
    };
  }

  // Override console methods
  console.log = wrapConsoleMethod('log', originalLog);
  console.error = wrapConsoleMethod('error', originalError);
  console.warn = wrapConsoleMethod('warn', originalWarn);
  console.info = wrapConsoleMethod('info', originalInfo);
  console.debug = wrapConsoleMethod('debug', originalDebug);

  /**
   * Capture uncaught errors
   */
  window.addEventListener('error', (event) => {
    sendToBackend('error', `Uncaught Error: ${event.message}`, [
      event.message,
      event.filename,
      event.lineno,
      event.colno,
      event.error
    ]);
  });

  /**
   * Capture unhandled promise rejections
   */
  window.addEventListener('unhandledrejection', (event) => {
    sendToBackend('error', `Unhandled Promise Rejection: ${event.reason}`, [event.reason]);
  });

  // Log initialization
  originalLog('[BrowserLogger] Initialized for project:', PROJECT_ID);
})();

