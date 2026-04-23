# KabuSys

日本株自動売買システムの一部コンポーネント群（設定管理・実行エンジン・監視・データ処理等）。  
このリポジトリは、kabuステーション（ローカルREST / WebSocket）や J-Quants 等の外部依存と連携して動作することを想定しています。

---

## プロジェクト概要

KabuSys は、シグナルに基づいて注文を行う ExecutionEngine、実行状況やシステム資源を監視する Monitoring、カレンダー・ニュース収集などの Data モジュール群を含む自動売買システムです。モジュールは明確に責務分離され、テストしやすいように Broker クライアントのモック実装（MockBrokerClient）を提供しています。

主な特徴:
- 設定ウィザード（.env の対話式作成）
- 起動前の設定検証 CLI（YAML/.env の不足や不正値の検出）
- ExecutionEngine：Signal Pull + WebSocket Push の発注フロー
- 強力なリスクガード（Gate1/2/3、サーキットブレーカー、レート制限）
- リコンシリエーション（起動時の OrderSent の突合）
- MockBrokerClient によるローカルでの安全な開発 / テスト

---

## 機能一覧

- 設定管理
  - .env/.env.local の自動読み込み（OS環境変数優先）
  - 対話式設定ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
- Execution（発注）
  - ExecutionEngine によるシグナル読み込み → 発注（時刻窓に応じた動作）
  - OrderManager、OrderRepository（SQLite）による注文状態管理
  - Broker クライアント抽象化（実運用向けの KabuStationClient、テスト用 MockBrokerClient）
  - リスク管理（3段階ガード、ドローダウン監視、サーキットブレーカー）
  - リコンシリエーション機能（再起動後の自動復旧）
- Monitoring（監視）
  - SystemMonitor のポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可）
  - 監視 DB（SQLite）への記録
- Data
  - マーケットカレンダー管理（DuckDB ベース）
  - ニュース収集（RSS -> raw_news、SSRF/XML攻撃対策あり）
- ユーティリティ
  - ロギング初期化、プロセス優先度設定 など

---

## 前提 / 必要環境

- Python 3.9+
- 主なパッケージ（用途別）
  - duckdb
  - httpx
  - websocket-client
  - PyYAML（config/*.yaml のパース検証に使用）
  - defusedxml（RSS パースの安全化）
- SQLite（標準ライブラリで利用）
- kabuステーションアプリ（本番連携時）

※パッケージはプロジェクト側で requirements.txt を用意していない場合があるため、上記を仮に pip install してください。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client PyYAML defusedxml
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境作成・依存ライブラリをインストール（上記参照）

3. .env を作成
   - 対話式ウィザードを使う（推奨）
     ```
     python -m kabusys.config_setup
     ```
     ウィザードは .env（デフォルト）を作成・更新します。既存の .env があれば読み込んで既存値を再利用できます。

   - 手動編集: .env を直接作成する場合は .env.example を参考にしてください（リポジトリに存在する場合）。

4. 起動前に設定を検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL として扱う場合:
   python -m kabusys.validate_config --strict
   ```

5. （任意）config/*.yaml のテンプレート作成
   - リポジトリ内に `scripts/generate_config.py` のようなスクリプトが参照されています（存在する場合）。なければ手動で `config/system_config.yaml` などを用意してください。
   - validate_config は PyYAML があると YAML のパース検証を行います。

---

## 主要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意／デフォルトあり（代表的なもの）:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABU_API_BASE_URL — kabuステーションのベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知（本番推奨設定）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）

自動ロードの振る舞い:
- .env がプロジェクトルートにある場合、自動で読み込みます（.env.local は上書き）。
- OS 環境変数が優先されます。
- 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## 使い方（実行コマンド）

- 設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path を使用します（KABUSYS_ENV に依存しません）。

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用の専用 SQLite DB（デフォルト: data/paper_trading.db）を使用します。
  - 実際の本番ブローカー連携は live 向けに別実装が想定されています（未実装の場合は NotImplementedError になることがあります）。

停止フラグ:
- data/stop_requested.flag ファイルを作成すると監視 / 実行ループが検知して安全に終了します。
- ExecutionEngine は kill.flag による Kill Switch を実装しています（設定によっては起動拒否や自動クリアの挙動があります）。

---

## 開発 / テストについて

- MockBrokerClient により外部 kabuステーションなしで発注フローやリスクロジックをテストできます。
- ExecutionEngine.run_session() は本番用の時間帯ロジックを含みますが、テストでは _process_signals() や _drain_push_queue() を直接呼び出して単体テスト可能です。
- 設定の自動読み込みが邪魔な場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使って無効化してください。

---

## ディレクトリ構成（抜粋）

プロジェクトルート例:
```
.
├── .env                      # (推奨) 環境変数ファイル（.git にコミットしないこと）
├── data/                     # DB・PID・フラグ等のデータ格納ディレクトリ
│   ├── monitoring.db         # 監視用 SQLite（デフォルト）
│   ├── paper_trading.db      # paper_trading 用 SQLite（paper トレード時）
│   ├── kabusys.duckdb        # DuckDB（分析用）
│   ├── stop_requested.flag   # ループ停止フラグ
│   └── execution.pid         # PID ファイル等
├── config/                   # 各種 YAML 設定ファイル（例: system_config.yaml など）
├── scripts/                  # 補助スクリプト（例: generate_config.py）
└── src/
    └── kabusys/
        ├── __init__.py
        ├── config.py                 # 環境変数読み込み・Settings
        ├── config_setup.py           # .env 対話式ウィザード
        ├── validate_config.py        # 起動前チェック CLI
        ├── run_execution.py          # ExecutionEngine 起動スクリプト
        ├── run_monitoring.py         # Monitoring 起動スクリプト
        ├── execution/                # 発注関連コンポーネント
        │   ├── broker_api.py
        │   ├── broker_factory.py
        │   ├── kabu_client.py
        │   ├── mock_client.py
        │   ├── order_repository.py
        │   ├── order_record.py
        │   ├── order_manager.py
        │   ├── execution_engine.py
        │   ├── reconciler.py
        │   ├── risk_manager.py
        │   └── ...
        ├── data/                     # データ処理モジュール（calendar/news 等）
        │   ├── calendar_management.py
        │   ├── news_collector.py
        │   └── ...
        ├── monitoring/               # 監視関連
        │   ├── monitoring_db.py
        │   └── system_monitor.py
        └── utils/
            ├── logging_setup.py
            └── process_priority.py
```

---

## 注意事項 / 運用上のヒント

- .env は絶対にリポジトリにコミットしないこと（README と同じく .gitignore に追加すること）。
- KABUSYS_ENV=live は本番運用になるため、LINE 通知等のアラート設定や kill switch の挙動を必ず確認してください。validate_config は live 時に警告を出します。
- DB ファイルの親ディレクトリがない場合、起動時に自動作成されることはありますが、事前に作成・権限確認を行うと安全です。
- ExecutionEngine の発注時間帯やログ出力は設定で調整可能です。ローカルでのテストは paper_trading 環境を推奨します。
- YAML 設定の構造やサンプルは config/*.yaml を参照してください。PyYAML が未インストールの場合、validate_config は YAML の検証をスキップします。

---

もし README に追加したい具体的な例（.env のサンプルや config/*.yaml のテンプレート、テスト手順、CI 設定など）があれば教えてください。必要に応じて追記・整形します。