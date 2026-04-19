# KabuSys

日本株自動売買システム（ライブラリ / 起動スクリプト群）

このリポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、注文発行（実運用・ペーパートレード）、およびシステム監視を統合した自動売買フレームワークです。  
README はコードベースの主要コンポーネントと起動手順、設定方法、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

- 目的：日本株向けの自動売買プラットフォームの骨格を提供する（ファクター計算、ポートフォリオ構築、発注、監視、AI 支援モジュール等）。
- 設計方針：
  - 分析は DuckDB、ランタイムの軽量永続化は SQLite を利用。
  - 本番（live）／ペーパートレード（paper_trading）を切り替え可能。ペーパートレード時は発注をモック化し、本番 DB と完全分離。
  - 設定は .env ファイルまたは環境変数で管理。`.env` の自動読み込み機能あり（テスト時に無効化可）。
  - Logging は統一化され、コンソール + 日次ローテーションログ（logs/）を提供。
  - OpenAI を使ったニュース NLP / レジーム判定モジュールを含む（API キー必要）。

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py — ExecutionEngine（注文処理エンジン）の起動。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し `data/paper_trading.db` に記録する。
  - run_monitoring.py — SystemMonitor のポーリングループ起動。環境にかかわらず監視用 SQLite は本番 sqlite_path を使用。
- 設定関連
  - config_setup.py — 対話式 .env 作成ウィザード。
  - validate_config.py — .env / config/*.yaml 等の設定検証 CLI。
  - config.py — Settings クラス（環境変数ラッパ）。
- 監視
  - monitoring/monitoring_engine.py, system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py — システム監視、アラート、Kill Switch 機能。
  - monitoring/monitoring_db.py — 監視用 SQLite スキーマ & 永続化。
- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py, position_sizing.py, risk_adjustment.py — 候補選定、重み計算、株数算出、セクター制約等。
- 研究 / ファクター計算
  - research/factor_research.py — Momentum / Volatility / Value 等のファクターを DuckDB 上で計算。
  - research/feature_exploration.py — 将来リターン、IC 計算、統計サマリー等。
- AI（OpenAI）
  - ai/news_nlp.py — ニュースを LLM でセンチメント化して ai_scores に格納。
  - ai/regime_detector.py — ETF 指標 + マクロニュースを LLM で評価し市場レジームを算出。
- ユーティリティ
  - utils/logging_setup.py — ログ設定ユーティリティ（Stream + 日次ファイル）。
  - utils/process_priority.py — プロセス優先度 / CPU affinity 設定。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <リポジトリURL>

2. Python 環境を準備（推奨: venv）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   - 通常は requirements.txt を用意している想定です:
     - pip install -r requirements.txt
   - 主な依存例: duckdb, psutil, openai, PyYAML（validate_config の YAML チェック用）など

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードは J-Quants / kabuAPI のトークンや DB パスなどを対話形式で設定します。
   - 生成された `.env` は絶対に Git にコミットしないでください。

5. 設定検証
   - python -m kabusys.validate_config
   - オプション: --strict を付けると警告も失敗扱い（exit 1）になります。

6. データディレクトリ作成（必要なら）
   - デフォルトの DB / ログ / data ディレクトリは自動作成されますが、手動作成してパーミッションを確認しておくと安全です。
   - 例: mkdir -p data logs

7. OpenAI を使う機能を使う場合
   - OPENAI_API_KEY を環境変数か .env に設定してください。

---

## 主要環境変数とデフォルト値

（重要なものを抜粋）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE — ペーパートレードの成行応答モード（instant/partial/never/reject、デフォルト: instant）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ出力ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI の API キー（AI モジュールで必要）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動削除するか（0/1、デフォルト: 0）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）  
  - 無効な値（<=0 や非整数）はデフォルト 60 秒にフォールバック。

注意: validate_config.py に検査される必須/任意の環境変数一覧が含まれます。起動前に `python -m kabusys.validate_config` で確認してください。

---

## 使い方（起動 / 実行）

- 環境の準備が済んでいることを確認（.env, DB パス等）。

1. ExecutionEngine（注文エンジン）を起動
   - 通常起動（本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替）:
     - python -m kabusys.run_execution
   - ペーパートレードに切替:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
     - ペーパートレード時は MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます。
   - 実行時の挙動:
     - 起動時にプロセス優先度を high に設定し、SQLite / DuckDB に接続します。
     - 停止シグナルはプロジェクトルート `data/stop_requested.flag` を作成することで送れます。
     - 実行中は `data/execution.pid` に PID が書き込まれます（スクリプトが管理）。

2. Monitoring（監視ループ）を起動
   - python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書きできます（秒）。
     - 例: export MONITOR_POLL_INTERVAL=30
   - 監視は常に Settings.sqlite_path（デフォルト: data/monitoring.db）を使用します（環境に依らず本番 sqlite_path を使用する設計）。
   - stop フラグで終了: `data/stop_requested.flag` を作成するとループが終了します。

3. 設定ウィザード
   - python -m kabusys.config_setup
   - .env の初期作成や更新を対話式で実施できます。

4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い。

5. Paper Trading 検証レポート（ツール）
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH （PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db を使用）
   - 出力: 稼働率、注文成功率、送信率、レイテンシ統計、PASS/FAIL 判定など。

6. AI / レジーム判定 / ニューススコアリング
   - AI 機能を使うには OPENAI_API_KEY の設定が必要。
   - モジュール関数として利用可能:
     - kabusys.ai.score_news(conn, target_date, api_key=None)
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - DuckDB 接続オブジェクト（kabusys のコードでは duckdb.connect(...)）を渡して実行します。

---

## 停止・Kill Switch・フラグ

- stop_requested.flag
  - path: プロジェクトルート/data/stop_requested.flag
  - run_execution / run_monitoring はこのファイルの存在を検知して安全に停止します。

- kill.flag（Kill Switch）
  - path: Settings.kill_flag_path（デフォルト: data/kill.flag）
  - RiskMonitor / KillSwitch は重大なリスク条件（ドローダウン超過やポジション上限超過）を検出すると kill.flag を書き込み、ExecutionEngine 側が停止する仕組みです。
  - KILL_FLAG_CLEAR_ON_START 環境変数を 1 にすると起動時に自動クリアされます（本番では 0 推奨）。

- PID ファイル
  - 実行エンジンは data/execution.pid に PID を書きます。

---

## ログ

- ログはデフォルトで stdout（コンソール）と files（logs/<app_name>.log）に出力されます。
- 日次ローテーション（TimedRotatingFileHandler）で 30 日分保持。
- ログ設定は kabusys.utils.logging_setup.setup_logging(app_name, log_dir, level) で統一的に行います。

---

## ディレクトリ構成

（リポジトリの主要ファイルを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — Settings / .env 自動ロード
    - config_setup.py          — .env 対話ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリング起動
    - tools/
      - paper_verification_report.py — ペーパートレード検証レポート
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
    - monitoring/
      - monitoring_db.py
      - monitoring_engine.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - …（execution, data, strategy 等のサブモジュールが存在）

- data/   — デフォルトで DB / フラグ / PID を置く想定ディレクトリ（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid）
- logs/   — ログ出力先（デフォルト）

---

## ライブラリとしての利用例（Python）

- ファクター計算（DuckDB 接続を渡して呼ぶ）
  - from kabusys.research import calc_momentum
  - conn = duckdb.connect("data/kabusys.duckdb")
  - result = calc_momentum(conn, date(2026, 4, 1))

- ポートフォリオ関数の利用
  - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

- AI スコアリング（DB と API キーを渡す）
  - from kabusys.ai import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, date(2026,4,1), api_key="sk-...")

---

## 運用上の注意点

- 本番（KABUSYS_ENV=live）では LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は本番時に警告を出します。
- Kill Switch 設定は運用上重要です。KILL_FLAG_CLEAR_ON_START=1 は本番では危険な設定です（自動クリアされるため）。
- run_monitoring は監視用 DB として Settings.sqlite_path を常に使用します（環境にかかわらず）。
- OpenAI を利用する API コールはコストがかかります。API 呼び出しの失敗処理はフェイルセーフ設計になっていますが、利用頻度に注意してください。
- .env は機密情報を含むためリポジトリにコミットしないでください。

---

この README はコードベースから抜粋して要点をまとめたものです。詳細実装や設計意図は各モジュールの docstring / コメントを参照してください。必要なら起動スクリプトのログや validate_config の出力を確認し、環境設定を修正してから実行してください。