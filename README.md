# KabuSys

日本株自動売買システムの一部（ライブラリ＋運用ツール群）。  
このリポジトリは、シグナル→ポートフォリオ構築→発注・リスク管理・監視・レポート生成・研究用ファクター計算・AIベースのニュースセンチメント評価などを含むモジュール群を提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株向けの自動売買（Execution）と運用監視（Monitoring）、研究（Research）とAI補助（News NLP / Regime Detector）を含むモジュール化されたソフトウェアです。本リポジトリは以下のような責務を持つコンポーネントで構成されています。

- Execution: ブローカーとの接続・発注・注文管理・リコンシリエーション
- Monitoring: システム状態・注文状況・リスク監視・アラート（LINE）・ダッシュボード
- Portfolio: 候補選定、重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- Research: ファクター計算（Momentum / Volatility / Value）・特徴探索用ユーティリティ
- AI: ニュースのセンチメントスコアリング（OpenAI）・市場レジーム判定
- Tools: Paper Trading 向けの検証レポート生成スクリプトなど

設計方針としては、外部副作用を最小限にし、DuckDB/SQLite を用いたデータ参照・永続化、OpenAI 連携は明示的に API キーを渡すか環境変数を利用する、といった点が挙げられます。

---

## 主な機能一覧

- Execution
  - ExecutionEngine の起動 (run_execution.py)
  - Broker クライアントの切替（本番 / paper_trading の Mock）
  - OrderManager、RiskManager、Reconciler による発注・リスク管理・再同期

- Monitoring
  - SystemMonitor: CPU / メモリ / ディスク / データ鮮度 / 実行プロセス監視
  - TradeMonitor: 注文滞留（stale orders）・約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限の監視とログ保存
  - KillSwitch: 条件に応じた停止フラグ（data/kill.flag）生成
  - AlertManager: LINE へのプッシュ通知（cooldown 管理）
  - Streamlit ダッシュボード（監視データ可視化）
  - 監視ループ起動スクリプト (run_monitoring.py)

- Portfolio
  - 候補選定（スコア降順）
  - 等金額・スコア加重の重み付け
  - リスクベース・等配分のポジションサイズ決定（単元株丸め・aggregate cap）
  - セクター上限適用・レジーム乗数

- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB 接続を受け取る）
  - 将来リターン計算・IC（Information Coefficient）計算・統計サマリー

- AI
  - ニュース記事を OpenAI に送り銘柄別センチメントスコアを ai_scores に保存（news_nlp）
  - ETF + マクロニュースを用いた市場レジーム判定（regime_detector）

- Tools
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

---

## セットアップ手順

※ 以下は開発環境 / ローカル実行向けの簡易手順です。

1. Python 環境
   - Python 3.9+ を推奨（コードは型ヒントで 3.10 以上が好ましい箇所あり）
   - 仮想環境を作成・有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージ（例）
   - pip install duckdb psutil requests openai streamlit
   - 実際のプロジェクトでは requirements.txt を用意して管理してください。

3. 環境変数 / .env
   - ルートに .env / .env.local を置くと自動で読み込まれます（Settings モジュールが自動読み込み）
   - 自動読み込みを無効にする場合: export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 必要な主要環境変数（代表的なもの）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
     - OPENAI_API_KEY (AI 機能を使う場合)
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG/INFO/...)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE (instant|partial|never|reject)
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（LINE 通知）
   - .env.example を参考に .env を作成してください（リポジトリに例が無ければ必要なキーを上記参考に作成）。

4. data ディレクトリ
   - デフォルトで DB やフラグファイルを data/ 以下に置きます。実行前に data/ を作成しておくか、実行時に自動作成されます。

---

## 使い方

### 監視ループを起動する（Monitoring）
- 簡単実行:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 動作:
  - 監視は Settings.env に関わらず本番 sqlite_path を使用して監視データを永続化します。
  - 停止はプロジェクトルートの data/stop_requested.flag の作成で検出します（停止フラグ）。

### Execution（発注エンジン）を起動する
- 例:
  - KABUSYS_ENV=development python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 挙動:
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、paper_trading 用 DB（data/paper_trading.db）へ動作ログを書きます。本番 DB と完全に分離されます。
  - 実行中に data/stop_requested.flag を作成するとエンジンは停止を受け付けます。
  - 実行は execution.pid（デフォルト data/execution.pid）を生成します。

### Streamlit ダッシュボード（監視用）
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 説明:
  - 監視 DB を read-only で開き、Overview / Positions / Orders / System タブを表示します。

### Paper Trading 検証レポート
- レポート生成:
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db PATH（PAPER_TRADING_SQLITE_PATH 環境変数が優先されます）
- 機能:
  - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数などを集計し PASS/FAIL を判定します。

### AI 機能（ニュース NLP / レジーム判定）
- ニューススコアリング:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - OpenAI API キーを api_key 引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。
- レジーム判定:
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - これらは DuckDB 接続を受け取り、raw_news / prices_daily 等のテーブルを参照します。
  - API 失敗時のフォールバックやリトライロジックが組み込まれていますが、API キー未設定では例外が発生します。

---

## 重要な動作・設定メモ

- .env の自動読み込み:
  - package 内の Settings 実装はプロジェクトルート（.git または pyproject.toml を基準）を探索し、.env/.env.local を自動で読み込みます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- MONITOR のポーリング間隔:
  - MONITOR_POLL_INTERVAL（秒）により監視ループの間隔を上書き可能。0 や負数は無効でデフォルトにフォールバックします。
- paper_trading モード:
  - KABUSYS_ENV=paper_trading を設定すると、MockBroker を使い paper_trading 用 SQLite に書き込むため本番 DB への影響なしにテストできます。
- 停止 / キルフラグ:
  - 実行停止には data/stop_requested.flag（run scripts 用）や data/kill.flag（KillSwitch による ExecutionEngine 停止要求）を使用します。KillSwitch はリスク条件（ドローダウン／ポジション上限）に応じて data/kill.flag を書き込みます。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys/ 以下の主要モジュール一覧（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動読み込み）
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト

  - execution/
    - execution_engine.py         — エンジン本体（起動・セッション管理）
    - broker_factory.py
    - broker_api.py
    - order_manager.py            — Order の作成 / 管理
    - order_repository.py
    - reconciler.py               — 起動時の再同期・照合
    - risk_manager.py
    - order_record.py

  - monitoring/
    - monitoring_db.py            — SQLite 永続化（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py      — Streamlit ダッシュボード

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py

  - research/
    - factor_research.py
    - feature_exploration.py

  - ai/
    - news_nlp.py                 — ニュース → OpenAI → ai_scores 書込み
    - regime_detector.py          — ETF + マクロニュースでレジーム判定

  - tools/
    - paper_verification_report.py

  - utils/
    - process_priority.py         — プロセス優先度 / CPU affinity 設定ユーティリティ

---

## 開発・運用上の注意

- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等にテーブル作成・簡易マイグレーション（カラム追加）を行います。
- ログ:
  - ほとんどのスクリプトは logging.basicConfig(level=logging.INFO) を使用します。詳細ログを得るには LOG_LEVEL=DEBUG を設定してください。
- 外部 API 呼び出し:
  - OpenAI など外部 API を使うコードはリトライ・バックオフやフェイルセーフ（API失敗時にゼロやスキップする）を実装していますが、本番運用では API キー・レート制限に注意してください。
- 単体テスト:
  - OpenAI 呼び出し等はテストのためモックしやすい設計（関数化・依存注入）になっています。テスト実行時は .env 自動ロードを無効にするかテスト用キーを用意してください。

---

もし README に追記したい実行例（具体的なコマンド）や、環境変数の完全な一覧、あるいは運用手順（systemd などへの登録例）が必要であれば、用途に合わせて補足を作成します。