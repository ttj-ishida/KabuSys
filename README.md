# KabuSys

KabuSys は日本株向けの自動売買・検証・監視フレームワークです。  
このリポジトリには、発注エンジン（ExecutionEngine）、監視コンポーネント、ポートフォリオ構築ロジック、リサーチ／ファクター計算、AI ベースのニュースセンチメント処理、ストリームリットダッシュボードなどが含まれます。

---

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 実際の起動例（Execution / Monitoring / Paper）
  - Paper Trading 検証レポート
  - 監視ダッシュボード（Streamlit）
  - AI モジュールの利用
- 環境変数（主な設定）
- ディレクトリ構成
- 補足・トラブルシューティング

---

## プロジェクト概要

KabuSys は以下の目的を持つ Python ベースの自動売買システム用ライブラリ／アプリケーション群です。

- 注文の作成・送信・状態同期（再起動時のリコンシリエーション）
- リスク管理（ドローダウン検出、ポジション上限）
- システム監視（CPU/メモリ/Disk、プロセス生存、データ鮮度）
- モニタリング DB（SQLite）へのログ永続化と Streamlit ダッシュボード
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制限）
- リサーチ用ファクター計算（DuckDB を用いた prices_daily/raw_financials の処理）
- AI を用いたニュースセンチメント評価（OpenAI API）
- Paper Trading（本番 DB と分離したシミュレーション記録）
- 運用ユーティリティ（PID ファイル、kill.flag、プロセス優先度設定等）

---

## 機能一覧

主な機能・モジュール（抜粋）

- execution
  - ExecutionEngine（注文実行セッション）
  - OrderManager / OrderRepository / Reconciler（再起動時の同期）
  - Broker クライアントファクトリ（paper_trading 時は MockBroker 使用）
- monitoring
  - SystemMonitor（CPU/メモリ/Disk、プロセス生存、データ鮮度）
  - TradeMonitor（滞留注文、約定異常）
  - RiskMonitor（ドローダウン・ポジション上限監視）
  - MonitoringDB（SQLite ベースのログ保存・永続化）
  - AlertManager（LINE Push による通知、クールダウン機能）
  - KillSwitch（kill.flag による ExecutionEngine 停止指示）
  - MonitoringEngine（監視ループ統括）
  - Streamlit ダッシュボード（監視用）
- portfolio
  - 候補選定 / 等金額・スコア重み / position sizing / セクター上限 / レジーム乗数
- research
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）等の統計関数
- ai
  - news_nlp: raw_news から OpenAI を用いた銘柄別センチメントスコアを ai_scores に書き込む
  - regime_detector: ETF ma200 とマクロニュース（LLM）を組み合わせて日次レジーム判定
- tools
  - paper_verification_report: Paper Trading DB を元に稼働率・成功率・レイテンシ等の検証レポートを出力

---

## セットアップ手順

前提
- Python 3.10 以上（型ヒントに `X | Y` 記法を使用）
- SQLite（標準で同梱）
- DuckDB（DuckDB Python パッケージ）

必須パッケージ（例）
- duckdb
- psutil
- requests
- streamlit
- openai

pip での例:
```bash
python -m pip install "duckdb" "psutil" "requests" "streamlit" "openai"
```

（プロジェクトに requirements.txt があればそれを利用してください）

プロジェクトルートに data/ ディレクトリを用意しておくとスムーズです:
```bash
mkdir -p data
```

.env の自動読み込み
- プロジェクトルートに `.env` / `.env.local` を置くと Settings モジュールが自動で読み込みます（ただし OS 環境変数が優先）。
- 自動ロードを無効にする場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 使い方

### 実行（Production / Paper Trading モード）

- ExecutionEngine を起動（本番 / paper_trading の区別は KABUSYS_ENV）
```bash
# 本番環境（default）
python -m kabusys.run_execution

# Paper Trading（MockBroker を使用し、data/paper_trading.db に記録）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

- Monitoring（監視ポーリングループ）を起動
```bash
# ポーリング間隔のオーバーライド（秒）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- 補足:
  - run_monitoring は Settings の sqlite_path（監視 DB）を使用して永続化します。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使う設計です。
  - run_execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path に書き出します（本番 DB と分離）。

### Paper Trading 検証レポート
Paper Trading の SQLite DB（デフォルト: data/paper_trading.db）からレポートを生成します。

```bash
python -m kabusys.tools.paper_verification_report \
    --from 2026-04-01 --to 2026-04-11 \
    --db data/paper_trading.db
```

オプション:
- --from YYYY-MM-DD
- --to YYYY-MM-DD
- --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数より優先）

レポートは標準出力に稼働率、注文成功率、P95 レイテンシ等を表示し、簡易 Pass/Fail を出します。

### 監視ダッシュボード（Streamlit）
監視 DB を読み取り専用で開いてダッシュボードを起動します:

```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- 既に monitoring が起動していないと DB ファイルが存在しないか読み取りできない旨のエラーを表示します。
- ダッシュボードではダッシュボード集計（portfolio value / cash / drawdown）、ポジション、最近の注文、最新のシステム状態、リスクログ等を参照できます。

### AI モジュールの利用（ニュース NLP / レジーム判定）
これらは DuckDB 接続と OpenAI API キーを渡して呼び出します。例（スクリプトや REPL から）:

- ニューススコアリング:
  - 関数: kabusys.ai.score_news（ai/news_nlp.py の score_news）
  - 引数: duckdb_conn（DuckDB 接続）、target_date（date）、api_key（省略時は env OPENAI_API_KEY を使用）
- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime
  - 同様に duckdb_conn と target_date, api_key を渡す

注意:
- OpenAI API キーが未設定だと ValueError が発生します（呼び出し前に OPENAI_API_KEY を設定するか引数で渡してください）。
- API の一時エラー（429、タイムアウトなど）には内部でリトライロジックが実装されています。

---

## 環境変数（主な設定）

設定は `kabusys.config.Settings` で管理されます。代表的な環境変数:

必須（実行時に必要な場合）
- JQUANTS_REFRESH_TOKEN … J-Quants API（プロジェクトによって必要）
- KABU_API_PASSWORD … kabuステーション API のパスワード

任意 / デフォルトあり
- KABUSYS_ENV … one of development | paper_trading | live（デフォルト: development）
- LOG_LEVEL … DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- OPENAI_API_KEY … OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID … AlertManager（LINE）用
- DUCKDB_PATH … DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH … 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH … Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE … paper_trading の約定動作（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH … ExecutionEngine 用 PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH … KillSwitch の flag パス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START … 起動時に kill.flag を自動でクリアする（"1" で有効）
- MONITOR_POLL_INTERVAL … run_monitoring のポーリング間隔を秒で上書き（デフォルト 60 秒）

.env ファイルの自動ロード:
- プロジェクトルート（.git または pyproject.toml を探索）にある `.env` と `.env.local` を自動的に読み込みます。
- OS 環境変数が優先され、`.env.local` は `.env` を上書きします。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py — 環境変数 / Settings
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト
- tools/
  - paper_verification_report.py — Paper Trading レポート
- monitoring/
  - __init__.py
  - monitoring_db.py — SQLite スキーマ初期化 + MonitoringDB クラス
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照・実装あり)
  - broker_factory / broker_api / execution_engine 等（発注系）
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- data/（想定）
  - katusys.duckdb（DuckDB）
  - monitoring.db（SQLite）
  - paper_trading.db（Paper Trading 用 DB）
- utils/
  - process_priority.py
  - __init__.py

注: 上のファイル一覧はこのリポジトリ内の主なファイルを示しています。詳細は各モジュールのドキュメント文字列（docstring）を参照してください。

---

## 補足・トラブルシューティング

- OpenAI API:
  - API キーがないと news_nlp / regime_detector は動作しません。テスト時はモック化（unittest.mock.patch）を推奨します。
- DuckDB / SQLite:
  - DuckDB は大量の時系列計算に使います。DuckDB ファイルパスは Settings.duckdb_path で指定します。
  - Streamlit ダッシュボードから DB を読み込む際は read-only URI を使用（既存プロセスが書き込み中でも読み取り可能にすることが望ましい）。
- プロセス優先度設定:
  - set_process_priority はプラットフォーム依存のためアクセス権がないと警告になり設定されません（無視して動作は継続します）。
- kill.flag:
  - KillSwitch は data/kill.flag を作成すると ExecutionEngine に停止指示を送る設計です。起動時に古い flag を消す場合は KILL_FLAG_CLEAR_ON_START=1 を設定してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は既存 DB に必要カラム（例: peak_value, latency_ms）がない場合に追加する簡易マイグレーションロジックを実行します。運用前にバックアップを取ってください。

---

この README はコードコメント（docstring）を元にまとめています。各モジュールの詳細な使い方や API は該当ファイルの docstring を参照してください。必要であれば、起動スクリプトの実行例や .env のサンプルなどを追加で作成します。どの情報を優先して詳細化しますか？