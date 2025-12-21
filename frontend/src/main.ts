import "./app.css";
import App from "./App.svelte";
import { mount } from "svelte";
import { initPWA } from "$lib/stores/pwa.svelte";
import { initAuth } from "$lib/stores/auth.svelte";

void (async () => {
  await initAuth();
  initPWA();

  mount(App, {
    target: document.getElementById("app")!,
  });
})();
