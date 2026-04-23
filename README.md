# KabuSys

日本株自動売買システムのコアモジュール群（README）。  
この README はリポジトリ内の主要モジュールに基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコアライブラリです。  
主な目的は以下のとおりです。

- シグナルに基づく発注フロー（ExecutionEngine）
- ブローカークライアント抽象化（実ブローカ / モック両対応）
- 注文状態管理（OrderRecord / OrderManager / OrderRepository）
- 起動時のリコンシリエーション（Reconciler）
- 3 段階のリスクガード（RiskManager）
- 監視ループ（System monitor）
- データ系ユーティリティ（マーケットカレンダー、ニュース収集など）
- .env を用いた設定管理・対話式ウィザード・検証ツール

安全性を重視しており、kill flag / PID 管理、サーキットブレーカー、rate-limit、ポジション上限などを備えます。

---

## 主な機能一覧

- 環境設定管理 (.env 自動ロード / Settings)
- 対話式 .env 作成ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
  - 必須環境変数チェック、YAML ファイル存在・パース確認（PyYAML がある場合）
- 実行エンジン（ExecutionEngine）
  - シグナル読み込み → Gate1/Gate2 によるチェック → 発注 → push ドレイン
  - kill_switch による全注文キャンセル
- 発注管理（OrderManager / OrderRepository / OrderRecord）
  - クラッシュ耐性を考慮した 2 相永続化ロジック
  - Reconciliation（OrderSent の再照合）
- ブローカークライアント
  - KabuStationClient（kabu station REST API）
  - MockBrokerClient（paper_trading / development 用）
- リスク管理（RiskManager）
  - Gate1: 余力・重複・ポジション上限
  - Gate2: レート制限・サーキットブレーカー
  - Gate3: ドローダウン監視
- データユーティリティ
  - カレンダー管理（next_trading_day / is_trading_day 等）
  - RSS ニュース収集（安全対策済み）
- 監視プロセス（run_monitoring）

---

## セットアップ手順（開発用）

1. リポジトリをクローンして作業ディレクトリへ移動します。

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 仮想環境を作成して有効化します（推奨）。

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 依存パッケージをインストールします。リポジトリに requirements.txt がある場合はそれを利用してください。無い場合は主要依存を手動でインストールします。

   例（主要依存）:
   ```bash
   pip install duckdb httpx websocket-client PyYAML defusedxml
   ```

   - PyYAML は validate_config の YAML パース検証（任意）
   - websocket-client は KabuStationClient の stream_push のため
   - duckdb / sqlite3 はデータベース接続のため（sqlite3 は標準ライブラリ）
   - defusedxml は RSS パーサの安全対策用

4. プロジェクトルートに .env を配置します（対話式ウィザード推奨）。

   初期作成は次を実行：
   ```bash
   python -m kabusys.config_setup
   ```

   ウィザードで入力後、.env が生成されます。絶対に .env を Git にコミットしないでください。

---

## 必要な環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意 / 推奨:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
  - paper_trading: MockBroker を使用、paper DB に書き込む
  - live: 本番（注意: 本実装では Live broker の一部が未実装の場合あり）
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- LOG_LEVEL — DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABU_API_BASE_URL — kabu station API のベース URL
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — 本番でのアラート通知用
- KILL_FLAG_CLEAR_ON_START — 起動時 kill flag を自動クリアするか（0/1）

自動ロード:
- プロジェクトルートに .env / .env.local がある場合、OS 環境変数を保護しつつ自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

例: 最低限の .env（サンプル）
```
JQUANTS_REFRESH_TOKEN=your_value
KABU_API_PASSWORD=your_value
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（主要 CLI / エントリ）

- 設定ウィザード（.env 作成・更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証 CLI（.env と config/*.yaml の検証）
  ```bash
  python -m kabusys.validate_config
  # 警告を FAIL 扱いにする:
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（発注プロセス）
  ```bash
  python -m kabusys.run_execution
  ```

  - KABUSYS_ENV が paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に記録します。
  - 起動時に data/execution.pid（デフォルト）が書かれます。停止は data/stop_requested.flag（または kill.flag 等）で制御。

- 監視プロセス起動
  ```bash
  python -m kabusys.run_monitoring
  ```

  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。

注意:
- 起動前に `python -m kabusys.validate_config` で設定を検証することを推奨します。
- 本番 (KABUSYS_ENV=live) では LINE 通知などの設定を確認してください（validate_config で警告あり）。

---

## 安全機構／運用上の注意

- kill flag:
  - settings.kill_flag_path（デフォルト: data/kill.flag）による強制停止・起動制御があります。
  - KILL_FLAG_CLEAR_ON_START=1 を本番で設定すると起動時に既存の kill.flag を消してしまうため危険です（デフォルトは 0）。
- PID 管理: 実行時に PID ファイルが書き込まれます。
- Reconciliation:
  - クラッシュ後は Reconciler が OrderSent の注文を broker と突合し、自動復旧を試みます。
- 発注フローはクラッシュ安全性を意識した設計（OrderSent の永続化など）になっていますが、本番運用前に十分なテストを行ってください。
- .env は機密情報を含むため絶対に Git にコミットしないでください。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・モジュールと簡単な説明です。

- src/kabusys/
  - __init__.py
  - config.py
    - Settings クラス: 環境変数から設定を取得
    - .env 自動ロードロジック
  - config_setup.py
    - 対話式 .env ウィザード
  - validate_config.py
    - 起動前チェック CLI（必須 env, YAML ファイル等）
  - run_execution.py
    - ExecutionEngine の起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - execution/
    - broker_api.py
      - BrokerAPIProtocol / データモデル / 例外 / create_broker_api
    - kabu_client.py
      - KabuStationClient（実ブローカ API）
    - mock_client.py
      - MockBrokerClient（テスト用）
    - broker_factory.py
      - Settings を元にブローカクライアントを生成
    - order_record.py
      - Order の状態遷移ロジック（純粋ビジネスロジック）
    - order_repository.py
      - SQLite 永続化層
    - order_manager.py
      - 発注フローの外向 API（create/send/sync/cancel）
    - execution_engine.py
      - シグナル処理〜pushドレイン〜セッション管理
    - reconciler.py
      - 起動時リコンシリエーション（OrderSent 突合、ポジション差分検出）
    - risk_manager.py
      - Gate1/2/3 によるリスク判定
  - data/
    - calendar_management.py
      - JPX カレンダー管理・営業日判定
    - news_collector.py
      - RSS ニュース収集（安全対策実装）
    - （jquants_client 等がある想定）
  - monitoring/
    - monitoring_db.py (参照される DB 初期化など)
    - system_monitor.py (SystemMonitor 実装)
  - utils/
    - logging_setup.py
    - process_priority.py

（実際のファイル・サブパッケージはコードベースに依存します。上は抜粋）

---

## 開発者向けメモ

- .env 自動読み込み:
  - プロジェクトルートは .git または pyproject.toml を探索して決定します。
  - 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途）。
- validate_config は PyYAML がない場合 YAML 内容検証をスキップします（警告）。
- MockBrokerClient は fill_mode（instant / partial / never / reject）を指定して挙動を制御できます。
- KabuStationClient の WebSocket push は websocket-client ライブラリの WebSocketApp を利用しています。
- DB 初期化関数（init_orders_db / init_monitoring_db 等）を呼んでテーブルを準備してください。

---

## 参考コマンドまとめ

- .env 作成ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行（発注）:
  ```bash
  python -m kabusys.run_execution
  ```

- 監視:
  ```bash
  python -m kabusys.run_monitoring
  ```

---

README は以上です。必要があればセットアップ手順や使い方を環境（開発 / テスト / 本番）別に分けた詳細ドキュメントを追加します。どの項目を詳しく書けば良いか指定してください。