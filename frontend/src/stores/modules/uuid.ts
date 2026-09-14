import { defineStore } from 'pinia';
import { ref } from 'vue';
import { v4 as uuidv4 } from 'uuid';

// localStorage 持久化键，http.js 的请求拦截器读取同一键值作为 uuid 头
const STORAGE_KEY = 'client_uuid';

function loadOrCreateUuid(): string {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved) return saved;
  const created = uuidv4();
  localStorage.setItem(STORAGE_KEY, created);
  return created;
}

export const useUUIDStore = defineStore('uuid', () => {
  const uuid = ref<string>(loadOrCreateUuid());

  const generateUUID = () => {
    uuid.value = uuidv4();
    localStorage.setItem(STORAGE_KEY, uuid.value);
  };

  return { uuid, generateUUID };
});
