README
======

概要
----
KabuSys は日本株向けの自動売買／リサーチ基盤です。本リポジトリには以下の主要機能を持つモジュール群が含まれます。
- 発注エンジン（ExecutionEngine）と注文管理・リスク管理
- 監視（Monitoring）: システム状態、注文状況、リスクを定期チェックして通知・Kill Switch を制御
- ポートフォリオ構築（候補選定、重み付け、株数算出、セクター制約）
- リサーチ（ファクター計算、特徴量探索）
- AI 補助（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- 開発用ユーティリティ（.env ウィザード、設定検証、Paper Trading レポート生成）

主な特徴
--------
- 明確に分離された「本番（live）」 / 「ペーパートレード（paper_trading）」モード（Paper は専用 SQLite DB を使用）
- DuckDB と SQLite を併用したデータ格納・分析設計
- Kill Switch（data/kill.flag）や stop フラグでプロセス制御が可能
- OpenAI を使ったニュース NLP による銘柄別センチメントと市場レジーム判定（API キー必須）
- ログはコンソールと日次ローテーションファイル（logs/*.log）に出力

前提・必須環境
--------------
- Python 3.10+ を推奨
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - sqlite3（標準ライブラリ）
- （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）

セットアップ手順（クイックスタート）
---------------------------------
1. リポジトリをクローン
   - git clone <repo-url>

2. 仮想環境を作って依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
   - pip install -r requirements.txt
   （requirements.txt がない場合は上記の主要ライブラリを個別に pip install してください）

3. .env の初期作成（対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants トークンや kabuAPI パスワードなどの入力を補助します
   - .env は絶対に Git にコミットしないでください

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります

5. データディレクトリの確認
   - デフォルトでは data/ 以下に DB・フラグ・PID 等が作成されます。必要に応じて .env で DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH を上書きしてください。

主要環境変数（主なもの）
-----------------------
- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading 時）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- LOG_LEVEL — ログレベル（例: INFO）
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト 60）

起動・使い方
------------

運用用プロセス
- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすると MockBrokerClient を使い data/paper_trading.db に記録します（本番 DB と分離）
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - ExecutionEngine の PID ファイルは data/execution.pid（設定可能）

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
  - 監視は Settings.sqlite_path（※監視は常に本番 sqlite_path を参照）と DuckDB を使います
  - 停止: プロジェクトルート/data/stop_requested.flag を作成すると監視ループが終了します

ユーティリティ
- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告もエラー扱い

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数の代替）

AI / OpenAI 関連
- ニュースセンチメント: kabusys.ai.news_nlp.score_news
- 市場レジーム判定: kabusys.ai.regime_detector.score_regime
- 両機能とも OPENAI_API_KEY が必要です。API 呼び出し時はリトライ・フォールバックが組み込まれており、失敗時には安全側で継続します。

停止・Kill フラグ
-----------------
- ExecutionEngine 停止用フラグ
  - data/stop_requested.flag を作成すると run_execution で起動中のエンジンを停止する（または起動をスキップ）
- Kill Switch（監視が発動して ExecutionEngine を止める仕組み）
  - data/kill.flag（設定は Settings.kill_flag_path）に理由を書き込むことで ExecutionEngine に停止を促す
  - KillSwitch.clear() に相当する処理は起動時に KILL_FLAG_CLEAR_ON_START を設定すると自動でクリアできます（ただし本番では 0 を推奨）

ログ
---
- ログは標準出力と logs/<app_name>.log（日次ローテーション、30日分保存）へ出力されます
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に行われます

ライブラリとしての利用例
-----------------------
- リサーチ（ファクター計算）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - DuckDB 接続を渡して関数を呼び出します（prices_daily / raw_financials テーブルを参照）

- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier

ディレクトリ構成（抜粋）
----------------------
プロジェクトの主要なファイル／ディレクトリを抜粋で示します（src/kabusys 以下）。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings 管理
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py             — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py      — 市場レジーム判定（OpenAI 混合）
  - research/
    - factor_research.py
    - feature_exploration.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は主要ファイルの抜粋です。詳細は src/kabusys 以下のソースを参照してください。）

運用上の注意
------------
- .env に API トークンやパスワードを保存する場合はアクセス管理に注意し、Git には絶対に含めないでください。
- KABUSYS_ENV=live の場合は特に Kill Switch / 通知設定（LINE_TOKEN など）を十分に整えてから運用してください。
- OpenAI 呼び出しは API コストが発生します。ペーパートレードやローカル検証時はキーの使用に注意してください。

サポート / 開発
----------------
ソースコードを参照してユニットテストや追加ドキュメントを整備してください。機能追加やバグ修正はモジュール単位で分かりやすく分割されているため、テストと差し替えが容易です。

以上。README に不足する情報（依存関係ファイル、起動オプションの詳細、実行例など）を追加したい場合は、どの項目を詳しく書くか教えてください。