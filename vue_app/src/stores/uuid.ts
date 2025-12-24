import { defineStore } from 'pinia';
import { v4 as uuidv4 } from 'uuid';

export const useUuidStore = defineStore('uuid', {
  state: () => ({
    uuid: '' as string,
  }),
  actions: {
    generateUuid() {
      this.uuid = uuidv4();
    },
  },
});