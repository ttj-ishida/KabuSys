# KabuSys

日本株自動売買システムのサンプル実装（ライブラリ＋運用スクリプト群）。

このリポジトリは、シグナルからポートフォリオ構築、発注、監視、紙トレード（paper trading）検証、研究／AI 補助までを含むコンポーネント群を提供します。各モジュールはできる限り副作用を避け、単体でテスト可能になるよう設計されています。

## 特徴（概要）
- ExecutionEngine（発注実行機構）
  - Broker クライアントの抽象化（実運用 / モック切替）
  - OrderManager / OrderRepository による状態管理
  - RiskManager（ポジション上限・利用率・ドローダウン等）
  - Reconciler による起動時の自動リコンシリエーション（発注復旧）
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk、プロセス生存、データ鮮度監視
  - TradeMonitor: 注文滞留 / 約定異常価格の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件達成時に flag ファイルを書いて ExecutionEngine を停止
  - AlertManager: LINE によるプッシュ通知（オプション）
  - streamlit による監視ダッシュボード
- Portfolio construction（銘柄選定・配分・サイズ計算）
  - 候補選定、等金額・スコア加重配分、リスク調整（セクター上限・レジーム乗数）、単元株丸め、リスクベースの発注量算出
- Research / Data（DuckDB を利用したファクター計算）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン・IC 計算・特徴量サマリ
- AI（OpenAI を利用）
  - news_nlp: ニュース記事を LLM でセンチメント化 → ai_scores 書き込み
  - regime_detector: マクロニュースと ETF (1321) MA200 を合成して日次レジーム判定
  - OpenAI API の呼び出しに対するリトライ・検証ロジックを実装
- ユーティリティ
  - 設定管理（.env / .env.local の自動読み込み、Settings クラス）
  - プロセス優先度・CPU affinity 設定ユーティリティ
  - 監視用 SQLite スキーマ初期化（init_monitoring_db）
- ツール
  - paper_verification_report: 紙トレード DB を集計して Pass/Fail レポートを生成

---

## 機能一覧（主要コンポーネント）
- kabusys.config.Settings: 環境変数 / .env を読み込み、各種設定値を提供
- run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV=paper_trading 時はモック）
- run_monitoring.py: SystemMonitor のポーリングプロセス起動スクリプト
- monitoring:
  - MonitoringDB / init_monitoring_db: SQLite スキーマ管理
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine
  - AlertManager: LINE プッシュ通知
  - KillSwitch: 停止フラグ管理（data/kill.flag）
  - streamlit_dashboard.py: 監視ダッシュボード（Streamlit）
- execution:
  - OrderManager / Reconciler / RiskManager / OrderRepository（SQLite ベース）
- portfolio:
  - portfolio_builder.py, position_sizing.py, risk_adjustment.py
- research:
  - factor_research.py, feature_exploration.py（DuckDB を想定）
- ai:
  - news_nlp.py（ニュースセンチメント）
  - regime_detector.py（市場レジーム）
- tools:
  - paper_verification_report.py（紙トレード検証レポート）

---

## 前提・依存関係
（実行環境に応じて適宜インストールしてください）

主な Python ライブラリ:
- duckdb
- psutil
- requests
- streamlit (ダッシュボード用)
- openai (AI 機能用)
- sqlite3（標準ライブラリ）

例（pip）:
pip install duckdb psutil requests streamlit openai

※requirements.txt がある場合はそれを使用してください:
pip install -r requirements.txt

---

## 環境変数（主要）
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（settings.jquants_refresh_token）
- KABU_API_PASSWORD — kabuステーション API パスワード（settings.kabu_api_password）

任意／デフォルトあり:
- KABUSYS_ENV — 起動環境: development / paper_trading / live（デフォルト: development）
  - paper_trading の場合、MockBrokerClient を利用し、paper 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
- PAPER_FILL_MODE — paper_trading の約定挙動: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB データベース（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
- PID_FILE_PATH — ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — kill.flag のパス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag をクリアするか（"1" で True）
- MONITOR_POLL_INTERVAL — run_monitoring.py のポーリング間隔（秒、デフォルト: 60）

.env の自動読み込み:
- プロジェクトルートに .env / .env.local があれば自動で読み込みます（OS 環境変数が優先）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動ロードを無効化できます

Settings クラスはプロパティ経由でこれらにアクセスできます。

.env のサンプル（例）
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=...
OPENAI_API_KEY=...
KABUSYS_ENV=paper_trading
PAPER_FILL_MODE=instant

---

## セットアップ手順（簡易）
1. リポジトリをクローン
2. Python 仮想環境を作成・有効化
   python -m venv .venv
   source .venv/bin/activate  （Windows: .venv\Scripts\activate）
3. 依存ライブラリをインストール
   pip install duckdb psutil requests streamlit openai
   （または pip install -r requirements.txt）
4. 必要な環境変数を .env に設定（必須トークン等）
5. data ディレクトリを作成（必要に応じて）
   mkdir -p data
6. DuckDB / SQLite 用データ準備（prices_daily, raw_financials, raw_news 等のテーブルは研究/AI 機能利用時に必要）
7. 監視 DB の初期化は run_monitoring/run_execution 内で自動的に行われます（init_monitoring_db）

※ psutil によるプロセス優先度設定は権限が必要な場合があります（Linux の nice 値を下げる等）。

---

## 使い方 / 実行例

- SystemMonitor の常駐監視（デフォルト poll 60 秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL は正の整数（1以上）。不正な値は 60 秒にフォールバックします。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）に書き込みます（環境に依らず本番 sqlite_path を使用）。

- ExecutionEngine 起動（本番 / 紙トレード切替）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading を付与すると MockBrokerClient を使い、paper 用 DB（PAPER_TRADING_SQLITE_PATH）に分離して記録されます。
  - 起動時にプロセス優先度を "high" に設定し、PID ファイル（Settings.pid_file_path）を書きます。

- Paper Trading 検証レポート出力
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルトの DB パスは data/paper_trading.db。--db で上書き可能。
  - 出力内容: 稼働率・注文成功率・送信率・レイテンシ（平均/最大/P95）を集計し Pass/Fail を判定します。

- Streamlit 監視ダッシュボード
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブを提供します。

- AI モジュール（ニューススコア / レジーム検出）
  - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または関数引数で指定）。
  - 例（Python から呼び出す）:
      from kabusys.ai.news_nlp import score_news
      score_news(conn, target_date, api_key="...")

---

## 重要な運用ポイント
- 監視（monitoring）は常に Settings.sqlite_path を使用します。paper_trading 環境でも監視ログは本番 sqlite_path を参照する設計です（run_execution は paper_trading時に別 DB を使います）。
- run_execution は起動時に PID ファイルを書きます。SystemMonitor はこの PID を参照して Execution の生存チェックを行います。PID ファイルが stale（プロセス不存在）な場合は削除してアラートを出します。
- KillSwitch は RiskMonitor などの結果に応じて data/kill.flag を書くことで ExecutionEngine に停止シグナルを送ります（Execution 側は起動時に KILL_FLAG_CLEAR_ON_START の設定に基づいてフラグをクリアできます）。
- OpenAI 等外部 API 呼び出しはリトライ・スロットリングを実装していますが、API キーや料金に注意してください。
- process priority の設定（set_process_priority）はプラットフォーム依存で、権限不足時は警告を出してスキップします。

---

## ディレクトリ構成（主要ファイル）
src/kabusys/
- __init__.py — パッケージメタ（version 等）
- config.py — Settings / .env 自動ロード / 設定値
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

src/kabusys/execution/
- order_manager.py — 発注状態管理と broker 連携
- reconciler.py — 起動時リコンシリエーション
- ...（BrokerFactory, ExecutionEngine, OrderRepository 等）

src/kabusys/monitoring/
- monitoring_db.py — SQLite スキーマ・永続化レイヤ
- system_monitor.py — システム/データ鮮度監視
- trade_monitor.py — 注文滞留・約定異常監視
- risk_monitor.py — ドローダウン・ポジション監視
- kill_switch.py — フラグファイル制御
- alert_manager.py — LINE 通知
- monitoring_engine.py — 複数 Monitor の統括
- streamlit_dashboard.py — Streamlit ダッシュボード

src/kabusys/portfolio/
- portfolio_builder.py — 候補選定・スコアソート
- position_sizing.py — 株数計算・単元丸め
- risk_adjustment.py — セクター上限・レジーム乗数

src/kabusys/research/
- factor_research.py — Momentum/Volatility/Value 計算
- feature_exploration.py — Forward returns / IC / summary

src/kabusys/ai/
- news_nlp.py — ニュースセンチメント集計・OpenAI 呼び出し
- regime_detector.py — レジーム判定（MA200 + マクロニュース）

src/kabusys/tools/
- paper_verification_report.py — 紙トレード検証レポート生成

src/kabusys/utils/
- process_priority.py — プロセス優先度・CPU affinity ユーティリティ

---

## SQLite / DuckDB スキーマ（監視 DB）
init_monitoring_db により以下のテーブルが作成されます（冪等）:
- system_status (recorded_at, cpu_percent, memory_percent, disk_percent, process_ok, ...)
- trade_logs (logged_at, event_type, client_order_id, code, side, qty, price, filled_qty, state, latency_ms)
- positions (code, qty, avg_price, current_price, updated_at)
- risk_logs (logged_at, event_type, metric_name, metric_value, threshold, detail)
- dashboard (id=1 固定行で集計値を保持: portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value, ...)

---

## 開発時の参考
- Settings クラスは実行時に .env / .env.local を自動読み込みします（プロジェクトルートの判定は .git または pyproject.toml を探索）。
- 単体関数群（portfolio、research 等）はできる限り DB に依存しない純粋関数として実装されています。ユニットテストが書きやすい設計です。
- OpenAI API 呼び出し部分はテスト時に差し替え（patch）することを想定して設計されています。

---

問題・不明点・追加したいドキュメント項目があれば教えてください。README に追記・修正して整備します。