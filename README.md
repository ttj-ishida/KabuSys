# KabuSys

日本株向け自動売買システムのモジュール群です。本リポジトリはトレード実行エンジン、監視（Monitoring）、リサーチ／ファクター計算、ポートフォリオ構築、AI ニュース解析などのコンポーネントを含みます。

この README ではプロジェクト概要、機能一覧、セットアップ手順、使い方（起動方法／ツール）、およびディレクトリ構成を日本語でまとめます。

---

## プロジェクト概要

KabuSys は以下の要素で構成される自動売買フレームワークです。

- ExecutionEngine（発注・注文管理、リスク管理、リコンシリエーション）
- Monitoring（システム／注文／リスクの監視、LINE 通知、kill flag）
- Research（DuckDB を用いたファクター計算・特徴量解析）
- Portfolio（候補選定、配分・株数決定、セクター制限）
- AI（ニュース NLP によるセンチメント評価、レジーム判定）
- 各種 CLI / スクリプト（Paper Trading 検証レポート、Streamlit ダッシュボード など）

設計方針として「本番 DB と Paper Trading の完全分離」「ルックアヘッドバイアスを避ける」「フェイルセーフの継続動作」が組み込まれています。

---

## 主な機能一覧

- 発注管理（OrderManager）: 注文生成、送信、状態同期、重複検知
- 発注リコンシリエーション（Reconciler）: 再起動時の自動復旧、ブローカーとのポジション照合
- リスク管理（RiskManager）: ポジション上限、ドローダウン監視（RiskMonitor）
- 監視（Monitoring）
  - SystemMonitor: CPU/MEM/DISK、プロセス生存確認、データ鮮度確認
  - TradeMonitor: 滞留注文・約定異常の検出
  - MonitoringDB: SQLite に監視ログを永続化（system_status / trade_logs / risk_logs / positions / dashboard）
  - AlertManager: LINE Push 通知、クールダウン管理
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine 停止指示
  - Streamlit ダッシュボード（データの読み取り専用）
- Research / Factor 計算（DuckDB 経由）
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC 計算、統計サマリー
- Portfolio 構築
  - 候補選定、等金額・スコア加重配分、リスクベース株数決定、セクター上限の適用
- AI（OpenAI）
  - news_nlp: raw_news を LLM（gpt-4o-mini）でセンチメント評価して ai_scores に保存
  - regime_detector: ma200 とマクロニュースを合成して market_regime を生成
- 開発用ツール
  - tools.paper_verification_report: Paper Trading DB を解析して PASS/FAIL レポートを出力
  - streamlit_dashboard: 監視情報の簡易ダッシュボード表示

---

## 要件（依存ライブラリ）

動作に必要な代表的なパッケージ（環境やバージョンにより追加が必要）:

- Python 3.10+
- duckdb
- psutil
- requests
- openai
- streamlit

pip で直接インストールする場合の例:
```
pip install duckdb psutil requests openai streamlit
```

requirements.txt がある場合は:
```
pip install -r requirements.txt
```

---

## セットアップ手順

1. リポジトリをクローン / コピー
2. Python 仮想環境を作成して有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```
3. 依存ライブラリをインストール
   ```
   pip install duckdb psutil requests openai streamlit
   ```
4. 環境変数を設定
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（OS 環境変数が優先されます）。
   - 自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

代表的な環境変数（主要なもの）:
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV: 実行環境 ("development" | "paper_trading" | "live")（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite（デフォルト: data/paper_trading.db）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
- PID_FILE_PATH / KILL_FLAG_PATH: pid / kill.flag のパス
- PAPER_FILL_MODE: paper_trading 時の模擬約定モード ("instant" | "partial" | "never" | "reject")
- LOG_LEVEL: ログレベル ("DEBUG","INFO",...)
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring の上書き）

注意:
- run_monitoring は「監視」用で、KABUSYS_ENV にかかわらず本番の sqlite_path を使用します（設計上の意図）。
- Paper Trading 実行（run_execution）では KABUSYS_ENV=paper_trading の場合に専用 DB（PAPER_TRADING_SQLITE_PATH）を使用します。

---

## 使い方（起動例）

基本的にスクリプトはパッケージのモジュールとして実行します。実行前に必要な環境変数を設定してください。

1. ExecutionEngine（発注実行）
   - 本番/開発/ペーパーに応じて KABUSYS_ENV を設定します。
   ```
   export KABUSYS_ENV=paper_trading
   python -m kabusys.run_execution
   ```
   run_execution はプロセス優先度を高く設定し、SQLite / DuckDB に接続してエンジンを起動します。paper_trading 環境では MockBrokerClient を使用し、Paper 用 DB（data/paper_trading.db）へ記録します。

2. Monitoring（ポーリングループ）
   - 監視ループを起動します（ポーリング間隔は MONITOR_POLL_INTERVAL で override 可能、デフォルト 60 秒）。
   ```
   export MONITOR_POLL_INTERVAL=30
   python -m kabusys.run_monitoring
   ```
   run_monitoring は process priority を高にして SystemMonitor を定期実行し、MonitoringDB（SQLite）へログを保存します。

3. Streamlit ダッシュボード（監視の可視化）
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```
   監視 DB を読み取り専用で開いてダッシュボードを表示します。MonitoringEngine を先に起動してデータを作成してください。

4. Paper Trading 検証レポート
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   # または DB パスを指定
   python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
   ```
   指定期間の稼働率・注文成功率・レイテンシ等を集計して PASS/FAIL 判定を行います。

5. AI 系処理（ニューススコア / レジーム判定）
   - OpenAI API キーが必要です（OPENAI_API_KEY 環境変数または関数引数で渡す）。
   - news_nlp.score_news / regime_detector.score_regime は DuckDB 接続と target_date を引数として使用します（スクリプト化されていないため呼び出しは Python 内で行います）。
   - 例（簡易イメージ）:
     ```python
     import duckdb
     from kabusys.ai.news_nlp import score_news
     conn = duckdb.connect("data/kabusys.duckdb")
     score_news(conn, target_date=date(2026,4,11))
     ```

---

## 環境変数（主な一覧と説明）

- KABUSYS_ENV: "development" | "paper_trading" | "live"（動作モード）
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- OPENAI_API_KEY: OpenAI API キー（AI 機能に必須）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: PaperTrading の約定モード ("instant"|"partial"|"never"|"reject")
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PID_FILE_PATH: ExecutionEngine の PID ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch の flag パス（デフォルト: data/kill.flag）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用設定
- LOG_LEVEL: ログレベル

（Settings モジュールにより多くのパラメータが管理されています。詳細は src/kabusys/config.py を参照してください。）

---

## 注意点 / 運用上のポイント

- 自動 .env ロード:
  - プロジェクトルート (.git または pyproject.toml のあるディレクトリ) にある `.env` / `.env.local` が自動で読み込まれます。OS の環境変数が優先され、`.env.local` は `.env` の上書き用です。自動ロードを無効化する場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DB の分離:
  - Paper Trading は専用の SQLite DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番の monitoring DB と分離するよう設計されています。
  - run_monitoring はどの env でも `sqlite_path`（本番用 monitoring DB）を使用します。
- KillSwitch:
  - RiskMonitor がトリガーすると data/kill.flag に理由を書き込み、ExecutionEngine がこのフラグを検知して安全に停止する想定です。フラグの自動クリア設定は Settings.kill_flag_clear_on_start を参照してください。
- AI 機能:
  - OpenAI API への呼び出しはネットワークやレート制限に影響されます。score_news は一部エラーを許容して継続する実装になっていますが、API キーの管理とコストに注意してください。
- プロセス優先度:
  - 起動スクリプト（run_execution, run_monitoring）は set_process_priority("high") を最初に実行します。権限や OS により設定できない場合は WARNING が出ます。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py — パッケージ定義（バージョン等）
  - config.py — 環境変数 / 設定の読み込み・検証（.env 自動読み込み含む）
  - run_execution.py — ExecutionEngine 起動スクリプト（Entry point）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート CLI
  - execution/
    - order_manager.py — OrderManager（発注ロジック）
    - reconciler.py — 起動時の注文・ポジション照合
    - (その他実装ファイル: broker_factory, execution_engine, order_repository, order_record, risk_manager, ...)
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化・永続化 API（MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留／約定異常監視
    - risk_monitor.py — ドローダウン／ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各モニタを束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・投下資金スケーリング
    - risk_adjustment.py — セクター上限・レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算
    - feature_exploration.py — 将来リターン・IC・統計サマリ
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — レジーム判定（ma200 + macro sentiment）
  - data/ (想定: 実データ配置)
    - kabusys.duckdb (DuckDB ファイル)
    - monitoring.db (SQLite)
    - paper_trading.db (Paper Trading 用 SQLite)

上記に挙げた他にも補助モジュールや実装ファイルがあります。詳細は各ファイルの docstring / コメントを参照してください。

---

## 開発・拡張のヒント

- DuckDB 接続を受け取る設計のため、研究系関数は本番口座やブローカー API にアクセスしません。これにより単体テストやローカル検証が容易です。
- AI 呼び出し部分（news_nlp._call_openai_api / regime_detector._call_openai_api）はモック可能に設計されています（unittest.mock.patch など）。
- MonitoringDB のスキーマは init_monitoring_db で冪等に初期化・簡易マイグレーションを行います。既存 DB への変更がある場合はここに追記してください。

---

この README は現行ソース（src/ 配下）を参照してまとめています。各モジュールの詳細（引数や戻り値、例外挙動など）は該当ファイルの docstring を参照してください。質問や追加で README に載せたい情報（例: デプロイ手順、systemd ユニットファイル例など）があれば教えてください。