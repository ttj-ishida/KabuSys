# KabuSys

日本株向けの自動売買システム（ミニマム実装）。  
このリポジトリは発注ロジック、リスク管理、監視、モックブローカー等の主要コンポーネントを含むサンプル実装です。

## 概要
KabuSys は以下の目的を持つモジュール群を提供します。

- シグナルに基づく発注エンジン（ExecutionEngine）
- 発注の状態遷移管理（OrderRecord / OrderManager）
- 注文永続化（SQLite を利用する OrderRepository）
- 発注前後のリスクガード（RiskManager：Gate1/2/3）
- 再起動時の復旧・照合（Reconciler）
- 本番向け REST ブローカークライアント（KabuStationClient）およびテスト用モック（MockBrokerClient）
- 監視ループ（SystemMonitor を起動する run_monitoring）
- 環境設定ウィザード（.env を生成する config_setup）および設定検証ツール（validate_config）

このコードベースは、実際のブローカー API（kabuステーション）を利用する際の構造例として設計されていますが、デフォルトではペーパートレード／開発用にモッククライアントが使えるようになっています。

## 主な機能一覧
- .env ウィザードでの対話的な初期設定（python -m kabusys.config_setup）
- .env と config/*.yaml の事前検証 CLI（python -m kabusys.validate_config）
- Signal-Pull 型の発注エンジン（ExecutionEngine）
- 注文状態遷移を厳密に扱う OrderRecord
- SQLite による注文永続化（orders テーブル、インデックス、ユニーク制約付き）
- 3 段階（Gate1/2/3）によるリスク管理（余力・重複・ポジション上限、レート制限・CB、ドローダウン）
- リコンシリエーション（OrderSent 状態の再照合・ポジション差異検出）
- WebSocket Push 受信による注文同期（kabu push）
- MockBrokerClient による fill モード切り替え（instant / partial / never / reject）
- DuckDB を利用したデータ（シグナル / カレンダー / position_entries 等）の参照・更新

## 依存関係（主なパッケージ）
必須／代表的なパッケージ（環境に応じて適宜インストールしてください）:

- Python 3.9+
- duckdb
- httpx
- websocket-client
- defusedxml
- pyyaml（YAML の詳細検証を有効にしたい場合）
- sqlite3（標準ライブラリ）

インストール例（最小）:
pip install duckdb httpx websocket-client defusedxml

YAML 検証を行いたい場合:
pip install pyyaml

（プロジェクト用 requirements.txt がある場合はそちらを使用してください）

## セットアップ手順（ローカルでの開発開始例）
1. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

2. 依存パッケージをインストール
   pip install duckdb httpx websocket-client defusedxml pyyaml

3. 対話式に .env を作成（推奨）
   python -m kabusys.config_setup
   - 指示に従って J-Quants トークンや kabu API パスワード等を設定します。
   - 生成された .env は決して Git にコミットしないでください。

4. 設定を検証
   python -m kabusys.validate_config
   - 警告もエラー扱いにする場合: --strict

5. 必要データベース / ディレクトリを用意
   - デフォルトで data/ 以下に DB や PID/flag ファイルを作る設計です。起動時に自動作成される項目もありますが、権限等に注意してください。

## 重要な環境変数（主なもの）
設定は OS 環境変数、.env.local、.env の順でロードされます（OS > .env.local > .env）。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD     — kabuステーション API 用パスワード

代表的なオプション:
- KABUSYS_ENV — 実行環境: development | paper_trading | live（既定: development）
- DUCKDB_PATH — DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（既定: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（既定: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- KABU_API_BASE_URL — kabu station のベース URL（既定: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知設定（本番でのアラートに必要）
- KILL_FLAG_PATH — kill.flag のパス（既定: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、既定: 0）
- PAPER_FILL_MODE — paper_trading 用の fill モード（instant | partial | never | reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、既定: 60）

validate_config では config/ 下の YAML ファイル群（system_config.yaml 等）が存在するかをチェックします。ファイルが足りない場合は警告となります（PyYAML が未インストールだと内容検証はスキップされます）。

## よく使うコマンド / 使い方
- 環境ウィザード（対話式 .env 作成）
  python -m kabusys.config_setup

- 設定検証（起動前チェック）
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict  # 警告も FAIL 扱い

- 実行エンジン起動（プロダクション / テスト）
  python -m kabusys.run_execution
  - KABUSYS_ENV により挙動が分岐します。development / paper_trading では MockBrokerClient を利用。live は未実装（明示的に NotImplementedError を投げます）。
  - 起動時に data/execution.pid が書き込まれ、data/stop_requested.flag の存在で停止する設計です。

- 監視ループ起動
  python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（既定 60 秒）。
  - 監視は sqlite（settings.sqlite_path）を使用します（paper_trading でも本番 sqlite_path を使う設計）。

- テスト／開発向けモック
  - MockBrokerClient は paper_trading / development で利用され、fill_mode により約定挙動を制御できます（instant / partial / never / reject）。
  - create_broker_api(mock=True, fill_mode=...) で作成できます。

## 設計上の注意点（運用上のポイント）
- .env は絶対に Git に含めないこと（config_setup のヘッダにも注意書きあり）。
- 起動時に kill.flag が存在すると基本的に起動を拒否します。KILL_FLAG_CLEAR_ON_START=1 にすると自動クリアして起動できます（本番では 0 を推奨）。
- 発注は二相永続化を採用（OrderSent を永続化 → ブローカー呼出 → broker_order_id を永続化 → OrderAccepted に遷移）し、クラッシュ後の復旧を容易にしています。
- サーキットブレーカー、レート制限、ドローダウン監視などのリスク制御を組み込んでいます。パラメータは RiskConfig で調整できます。
- live 環境での本番ブローカークライアント（KabuStationClient）は実装済みですが、BrokerClientFactory は live を未許可（NotImplementedError）として安全側に設計されています。運用時は慎重に有効化してください。

## ディレクトリ構成（主要ファイル）
プロジェクトの主要ファイル・モジュールは次の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数読み込み・Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前チェック CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - execution/
    - __init__.py
    - broker_api.py          — BrokerAPI の Protocol / データモデル / ファクトリ
    - broker_factory.py      — Settings に基づくブローカー生成
    - kabu_client.py         — kabu station REST API クライアント
    - mock_client.py         — MockBrokerClient（テスト用）
    - order_record.py        — OrderRecord（状態遷移）
    - order_repository.py    — SQLite 永続化層（orders テーブル）
    - order_manager.py       — OrderManager（外向き API）
    - execution_engine.py    — ExecutionEngine（シグナルプル + push ドレイン）
    - reconciler.py          — リコンシリエーション / 復旧
    - risk_manager.py        — リスクガード（Gate1/2/3）
    - ...（その他実装ファイル）
  - data/
    - calendar_management.py — マーケットカレンダー管理（DuckDB）
    - news_collector.py      — RSS ニュース収集（defusedxml 等）
    - jquants_client.py      — （参照される想定の J-Quants クライアント）
  - monitoring/
    - monitoring_db.py      — 監視 DB 初期化 / ログ機能
    - system_monitor.py     — システム監視ロジック
  - utils/
    - logging_setup.py      — ロギング初期化
    - process_priority.py   — プロセス優先度設定ユーティリティ

（上記はコードベースの抜粋です。実プロジェクトではさらに多くのモジュールやスクリプトが含まれる想定です）

## 開発メモ / トラブルシューティング
- .env の自動読み込みは OS 環境変数を上書きしないよう保護されています。テスト時に明示的に .env を読み込ませたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って無効化できます。
- validate_config は PyYAML の有無により config/*.yaml の中身検証をスキップします（存在チェックは行います）。YAML パーサが不要な軽量実行をする場合は PyYAML を入れなくても OK ですが、本番ではインストール推奨です。
- DuckDB / SQLite のパスに指定されるディレクトリが存在しないと警告が出ますが、多くは起動時に自動作成されます。ただし権限やパスの整合性には注意してください。
- run_execution / run_monitoring は stop フラグ（data/stop_requested.flag）や kill.flag を設計上利用します。運用スクリプトからこれらを触ることで安全に停止できます。

---

この README はコードベースの主要点をまとめた概要です。詳しい実装や追加の設定項目はソース内コメントおよび各モジュールの docstring を参照してください。ご不明点や追加のドキュメントが必要であれば教えてください。