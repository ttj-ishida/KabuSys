# KabuSys

軽量な日本株自動売買システムのコアライブラリ群と運用ツール群です。本リポジトリは取引実行、監視、リサーチ、ポートフォリオ構築、AI（ニュースセンチメント／レジーム判定）などのモジュールを含み、ローカル SQLite / DuckDB を用いて動作します。

## 特徴（概要）
- 実行エンジン（ExecutionEngine）と監視エンジン（MonitoringEngine）を分離
- Production / Paper Trading 環境を分離（KABUSYS_ENV）
- DuckDB を用いたファクタ計算・リサーチ（prices_daily / raw_financials 参照）
- OpenAI（gpt-4o-mini）を用いたニュースセンチメントとレジーム判定（フォールバックあり）
- 監視データを SQLite に永続化、Streamlit ダッシュボードで可視化
- プロセス優先度・CPU affinity 管理ユーティリティを内蔵
- Paper Trading 用の検証レポート生成ツール付き

## 主な機能一覧
- Execution
  - 起動スクリプト: kabusys.run_execution
  - Broker クライアントの差し替え（paper_trading では MockBroker を使用）
  - OrderManager / Reconciler による再起動時リコンシリエーション
  - RiskManager による注文前の各種リスク制御
- Monitoring
  - 起動スクリプト: kabusys.run_monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor による定期監視
  - MonitoringDB: system_status / trade_logs / positions / risk_logs / dashboard テーブル
  - KillSwitch による flag ファイルでの ExecutionEngine 停止指示
  - AlertManager による LINE Push 通知（任意）
  - Streamlit ダッシュボード（read-only）
- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC 計算・統計サマリー
  - ポートフォリオ構築（候補選定、重み付け、単元丸め、リスク調整）
- AI
  - ニュース記事のセンチメントスコアリング（ai.score_news）
  - 市場レジーム判定（ai.regime_detector.score_regime）
- ツール
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

## 必要要件（主な依存パッケージ）
- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボードを使う場合)
- sqlite3（標準ライブラリ）
（実際のプロジェクトでは requirements.txt を用意して pip install -r requirements.txt を推奨します。）

例:
pip install duckdb psutil requests openai streamlit

## 環境変数（主なもの）
（プロジェクトルートの `.env` / `.env.local` を自動ロードします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能））

- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- SQLITE_PATH: 監視 DB（SQLite）パス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の約定挙動（"instant" | "partial" | "never" | "reject"、デフォルト: "instant"）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）用
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: kill flag パス（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag をクリアする場合 "1"
- LOG_LEVEL: "DEBUG" | "INFO" | ...

監視ループのポーリング間隔:
- MONITOR_POLL_INTERVAL: 秒（デフォルト: 60）。不正な値や 0 以下はデフォルトにフォールバックします。

注意点:
- Monitoring は KABUSYS_ENV にかかわらず sqlite_path（本番）を使用してログを記録します（設計上の仕様）。
- Execution は KABUSYS_ENV=paper_trading の場合 paper_sqlite_path（data/paper_trading.db）を使用し、本番 DB と完全に分離します。

## セットアップ手順（簡易）
1. リポジトリをクローンして作業ディレクトリをプロジェクトルートにする
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows: .venv\Scripts\activate）
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）
4. .env を作成（.env.example があれば参考に）
   例:
   ```
   KABUSYS_ENV=development
   JQUANTS_REFRESH_TOKEN=xxx
   KABU_API_PASSWORD=yyy
   OPENAI_API_KEY=sk-...
   SQLITE_PATH=data/monitoring.db
   DUCKDB_PATH=data/kabusys.duckdb
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   LINE_CHANNEL_ACCESS_TOKEN=
   LINE_USER_ID=
   ```
5. 必要なデータベースファイル（DuckDB の prices_daily や raw_financials 等）を準備

## 使い方（主要なエントリポイント）

- Monitoring を起動（ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL でポーリング間隔を秒で上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - プロセス優先度を "high" に設定して起動します

- Execution を起動（実行エンジン）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB を使用し MockBrokerClient を利用します
  - 起動時に Reconciler による同期等が行われます

- Paper Trading 検証レポート（コマンドライン）
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で別の SQLite ファイルを指定可能
  - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH による上書き可）

- Streamlit ダッシュボード（監視用）
  ```
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```
  - 監視 DB を read-only モードで開き、Overview / Positions / Orders / System を表示します

- AI 機能の利用
  - ニュースセンチメント: kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジームスコア: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用。未設定時は ValueError。

## 運用上の注意
- Monitoring は監視ログへ永続化するため、監視 DB は定期バックアップを推奨します。
- KillSwitch は data/kill.flag を書き込むことで Execution を停止させる仕組みです（冪等に書き込む）。
- Paper Trading モードでは本番 DB と分離されるため、実運用前に paper_trading にて十分な検証を行ってください。
- OpenAI を用いる機能は外部 API に依存するため、API 失敗時のフォールバック（score=0 やスキップ）がコード内で実装されていますが、API コスト・レート制限に注意してください。

## ディレクトリ構成（主要ファイル）
（src/kabusys 配下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数・設定の読み込み / Settings
  - run_monitoring.py        — Monitoring のポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py        — SQLite スキーマ初期化・DB API
    - monitoring_engine.py    — Monitor の束ね実行 (MonitoringEngine)
    - system_monitor.py       — システム状態・データ鮮度監視
    - trade_monitor.py        — 注文滞留・約定異常監視
    - risk_monitor.py         — ドローダウン・ポジション上限監視
    - kill_switch.py          — kill.flag 管理
    - alert_manager.py        — LINE 通知
    - streamlit_dashboard.py  — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py     — (Referential) Orders DB 操作（実装一部）
    - reconciler.py          — 起動時リコンシリエーション
    - ...（他 execution 関連モジュール）
  - portfolio/
    - portfolio_builder.py    — 候補選定・重み計算
    - position_sizing.py      — 株数計算・単元丸め・キャップ処理
    - risk_adjustment.py      — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py     — momentum/volatility/value
    - feature_exploration.py — 将来リターン・IC・統計サマリー
    - __init__.py
  - ai/
    - news_nlp.py            — ニュースセンチメント周り（OpenAI）
    - regime_detector.py     — レジーム判定（MA + LLM）
    - __init__.py
  - utils/
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
    - __init__.py
  - research/, data/ 等（外部データ格納と連携）

（実際のプロジェクトではさらに細かいモジュール群や data/ のテーブル定義等が存在します）

## 開発・テストのヒント
- Settings は .env の自動読み込みロジックを持ちます。テスト時は環境変数でオーバーライドまたは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して挙動を制御してください。
- OpenAI 呼び出し部分は内部で小さくラップされているためユニットテストではモックしやすい設計です（例: unittest.mock.patch）。
- DuckDB / SQLite のクエリは SQL を直接書いているため、小規模データでの動作確認が容易です。

---

不明な点や README に追加したい内容（例: 各モジュールの詳細な API 仕様、requirements.txt の作成、運用 runbook など）があれば教えてください。必要に応じて追記・翻訳・テンプレート化します。