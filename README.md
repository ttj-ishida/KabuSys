# KabuSys

日本株自動売買システムのコードベース README（日本語）

---

目次
- プロジェクト概要
- 主な機能
- 動作要件
- 環境変数（重要）
- セットアップ手順
- 使い方（コマンド例）
- ライブラリ/API の利用例
- ディレクトリ構成
- 運用上の注意 / 補足

---

## プロジェクト概要
KabuSys は日本株の自動売買／リサーチ／監視を行うためのモジュール群です。発注実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、ファクター計算、ニュースを用いた AI スコアリングなどを含みます。設計方針として、本番・ペーパートレードの分離、ログの一元管理、フェイルセーフ（API失敗時の安全動作）を重視しています。

---

## 主な機能
- 実行エンジン（ExecutionEngine）
  - 本番／ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory による実ブローカー or Mock ブローカーの差し替え
  - リスク管理（RiskManager）、注文管理（OrderManager）、再整合（Reconciler）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - system_status / trade_logs / risk_logs / positions / dashboard の永続化（SQLite）
  - Kill Switch（条件達成で data/kill.flag を書き込み Execution を停止）
  - run_monitoring のポーリングループ（MONITOR_POLL_INTERVAL で間隔変更可）
- ポートフォリオ構築
  - 候補選定、重み計算（等金額、スコア）、ポジションサイズ計算（単元処理、上限、スケーリング）
  - セクター上限やレジーム乗数の適用
- リサーチ / ファクター計算（DuckDB 経由）
  - Momentum / Volatility / Value などのファクター計算
  - 将来リターン計算、IC（相関）計算、統計サマリー
- AI モジュール
  - ニュースのセンチメントを OpenAI（gpt-4o-mini 等）で評価し ai_scores に保存
  - 市場レジーム判定（ETF の MA200 乖離 + マクロニュースの LLM スコア）
  - API 呼び出しはリトライやフォールバックを備える
- ツール
  - 環境設定ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools.paper_verification_report）
- ユーティリティ
  - 統一的なログ設定（logs/<app>.log、日次ローテーション）
  - プロセス優先度／CPU affinity 設定ユーティリティ

---

## 動作要件
- Python 3.9+（型アノテーション等を使用）
- 必須（機能に応じて）パッケージ:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
- 任意:
  - PyYAML（config/*.yaml の内容検証に使用）
- OS: Linux / macOS / Windows（プロセス優先度処理はプラットフォーム依存の差分を吸収）

インストール例:
pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt があればそれを使用してください）

---

## 環境変数（主要なもの）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用
- KABU_API_PASSWORD — kabuステーション API パスワード

主要（任意・デフォルトあり）:
- KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBrokerClient を使用、paper_trading 用 DB に記録
  - live: 実際の発注を行う（設定に注意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL。デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を使用する場合の API キー
- PAPER_FILL_MODE — ペーパートレードでの約定モード（instant/partial/never/reject）

監視用の調整:
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1。デフォルト 0）

ログ / ファイル:
- デフォルトでログは logs/<app>.log に日次ローテーションで出力
- PID / フラグファイルは data/ 以下に作成される（例: data/execution.pid, data/kill.flag, data/stop_requested.flag）

---

## セットアップ手順（簡易）
1. リポジトリをチェックアウト
2. Python 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要ライブラリをインストール
   - pip install duckdb psutil openai pyyaml
4. .env の作成（推奨: 対話ウィザード）
   - python -m kabusys.config_setup
   - ウィザード後、.env がプロジェクトルートに保存される
5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正。--strict を付けると警告も失敗扱い
6. データディレクトリ等の準備
   - デフォルトでは data/ と logs/ は自動作成されるが、権限等を確認してください

---

## 使い方（コマンド例）
- 環境ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 実行エンジン起動（通常はサービスとして起動）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を設定するとペーパートレード（MockBroker）を使用

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring  （ポーリング間隔を30秒に変更）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- ライブラリ API を呼ぶ（例: AI スコア付け）
  - Python 内から:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, target_date, api_key="...")

---

## ライブラリ/API の利用例（簡易）
- ファクター計算（research）
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
  - results = calc_momentum(duckdb_conn, date(2026, 4, 1))

- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
  - candidates = select_candidates(signals, max_positions=10)
  - weights = calc_score_weights(candidates)
  - sizes = calc_position_sizes(weights, candidates, portfolio_value, cash, current_positions, open_prices)

- AI ニューススコアリング
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")

---

## ディレクトリ構成（主要ファイル・概要）
（ルートが src/kabusys のパッケージ構成を想定）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / Settings クラス、自動 .env ロード機能
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト（PID, stop フラグ管理）
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト（MONITOR_POLL_INTERVAL）
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）で ai_scores を書き込み
    - regime_detector.py — マーケットレジーム判定（MA200 + マクロニュース）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数決定・スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — momentum/volatility/value の計算
    - feature_exploration.py — forward returns / IC / summary
  - monitoring/
    - monitoring_db.py — monitoring DB スキーマ + 永続化ラッパー
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 注文ログの監視（ファイル参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — 各 monitor を束ねるエンジン
    - kill_switch.py — kill.flag を書き込むロジック
    - alert_manager.py — （アラート送信ロジック）
  - execution/（発注周り: BrokerFactory, ExecutionEngine, OrderManager 等）
  - data/（実行時に生成される）
    - monitoring.db（デフォルト）
    - paper_trading.db（ペーパートレード用）
    - kill.flag, stop_requested.flag, execution.pid など
  - logs/（ログファイル: <app>.log）

---

## 運用上の注意 / 補足
- KABUSYS_ENV による本番・テストの切替を厳密に管理してください。live モードは実際に発注を行います。
- ペーパートレード（paper_trading）は専用の SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB とは分離されています。
- run_monitoring は Monitoring 用の DB（settings.sqlite_path）を環境にかかわらず「本番 sqlite_path」として使用します（監視は常に本番 DB を監視する設計）。
- 停止フラグ:
  - data/stop_requested.flag：run_execution / run_monitoring の外部停止フラグ（存在するとループを終了）
  - data/kill.flag：kill switch による Execution 停止シグナル。KILL_FLAG_CLEAR_ON_START=1 に注意（本番では 0 推奨）
- ログ:
  - setup_logging がログディレクトリを作成するため、logs/ に書き込み権限が必要
- OpenAI API を利用する機能は API 利用料・レート制限に注意。APIKey は OPENAI_API_KEY または関数引数で渡してください。
- DuckDB を用いたリサーチ処理は大規模データの読み込み・クエリ実行を行うため、適切なストレージ容量・メモリを確保してください。
- .env は機密情報を含むため、絶対に Git などにコミットしないでください（config_setup でもその旨の注意が入ります）。

---

この README はコードベースに含まれる主要な設計意図と運用手順をまとめたものです。より詳細な仕様（PortfolioConstruction.md や StrategyModel.md 等）はリポジトリ内のドキュメントをご参照ください。必要であれば、この README を英語版に翻訳したり、各コンポーネントごとの詳細ドキュメントを作成します。