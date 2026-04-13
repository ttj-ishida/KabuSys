# KabuSys

KabuSys は日本株の自動売買・リサーチ・監視を目的とした Python パッケージ群です。本リポジトリは主に以下の領域を実装しています。

- 注文実行エンジン (Execution)
- 監視（System / Trade / Risk）とアラート
- ポートフォリオ構築ロジック（銘柄選定・配分・ポジションサイズ計算）
- リサーチ（ファクター計算・特徴量探索）
- AI ベースのニュース NLP（OpenAI を利用したセンチメント評価）
- Paper Trading 向け検証ツール・レポート生成

この README ではプロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成をまとめます。

---

## プロジェクト概要

KabuSys は取引ロジック（戦略）と実行・監視インフラを分離して設計されています。DuckDB を用いた時系列データ処理、SQLite による監視・取引ログ永続化、外部ブローカー API との連携を考慮した実装が含まれます。OpenAI API を用いたニュースセンチメント評価や、市場レジーム判定ロジックも備えています。

設計上の特徴：
- テストしやすい純粋関数群（portfolio、research 等）
- DB マイグレーションを含む簡易永続化レイヤ（monitoring_db）
- Paper Trading と本番（live）を分離できる設定
- 監視ループはプロセス優先度設定や kill flag に対応

---

## 機能一覧

主な機能（抜粋）:

- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアントの抽象化とファクトリ
  - OrderManager / Reconciler による注文管理と再同期
  - RiskManager によるリスク制御（最大ポジション比率、利用率、ドローダウン等）

- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク・プロセス・データ鮮度チェック
  - TradeMonitor: 注文滞留・約定価格異常チェック
  - RiskMonitor: ドローダウン/ポジション上限の監視・kill flag 発動
  - AlertManager: LINE Push による通知（cooldown 管理）
  - MonitoringEngine: これらを束ねるポーリングエンジン
  - Streamlit ベースの監視ダッシュボード

- Portfolio（ポートフォリオ構築）
  - 候補選定（select_candidates）
  - 等配分・スコア配分（calc_equal_weights / calc_score_weights）
  - セクター制限・レジーム乗数（apply_sector_cap / calc_regime_multiplier）
  - ポジションサイズ計算（calc_position_sizes）

- Research（リサーチ）
  - Momentum / Volatility / Value のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI
  - news_nlp.score_news: raw_news を集約して OpenAI でセンチメントを算出し ai_scores テーブルへ書込
  - regime_detector.score_regime: ETF MA とマクロニュースの LLM センチメントを併せて日次レジーム判定

- Tools
  - paper_verification_report: Paper Trading DB から稼働率・成功率・レイテンシ等の検証レポートを生成

---

## セットアップ手順

前提: Python 3.10+ を推奨（typing の union やその他仕様に依存）

1. リポジトリをクローン / ソースを取得
2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール
   ここではソース内で利用されている主要ライブラリを示します。requirements.txt がない場合は手動でインストールしてください。
   - pip install duckdb psutil requests openai streamlit

   実際のプロジェクトでは追加パッケージ（pandas 等）が必要になる場合があります。目的に応じて追加してください。

4. データディレクトリ作成（デフォルトの DB パス）
   - mkdir -p data

5. 環境変数設定
   プロジェクトは .env / .env.local を自動ロードします（プロジェクトルートが検出できる場合）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主要な環境変数（例）:
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...
   - KABUSYS_ENV=development|paper_trading|live  (デフォルト: development)
   - PAPER_FILL_MODE=instant|partial|never|reject (Paper Trading の約定モード)
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - SQLITE_PATH=data/monitoring.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - LINE_CHANNEL_ACCESS_TOKEN=...
   - LINE_USER_ID=...
   - PID_FILE_PATH=data/execution.pid
   - KILL_FLAG_PATH=data/kill.flag

6. DB 初期化
   - run_monitoring あるいは run_execution を起動すると、monitoring 用の SQLite テーブルが自動作成されます（init_monitoring_db）。

注意:
- process priority の設定は OS に依存し、権限が必要な場合があります（psutil による nice / priority 設定）。権限不足時は警告が出てスキップされます。
- OpenAI API を使う機能は API キーが必要です。キー未設定時は明示的な例外またはフェイルセーフ処理が行われます。

---

## 使い方

以下は代表的な実行例です。

1) 監視ループの起動（Monitoring）
- デフォルトは monitoring.db（data/monitoring.db）を使用し、MONITOR_POLL_INTERVAL によりポーリング間隔を秒単位で上書きできます（デフォルト 60 秒）。

実行:
- python -m kabusys.run_monitoring

または環境変数で間隔を変更:
- export MONITOR_POLL_INTERVAL=30
- python -m kabusys.run_monitoring

挙動:
- プロセス優先度を high に設定（可能な場合）
- SQLite / DuckDB に接続し SystemMonitor のポーリングを継続

2) 実行エンジンの起動（Execution）
- KABUSYS_ENV が paper_trading の場合は MockBrokerClient を利用し、Paper Trading 用 DB（デフォルト data/paper_trading.db）を使用します。

実行:
- python -m kabusys.run_execution

3) Streamlit 監視ダッシュボード
- 監視 DB を read-only モードで開いて簡易ダッシュボードを表示します。

実行:
- streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

（備考）--db 引数で DB パスを指定できます。

4) Paper Trading 検証レポート
- 保存された paper_trading DB から検証レポートを生成します。

実行例:
- python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- または DB を指定: python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db

出力:
- 稼働率、注文成功率、送信率、P95 レイテンシ等を標準出力へ表示し PASS/FAIL 判定を行います。

5) AI モジュールの利用例（Python から）
- news_nlp.score_news や regime_detector.score_regime は DuckDB 接続と target_date を受け取る関数です。OpenAI API キーを引数で渡すか環境変数 OPENAI_API_KEY を利用します。

簡単な利用例（擬似コード）:
- import duckdb
- from kabusys.ai.news_nlp import score_news
- conn = duckdb.connect("data/kabusys.duckdb")
- n_written = score_news(conn, target_date=date(2026,4,1), api_key="sk-...")

注意:
- API 呼び出しはリトライ・フェイルセーフの実装がありますが、ネットワークや課金に注意してください。
- news_nlp は raw_news / news_symbols / ai_scores テーブルを前提とします。

6) 設定（Settings）
- 設定は環境変数または .env ファイルから読み込まれます。自動ロードはプロジェクトルート（.git または pyproject.toml）を基準に行われます。自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV は development / paper_trading / live のいずれかで、挙動（DB パスや Broker クライアント）が切り替わります。

---

## 重要な環境変数（まとめ）

- KABUSYS_ENV: development | paper_trading | live (default: development)
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- SQLITE_PATH: 監視用 SQLite（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（default: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- PID_FILE_PATH: 実行エンジン PID ファイル（default: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（default: data/kill.flag）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定振る舞い）
- OPENAI_API_KEY: OpenAI API キー（AI モジュールで使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE）に必要

---

## ディレクトリ構成

主要なファイル・パッケージ（src/kabusys 配下）:

- run_monitoring.py
- run_execution.py
- config.py                  — 環境変数 / Settings の管理（.env 自動ロード）
- __init__.py

- ai/
  - news_nlp.py              — ニュースを LLM でスコアリングして ai_scores に書き込む
  - regime_detector.py       — MA とマクロニュースを併合して市場レジームを判定
  - __init__.py

- monitoring/
  - monitoring_db.py         — SQLite スキーマ初期化・永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
  - streamlit_dashboard.py
  - __init__.py

- execution/
  - order_manager.py
  - reconciler.py
  - （他: broker_factory 等のモジュールを含む想定）
  - （注）execution パッケージにはブローカー API 抽象化・OrderRepository 等が含まれます

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

- utils/
  - process_priority.py      — psutil を使った優先度 / CPU affinity 設定
  - __init__.py

- data/                      — デフォルトの DB やログ等を置く想定ディレクトリ（gitignore 推奨）

---

## 運用上の注意・補足

- DB のスキーマは init_monitoring_db() で冪等的に作成・簡易マイグレーションされます。既存 DB を扱う際はバックアップを推奨します。
- Paper Trading と本番 DB は分離されるよう Settings によりパスが切り替わります（KABUSYS_ENV=paper_trading の場合は paper_sqlite_path を使用）。
- プロセス優先度（高）を設定しますが、OS・権限によっては設定できず警告が出力されます。
- kill.flag を利用して外部から ExecutionEngine に停止シグナルを送れます（KillSwitch）。ExecutionEngine 側で kill.flag の存在チェックを行う設計になっています。
- AI モジュールは外部 API を呼ぶため、コスト・レート制限に注意してください。429 等は指数バックオフでリトライします。

---

この README はコードベースの主要部分をまとめた簡易ガイドです。各モジュールには詳細ドキュメント（docstring）と設計メモが含まれていますので、実装や拡張の際は個別モジュールの docstring を参照してください。必要であればインストール用の requirements.txt、例示的な .env.example、起動用 systemd/pm2 サービス定義のサンプルなどを別途作成できます。