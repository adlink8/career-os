/**
 * 把捕获 JSON 写到用户绑定的项目目录（File System Access）。
 * Chrome 不允许 chrome.downloads 指定 D:\项目\... 绝对路径。
 */
(function (root) {
  'use strict';

  var DB_NAME = 'career-os-fs';
  var STORE = 'handles';
  var KEY = 'captures';

  function openDb() {
    return new Promise(function (resolve, reject) {
      var req = indexedDB.open(DB_NAME, 1);
      req.onupgradeneeded = function () {
        req.result.createObjectStore(STORE);
      };
      req.onsuccess = function () { resolve(req.result); };
      req.onerror = function () { reject(req.error); };
    });
  }

  function saveDirHandle(handle) {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readwrite');
        tx.objectStore(STORE).put(handle, KEY);
        tx.oncomplete = function () { resolve(handle); };
        tx.onerror = function () { reject(tx.error); };
      });
    });
  }

  function getDirHandle() {
    return openDb().then(function (db) {
      return new Promise(function (resolve, reject) {
        var tx = db.transaction(STORE, 'readonly');
        var req = tx.objectStore(STORE).get(KEY);
        req.onsuccess = function () { resolve(req.result || null); };
        req.onerror = function () { reject(req.error); };
      });
    });
  }

  function contextFileName(ctx) {
    var host = String((ctx && ctx.host) || 'job').replace(/[^a-zA-Z0-9.-]/g, '_');
    var stamp = String((ctx && ctx.captured_at) || new Date().toISOString())
      .replace(/[:.]/g, '-')
      .replace(/Z$/, '')
      .slice(0, 19);
    return 'job-context-' + host + '-' + stamp + '.json';
  }

  function ensurePermission(dir) {
    return dir.queryPermission({ mode: 'readwrite' }).then(function (status) {
      if (status === 'granted') return 'granted';
      return dir.requestPermission({ mode: 'readwrite' });
    });
  }

  function writeContext(ctx) {
    return getDirHandle().then(function (dir) {
      if (!dir) {
        var err = new Error('NO_DIR');
        err.code = 'NO_DIR';
        throw err;
      }
      return ensurePermission(dir).then(function (perm) {
        if (perm !== 'granted') {
          var e = new Error('NO_PERM');
          e.code = 'NO_PERM';
          throw e;
        }
        var name = contextFileName(ctx);
        return dir.getFileHandle(name, { create: true }).then(function (fh) {
          return fh.createWritable().then(function (writable) {
            return writable.write(JSON.stringify(ctx, null, 2)).then(function () {
              return writable.close();
            });
          }).then(function () {
            return { name: name, folder: dir.name };
          });
        });
      });
    });
  }

  root.CareerOsDirStore = {
    saveDirHandle: saveDirHandle,
    getDirHandle: getDirHandle,
    writeContext: writeContext,
    contextFileName: contextFileName
  };
})(typeof self !== 'undefined' ? self : this);
