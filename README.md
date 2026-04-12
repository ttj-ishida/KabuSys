# KabuSys — README (日本語)

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。実行エンジン、監視・アラート、ポートフォリオ構築、リサーチ、AI を使ったニュース分析などを含みます。本 README はプロジェクト概要、主な機能、セットアップ手順、使い方、ディレクトリ構成を簡潔にまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネントをモジュール化したライブラリ群です。主な責務は以下です。

- Execution（ExecutionEngine）：シグナルから発注、リスク管理、発注ログ管理、再起動時のリコンシリエーション。
- Monitoring：システム稼働監視、注文滞留・約定異常検知、ドローダウン監視、Kill Switch（停止フラグ）と LINE アラート、監視ダッシュボード（Streamlit）。
- Portfolio：銘柄選定・重み計算・ポジションサイズの決定、セクター制約やレジーム乗数。
- Research：DuckDB を使ったファクター計算（Momentum／Value／Volatility）と特徴量探索（IC 等）。
- AI：OpenAI を利用したニュースのセンチメントスコアリング（ai/news_nlp）と市場レジーム判定（ai/regime_detector）。
- Tools：Paper Trading 検証レポート生成スクリプト等。

設計上のポイント：
- DuckDB / SQLite を用いてデータ永続化・分析を分離。
- .env / 環境変数ベースでの設定管理（自動読み込み機能あり）。
- Paper Trading 環境は本番 DB と分離される（デフォルトで data/paper_trading.db）。
- 外向き API 呼び出し（OpenAI / broker / LINE）は抽象化・フェイルセーフ実装。

---

## 機能一覧（抜粋）

- Execution
  - 起動エントリ: run_execution.py（KABUSYS_ENV に応じて本番 / paper_trading を切替）
  - Broker クライアントの抽象化・ファクトリ（MockBroker を含む）
  - Order 管理（OrderManager、OrderRepository、Reconciler）
  - RiskManager による発注制限

- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス liveness、データ鮮度監視
  - TradeMonitor：滞留注文・約定異常検知
  - RiskMonitor：ドローダウン・ポジション上限監視（Kill Switch と連携）
  - AlertManager：LINE Push による通知（クールダウン管理）
  - MonitoringEngine：上記を束ねたポーリングループ
  - Streamlit ダッシュボード（read-only で監視 DB を可視化）

- Portfolio / Position sizing
  - 銘柄候補選定、等重/スコア加重、リスクベース発注量計算
  - セクターキャップ、レジーム乗数

- Research
  - DuckDB を用いるファクター計算（momentum/volatility/value）
  - 将来リターン計算、IC、統計サマリー

- AI（OpenAI）
  - ニュースのセンチメントを銘柄単位でスコア化し ai_scores テーブルへ書込
  - マクロ記事を用いた市場レジーム判定と write to market_regime テーブル

- Tools
  - Paper Trading 検証レポート（paper_verification_report.py）

---

## セットアップ手順（ローカル実行向け）

※ 以下は最低限の手順例です。プロダクション環境では追加の運用手順が必要です。

1. Python（推奨: 3.10+）をインストール

2. 仮想環境を作成して有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール（例）
   - pip install duckdb psutil requests openai streamlit

   ※ requirements.txt はリポジトリに含まれていないため、実行に必要なライブラリを上記のように揃えてください。
   - duckdb: 分析用 DB
   - psutil: プロセス/リソース情報
   - requests: LINE API 呼び出し
   - openai: OpenAI API クライアント（ai モジュール利用時）
   - streamlit: ダッシュボード起動時

4. データディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに `.env` を置くと自動で読み込まれます（.env.local で上書き可能）。
   - 主要な環境変数例（必要に応じて設定）:

     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - KABU_API_BASE_URL=http://localhost:18080/kabusapi
     - OPENAI_API_KEY=...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - KABUSYS_ENV=development   # development | paper_trading | live
     - LOG_LEVEL=INFO
     - PAPER_FILL_MODE=instant  # instant | partial | never | reject
     - MONITOR_POLL_INTERVAL=60  # run_monitoring 用（秒）

   - 重要: 必須変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）は Settings クラスで require されます。実行コンポーネントに応じて設定してください。

---

## 使い方

以下は主要なエントリポイントと起動方法の例です。

1. 監視ループ（MonitoringEngine の簡易スクリプト）
   - 実行:
     - python -m kabusys.run_monitoring
   - 説明:
     - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可（デフォルト 60 秒）。
     - 監視用の SQLite（settings.sqlite_path）と DuckDB（settings.duckdb_path）を使用。monitoring DB の初期化は自動。

2. 実行エンジン（ExecutionEngine 起動）
   - 実行:
     - python -m kabusys.run_execution
   - 説明:
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db（または PAPER_TRADING_SQLITE_PATH）へ記録して本番 DB と分離。
     - 起動時にプロセス優先度を高に設定する試みを行います（プラットフォームによる）。

3. Paper Trading 検証レポート
   - 実行:
     - python -m kabusys.tools.paper_verification_report
     - または期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB 指定:
       - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

4. Streamlit 監視ダッシュボード（read-only）
   - 実行:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブで可視化します。

5. AI モジュール（ニューススコア・レジーム判定）
   - ニューススコア:
     - kabusys.ai.score_news(conn, target_date, api_key=None)  （DuckDB 接続を渡す）
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - 注意:
     - OPENAI_API_KEY が必要（api_key 引数で渡すことも可）。API 呼び出しはリトライやフェイルセーフを備えていますがコストに注意してください。

---

## 設定のポイント

- 自動 env ロード:
  - プロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に `.env` / `.env.local` をロードします。
  - OS 環境変数は優先されます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- KABUSYS_ENV:
  - 値: development, paper_trading, live
  - paper_trading にすると paper 用 DB を使い、ブローカーはモックを選択する想定。

- PAPER_FILL_MODE:
  - paper_trading 時の約定挙動: instant / partial / never / reject

- Kill Switch:
  - RiskMonitor がトリガー（ドローダウンやポジション上限）した場合、KillSwitch が data/kill.flag を書き込みます。
  - ExecutionEngine 起動時にこのフラグをクリアするオプション（KILL_FLAG_CLEAR_ON_START）があります。

---

## ディレクトリ構成（主要ファイルと役割）

以下はソースツリー（src/kabusys）内の主要ファイルと短い説明です。

- src/kabusys/
  - __init__.py                 — パッケージ初期化、バージョン
  - config.py                   — 環境変数 / Settings 管理（.env 自動ロード・検証）
  - run_monitoring.py           — SystemMonitor の単純ポーリングループ起動スクリプト
  - run_execution.py            — ExecutionEngine 起動スクリプト

- src/kabusys/execution/
  - order_manager.py            — 発注フロー（OrderManager）
  - reconciler.py               — 再起動時のリコンシリエーション
  - （その他: broker, order_repository 等：発注周りの実装）

- src/kabusys/monitoring/
  - monitoring_db.py            — SQLite 監視 DB スキーマ & DB ラッパー（MonitoringDB）
  - system_monitor.py           — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py            — 注文滞留・約定異常検知
  - risk_monitor.py             — ドローダウン・ポジション上限監視
  - kill_switch.py              — 停止フラグファイル操作
  - alert_manager.py            — LINE Push 通知（クールダウン管理）
  - monitoring_engine.py        — 各 Monitor を束ねるエンジン
  - streamlit_dashboard.py      — Streamlit ベースの監視 UI

- src/kabusys/portfolio/
  - portfolio_builder.py        — 候補選定・重み計算
  - position_sizing.py          — 株数計算・リスク制限
  - risk_adjustment.py          — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py          — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py      — 将来リターン / IC / 統計サマリー

- src/kabusys/ai/
  - news_nlp.py                 — ニュースを LLM でスコアリングし ai_scores へ書込み
  - regime_detector.py          — マクロニュース + ETF MA でレジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト

- src/kabusys/utils/
  - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 運用上の注意・ベストプラクティス

- 本番運用前に十分なテストを行ってください。特にブローカー API 周りは実トレードに直結します。
- OpenAI API の使用はコストが発生します。AI モジュールを定期実行する場合は注意してください。
- monitoring DB（SQLite）は単一ファイルのためバックアップやログローテートを検討してください。
- PID ファイル / kill.flag などのフラグはファイルベースで扱われます。オーケストレーション環境（systemd 等）に統合する場合は適切な調整が必要です。
- Paper Trading 環境（KABUSYS_ENV=paper_trading）は本番 DB と明確に分離されます。検証用途に活用してください。

---

この README はコードベースの主要点をまとめたものです。詳細な内部ロジックや API 仕様は各モジュール（ソースコード内の docstring）をご参照ください。必要であれば、さらに詳細なセットアップ手順（systemd unit、docker-compose、CI 設定例）や運用手順のテンプレートも作成できます。ご希望があれば教えてください。