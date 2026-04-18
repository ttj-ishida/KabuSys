# KabuSys

日本株向け自動売買システム（KabuSys）のリポジトリ説明書。  
この README はコードベースを元に、プロジェクト概要・機能一覧・セットアップ手順・使い方・ディレクトリ構成を日本語でまとめたものです。

目次
- プロジェクト概要
- 主な機能
- 必要条件（依存関係）
- セットアップ手順
- 使い方（主要スクリプト・コマンド）
- 環境変数（代表的なもの）
- 実行時の挙動に関する注意点
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（研究用／ペーパートレード／本番）です。  
主要なサブシステム：
- Execution Engine：発注管理、リスク管理、約定・注文履歴の永続化
- Monitoring：システム監視・データ鮮度チェック・キルスイッチ
- Research / Factors：ファクター計算、特徴量探索
- AI：ニュース NLP によるセンチメント評価、レジーム判定（OpenAI を利用）
- Portfolio：銘柄候補選定、重み付け、ポジションサイジング
- Tools：ペーパートレード検証レポートなどのスクリプト

設計上の要点：
- DB：監視・発注履歴は SQLite（monitoring DB、paper_trading 用 DB 等）、分析は DuckDB を使用
- 環境分離：KABUSYS_ENV に応じて paper_trading（モックブローカー + data/paper_trading.db）や live（本番）等を切替
- .env と config/*.yaml で設定を管理。config_setup.py による対話式 .env 生成支援あり
- OpenAI（gpt-4o-mini）を利用する AI モジュールは API エラーに対してフェールセーフな設計

---

## 主な機能

- システム監視（CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度チェック）
- リスク監視（ドローダウン警告、ポジション上限検出、リスクログ）
- Kill Switch：閾値超過時に data/kill.flag を書き込み ExecutionEngine を安全に停止
- ExecutionEngine：ブローカーインターフェース、注文管理、約定ログの永続化
- ペーパートレード対応：KABUSYS_ENV=paper_trading 時は MockBroker を使用し本番 DB と分離
- ポートフォリオ構築ユーティリティ（候補選定・重み計算・ポジションサイズ）
- ファクター計算（モメンタム・ボラティリティ・バリュー等）と研究用ユーティリティ（IC 計算等）
- ニュース NLP：OpenAI を使った銘柄別センチメントスコア生成（ai_scores テーブルへ書込）
- レポート生成：ペーパートレードの検証レポート出力スクリプト

---

## 必要条件（依存関係）

最低限の Python 環境が必要です（例: Python 3.9+ 推奨）。代表的な Python ライブラリ：
- duckdb
- psutil
- openai
- PyYAML（config の内容検証を行う場合）
- （その他）標準ライブラリのみで動作するモジュール多数

インストール例（仮）：
pip install duckdb psutil openai pyyaml

※ 実際の配布では requirements.txt / pyproject.toml を参照してください。  

---

## セットアップ手順

1. リポジトリを取得
   - git clone してクローンしてください。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージのインストール
   - pip install duckdb psutil openai pyyaml
   - 必要に応じて他のパッケージを追加してください。

4. .env の作成
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - もしくは手動で .env を作成（プロジェクトルートに保存）。
   - .env.example が存在する場合、それを参考に設定してください。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳密に扱いたい場合: python -m kabusys.validate_config --strict

6. DB 初期化
   - 実行スクリプトが起動時に必要テーブルを作成します（init_monitoring_db が冪等でテーブルを作成）。
   - DuckDB 用のファイルパス（DUCKDB_PATH）が存在しない場合はディレクトリを作成してください。

7. OpenAI を使用する機能を使う場合
   - OPENAI_API_KEY を .env に設定

---

## 使い方（主要スクリプト・コマンド）

各スクリプトはモジュールとして実行できます（python -m ...）。

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Execution Engine 起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録
    - 起動時に data/stop_requested.flag があれば起動せず終了
    - data/execution.pid に PID を書く（設定で異なる可能性あり）

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可。デフォルト 60 秒。
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用して監視データを記録します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラムから呼び出す API）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - raw_news / news_symbols / ai_scores テーブルを使って OpenAI で銘柄別スコアを作成し ai_scores に書き込む
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - マクロニュース + ETF (1321) の MA200 を組合せて market_regime テーブルに書込

- ライブラリ利用
  - portfolio モジュール等はスクリプトからインポートして利用可能
    - 例: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes

---

## 環境変数（代表的なもの）

必須（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

重要なオプション／設定
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト INFO）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で必須）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- PAPER_FILL_MODE — ペーパートレード時の約定モード（instant/partial/never/reject）
- LOG_DIR — ログの出力ディレクトリ（logs デフォルト）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — 監視・キルフラグ関連

詳細は kabusys.config.Settings のプロパティと config_setup.py を参照してください。

---

## 実行時の注意点・設計上の考慮

- Monitoring は常に本番の SQLITE_PATH を参照して監視データを記録します（環境にかかわらず）。そのため監視 DB の配置に注意してください。
- KABUSYS_ENV=paper_trading を指定すると Execution は MockBroker を使い、paper_trading 用の別 DB に記録されます。本番 DB とデータを分離できます。
- Kill Switch（data/kill.flag）は一度書かれると存在する限り Execution 停止を促します。KILL_FLAG_CLEAR_ON_START=1 に設定すると起動時に自動クリアされますが、本番では危険です（デフォルト 0 推奨）。
- OpenAI を使う機能は API のエラーやレート制限を考慮してリトライ・フェールセーフを実装していますが、API キーやコスト管理に注意してください。
- ログは logs/<app_name>.log に日次ローテーションで保存されます。LOG_DIR を環境変数で指定可能です。
- DB マイグレーション（monitoring_db.init_monitoring_db）は起動時に自動で必要カラムを追加する処理を行います（冪等）。

---

## ディレクトリ構成（抜粋）

プロジェクトルート（src/kabusys/）を基準にした主要ファイル／パッケージ:

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py      — 市場レジーム判定（LLM + MA）
    - __init__.py
  - monitoring/
    - monitoring_db.py        — SQLite 永続層（監視）
    - system_monitor.py
    - trade_monitor.py        — （注文監視ロジック）
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py        — （アラート通知）
  - execution/
    - execution_engine.py     — ExecutionEngine 本体
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - data/                     — 実行時データ (例: data/monitoring.db, data/paper_trading.db, data/kill.flag 等)
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（上記は主要なファイル群の抜粋です。細かいモジュールは repo を参照してください。）

---

README の補足・推奨ワークフロー
- 開発環境では KABUSYS_ENV=development を使用し、ペーパートレード検証は paper_trading 環境で行うことを推奨します。
- 本番（live）に切り替える前に必ず python -m kabusys.validate_config を実行して設定の妥当性を確認してください。
- 定期的なモニタリング（run_monitoring）は systemd / cron / Supervisor 等でデーモン化することを推奨します。
- AI 機能を運用で使う際は OpenAI のレート・コスト・キー管理に注意してください。

---

必要に応じて README に追記します。特定のコマンド例や .env のテンプレート、デプロイ手順（systemd サービスファイル例など）を追加希望があれば教えてください。