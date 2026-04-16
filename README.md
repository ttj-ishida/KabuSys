# KabuSys

日本株向けの自動売買・リサーチ基盤のサンプル実装です。  
このリポジトリは、取引実行エンジン、監視（Monitoring）、AI を使ったニューススコアリング、ファクター計算（Research）やポートフォリオ構築の純粋関数群などを含みます。

---

## 概要

KabuSys は以下の主要機能をコンポーネントとして提供します。

- ExecutionEngine: ブローカーとのやり取りを行い、注文の作成／管理／同期を行う（Reconciler による再起動後の自動復旧を含む）。
- Monitoring: システムリソース・データ鮮度・注文滞留・リスク指標（ドローダウン、保有上限）をポーリングしてログ／アラートを行う。LINE 通知と Streamlit ダッシュボードをサポート。
- AI: OpenAI を用いたニュースセンチメント（ai_scores）および市場レジーム判定（market_regime）。
- Research: DuckDB 上の時系列データ（prices_daily / raw_financials 等）を使ったファクター計算（モメンタム / ボラティリティ / バリュー）と特徴量解析ユーティリティ。
- Portfolio: 候補選択、重み付け、ポジションサイズ計算、セクター制限などの純粋関数群。
- Tools: Paper Trading の検証レポート生成ツール等。

設計上の特徴：
- DuckDB（分析用）と SQLite（監視／注文ログ）を併用。
- 環境ごとの分離（KABUSYS_ENV により paper_trading 用 DB を分ける等）。
- 自動ロードされる .env（プロジェクトルートにある場合）から環境変数を読み込む仕組み（Settings クラス）。

---

## 主な機能一覧

- 実行関連
  - 注文管理（OrderManager）
  - ブローカー同期・リコン（Reconciler）
  - リスク管理（RiskManager）※設定ファイルにより動作
- 監視関連
  - SystemMonitor: CPU / メモリ / ディスク / プロセス死活 / データ鮮度
  - TradeMonitor: 注文滞留・約定価格異常
  - RiskMonitor: ドローダウン・ポジション数アラート
  - KillSwitch: フラグファイルでエンジン停止指示
  - AlertManager: LINE push による通知（クールダウン管理あり）
  - Streamlit ダッシュボード（読み取り専用で監視情報を可視化）
- AI / NLP
  - ニュース記事のセンチメント評価（OpenAI）
  - マクロニュース + 指標合成による市場レジーム判定
  - 再試行・バッチ処理・レスポンス検証・スコアクリッピング等の実装
- Research / Data
  - DuckDB を用いたファクター計算（calc_momentum, calc_volatility, calc_value）
  - 将来リターン計算・IC 計測・ファクター統計サマリ
- Portfolio
  - 候補選出（スコア/順位ベース）
  - 重み計算（等金額 / スコア加重）
  - ポジションサイズ決定（risk_based / equal / score）
  - セクターキャップ適用、レジーム乗数
- ツール
  - Paper Trading 検証レポート生成（paper_verification_report）

---

## セットアップ手順

想定環境:
- Python 3.10 以上（typing に | を使用）
- OS: Linux / macOS / Windows（ただし一部の process-priority / cpu-affinity は OS 依存）

1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   ```bash
   git clone <repo-url>
   cd <repo>
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

2. 必要なパッケージをインストールします（例）。
   必要最低限のパッケージ:
   - duckdb
   - psutil
   - openai
   - requests
   - streamlit (ダッシュボードを使う場合)
   インストール例:
   ```bash
   pip install duckdb psutil openai requests streamlit
   ```

   （プロジェクトに requirements.txt がある場合は `pip install -r requirements.txt` を使用してください）

3. 環境変数を設定します。
   プロジェクトルートに `.env`（または `.env.local`）を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

   主要な環境変数（例）:
   ```
   KABUSYS_ENV=development        # development | paper_trading | live
   OPENAI_API_KEY=sk-...
   JQUANTS_REFRESH_TOKEN=...
   KABU_API_PASSWORD=...
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   PAPER_FILL_MODE=instant       # instant|partial|never|reject
   LINE_CHANNEL_ACCESS_TOKEN=...
   LINE_USER_ID=...
   LOG_LEVEL=INFO
   ```

   Settings クラスは必須の変数が未設定だと例外を出します（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD は require）。

4. 初期データディレクトリを作成（任意だが推奨）。
   ```bash
   mkdir -p data
   ```

---

## 使い方

プロジェクトはモジュールとして動かす、またはスクリプトを直接実行することができます。実行はプロジェクトルートから行ってください（src を PYTHONPATH に含めるかパッケージインストールしていることが前提）。

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV で切替）
  ```bash
  # モジュールとして（推奨）
  python -m kabusys.run_execution

  # 直接スクリプト実行（src/kabusys/run_execution.py から）
  python src/kabusys/run_execution.py
  ```
  注意: KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使われ、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）に書き込まれます。

- Monitoring（ポーリング）を起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。  
  停止はプロジェクトルートの `data/stop_requested.flag` を作成することで検知されます（run_monitoring と run_execution はこのファイルを参照します）。

- Streamlit ダッシュボード（監視ビュー）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  データベースを読み取り専用で開きます。MonitoringEngine によって monitoring.db が生成・更新されることを前提とします。

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # またはデフォルト DB を使う:
  python -m kabusys.tools.paper_verification_report
  ```
  `--db` オプションや環境変数 `PAPER_TRADING_SQLITE_PATH` で DB パスを指定可能。

- AI（ニューススコア／レジーム判定）
  Python から呼び出す例:
  ```python
  from kabusys.ai import score_news
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date は datetime.date 型
  count = score_news(conn, target_date, api_key="sk-...")
  ```
  OpenAI APIキーは引数で渡すか環境変数 `OPENAI_API_KEY` を利用します。失敗時はフェイルセーフでスキップする挙動が多く実装されています。

- Research（ファクター計算）
  Python から呼び出す例:
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value
  import duckdb
  conn = duckdb.connect("data/kabusys.duckdb")
  results = calc_momentum(conn, target_date)
  ```

- Portfolio（候補選定・比率計算・ポジションサイズ）
  Python から:
  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  candidates = select_candidates(buy_signals, max_positions=10)
  weights = calc_score_weights(candidates)
  sizes = calc_position_sizes(weights, candidates, portfolio_value, available_cash, current_positions, open_prices)
  ```

- 設定（Settings）関連
  環境変数は `kabusys.config.Settings` で取得します。代表的な設定:
  - KABUSYS_ENV: development | paper_trading | live
  - PAPER_FILL_MODE: instant | partial | never | reject
  - PID/FLAG 関連: PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START
  - 閾値: CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT

- 停止／強制停止フラグ
  - `data/stop_requested.flag`：run_monitoring / run_execution が起動ループ中に検出して正常終了するためのフラグ。
  - `data/kill.flag`（KillSwitch）：監視が特定のリスク条件を満たした際に ExecutionEngine 側に停止指示を出すために書き込まれる。`KillSwitch.clear()` で削除可能。設定 `KILL_FLAG_CLEAR_ON_START=1` を使うことで起動時にクリアする動作が設定可能。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下の主要モジュールを抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数読み込み + Settings
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor ポーリングスクリプト
    - tools/
      - paper_verification_report.py — Paper Trading 検証レポート（CLI）
    - execution/
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - execution_engine.py     (実装の続きが別ファイルにある想定)
      - broker_factory.py
      - broker_api.py
      - order_record.py
    - monitoring/
      - monitoring_db.py       — SQLite スキーマ & ラッパー
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - ai/
      - news_nlp.py            — OpenAI を使ったニューススコアリング
      - regime_detector.py     — 市場レジーム判定
    - research/
      - factor_research.py
      - feature_exploration.py
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - utils/
      - process_priority.py    — psutil を使った優先度 / affinity 設定
    - data/                    — 既定の DB / PID / FLAG を置く想定（.gitignore 推奨）

---

## 運用上の注意 / Tips

- DB の分離:
  - monitoring（監視）は常に Settings.sqlite_path（デフォルト data/monitoring.db）を参照します。
  - Execution は KABUSYS_ENV=paper_trading の場合に paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離されます。
- 環境依存機能:
  - process priority や CPU affinity の設定は psutil／OS 権限に依存します。権限不足の場合は警告ログを出してスキップします。
- OpenAI 呼び出し:
  - rate limit 等に対して指数バックオフでリトライしますが、APIキー未設定時は ValueError を出す箇所があるため事前に OPENAI_API_KEY を用意してください。
- Streamlit ダッシュボードは DB を読み取り専用で開くため、監視ループが動いている環境で使用してください。
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を基準に `.env` と `.env.local` を自動的に読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## よく使うコマンドまとめ

- 依存ライブラリのインストール
  ```bash
  pip install duckdb psutil openai requests streamlit
  ```

- 実行エンジン起動
  ```bash
  python -m kabusys.run_execution
  ```

- 監視ループ起動
  ```bash
  python -m kabusys.run_monitoring
  ```

- Streamlit ダッシュボード起動
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## ライセンス / 貢献

この README はコードベースの簡易ドキュメントです。プロジェクトのライセンス、貢献ガイドライン（CONTRIBUTING.md）や詳細な設計ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）が別途ある想定です。実装や運用ポリシーに合わせて README を拡張してください。

ご不明点や追記してほしい項目があれば教えてください。