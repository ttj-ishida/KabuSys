KabuSys
======

日本株向けの自動売買 / 研究プラットフォームのコア実装サンプル集です。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター研究、LLM を使ったニュース NLP / レジーム判定、ユーティリティ群などを含むモジュール構成になっています。

プロジェクト概要
--------------
- 実運用を想定したモジュール設計（プロセス優先度設定、ログ出力、DB マイグレーション、フェイルセーフ実装など）
- 発注系と監視系を分離（paper_trading モードでは本番 DB を分離）
- DuckDB を使った履歴・リサーチ処理、SQLite を使った監視・トレードログ永続化
- OpenAI API を用いたニュースセンチメント / マクロ判定のサンプル実装
- 簡易的な CLI（.env ウィザード、設定検証、検証レポート生成）

主な機能一覧
--------------
- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - paper_trading モードでは MockBrokerClient を使用し data/paper_trading.db に分離記録
  - リスク管理（RiskManager）や注文管理（OrderManager / OrderRepository）との組立て

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - run_monitoring スクリプト（python -m kabusys.run_monitoring）
  - SQLite に監視ログを永続化（monitoring_db）
  - Kill Switch（データ駆動で ExecutionEngine を停止させるフラグファイル）

- Portfolio Construction
  - 候補選定、等配分 / スコア配分、ポジションサイジング、セクターキャップ、レジーム乗数

- Research
  - DuckDB 上でのファクター計算（モメンタム・ボラティリティ・バリュー）
  - 将来リターン計算、IC（Information Coefficient）計算などの解析ユーティリティ

- AI（LLM）
  - ニュースセンチメントスコア（kabusys.ai.news_nlp）
    - OpenAI（gpt-4o-mini）を使用してニュースを銘柄別にスコア化
  - レジーム判定（kabusys.ai.regime_detector）
    - ETF の MA200 乖離とマクロニュースの LLM センチメントを合成して regime を判定

- ツール
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

セットアップ手順
----------------
前提
- Python 3.10+（コードは型ヒント等が含まれるため互換性に注意）
- SQLite は標準ライブラリで OK
- 以下の外部パッケージが必要（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（設定検証で YAML を検証する場合に必要）
これらは requirements.txt がある場合はそれを使うか、手動で pip install してください。

推奨手順
1. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML

3. .env の作成（推奨: 対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザードで JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD 等を入力し .env を生成

4. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合は --strict を付ける

5. データディレクトリ / ログディレクトリの確認
   - デフォルトの SQLite / DuckDB パスは .env で設定できます（デフォルト: data/monitoring.db, data/kabusys.duckdb）
   - ログは logs/<app_name>.log に日次ローテーションで出力されます（logs ディレクトリを作成）

環境変数の主なもの
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API を使うモジュールで必要
- DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH: DB ファイルパス
- LOG_LEVEL, LOG_DIR: ログ設定
- MONITOR_POLL_INTERVAL: run_monitoring が使うポーリング間隔（秒、デフォルト 60）

使い方
-------
起動スクリプト
- ExecutionEngine（取引エンジン）起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用の DB（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録されます。
    - 起動前に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid に PID が書き込まれます（設定で変更可能）。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - デフォルトは本番 sqlite_path を使用して監視ログを記録します（Monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を参照する設計）。
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒、デフォルト 60）。

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config [--strict]

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

注意事項（運用上のポイント）
- Kill Switch / stop flag
  - Execution と Monitoring はフラグファイル（data/kill.flag, data/stop_requested.flag 等）を読む／書くことで停止や停止要求を行います。ファイルの存在により起動可否や停止処理が制御されます。
  - Settings.kill_flag_clear_on_start を 1 にすると起動時に kill.flag を自動クリアします（本番では 0 を推奨）。

- ログ
  - 各アプリ名（execution / monitoring 等）ごとに logs/<app>.log に日次ローテーションで出力されます。ログディレクトリが作成できない場合はコンソール出力のみになります。

- OpenAI 連携
  - AI モジュール（news_nlp / regime_detector）は OPENAI_API_KEY を必要とします。API 呼び出しはリトライやフェイルセーフを備えていますが、API の料金やレートに注意してください。

ディレクトリ構成（主要ファイル）
---------------------------------
（src/kabusys 以下を省略表記）

- kabusys/
  - __init__.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — SystemMonitor ポーリング起動スクリプト
  - config.py                  — 環境変数/設定読み込みロジック（.env 自動ロード等）
  - config_setup.py            — .env 対話式ウィザード
  - validate_config.py         — 設定検証 CLI
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - execution/                  — 発注関連（OrderManager, ExecutionEngine, BrokerFactory 等）
    - (OrderRepository, OrderManager, Reconciler, RiskManager 等の実装を含む)
  - monitoring/
    - monitoring_db.py         — monitoring 用 SQLite 永続化層（テーブル作成 / CRUD）
    - system_monitor.py        — システム状態 / データ鮮度監視
    - trade_monitor.py         — （トレード監視ロジック）
    - risk_monitor.py          — ドローダウン・ポジション上限監視
    - kill_switch.py           — フラグファイルによる停止シグナル書き込み
    - monitoring_engine.py     — 各 Monitor を束ねるエンジン
  - portfolio/
    - portfolio_builder.py     — 候補選定・重み計算
    - position_sizing.py       — 発注株数計算
    - risk_adjustment.py       — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py       — ファクター計算（momentum, volatility, value）
    - feature_exploration.py   — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py              — ニュースセンチメント（OpenAI を利用）
    - regime_detector.py       — レジーム判定（MA200 + マクロ NLP）
  - utils/
    - logging_setup.py         — 統一ログ設定ユーティリティ
    - process_priority.py      — プロセス優先度 / CPU affinity 設定ユーティリティ

この README に記載の以外にも多くの補助関数や設計上の注意がコード中にコメントで記されています。実運用する際は .env の内容・KABUSYS_ENV の設定、DB のバックアップ、OpenAI API キー管理やコスト管理、Kill Switch の運用ポリシーなどを必ず検討してください。

開発支援
--------
- 単体実装の多くは純粋関数（副作用の少ない実装）で書かれており、ユニットテストが書きやすい構造です。
- DuckDB / SQLite に依存する部分はテスト用にインメモリ DB を使って検証できます。
- OpenAI 呼び出し部分はラッパー関数をモック可能に設計しています（テスト時は monkeypatch / patch で差し替え可能）。

ライセンス / 貢献
-----------------
実運用向けに利用する場合は各自の責任でコードの安全性・外部 API 利用ポリシー・資金管理を行ってください。外部ライブラリのライセンスや API 利用規約も遵守してください。

---
必要であれば、README に「環境変数の完全な一覧」や「起動例（systemd / cron / Supervisor 用）」、あるいは「主要な API / DB スキーマの詳細」などを追記します。どの情報が欲しいか教えてください。