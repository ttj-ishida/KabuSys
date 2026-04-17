# KabuSys

日本株向け自動売買システムのコアライブラリ群（ドキュメント用簡易 README）。  
この README はリポジトリ内の主要スクリプト・モジュールから要点を抜粋して作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買／バックテスト／リサーチ機能を持つモジュール群です。  
主な責務は以下の通りです：

- データ格納・分析（DuckDB / prices_daily / raw_financials 等）
- シグナル生成とポートフォリオ構築（portfolio パッケージ）
- 注文実行とリスク管理（execution パッケージ — エンジン起動スクリプトあり）
- 監視・アラート（monitoring パッケージ）
- LLM を用いたニュース NLP / レジーム判定（ai パッケージ）
- 開発支援ツール（設定ウィザード、設定検証、ペーパートレード検証レポート等）

設計方針として、実際の発注系・本番 DB の分離（paper_trading モードでの専用 DB）、ルックアヘッドバイアス防止、外部 API 呼び出しのフェイルセーフ、単一責任のモジュール化が採られています。

---

## 主な機能一覧

- Execution 起動スクリプト（run_execution.py）
  - KABUSYS_ENV が `paper_trading` のときは MockBrokerClient を使用し、ペーパートレード専用 DB（デフォルト: data/paper_trading.db）に記録
  - プロセス優先度設定、PID ファイル管理、停止フラグ（data/stop_requested.flag）対応

- Monitoring 起動スクリプト（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor 等をポーリングしログ（SQLite）へ記録
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト: 60 秒）
  - 監視は環境に関わらず本番 sqlite_path を参照する点に注意

- 設定関連
  - Settings クラス（kabusys.config）: 環境変数・.env の自動読み込み（.env, .env.local）／必須項目チェック
  - config_setup.py: 対話式 .env 生成ウィザード
  - validate_config.py: 起動前チェック CLI（--strict あり）

- 研究・リサーチ
  - research パッケージ: ファクター計算（momentum/value/volatility）、forward returns、IC 計算、統計サマリ等（DuckDB 経由）

- ポートフォリオ構築
  - portfolio パッケージ: 候補選定、等重配分／スコア重み、リスク調整（セクターキャップ、レジーム乗数）、ポジションサイズ計算（単元丸め・集約調整）

- AI（LLM）連携
  - ai.news_nlp: raw_news を集約して OpenAI API（gpt-4o-mini）で銘柄別センチメントを取得 → ai_scores テーブルへ保存
  - ai.regime_detector: ETF (1321) の MA とマクロニュースを組み合わせて市場レジーム判定 → market_regime テーブルへ永続化
  - API 呼び出しはリトライ／バックオフ／バリデーション処理あり。API キーは OPENAI_API_KEY 環境変数または関数引数で指定

- 監視・アラート
  - monitoring パッケージ: system_monitor, trade_monitor, risk_monitor, monitoring_engine, alert_manager（LINE push）
  - KillSwitch: 条件（例: ドローダウン超過、ポジション上限超過）で data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送る

- ユーティリティ
  - process_priority: psutil を使ったプロセス優先度 / CPU affinity 設定ユーティリティ

- ツール
  - tools.paper_verification_report: ペーパートレード DB を集計して PASS/FAIL レポートを標準出力に出力

---

## 前提・インストール

必須（実行に最低限必要なもの）：
- Python 3.9+（コードで型注釈を利用）
- pip

主な依存パッケージ（抜粋）：
- duckdb
- psutil
- openai
- requests
- PyYAML（config.yaml の検証に必要だが任意）
- そのほか実行環境に応じた依存がある場合があります

例: 仮想環境を作り必要パッケージをインストールする（requirements.txt がある場合はそちらを利用）:

1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - pip install duckdb psutil openai requests PyYAML

※ 実際のプロジェクトでは requirements.txt を用意することを推奨します。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション（デフォルト値や説明付き）:
- KABUSYS_ENV: execution モード。valid: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（INFO 等）
- OPENAI_API_KEY: OpenAI API キー（ai モジュールで利用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用（任意）
- MONITOR_POLL_INTERVAL: run_monitoring.py のポーリング間隔（秒）を上書き（例: 30）
- PAPER_FILL_MODE: ペーパートレードでの約定挙動（instant / partial / never / reject）

Settings は .env, .env.local を自動ロードします（プロジェクトルートが自動検出できない場合はスキップ）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

---

## セットアップ手順（簡易）

1. リポジトリをクローンしてプロジェクトルートへ移動
2. 仮想環境作成・有効化
3. 依存パッケージをインストール
4. .env を作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 生成後: python -m kabusys.validate_config で検証（--strict を付けると警告もエラー扱い）
5. 必要な DB ディレクトリ（data/ 等）を作成
6. DuckDB に prices_daily / raw_financials 等を投入（外部スクリプトや ETL パイプラインが別途必要）

---

## 使い方（代表的なコマンド）

- 設定ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数で間隔を変更: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 注意: monitoring は環境にかかわらず settings.sqlite_path（本番）を使用します

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient が使用され、PAPER_TRADING_SQLITE_PATH に記録されます

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定: --db PATH（指定がない場合は env またはデフォルトを使用）

- AI モジュール呼び出し（例: ニューススコア）
  - スクリプトから関数を呼ぶ例:
    - from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=...)
  - 必要: OPENAI_API_KEY または引数で API キーを指定

---

## 重要な挙動・注意点

- run_monitoring.py は MONITOR_POLL_INTERVAL でポーリング。0 以下が指定されるとデフォルト（60 秒）にフォールバックします。
- run_monitoring.py と monitoring 系は監視用 SQLite（settings.sqlite_path）を使用し、KABUSYS_ENV に依存しません（意図的）。
- run_execution.py は KABUSYS_ENV=paper_trading の場合 DB を分離（settings.paper_sqlite_path）し、実発注を行いません。
- Kill Switch / Stop フラグ:
  - data/stop_requested.flag: 起動スクリプトが存在を検知すると終了処理を行うための内部停止フラグ（run_monitoring/run_execution で使用）
  - data/kill.flag: KillSwitch が監視条件により書き込むファイル。ExecutionEngine はこのファイル存在を検出して安全停止します
- OpenAI API 呼び出しは外部ネットワークを使用します。API のエラーやレート制限はリトライ戦略で扱われますが、API キー未設定だと例外になる関数もあります（明記）。
- process_priority.set_process_priority() は psutil を使用。権限が不足する場合は警告を出してスキップします。
- DB スキーマは monitoring_db.init_monitoring_db() により冪等に初期化／簡易マイグレーションされます（例: カラム追加など）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内の src/kabusys を前提）

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_monitoring.py            — 監視ポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - execution/                    — 発注エンジン関連（OrderManager 等、リポジトリ参照）
  - data/                         — デフォルトの DB/フラグファイル格納場所（data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag など）

---

## よくある運用上のヒント / トラブルシューティング

- .env を編集したら python -m kabusys.validate_config で起動前のチェックを行うと設定漏れを早期発見できます。
- run_execution を本番で動かす場合は KABUSYS_ENV=live の設定を十分に確認し（LINE 通知や Kill Switch の設定等）慎重に運用してください。
- psutil による優先度設定や cpu_affinity 設定は環境（OS・権限）に依存します。権限不足だと警告が出るだけで処理は継続しますが、意図した優先度にならないことがあります。
- OpenAI 関連は API 利用料が発生します。ローカル開発・テストではモック／スタブ化して呼び出しを避けてください（モジュール内で呼び出し関数を差し替えられる設計になっています）。
- DuckDB / SQLite のファイルパスは Settings でカスタマイズ可能です。複数プロセスで同一ファイルを扱う際はロックや同時書き込みの影響を考慮してください（通常の運用で問題にならないように設計されていますが、環境依存の問題が発生する可能性あり）。

---

この README はコードベースの主要点をまとめたものです。実運用や拡張を行う際は各モジュールの docstring や関数コメント（コード内）を参照してください。もし README をプロジェクト用に整備して requirements.txt、使用例、図、ユースケース別の手順などを追加したい場合は、目的に合わせて追記できます。