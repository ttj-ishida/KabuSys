# KabuSys — README (日本語)

本リポジトリは日本株向けの自動売買システム（KabuSys）のモジュール群です。価格データの集計・ファクター計算、ポートフォリオ構築、注文実行／リコンシリエーション、監視・アラート、News NLP によるセンチメント評価などの機能を含みます。

---

## プロジェクト概要

KabuSys は以下の関数群・コンポーネントで構成されるモジュール式の自動売買基盤です。

- research: DuckDB を使ったファクター計算、将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ
- portfolio: 候補選定・重み付け、リスク制御（セクター上限・レジーム乗数）、ポジションサイズ計算
- execution: ブローカー抽象化、Order 管理、Execution Engine、再起動時のリコンシリエーション
- monitoring: システム／注文／リスク監視、アラート（LINE）、ダッシュボード（Streamlit）
- ai: ニュース NLP（OpenAI）を使った銘柄別センチメント付与、レジーム判定
- tools: 検証レポート生成などの CLI ツール
- utils: プロセス優先度や CPU affinity 等のユーティリティ

設計方針として、DuckDB/SQLite を用いたローカルデータ管理、外部 API へのアクセスを抽象化（テスト容易性）、およびルックアヘッドバイアス対策（日時参照の扱い）を重視しています。

---

## 主な機能一覧

- ファクター計算（モメンタム、ボラティリティ、バリューなど） — src/kabusys/research/factor_research.py
- 特徴量解析・IC 計算・統計サマリー — src/kabusys/research/feature_exploration.py
- 銘柄候補選定・スコア重み付け・等配分 — src/kabusys/portfolio/*
- ポジションサイズ計算（リスクベース／等配分）と丸め（単元株） — src/kabusys/portfolio/position_sizing.py
- ExecutionEngine 起動・Order 管理・再同期（Reconciler） — src/kabusys/execution/*
- 監視（System / Trade / Risk）と永続化（SQLite） — src/kabusys/monitoring/*
- アラート（LINE Push） — AlertManager
- Streamlit を使った監視ダッシュボード — src/kabusys/monitoring/streamlit_dashboard.py
- OpenAI を用いたニュースセンチメント（ai/news_nlp.py）・市場レジーム判定（ai/regime_detector.py）
- Paper Trading 用検証レポート生成ツール — src/kabusys/tools/paper_verification_report.py

---

## 要件（例）

- Python 3.9+
- duckdb
- psutil
- requests
- openai (OpenAI Python SDK)
- streamlit (ダッシュボード利用時)
- sqlite3（標準ライブラリ）
- その他（ビルド/環境により）: pip 等

※ requirements.txt が無ければ以下のようにインストールしてください（例）:
pip install duckdb psutil requests openai streamlit

---

## セットアップ手順

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. Python 仮想環境を作成・有効化（推奨）
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)

3. 依存パッケージをインストール
   pip install -r requirements.txt
   または
   pip install duckdb psutil requests openai streamlit

4. 環境変数設定
   プロジェクトルートに `.env` または `.env.local` を置いて環境変数を定義できます（Settings モジュールで自動ロードします）。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

5. データディレクトリ
   デフォルトの DB /フラグパスは `data/` 下にあります（自動的に作成されます）。実行前に権限を確認してください。

---

## 設定（主な環境変数）

Settings クラス（src/kabusys/config.py）が参照する主な環境変数：

必須または重要なもの
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API のパスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（ai モジュール利用時）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）

DB 関連（デフォルトは data 以下）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）

Paper Trading 関連
- PAPER_FILL_MODE — MockBroker の fill モード: instant | partial | never | reject（デフォルト: instant）

監視 / 実行関連
- PID_FILE_PATH — ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — KillSwitch が書き込むパス（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

ロギング / アラート
- LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
- LINE_CHANNEL_ACCESS_TOKEN — LINE push 用 token
- LINE_USER_ID — LINE push 宛先ユーザ ID

そのほか Settings に定義されているプロパティを参照してください（src/kabusys/config.py）。

注意:
- Settings は `.env` と `.env.local` を自動読み込みします（OS 環境変数 > .env.local > .env の優先順）。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して自動ロードを無効化できます。

---

## 使い方（主なコマンド）

パッケージのトップにあるスクリプトはモジュールとして起動できます。パッケージを PYTHONPATH に含めるかプロジェクトルートで実行してください。

- 監視ループを起動（SystemMonitor をポーリング）
  python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能
  - run_monitoring は MonitoringDB（sqlite）を初期化します
  - 監視は data/stop_requested.flag の検出で終了します

- Execution Engine を起動（注文実行）
  python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します
  - 起動中に data/stop_requested.flag が作成されると停止を試みます
  - PID ファイル: data/execution.pid（既定）

- Paper Trading 検証レポート（CSV ではなくコンソール出力）
  python -m kabusys.tools.paper_verification_report
  例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

- Streamlit ダッシュボード（監視 UI）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ニュース NLP（Python API）
  from kabusys.ai.news_nlp import score_news
  score_news(conn, target_date, api_key="xxxx")
  - conn は DuckDB 接続（duckdb.connect(...)）
  - target_date は datetime.date（例: date(2026,4,1)）
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY

- レジーム判定（ai/regime_detector）
  from kabusys.ai.regime_detector import score_regime
  score_regime(conn, target_date, api_key="xxxx")

停止の仕組み
- run_execution / run_monitoring はプロジェクト内の data/stop_requested.flag をポーリングします。外部から停止を要求する場合はこのファイルを作成してください（管理ツールやスクリプトで作成）。

KillSwitch（自動停止）
- RiskMonitor + KillSwitch により、ドローダウンやポジション上限等の条件で data/kill.flag を書き込み、ExecutionEngine 側で検出して停止させる仕組みがあります。

ログレベル設定
- 環境変数 LOG_LEVEL でログレベルを調整できます（例: LOG_LEVEL=DEBUG）。

---

## ディレクトリ構成（主要ファイル）

- src/
  - kabusys/
    - __init__.py
    - config.py — 環境変数 / 設定管理（.env 自動ロード）
    - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py — ExecutionEngine 起動スクリプト
    - ai/
      - news_nlp.py — ニュースセンチメント（OpenAI）処理
      - regime_detector.py — 市場レジーム判定（MA + macro sentiment）
      - __init__.py
    - monitoring/
      - monitoring_db.py — SQLite テーブル定義 / 永続化 API
      - system_monitor.py — CPU / メモリ / PID / データ鮮度監視
      - trade_monitor.py — 滞留注文 / 約定異常監視
      - risk_monitor.py — ドローダウン・ポジション上限監視
      - kill_switch.py — kill.flag 書き込み管理
      - monitoring_engine.py — 各監視を束ねるエンジン
      - alert_manager.py — LINE push 通知
      - streamlit_dashboard.py — Streamlit ダッシュボード
      - __init__.py
    - execution/
      - order_manager.py
      - reconciler.py
      - (その他実行系のモジュール)
    - portfolio/
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
      - __init__.py
    - research/
      - factor_research.py
      - feature_exploration.py
      - __init__.py
    - utils/
      - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
      - __init__.py
    - tools/
      - paper_verification_report.py — 検証レポート生成 CLI
      - __init__.py
- data/
  - monitoring.db (デフォルト)
  - kabusys.duckdb (デフォルト)
  - paper_trading.db (paper_trading 用、デフォルト)
  - execution.pid
  - stop_requested.flag
  - kill.flag
  （data/ は実行時に作成されます）

---

## 開発・運用上の注意

- DB 分離: paper_trading 環境は paper_trading 用 SQLite を使用することで本番 DB と完全分離されます（安全性確保）。
- 監視 DB（monitoring.db）は run_monitoring / run_execution が start 時にテーブルを冪等で初期化します（init_monitoring_db）。
- OpenAI 呼び出しはリトライ/バックオフ処理を含みますが、API キー未設定では例外を投げます（呼び出し側でハンドルしてください）。
- 時刻取扱い: ルックアヘッドバイアスを防ぐため、モジュールは date / datetime の扱いに注意しており、target_date を明示的に渡す設計を推奨します。
- 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml）を検出して `.env` / `.env.local` を読み込みます。OS 環境変数を保護するため .env の上書き制御が入ります。
- プロセス優先度: 起動スクリプトは set_process_priority("high") を呼び出して優先度を上げようとしますが、権限不足などで失敗する可能性があります（警告ログのみ）。

---

## よく使うコマンドまとめ

- 監視起動:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン起動（Paper Trading）:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- 検証レポート:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

- Streamlit ダッシュボード:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

---

必要であれば README に具体的な .env.example（必須項目のテンプレート）、デバッグ手順、ユニットテスト実行の説明なども追加できます。どの情報を追記しますか？