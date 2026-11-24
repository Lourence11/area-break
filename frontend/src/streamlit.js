/*
 * Minimal Streamlit component bridge (the same postMessage protocol that
 * streamlit-component-lib implements, without its React 16 peer dependency).
 */
import { useEffect, useRef, useState } from "react";

function post(type, data = {}) {
  window.parent.postMessage({ isStreamlitMessage: true, type, ...data }, "*");
}

/** Latest `state` argument passed from Python. */
export function useStreamlitState() {
  const [state, setState] = useState(null);
  useEffect(() => {
    const onMessage = (event) => {
      if (event.data?.type === "streamlit:render") {
        setState(event.data.args?.state ?? null);
      }
    };
    window.addEventListener("message", onMessage);
    post("streamlit:componentReady", { apiVersion: 1 });
    return () => window.removeEventListener("message", onMessage);
  }, []);
  return state;
}

/** Keep the iframe exactly as tall as the app. */
export function useFrameHeight() {
  const last = useRef(0);
  useEffect(() => {
    const root = document.getElementById("root");
    const update = () => {
      const h = Math.ceil(root.getBoundingClientRect().height);
      if (h !== last.current) {
        last.current = h;
        post("streamlit:setFrameHeight", { height: h });
      }
    };
    const ro = new ResizeObserver(update);
    ro.observe(root);
    update();
    return () => ro.disconnect();
  }, []);
}

let counter = 0;

/** Send an event to Python. Returns the nonce so the caller can await its ack. */
export function sendEvent(type, payload = {}) {
  const nonce = Date.now() * 100 + (counter++ % 100);
  post("streamlit:setComponentValue", {
    value: { type, nonce, ...payload },
    dataType: "json",
  });
  return nonce;
}
