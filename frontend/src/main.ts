import "./app.css";
import App from "./App.svelte";
import { mount } from "svelte";
import { initPWA } from "$lib/stores/pwa.svelte";

initPWA();

mount(App, {
  target: document.getElementById("app")!,
});
