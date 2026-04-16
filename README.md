# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ＋実行スクリプト群）  
この README はリポジトリ内の主要モジュール・起動スクリプト・ツールの使い方とセットアップ手順をまとめたものです。

---

## プロジェクト概要

KabuSys は以下の機能を備えた、自動売買および研究用のコード群です。

- 注文発行・状態管理（ExecutionEngine、OrderManager、Reconciler）
- 監視機能（SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、AlertManager）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限など）
- リサーチ（ファクター計算、将来リターン、IC計算、統計サマリー）
- AI（OpenAI）を用いたニュースセンチメント評価・市場レジーム判定
- Paper Trading 向けの分離された DB と検証レポート生成ツール
- Streamlit ベースの監視ダッシュボード

設計方針の一例：
- 本番データと Paper Trading は DB を分離して扱う
- ルックアヘッドバイアスを避けるために内部で date.today()/datetime.today() を直接参照しない実装を心がける
- 外部 API 呼び出しはフェイルセーフ（失敗時はフォールバックして継続）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - Broker クライアントの抽象化と Factory（paper/live 切替）
  - OrderManager（注文生成・同期）、Reconciler（起動時リコンシリエーション）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク/データ鮮度/プロセス稼働を監視して SQLite にログ
  - TradeMonitor：滞留注文や約定異常を検出してリスクログに記録
  - RiskMonitor：ドローダウン・ポジション上限を判定して kill flag をトリガ
  - AlertManager：LINE push による通知（クールダウン管理）
  - MonitoringEngine：上記を束ねたポーリングループ
  - Streamlit ダッシュボード（監視 DB を参照）
- Portfolio
  - 候補選定、等重・スコア重み付け、リスク調整（セクター制限、レジーム乗数）、ポジションサイズ計算
- Research
  - ファクター計算（モメンタム、バリュー、ボラティリティ）
  - 将来リターン計算、IC（スピアマン）計算、統計サマリー
- AI
  - news_nlp: raw_news から OpenAI で銘柄毎のセンチメントスコアを生成して ai_scores に保存
  - regime_detector: ma200 とマクロニュースの LLM スコアを合成して market_regime に書込
- Tools
  - paper_verification_report: Paper Trading DB を分析して検証レポートを標準出力に出す

---

## セットアップ手順（開発向け）

1. リポジトリをクローン／チェックアウトします。

2. Python 環境を用意（推奨: venv / pyenv）
   - 例:
     python -m venv .venv
     source .venv/bin/activate

3. 必要パッケージをインストール
   - リポジトリに requirements.txt が無い場合、最低限次をインストールしてください：
     pip install duckdb psutil requests openai streamlit
   - 他にテストや開発で必要なパッケージがあれば適宜追加してください。

4. data ディレクトリを準備（任意ですが便利）
   mkdir -p data

5. 環境変数を設定
   - 開発ではプロジェクトルートに `.env` / `.env.local` を置くと自動ロードします（OS 環境優先）。  
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 主要な環境変数（必要に応じて設定）：
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須機能を使う場合）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI キー（AI 機能を使うとき）
     - KABUSYS_ENV — 開発/本番/ペーパートレード: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の約定モード: instant | partial | never | reject（デフォルト: instant）
     - PAPER_TRADING_SQLITE_PATH — Paper DB パス（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視用 sqlite DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
     - LOG_LEVEL — ログレベル（DEBUG|INFO|...）
   - 例 (.env):
     KABUSYS_ENV=development
     KABU_API_PASSWORD=your_password
     OPENAI_API_KEY=sk-...
     SQLITE_PATH=data/monitoring.db
     DUCKDB_PATH=data/kabusys.duckdb

6. DB 初期化は多くの起動スクリプト内で自動的に行われます（monitoring のテーブルは init_monitoring_db で冪等に作成）。

---

## 使い方（起動 / 実行例）

※ すべてプロジェクトルート（src の親）で実行することを想定しています。

- 監視ループを起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60 秒）
  - 停止はプロジェクトルートの data/stop_requested.flag を作成することで安全に停止可能
  - 実行:
    python -m kabusys.run_monitoring
  - 補足:
    - run_monitoring は Monitoring DB に常に本番の sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しない）。

- ExecutionEngine（注文実行エンジン）を起動
  - Paper Trading の場合（KABUSYS_ENV=paper_trading）MockBrokerClient を使い、Paper DB（デフォルト: data/paper_trading.db）に記録します。
  - 実行:
    python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成するとエンジンは検知して安全に停止します。
    - PID ファイルは data/execution.pid に保存されます。

- Paper Trading 検証レポート
  - SQLite DB を指定して検証レポートを標準出力へ表示
  - 実行例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db data/paper_trading.db

- Streamlit 監視ダッシュボード
  - 実行例:
    streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で開きます（起動中の MonitoringEngine と併用可能）。

- AI 機能（ニューススコア / レジーム判定）
  - プログラム／REPL から呼び出す例:
    from kabusys.ai import score_news
    score_news(duckdb_conn, target_date, api_key="sk-...")
  - OpenAI API エラーはリトライ処理やフォールバックを備えていますが、API キーの設定が必要です。

---

## 主要な環境変数（要点）

- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、ExecutionEngine は専用の Paper DB を使用します。
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 を設定すると .env 自動ロードを無効化
- PAPER_FILL_MODE: instant | partial | never | reject（paper trading の約定挙動）
- OPENAI_API_KEY: OpenAI を使う機能で必須
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager を有効にするため

Settings モジュール（kabusys.config.Settings）が環境変数をラップしており、必要な変数が不足している場合は ValueError を投げます。

---

## 停止 / キルフラグ

- ExecutionEngine / Monitoring の起動スクリプトはプロジェクトルートの data/stop_requested.flag の有無を監視し、ファイルが存在すると安全に終了します。
- KillSwitch は data/kill.flag を書き込んで ExecutionEngine に外部停止要求を出す仕組みです（RiskMonitor がトリガ）。kill.flag が既にある場合は再書き込みしません。ExecutionEngine 側は起動時に kill.flag をクリアする設定（Settings.kill_flag_clear_on_start）を持つことができます。

---

## 開発者向け補足

- 自動的に .env／.env.local をロードする実装:
  - OS 環境変数 > .env.local（上書き）> .env（未設定キーのみ）
  - プロジェクトルートの判定は .git または pyproject.toml によって行います
- process priority / cpu affinity:
  - kabusys.utils.process_priority.set_process_priority() で Windows/Linuxの差分を吸収して優先度変更を試みます（権限不足時は警告でスキップ）。
- DB マイグレーション:
  - monitoring DB の init_monitoring_db() は必要なカラムが無ければ ALTER TABLE で追加する簡単なマイグレーション処理を行います（冪等）。

---

## ディレクトリ構成（抜粋）

src/
- kabusys/
  - __init__.py
  - config.py                        — 環境変数 / Settings
  - run_monitoring.py                — SystemMonitor ポーリング起動スクリプト
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading 検証レポート
  - ai/
    - news_nlp.py                    — ニュースセンチメント（OpenAI）
    - regime_detector.py             — 市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py               — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - (他: broker_factory, execution_engine, order_repository, ...)
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
    - process_priority.py
    - __init__.py
  - data/ (プロジェクトルートに想定される出力／フラグ／DB ファイル)
    - monitoring.db (デフォルト SQLite)
    - kabusys.duckdb (デフォルト DuckDB)
    - paper_trading.db (Paper Trading 用 SQLite)
    - stop_requested.flag / kill.flag / execution.pid

（実装ファイルはリポジトリ内にさらに多数存在します。上は主要モジュールの抜粋です）

---

## よくある質問 / 注意点

- データベースファイルが無い場合、初回起動時に必要なテーブルが作成されます（Monitoring 側）。
- Paper Trading と Live は DB を分離しているため、Paper 環境での操作は本番 DB に影響しません。
- OpenAI による処理は API の利用料が発生します。テスト時はモック（unittest.mock.patch）で _call_openai_api を差し替えてください（コードにその旨の注釈あり）。
- MONITOR_POLL_INTERVAL に 0 や負数を設定すると無効値としてデフォルト（60 秒）にフォールバックします。
- PAPER_FILL_MODE の値は限定されており、不正値を設定すると例外になります。

---

この README はコードの主要な点をまとめたものです。より詳しい実装意図やアルゴリズム設計（PortfolioConstruction.md、StrategyModel.md 等の設計文書）があればそちらを参照してください。必要であればセットアップスクリプト（requirements.txt、Dockerfile、systemd unit など）のテンプレートも作成できます。ご希望があれば教えてください。