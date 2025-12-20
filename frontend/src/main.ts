import "./app.css";
import App from "./App.svelte";
import { mount } from "svelte";
import { initPWA } from "$lib/stores/pwa.svelte";

initPWA();

const app = mount(App, {
  target: document.getElementById("app")!,
});

export default app;
