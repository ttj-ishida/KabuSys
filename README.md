README
======

概要
----
KabuSys は日本株向けの自動売買/リサーチ基盤ライブラリです。  
このリポジトリには、発注実行エンジン（ExecutionEngine）、システム監視（Monitoring）、ポートフォリオ構築・ポジション算出、リサーチ用ファクター計算、AIを用いたニュースセンチメント評価などの主要コンポーネントが含まれます。設計方針として「本番系とペーパートレードを分離」「ルックアヘッドバイアスを避ける」「外部 API 呼び出しは明示的に行う（テストしやすさ）」が取られています。

主な機能
--------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV に応じて本番またはペーパートレード（MockBrokerClient）を自動選択
  - ペーパートレード時はデータベースが本番 DB と分離（デフォルト: data/paper_trading.db）
  - PID ファイル管理、停止フラグ（data/stop_requested.flag / data/kill.flag）との連携
- Monitoring（run_monitoring.py / monitoring/*）
  - システム稼働状況（CPU/メモリ/ディスク）、データ鮮度、注文滞留・約定異常、ドローダウン／ポジション上限監視
  - Kill Switch（条件に応じて data/kill.flag を書き込み、Execution を停止させる）
  - 監視ログは SQLite（デフォルト: data/monitoring.db）へ保存（スキーマは自動初期化）
- Portfolio（portfolio/*）
  - 候補選定（スコア/ランク）、等配分・スコア重み付け、セクター制限、レジーム乗数、ポジションサイズ算出（単元丸め・利用可能資金に応じたスケール）
- Research（research/*）
  - DuckDB を使ったファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC 計測、ファクター統計要約
- AI（ai/*）
  - ニュースを LLM（OpenAI）で評価し ai_scores テーブルへ書き込み（news_nlp.score_news）
  - マクロニュース＋ETF MA を組み合わせた市場レジーム判定（regime_detector.score_regime）
  - API 失敗時はフェイルセーフで継続（規定のフォールバック値を使用）
- ツール（tools/*）
  - Paper Trading の検証レポート生成（tools/paper_verification_report.py）
- 設定管理
  - .env 自動ロード（プロジェクトルートを検出）
  - 対話式設定ウィザード（config_setup.py）
  - 起動前設定検証 CLI（validate_config.py）

セットアップ手順
----------------
1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - pip install duckdb psutil openai
   - 追加（任意）: PyYAML（config/*.yaml の検証に使用）
     - pip install pyyaml

   （プロジェクトに requirements.txt がある場合はそれを利用してください。）

3. ディレクトリ作成
   - data ディレクトリを作成（DB / PID / フラグファイル用）
     - mkdir -p data

4. .env 作成（推奨: 対話式ウィザード）
   - python -m kabusys.config_setup
   - ウィザード実行後、.env が生成されます（.env は絶対に Git にコミットしないでください）。

5. 設定検証
   - python -m kabusys.validate_config
   - 警告を厳格扱いする場合は --strict を付与

主要な環境変数（主なもの）
-------------------------
- JQUANTS_REFRESH_TOKEN : J-Quants API 用（必須）
- KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
- OPENAI_API_KEY        : OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV           : 実行環境（development | paper_trading | live）デフォルト: development
  - paper_trading の場合、発注は MockBrokerClient を使用し PAPER_TRADING_SQLITE_PATH に記録
- DUCKDB_PATH           : DuckDB DB パス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH : ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL             : ログレベル（INFO など）
- PAPER_FILL_MODE       : ペーパートレードの約定挙動（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL : run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START : Execution 起動時に data/kill.flag を自動クリアするか（'1' はクリアする）

使い方（主なコマンド）
--------------------
- 環境ウィザード（.env の作成・更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン起動（デフォルトは KABUSYS_ENV に依存）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にすることでペーパートレード運用
    - export KABUSYS_ENV=paper_trading
    - export PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更する場合:
    - export MONITOR_POLL_INTERVAL=30  (秒)

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- AI スコアリング / レジーム判定（プログラムから呼び出す）
  - from kabusys.ai.news_nlp import score_news
    - score_news(conn, target_date, api_key=...)
  - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=...)

停止・Kill スイッチ
-------------------
- 監視・実行はフラグファイルで停止を受け付けます:
  - 停止要求（run_monitoring / run_execution 共通）:
    - data/stop_requested.flag を作成すると run_monitoring や run_execution のループが終了します（起動スクリプトがチェックしています）。
  - Kill Switch（自動停止）:
    - monitoring の判定により data/kill.flag が書き込まれると ExecutionEngine 停止のトリガーになります。
  - 起動時に kill_flag_clear_on_start=1 を設定すると起動時に kill.flag を自動削除します（本番では 0 推奨）。

重要な挙動（実装上の注意）
------------------------
- Monitoring は常に本番用の sqlite_path を使用する（環境に依存しない）。ただし run_execution は KABUSYS_ENV=paper_trading 時に専用 DB を使用します。
- 各 DB テーブルの初期化（マイグレーション）は init_monitoring_db() が冪等に行います。既存 DB に不足カラムがあれば ALTER TABLE で追加します。
- OpenAI を使う AI 部分は API エラー等に頑健（リトライ／フォールバック）な実装になっていますが、API キーは必ず設定してください。
- process_priority（utils/process_priority.py）で起動時にプロセス優先度を上げる処理を行います。権限不足等で失敗しても警告ログに留まります。

ディレクトリ構成（抜粋）
---------------------
以下は src/kabusys 以下の主要ファイル・ディレクトリと役割の一覧です。

- kabusys/
  - __init__.py
  - config.py                 — 環境変数/.env 管理、Settings クラス
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 起動前設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト（エントリポイント）
  - run_monitoring.py         — SystemMonitor ポーリングスクリプト（エントリポイント）
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート生成
  - execution/                — 発注処理関連（OrderManager 等）※詳細実装は別ファイル群
  - monitoring/
    - monitoring_db.py        — 監視ログの永続化（SQLite）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py        — （アラート送信管理、LINE等）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - data/                     — データ読み書きやパイプライン用（DuckDB/CSV 取り込み等）
  - utils/
    - process_priority.py      — プロセス優先度と CPU Affinity 設定ユーティリティ

開発・テストのヒント
---------------------
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を見て行われます。テストで自動ロードを抑制する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続を受け取って計算する関数群（research, ai）は副作用を最小化するよう設計されています。ユニットテスト時は DuckDB コネクションをモック／テスト DB に差し替えてください。
- OpenAI の呼び出し部分は内部的に _call_openai_api を集約しており、テスト時はこれを patch して API 呼び出しをモックできます。

ライセンス・貢献
----------------
本 README はコードベースの説明をまとめたものです。実運用や公開時には機密情報（.env や API キー）を厳重に管理してください。貢献やバグ報告はリポジトリの issue / PR をご利用ください。

以上。必要であればインストール用 requirements.txt の推奨内容、より詳細な起動シーケンス例（実行ログ例）や、各モジュールの公開 API サンプルを追記します。どの部分を詳しく載せますか？