# KabuSys

日本株向けの自動売買・リサーチ基盤ライブラリです。  
このリポジトリは、発注エンジン（ExecutionEngine）、監視コンポーネント（Monitoring）、研究用のファクター計算・特徴量解析、AI を用いたニュースセンチメント評価など、実運用を見据えた複数のモジュールで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の目的で設計されています。

- 自動発注の実行（実口座 / ペーパートレードの分離）
- システム稼働状況や注文状況、リスク指標の継続的監視
- ポートフォリオ構築（候補選定、重み付け、株数決定、セクター・レジーム調整）
- 研究用途のファクター計算・特徴量解析（DuckDB 経由）
- OpenAI を使ったニュース NLP（銘柄・マクロのセンチメント評価）
- 運用運用前の設定検証・対話式 .env 作成ウィザード

設計方針の一部：
- DuckDB / SQLite を利用したローカルデータベース中心
- 本番・ペーパートレードの DB 分離
- 外部 API 呼び出し箇所を限定（OpenAI などは明示的にキー指定）
- ルックアヘッドバイアス対策（date.today() 等を直接参照しない実装方針）

---

## 主な機能一覧

- Execution
  - ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - Broker クライアントファクトリ（paper_trading では MockBroker を利用）
  - 注文管理・リスク管理・オーダー照合などの実装（execution パッケージ）

- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - システム指標（CPU/メモリ/Disk）、プロセス死活、データ鮮度チェック
  - Kill Switch（条件を満たすと data/kill.flag を出力して ExecutionEngine を停止）
  - 監視ログを保持する SQLite 層（monitoring.monitoring_db）

- Research / Portfolio
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算・IC（Information Coefficient）評価
  - 銘柄選定・重み計算・ポジションサイズ決定ロジック（純粋関数群）

- AI
  - ニュース記事から銘柄別センチメントを OpenAI で算出し ai_scores に書き込み
  - 市場レジーム判定（ETF の MA200 とマクロニュースの LLM センチメントを合成）

- ツール / CLI
  - .env 対話式ウィザード（python -m kabusys.config_setup）
  - 設定検証 CLI（python -m kabusys.validate_config）
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt が無い場合、最低限以下をインストールしてください:
     - duckdb
     - psutil
     - openai
     - PyYAML（config.yml の検証に必要、任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

4. 環境変数設定 (.env)
   - 対話式で .env を作成する:
     - python -m kabusys.config_setup
   - あるいは .env.example を参照して .env を作成してください（リポジトリに例ファイルがある想定）。
   - 自動読み込み: config.py はプロジェクトルートの .env/.env.local を起動時に自動読み込みします（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告を厳密に扱う場合:
     - python -m kabusys.validate_config --strict

6. データディレクトリ（必要時）
   - デフォルトで使用されるディレクトリ:
     - data/ (SQLite、PID、フラグファイル等)
     - logs/（ログファイル）
   - 設定変数によりパスを上書きできます（下記参照）。

---

## 主要な環境変数（抜粋）

- 必須（運用時）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live
    - paper_trading: Execution は paper 用 DB（data/paper_trading.db）を使用
    - live: 本番挙動（注意喚起あり）

- データベース / ファイルパス
  - DUCKDB_PATH: デフォルト data/kabusys.duckdb
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
  - PID_FILE_PATH: execution.pid のパス（デフォルト data/execution.pid）
  - KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（"1" 有効。デフォルト "0"）

- ロギング
  - LOG_LEVEL: DEBUG / INFO / WARNING / ERROR / CRITICAL（デフォルト INFO）
  - LOG_DIR: ログ格納先（デフォルト logs/）

- モニタリング
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）

- Paper Trading / AI
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト instant）
  - OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: アラート通知（任意）

---

## 使い方（起動例）

- ExecutionEngine を起動（通常はサービスとして実行）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading を指定するとペーパートレード専用 DB を使用します。

- Monitoring を起動（常駐プロセス）
  - MONITOR_POLL_INTERVAL を指定（任意）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- .env の対話式設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポートの生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

- ライブラリとしての利用例（Python 内から）
  - DuckDB 接続を渡してファクター計算:
    - from kabusys.research import calc_momentum
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - recs = calc_momentum(conn, datetime.date(2026, 4, 1))

  - AI ニューススコアリング（OpenAI キー必須）:
    - from kabusys.ai import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, target_date, api_key="sk-...")

注意点:
- run_monitoring は MONITORING 用の sqlite_path（Settings.sqlite_path）を環境に関わらず使用します（コードの設計上の仕様）。
- run_execution は KABUSYS_ENV=paper_trading の場合、paper_trading 用 SQLite を使います（本番 DB と分離）。
- 停止フラグファイル:
  - data/stop_requested.flag を作成すると run_monitoring / run_execution のループを終了させます（実行スクリプトはこのフラグの存在をポーリングして終了処理を行います）。
  - Kill Switch は data/kill.flag を書き込み、ExecutionEngine の安全停止を促します。

---

## ディレクトリ構成（主要ファイル）

- src/kabusys/
  - __init__.py
  - config.py                          — 環境変数 / Settings 管理
  - config_setup.py                    — .env 対話式ウィザード CLI
  - validate_config.py                 — 設定検証 CLI
  - run_execution.py                   — ExecutionEngine 起動スクリプト
  - run_monitoring.py                  — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py     — ペーパー検証レポート生成
  - ai/
    - news_nlp.py                      — ニュース NLP スコアリング
    - regime_detector.py               — 市場レジーム判定（LLM + MA200）
  - monitoring/
    - monitoring_db.py                 — SQLite 永続化層（監視用）
    - monitoring_engine.py             — 各 Monitor を束ねる
    - system_monitor.py                — システム状態 / データ鮮度監視
    - trade_monitor.py                  (注: 実装ファイルが存在する想定)
    - risk_monitor.py                  — ドローダウン / ポジション上限監視
    - kill_switch.py                    — Kill Switch 実装
    - alert_manager.py                  (注: 実装ファイルが存在する想定)
  - execution/
    - execution_engine.py              — ExecutionEngine（起動/セッション管理）
    - order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py
  - portfolio/
    - portfolio_builder.py             — 候補選定・重み計算
    - position_sizing.py               — 株数決定・資金配分
    - risk_adjustment.py               — セクター上限 / レジーム乗数
  - research/
    - factor_research.py               — Momentum/Value/Volatility 計算
    - feature_exploration.py           — 将来リターン・IC・統計サマリー
  - data/                               — 実行時に使用する DB / PID / フラグ（デフォルトパス）
  - logs/                               — ログ出力先（設定で変更可）
  - config/                             — YAML 設定群（system_config.yaml など、存在が期待される）

注: 一部モジュールはここで抜粋して掲載しており、実装ファイルはリポジトリ内に揃っている想定です。

---

## 運用上の注意

- 本番（KABUSYS_ENV=live）では必ず設定を慎重に確認し、LINE 等の通知設定を整備してください。
- KILL_FLAG_CLEAR_ON_START は本番で 1 にするのは危険です（kill flag が自動でクリアされてしまうため）。デフォルトは 0 を強く推奨します。
- OpenAI を利用する処理（news_nlp / regime_detector）は API 呼び出し回数に依存します。料金・レート制限に注意してください。リトライやバックオフは実装されていますが、運用設定で制御してください。
- ロギングは stdout と logs/<app_name>.log（日次ローテーション）に出力されます。ログディレクトリの作成失敗時はコンソールのみで動作します。

---

## テスト・開発時のヒント

- 自動環境ロードは config.py により .env/.env.local をプロジェクトルートから読み込みます。テストで自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- AI 呼び出し部分は個別のラッパー関数（_call_openai_api 等）を patch することでユニットテストが容易です。score_news や score_regime は api_key を引数で渡せます。
- DuckDB を利用した研究関数は副作用を持たない純粋関数として設計されているので、テスト用に小さな DuckDB ファイルを用意して検証できます。

---

もし README に追加してほしい内容（例: サービス化手順 systemd ユニット例、Dockerfile、詳細な設定項目の説明、API モックの実装例など）があれば教えてください。必要に応じて追記します。