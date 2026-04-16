# KabuSys

KabuSys は日本株向けの自動売買・リサーチ・監視フレームワークです。  
このリポジトリは取引エンジン、監視基盤、ポートフォリオ構築、リサーチ、AI を用いたニュース解析などを含むコンポーネント群から構成されています。

以下はこのコードベースの概要・セットアップ・使い方・ディレクトリ構成をまとめた README です。

---

## プロジェクト概要

- 日本株自動売買システム（KabuSys）のコア実装群。
- 主な機能：
  - ExecutionEngine（発注・注文管理・リコンシリエーション）
  - Monitoring（プロセス／資源／注文監視、Kill Switch、LINE アラート）
  - Portfolio Construction（候補抽出、重み付け、ポジションサイジング）
  - Research（ファクター計算、特徴量解析、IC 計測）
  - AI（ニュースの NLP によるセンチメント・レジーム判定）
  - Tools（Paper Trading 検証レポート、Streamlit ダッシュボード起動など）
- 設定は環境変数および `.env` / `.env.local` によって管理（自動ロード可、無効化オプションあり）。

---

## 主な機能一覧

- Execution
  - Broker クライアント抽象化（本番 / Paper Trading 切替）
  - OrderManager / OrderRepository による安全な注文管理
  - Reconciler による起動時の自動復旧（ブローカー照合・ポジション差分検出）
- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク、プロセス存在確認、株価データ鮮度
  - TradeMonitor: 滞留注文検出、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件達成時に `data/kill.flag` を書き込み ExecutionEngine を停止
  - AlertManager: LINE への一方向プッシュ通知（クールダウン管理）
  - streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 候補選定、等比率／スコア重み、リスク調整（セクターキャップ、レジーム乗数）
  - ポジションサイズ計算（単元株丸め、aggregate cap, cost buffer）
- Research
  - ファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- AI
  - news_nlp: OpenAI を用いたニュースの銘柄別センチメントスコア化（ai_scores テーブルへ保存）
  - regime_detector: ETF(1321) の MA 乖離とマクロニュースの LLM センチメントを合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB から検証レポートを生成
  - streamlit_dashboard: 監視 DB を可視化する Streamlit アプリ

---

## セットアップ手順（開発環境）

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo-root>
   ```

2. Python 環境（推奨: venv）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows
   ```

3. 必要な依存パッケージをインストール  
   （プロジェクトに requirements.txt が無い場合は以下を参考にインストールしてください）
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   - duckdb: DuckDB 接続
   - psutil: プロセス優先度・CPU 使用率等
   - requests: LINE API 呼び出し
   - openai: OpenAI API（news_nlp / regime_detector）
   - streamlit: ダッシュボード（オプション）

4. 環境変数 / .env
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（CWD に依存しない探索）。
   - 自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```
   - 重要な環境変数（主要）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID
     - SQLITE_PATH (監視 DB のパス, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper trading 用 DB, デフォルト: data/paper_trading.db)
     - DUCKDB_PATH (DuckDB ファイル, デフォルト: data/kabusys.duckdb)
     - MONITOR_POLL_INTERVAL (監視ループ間隔秒; デフォルト 60)
     - PAPER_FILL_MODE (paper_trading 時の挙動: instant|partial|never|reject)

5. データディレクトリ
   - デフォルトで `data/` 下に DB や pid/flag ファイルを置きます。必要に応じてディレクトリを作成してください。
   ```
   mkdir -p data
   ```

---

## 使い方（主要スクリプト）

### 監視ループ起動（run_monitoring）
- スクリプト: `src/kabusys/run_monitoring.py`
- 概要: SystemMonitor をポーリングして監視情報を SQLite に書き込む。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可（秒）。
- 実行:
  ```
  python -m kabusys.run_monitoring
  ```
- デフォルト:
  - ポーリング間隔: 60 秒（MONITOR_POLL_INTERVALで上書き）
  - 監視 DB: Settings.sqlite_path（環境にかかわらず本番 sqlite_path を使用する点に注意）

- 停止方法:
  - Ctrl+C（KeyboardInterrupt）
  - またはプロジェクトルート `data/stop_requested.flag` を作成するとループが検知して終了します。

### ExecutionEngine 起動（run_execution）
- スクリプト: `src/kabusys/run_execution.py`
- 概要: ExecutionEngine を起動。KABUSYS_ENV=paper_trading のときは MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB とは分離。
- 実行:
  ```
  python -m kabusys.run_execution
  ```
- プロセス優先度を上げ、PID を `data/execution.pid` に書きます。停止は `data/stop_requested.flag` の作成で検知して停止します。

### Streamlit ダッシュボード
- ファイル: `src/kabusys/monitoring/streamlit_dashboard.py`
- 実行:
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  `--db` オプションで監視 DB を指定できます。読み取り専用 URI を使って DB を開きます。

### Paper Trading 検証レポート
- スクリプト: `src/kabusys/tools/paper_verification_report.py`
- 実行例:
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
- 検証指標: 稼働率、注文成功率、送信率、P95 レイテンシ など。デフォルト DB は `data/paper_trading.db`。

### AI モジュール（プログラミングからの利用）
- ニュースセンチメント
  ```
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key=None)  # api_key が None の場合 OPENAI_API_KEY を参照
  ```
  - DuckDB 接続（conn）を渡して実行。結果は ai_scores テーブルへ書き込まれます。

- レジーム判定
  ```
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key=None)
  ```

---

## フラグ・PID ファイルの取り扱い

- 停止フラグ（Monitoring / Execution の監視や停止用）
  - data/stop_requested.flag : 実行中の run_execution / run_monitoring が停止を検知するためのフラグ
  - data/kill.flag : KillSwitch が条件を満たした場合に ExecutionEngine 停止要求として書き込むファイル
- PID
  - data/execution.pid : ExecutionEngine 起動時に書き込む PID ファイル（SystemMonitor が存在確認に使用）

---

## 設定管理（Settings モジュール）

- `kabusys.config.Settings` が環境変数の集約を担います。主なプロパティ:
  - env, is_live, is_paper, is_dev
  - sqlite_path, paper_sqlite_path, duckdb_path
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - PAPER_FILL_MODE の検証（instant|partial|never|reject）

- `.env` 読み込み:
  - プロジェクトルート（.git または pyproject.toml を基準）を自動検出して `.env` / `.env.local` を順に読み込みます。
  - OS 環境変数が優先され、`.env.local` は上書きが可能。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。

---

## 主要ディレクトリ構成

（src/kabusys 以下の主要ファイル・モジュール）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数 / Settings
  - run_monitoring.py       — SystemMonitor ポーリング起動スクリプト
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート CLI
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI）による銘柄センチメント
    - regime_detector.py     — レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py       — SQLite スキーマ + MonitoringDB ラッパー
    - system_monitor.py      — システム / データ鮮度監視
    - trade_monitor.py       — 注文滞留・約定異常監視
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - alert_manager.py       — LINE 通知
    - monitoring_engine.py   — 各 Monitor を束ねる実行ループ
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py (存在を前提)
    - broker_factory.py (存在を前提)
    - ... (ブローカー API 抽象・注文レコード等)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
  - data/ (runtime)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用)
    - kabusys.duckdb
    - execution.pid
    - stop_requested.flag
    - kill.flag

（注）一部モジュールは本 README の抜粋に含まれない補助ファイルや依存モジュールを参照することがあります。

---

## 運用上の注意・ベストプラクティス

- Paper Trading は本番 DB と分離されています（Settings.is_paper に基づく）。
- Monitoring は環境にかかわらず Settings.sqlite_path（本番監視 DB）を使用する仕様に注意。
- AI（OpenAI）を利用する機能は API キーの管理・レート制限・エラー時のフォールバックロジックが組み込まれていますが、課金やレートに注意してください。
- PID / flag ファイルの操作は冪等性（既存ファイルの再書き込みを避ける等）を保つよう実装されています。
- `PAPER_FILL_MODE` を用いて Paper Trading の約定挙動を制御できます（instant / partial / never / reject）。
- `MONITOR_POLL_INTERVAL` は整数秒で設定。1 未満・不正値はデフォルト（60s）にフォールバックします。

---

## 開発・拡張のヒント

- DuckDB を使って prices_daily / raw_financials 等の時系列データを高速に集計できます。research モジュールは DuckDB 接続を引数で受け取る設計です。
- AI 関連の HTTP 呼び出しはテスト時に差し替えやすいようにラッパー関数を提供しています（ユニットテストでのモックが容易）。
- MonitoringDB の init 関数はマイグレーション（列の追加など）をシンプルに行います。DB スキーマの安全な拡張を考慮してあります。

---

この README はコードベースの主要点を抜粋してまとめたものです。詳細な設計（StrategyModel.md / PortfolioConstruction.md 等）や Broker 実装、ExecutionEngine の詳細動作は別ドキュメント・実装内コメントをご参照ください。必要であれば、この README を基に .env.example や運用手順書（Runbook）も作成できます。