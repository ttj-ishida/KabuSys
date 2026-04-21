# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、戦略の研究（ファクター計算）、ポートフォリオ構築、発注実行（ExecutionEngine）、監視（Monitoring）、およびニュースの NLP スコアリングなどを含む自動売買システムのコンポーネント群を提供します。

## プロジェクト概要
- DuckDB を用いた時系列データの集計・研究（prices_daily / raw_financials 等）
- ExecutionEngine による発注ロジック（本番／ペーパートレード対応）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch による自動停止
- ニュースに対する LLM（OpenAI）ベースのセンチメントスコアリングと市場レジーム判定
- ペーパートレードの検証レポート生成ツール
- 環境設定ウィザード（.env 生成）と設定検証ツール

## 主な機能一覧
- strategy / portfolio
  - 候補選定（select_candidates）
  - 重み算出（等金額 / スコア加重）
  - ポジションサイズ計算（risk_based, equal, score）
  - セクター上限適用、レジーム乗数算出
- research
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB SQL）
  - 将来リターン・IC（情報係数）計算、ファクター統計
- execution
  - Broker クライアント抽象化（本番／Mock）
  - RiskManager / OrderManager / Reconciler / ExecutionEngine
  - Paper trading（KABUSYS_ENV=paper_trading 時は MockBroker を使用し DB を分離）
- monitoring
  - システム稼働監視・データ鮮度チェック（SystemMonitor）
  - リスク監視（ドローダウン / ポジション上限）
  - 監視ログ永続化（SQLite: monitoring.db）
  - KillSwitch（data/kill.flag）による実行系停止
  - 監視ループ起動スクリプト（run_monitoring）
- ai
  - ニュース NLP による銘柄別センチメント取得（OpenAI）
  - マクロニュース＋ETF MA200 を用いた市場レジーム判定（regime_detector）
- utils
  - ロギング設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定
- tools
  - Paper Trading 検証レポート生成スクリプト（paper_verification_report）
- 開発支援
  - .env 対話ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）

---

## セットアップ手順（簡易）
※ 以下は一般的な手順です。プロジェクトに requirements.txt がある場合はそちらを優先してください。

1. リポジトリを取得
   - git clone ...

2. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必要パッケージ例（プロジェクトで利用されているもの）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証用に任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の作成
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - ウィザードで作成した .env をプロジェクトルートに保存してください。
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主要な設定例:
     - KABUSYS_ENV=development|paper_trading|live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=...

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告もエラーにしたい場合:
     - python -m kabusys.validate_config --strict

6. ディレクトリ作成（必要に応じて）
   - data/ （DB・フラグ）
   - logs/ （ログ）

---

## 使い方（起動・主要コマンド）
- ExecutionEngine（発注エンジン）起動
  - 簡易:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し data/paper_trading.db に記録（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
    - 実行中は data/execution.pid（デフォルト）に PID を書きます。

- Monitoring（監視ループ）起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL（秒）: ポーリング間隔を上書き（デフォルト 60）
  - 監視は Settings の sqlite_path（監視 DB）を常に使用します（環境に依らず実DB）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit 1）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定:
    - --db PATH（または環境変数 PAPER_TRADING_SQLITE_PATH）

- AI（Python API 利用例）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # duckdb_conn は duckdb.connect(...)
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

- 停止 / Kill Switch
  - 実行系を安全に停止させたい場合は監視コンポーネント経由で data/kill.flag が書かれます。
  - 手動で強制停止したい場合は data/stop_requested.flag を作成すると run_monitoring / run_execution のポーリングループが検知して終了します。
  - KillSwitch は条件（ドローダウンやポジション上限）発生時に data/kill.flag を生成します。

---

## 重要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (ペーパートレード専用 DB, デフォルト: data/paper_trading.db)
- LOG_LEVEL (DEBUG/INFO/...)
- LOG_DIR (ログ保存先、デフォルト logs/)
- OPENAI_API_KEY (OpenAI を使う機能で必須)
- MONITOR_POLL_INTERVAL (監視ポーリング秒数; デフォルト 60)
- PAPER_FILL_MODE (paper_trading 用の約定モード: instant|partial|never|reject)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか: 0/1)

---

## ディレクトリ構成（主要ファイル / モジュール）
- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py            — ExecutionEngine 起動スクリプト
  - run_monitoring.py          — Monitoring ポーリングループ起動スクリプト
  - ai/
    - news_nlp.py              — ニュース NLP スコアリング
    - regime_detector.py       — 市場レジーム判定
    - __init__.py
  - monitoring/
    - monitoring_db.py         — SQLite テーブル初期化・アクセス層
    - system_monitor.py
    - trade_monitor.py         — （ファイル内参照あり）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py         — （アラート送信ロジック）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

（注）一部ファイルはここに列挙されていない可能性があります。リポジトリ全体を参照してください。

---

## 運用上の注意 / トラブルシューティング
- .env は絶対にリポジトリにコミットしないこと（機密情報を含む）。
- ロギング:
  - setup_logging() は stdout と日次ローテートファイル（logs/<app>.log）を設定します。
  - LOG_DIR の作成に失敗した場合はコンソールのみで継続します。
- DB:
  - paper_trading は paper 用 SQLite を使い、本番 DB と分離します（PAPER_TRADING_SQLITE_PATH）。
  - Monitoring 用の SQLite（SQLITE_PATH）は監視ログ専用に利用されます（run_monitoring 側で使用）。
- OpenAI:
  - OPENAI_API_KEY が未設定だと AI 機能は動作しません（明示的に ValueError を投げます）。
  - API の呼び出しはリトライとフォールバック（失敗時はゼロスコア等）を行い、システムが停止しない設計です。
- 設定検証:
  - 起動前に python -m kabusys.validate_config を実行して不足や警告を確認してください。
- 停止フラグ:
  - 手動で停止させるにはプロジェクトルートの data/stop_requested.flag を作成します（run_* スクリプトが検出してループを抜けます）。

---

以上がプロジェクトの概要と主要な使い方です。さらに詳細な設計・仕様（ポートフォリオ構築のアルゴリズムや ExecutionEngine の内部挙動など）は、各モジュールの docstring やコードコメントに記載されていますので参照してください。README にない補足や具体的な導入手順のカスタマイズが必要であれば教えてください。