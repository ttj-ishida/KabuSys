# KabuSys — README (日本語)

概要
---
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした小規模なパイプライン群です。本リポジトリは以下の機能群を含みます（価格データ集計・ファクター計算・ポートフォリオ構築・発注エンジン・監視・AI ベースのニュース評価など）。軽量なローカル DB（SQLite / DuckDB）を使って、実運用（live）と紙 (paper_trading) を明確に分離できる設計です。

主な特徴
---
- ファクター計算（Momentum, Volatility, Value など）を DuckDB 上の prices_daily/raw_financials テーブルから計算
- ポートフォリオ構築（候補選定、等重・スコア重み、リスク調整、ポジションサイズ計算）
- ExecutionEngine 用の起動スクリプト（本番 / paper_trading の切り替え）
- OrderManager / Reconciler による起動時リコンシリエーションと注文状態管理
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / AlertManager）
- 監視ダッシュボード（Streamlit）
- AI モジュール（OpenAI を用いたニュースセンチメント評価・レジーム判定）
- 検証ツール（Paper Trading 検証レポート生成）

セットアップ手順
---
1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-dir>
   ```

2. 仮想環境の作成（任意だが推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Unix/macOS
   .venv\Scripts\activate.bat  # Windows
   ```

3. 必要パッケージをインストール
   プロジェクトに requirements.txt があればそれを使って下さい。なければ主要な依存パッケージの例:
   ```
   pip install duckdb psutil openai requests streamlit
   ```
   注: sqlite3 は標準ライブラリです。

4. データディレクトリ作成
   ```
   mkdir -p data
   ```
   デフォルトの DB パスは以下:
   - DuckDB: data/kabusys.duckdb
   - SQLite (monitoring): data/monitoring.db
   - Paper trading SQLite: data/paper_trading.db

5. 環境変数の設定
   ルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   重要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
   - KABU_API_PASSWORD: kabuステーション API 用パスワード（必須）
   - OPENAI_API_KEY: OpenAI API キー（AI 機能利用時に必須）
   - KABUSYS_ENV: 実行環境: development | paper_trading | live（デフォルト: development）
   - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
   - SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
   - PID_FILE_PATH: ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: Kill flag ファイル（デフォルト: data/kill.flag）
   - PAPER_FILL_MODE: paper_trading の注文約定モード（instant|partial|never|reject、デフォルト: instant）
   - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）

   参考となる .env の行例:
   ```
   JQUANTS_REFRESH_TOKEN=xxxx
   KABU_API_PASSWORD=yyyy
   OPENAI_API_KEY=sk-...
   KABUSYS_ENV=paper_trading
   ```

使い方（主要スクリプト）
---
- 監視ループ起動
  - 説明: SystemMonitor をポーリングして monitoring DB にログ、KillSwitch 評価やアラート送信を行います。
  - 実行:
    ```
    python -m kabusys.run_monitoring
    ```
  - オプション: 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能。例: `MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring`

- ExecutionEngine 起動
  - 説明: 発注エンジンを起動します。KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し paper_db（data/paper_trading.db）に記録して本番 DB と分離します。
  - 実行:
    ```
    python -m kabusys.run_execution
    ```
  - 注意: 起動時に PID ファイルが作成され、SystemMonitor はこれを使ってプロセスの生存チェックを行います。KillSwitch は data/kill.flag を書くことで外部から停止指示が出せます。

- Paper Trading 検証レポート
  - 説明: paper_trading DB のログを集計して検証レポートを標準出力に表示します。
  - 実行:
    ```
    python -m kabusys.tools.paper_verification_report
    ```
  - 期間指定:
    ```
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    ```
  - DBパス指定:
    ```
    python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
    ```

- 監視ダッシュボード（Streamlit）
  - 説明: monitoring DB を read-only で開いてダッシュボードを表示します。
  - 実行:
    ```
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    ```
  - 監視ループが起動していないと DB が存在しないためエラーになります。

- AI 関連（ニューススコア / レジーム判定）
  - ai.news_nlp.score_news と ai.regime_detector.score_regime を呼び出すことで、DuckDB の raw_news 等から OpenAI を用いてスコアを算出・書き込みします。
  - 事前に OPENAI_API_KEY を設定してください。プログラムから呼ぶ例:
    ```
    python - <<'PY'
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, date(2026,4,10))
    PY
    ```

主要設定と振る舞い（補足）
---
- KABUSYS_ENV:
  - development: 開発モード
  - paper_trading: 紙トレード。MockBroker を使用し、paper_trading 用 SQLite を参照
  - live: 本番
  Settings クラスが環境変数を検証します。無効な値は例外になります。

- DB と分離:
  - 監視 (monitoring) は常に設定された sqlite_path（デフォルト data/monitoring.db）を使います。paper_trading 実行時は ExecutionEngine 側で paper_sqlite_path を使用して本番 DB と分離します。

- プロセス優先度:
  - run_monitoring / run_execution の起動時に set_process_priority("high") を呼びプロセス優先度を上げようとします（psutil を使用）。権限がない場合は警告ログを出してスキップします。

- Kill Switch:
  - RiskMonitor がしきい値を超えると KillSwitch が data/kill.flag を書き込みます。ExecutionEngine はこのフラグを監視してシャットダウンする想定です。

ディレクトリ構成（主要ファイル）
---
リポジトリ内の主要なモジュール構成は次の通りです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（Settings）
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                   — ニュースセンチメント判定（OpenAI）
    - regime_detector.py            — 市場レジーム判定（MA + マクロニュース）
  - monitoring/
    - __init__.py
    - monitoring_db.py              — SQLite 永続化層 + MonitoringDB API
    - system_monitor.py             — システム状態・データ鮮度監視
    - trade_monitor.py              — 注文滞留・約定異常監視
    - risk_monitor.py               — ドローダウン・ポジション上限監視
    - kill_switch.py                — Kill flag 操作
    - alert_manager.py              — LINE Push (通知)
    - monitoring_engine.py          — 各 Monitor を束ねる
    - streamlit_dashboard.py        — Streamlit ダッシュボード
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他: broker_factory, execution_engine, order_repository など)
  - utils/
    - __init__.py
    - process_priority.py

開発者向けメモ / 注意点
---
- .env の自動読み込み:
  - プロジェクトルートを .git または pyproject.toml で検出し、自動的に .env と .env.local を読み込みます。テスト等で自動読み込みを止めたい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットしてください。
- PAPER_FILL_MODE の有効値:
  - instant | partial | never | reject（不正値だと ValueError）
- OpenAI 呼び出し:
  - リトライやエラー処理を含む堅牢な実装を意図しているため、API 失敗時は多くの箇所でフェイルセーフ（0.0 やスキップ）にフォールバックします。実運用ではレート制限・料金などに注意してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対してカラム追加など最低限のマイグレーション（冪等）を行います。

ライセンス / 貢献
---
リポジトリに LICENSE ファイルがあれば従ってください。バグ報告やプルリクエストは歓迎します。

お問い合わせ
---
実装や使い方について質問があればリポジトリの Issue を立ててください。

以上。