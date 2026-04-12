# KabuSys — README

KabuSys は日本株の自動売買／リサーチ／監視を目的とした軽量フレームワークです。DuckDB / SQLite をデータ層に、外部 API（kabuステーション、J-Quants、OpenAI）や LINE を通知手段として利用する設計になっています。本リポジトリは実運用（live）・ペーパートレード（paper_trading）・開発（development）を想定したモジュール群を含みます。

注意: この README はソースコード（src/ 以下）を基に作成しています。実際の運用では .env の設定や外部サービスの API キー・認証情報の管理に十分注意してください。

## 主な機能

- Execution（発注）フレームワーク
  - OrderManager / OrderRepository / ExecutionEngine（起動スクリプト: run_execution.py）
  - Broker クライアント抽象化（paper_trading ではモックを使用して本番 DB と分離）
  - 再起動時のリコンシリエーション（Reconciler）

- Portfolio 枠組み（銘柄選定・重み・ポジションサイズ）
  - 候補選定、等金額・スコア加重、リスクベースの株数算出
  - セクター集中制限、レジーム乗数

- Research（因子・特徴量解析）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB ベース）
  - 将来リターン、IC（Spearman）計算、統計サマリ

- AI ベース拡張
  - ニュース NLP による銘柄センチメント（OpenAI を使用） — kabusys.ai.news_nlp
  - マクロセンチメント＋ETF MA200 からの市場レジーム判定 — kabusys.ai.regime_detector

- Monitoring（監視）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねた MonitoringEngine（起動スクリプト: run_monitoring.py）
  - SQLite ベースの監視 DB（schema 初期化・マイグレーション対応）
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（監視データの可視化）
  - Kill switch（データ/kill.flag）で ExecutionEngine の停止指示

- ユーティリティ
  - process priority / CPU affinity 設定ユーティリティ
  - Paper Trading 検証レポート生成ツール（kabusys.tools.paper_verification_report）

## セットアップ手順（ローカル）

1. 必須依存のインストール（例: pip）
   - Python 3.9+ を想定
   - 主な依存:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit（ダッシュボード利用時）
   - 例:
     python -m pip install duckdb psutil requests openai streamlit

2. プロジェクトルートの確認
   - config モジュールは .git または pyproject.toml を探索してプロジェクトルートを特定します。
   - ルートに .env / .env.local を置くと自動で読み込まれます（OS 環境変数 > .env.local > .env の優先順）。
   - 自動ロードを無効にするには環境変数を設定:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

3. 環境変数（代表例）
   - 必須（実行する機能により必要）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
     - KABU_API_PASSWORD — kabuステーション API パスワード
   - OpenAI を使う場合:
     - OPENAI_API_KEY — OpenAI API キー（news_nlp / regime_detector）
   - 監視 / 実行に関するよく使う設定（デフォルト値は括弧内）:
     - KABUSYS_ENV (development / paper_trading / live) — 実行環境（デフォルト: development）
     - PAPER_FILL_MODE ("instant" | "partial" | "never" | "reject") — paper_trading の約定挙動（デフォルト: "instant"）
     - PAPER_TRADING_SQLITE_PATH (data/paper_trading.db) — ペーパートレード用 SQLite
     - SQLITE_PATH (data/monitoring.db) — 監視用 SQLite
     - DUCKDB_PATH (data/kabusys.duckdb) — DuckDB ファイルパス
     - PID_FILE_PATH (data/execution.pid) — ExecutionEngine が保持する PID ファイル
     - KILL_FLAG_PATH (data/kill.flag) — Kill switch フラグファイル
     - MONITOR_POLL_INTERVAL (60) — Monitoring ポーリング間隔（秒）
     - LOG_LEVEL (INFO 等)

   - 例 .env（簡易）
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     OPENAI_API_KEY=sk-...
     KABUSYS_ENV=development
     PAPER_FILL_MODE=instant

4. データディレクトリ
   - デフォルトで data/ 以下に DB ファイルや PID/flag が作られます。必要に応じてディレクトリ作成を行ってください。
     mkdir -p data

## 使い方（主要スクリプト / 実行方法）

- 監視ループを起動（SystemMonitor の簡易ループ）
  - MONITOR_POLL_INTERVAL 環境変数で秒数を変更可能（デフォルト 60）
  - 実行:
    python -m kabusys.run_monitoring

- ExecutionEngine を起動（発注エンジン）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を用いて paper DB に記録（data/paper_trading.db）
  - 実行:
    python -m kabusys.run_execution

- Paper Trading 検証レポート（コマンドライン）
  - 期間指定や DB パス指定が可能:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

- Streamlit ダッシュボード（監視 DB を読む、読み取り専用）
  - 実行:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 系機能（プログラムから呼び出す例）
  - ニュースセンチメント:
    from kabusys.ai.news_nlp import score_news
    score_news(conn=duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn=duckdb_conn, target_date=date(2026,4,1), api_key="sk-...")

  - 注意: OPENAI_API_KEY を環境変数で設定しておけば api_key 引数は不要。

- 設定注記
  - run_monitoring は KABUSYS_ENV に関係なく監視用 SQLite（settings.sqlite_path）を使います（監視ログは本番 DB と分離しない設計）。
  - run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path（data/paper_trading.db）を使用して本番 DB と完全分離します。

## 主要ディレクトリ構成（src/kabusys）

- __init__.py
  - パッケージ情報（__version__ 等）

- config.py
  - .env 自動ロード、Settings クラス（環境依存フラグ・パス・閾値など）

- run_monitoring.py
  - SystemMonitor をポーリング起動するエントリポイント

- run_execution.py
  - ExecutionEngine を起動するエントリポイント（paper_trading をサポート）

- ai/
  - news_nlp.py — ニュースの LLM によるセンチメント付与
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）

- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 + 永続化 API（MonitoringDB）
  - system_monitor.py — CPU/MEM/DISK / データ鮮度 / PID チェック
  - trade_monitor.py — 注文滞留 / 約定異常価格の検出
  - risk_monitor.py — ドローダウン・ポジション上限チェック + dashboard 更新
  - kill_switch.py — kill.flag の書き込み / 解除
  - alert_manager.py — LINE push 通知（クールダウン管理）
  - monitoring_engine.py — 上記 Monitor を束ねる実行ループ
  - streamlit_dashboard.py — Streamlit ベースの監視 UI

- execution/
  - order_manager.py — 発注状態管理（Order State Machine）
  - reconciler.py — 再起動時のリコンシリエーション（Order/Position 照合）
  - （その他 brokerFactory / execution_engine / order_repository などの実装ファイルが想定されます）

- portfolio/
  - portfolio_builder.py — 候補選定・重み
  - position_sizing.py — 株数決定 / aggregate cap スケーリング
  - risk_adjustment.py — セクター上限・レジーム乗数

- research/
  - factor_research.py — momentum / volatility / value 等ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン / IC / 統計サマリ

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート CLI

- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

## 注意点・運用上のポイント

- 環境分離
  - paper_trading モードでは発注動作をローカル DB に分離することで実運用 DB の汚染を防ぎます。ただし完全な隔離は broker 実装にも依存します。

- OpenAI / 外部 API
  - OpenAI API 呼び出しはリトライ・エラーハンドリングを実装していますが、API キーのレート制限やコストに注意してください。
  - AI 機能は失敗時にフェイルセーフ（スコア=0 やスキップ）とする設計です。

- プロセス優先度
  - set_process_priority() はプラットフォーム依存の処理を行い、権限不足で失敗する場合は警告を出してスキップします。運用環境で権限（root/管理者）が必要になることがあります。

- DB マイグレーション
  - monitoring_db.init_monitoring_db は冪等でテーブル作成と簡易マイグレーション（列追加）を行います。複雑なスキーマ変更は別途管理が必要です。

## 開発のための補足

- プロジェクトルート検出
  - config._find_project_root() は .git または pyproject.toml を探索して自動で .env を読み込みます。パッケージ展開後やテスト環境で自動読み込みを抑止するには KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。

- ロギング
  - シンプルに logging.basicConfig(level=logging.INFO) を使用しています。詳細な設定は実行スクリプト側で変更可能です。

- テスト
  - 本 README に含まれるソース群にはユニットテストは同梱されていません（リポジトリにテストディレクトリがある場合は別途参照してください）。

---

必要であれば、README に含めるコマンドの具体例（systemd ユニットや Dockerfile、CI 設定例）や、各モジュールの API ドキュメント（関数一覧・引数説明）を別途作成します。どの情報を優先して追加しますか？