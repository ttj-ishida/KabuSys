# KabuSys

日本株自動売買システム（KabuSys）のコードベース README。

以下はリポジトリ内の主要コンポーネントの説明、セットアップ手順、実行方法およびディレクトリ構成の要約です。

---

## プロジェクト概要

KabuSys は kabuステーション や J-Quants 等を利用した日本株の自動売買向けフレームワークです。  
主に以下を提供します。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注状態管理（OrderState / OrderRecord / OrderRepository）
- ブローカー API 抽象レイヤ（実環境用 / モック）
- リスク管理（3段階ゲート：シグナル、エグゼキューション、メトリクス）
- 起動時リコンシリエーション（Reconciler）
- 監視プロセス（SystemMonitor/監視DB）
- データ側：マーケットカレンダー管理、ニュース収集など
- 環境設定ウィザード（.env 生成）と設定検証ツール

設計上、DB（SQLite / DuckDB）により状態を永続化し、クラッシュ耐性・再起動時復旧（Reconciliation）を重視しています。開発 / ペーパートレード用に MockBrokerClient を用意しており、kabuステーションを実際に起動せずにテスト可能です。

---

## 主な機能一覧

- .env 対話式セットアップウィザード（kabusys.config_setup）
- 起動前設定検証 CLI（kabusys.validate_config）
- ExecutionEngine（シグナル読み取り → 発注 → push ドレイン）
- Order 管理：OrderRecord（状態遷移）、OrderRepository（SQLite 永続化）、OrderManager（API 呼び出しフロー）
- ブローカーファクトリ（Mock / 実実装の切替）
- RiskManager（Gate1/2/3：余力・重複・ポジション上限、レート制限・サーキットブレーカー、ドローダウン）
- Reconciler（OrderSent 状態の自動復旧・ポジション差分検出）
- Monitoring（定期ポーリングでシステムメトリクス等を収集）
- データユーティリティ：マーケットカレンダー（next_trading_day 等）、ニュース収集（RSS 前処理）

---

## 前提条件（推奨）

- Python 3.9+
- pip（仮想環境推奨）
- システムに応じて以下ライブラリをインストール:
  - duckdb
  - httpx
  - websocket-client
  - defusedxml
  - PyYAML（config 検証の YAML パースに使用。未インストールでも動くが内容検証はスキップされる）
- （本番で kabu station と連携する場合）kabuステーションアプリが稼働していること

依存関係はプロジェクトの requirements.txt にまとめてください（本コードベースではファイル未提供のため、上記を手動でインストールしてください）。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb httpx websocket-client defusedxml PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
2. 仮想環境を作成して依存をインストール（上記参照）
3. .env を作成（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードは .env（デフォルトはプロジェクトルート/.env）を生成・更新します。
4. 生成した .env を検証
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を指定すると警告も失敗扱い（exit code 1）になります。
5. DB 初期化やデータ取得が必要な場合はプロジェクト内スクリプト（存在するなら）を実行してください。
   - 例: DuckDB に分析用スキーマを用意する等（プロジェクト固有のスクリプトに従う）。

---

## 環境変数（主要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

任意（主要なもの）:
- KABUSYS_ENV: execution 環境（development / paper_trading / live）。デフォルト: development
  - paper_trading / development → MockBrokerClient を使用（実際の発注を行わない）
  - live → 実ブローカー（未実装の箇所あり、注意）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- LOG_LEVEL: ログレベル（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- KABU_API_BASE_URL: kabu station API ベース URL（デフォルト http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番通知（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時 kill.flag を自動クリアするか（0/1。デフォルト 0）
- PAPER_FILL_MODE: paper_trading 時のモックの約定動作（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

自動環境ロード:
- OS 環境変数 > .env.local > .env の順で読み込まれます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます（テスト用途）。

サンプル minimal .env（ウィザード実行で生成推奨）:
```
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

---

## 使い方（主要 CLI / スクリプト）

- 環境設定ウィザード（.env 作成・更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視プロセス起動（SystemMonitor ポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。
  - 監視は設定にかかわらず本番の sqlite_path を使用します（SQLite ファイルは設定参照）。
  - 停止フラグ: プロジェクトルート/data/stop_requested.flag を作成するとループを終了。

- 発注エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite に記録（data/paper_trading.db）。
  - kill.flag（data/kill.flag）が存在すると起動を拒否（KILL_FLAG_CLEAR_ON_START=1 の場合は起動時に削除して開始）。
  - 実行中に停止させるには stop_requested.flag を作成するか、kill.flag を作成して kill_switch を発動。

- 開発用モックブローカー（テスト）
  - MockBrokerClient の fill_mode は環境変数 `PAPER_FILL_MODE` で制御できます（instant / partial / never / reject）。

---

## 実装上の注意点 / トラブルシューティング

- validate_config は PyYAML がない場合、config/*.yaml の内容検証をスキップします（存在確認のみ）。PyYAML をインストールすると YAMl のパース検証が有効になります。
- ExecutionEngine はセッション時間（デフォルト 8:50 - 15:30）に基づき動作し、シグナル処理・push ドレインを行います。テストでは内部メソッドを直接呼ぶことが想定されています。
- Order 管理はクラッシュ耐性を考慮し、OrderSent の永続化→ブローカー呼び出し→broker_order_id 永続化→OrderAccepted 遷移の順で二相的に永続化されます。クラッシュ後の復旧は Reconciler により行われます。
- 本番で LINE 通知を使う場合は LINE のトークンとユーザーIDを設定してください。設定がないと通知が送られません（validate_config で警告）。

---

## ディレクトリ構成（抜粋）

（プロジェクトルートの src/kabusys を基準に主要ファイルを列挙）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数読み込み / Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 起動前設定検証 CLI
  - run_monitoring.py            — 監視プロセス起動スクリプト
  - run_execution.py             — 発注エンジン起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py              — BrokerAPIProtocol, データモデル, 例外, ファクトリ
    - broker_factory.py          — Settings に応じたクライアント生成
    - kabu_client.py             — kabu station REST クライアント（httpx）
    - mock_client.py             — MockBrokerClient（テスト用）
    - order_record.py            — OrderRecord（状態遷移ロジック）
    - order_repository.py        — SQLite を使った永続化層
    - order_manager.py           — 発注フロー / 同期 / キャンセル
    - execution_engine.py        — ExecutionEngine（シグナル処理 + push ドレイン）
    - reconciler.py              — 起動時リコンシリエーション
    - risk_manager.py            — 3段階リスクガード
  - data/
    - calendar_management.py     — マーケットカレンダー管理（next_trading_day など）
    - news_collector.py          — RSS ニュース収集（前処理 / 保存ロジック）
    - jquants_client.py          — （参照あり、J-Quants との連携）
  - monitoring/
    - monitoring_db.py           — 監視 DB 初期化 / 書き込み（使用箇所あり）
    - system_monitor.py          — 実際の監視ロジック（使用箇所あり）
  - utils/
    - logging_setup.py           — ログセットアップユーティリティ
    - process_priority.py        — プロセス優先度設定ユーティリティ

上記以外に strategy, data platform 向けユーティリティ等のモジュールが存在する想定です。

---

## 開発・テストのヒント

- 本番動作を想定する場合は KABUSYS_ENV=live、ただしコード内にある Live broker client 部分は将来的な実装依存のため現状は注意が必要です。
- 単体テストでは MockBrokerClient を利用して API 呼び出しや発注フローを検証してください（KABUSYS_ENV を paper_trading / development に設定）。
- DB 初期化関数（init_orders_db, init_monitoring_db など）をテストセットアップで呼んでテーブルを作成してください。
- リプレイや解析用に DuckDB を利用する設計のため、DuckDB 上でのクエリやシグナル生成ロジックは検証対象になります。

---

## 最後に

- .env は絶対にリポジトリにコミットしないでください（config_setup.py も同様に警告を表示します）。
- 起動前に必ず `python -m kabusys.validate_config` で設定チェックを行ってください。

必要に応じて README をプロジェクトの実情に合わせて拡張（依存の正確なバージョン、Docker イメージ、CI 設定、テスト手順などの追加）してください。