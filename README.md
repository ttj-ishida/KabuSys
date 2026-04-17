# KabuSys

日本株自動売買システムのパッケージ（ドキュメント用抜粋）。本 README はソースツリー内の主要スクリプト・モジュールに基づく概要、セットアップ、使い方、ディレクトリ構成を日本語でまとめたものです。

注意：このリポジトリは複数の実行モード（development / paper_trading / live）や外部 API（kabuステーション、J-Quants、OpenAI など）に依存します。実運用前に必ず設定と権限を確認してください。

## プロジェクト概要

KabuSys は日本株の自動売買、監視、検証、リサーチ機能を備えた Python ベースのシステムです。主な役割は以下の通りです。

- ExecutionEngine：発注・注文管理・リスク管理・注文の再同期（リコンシリエーション）
- Monitoring：システムリソース・データ鮮度・注文状態・リスクを定期監視し、アラートや停止フラグを発行
- Portfolio：銘柄選定・配分・ポジションサイズ計算などのポートフォリオ構築ロジック（純粋関数）
- Research：DuckDB 上の株価・財務データを使ったファクター計算・特徴量解析
- AI モジュール：OpenAI を利用したニュースセンチメント評価・市場レジーム判定
- Tools：Paper Trading の検証レポート生成等のユーティリティスクリプト
- Streamlit ダッシュボード：監視データの可視化 UI

## 主な機能一覧

- システム監視（CPU / メモリ / ディスク / プロセス PID チェック）
- 注文滞留検出・約定価格異常検出
- ドローダウン検出・ポジション上限監視と kill フラグ発行
- LINE 通知（AlertManager）によるアラート送信（トークン未設定時はログのみ）
- ExecutionEngine の起動/停止・PID ファイル管理・再起動時のリコンシリエーション
- Paper Trading モード（本番 DB と分離された専用 SQLite に記録）
- DuckDB を使ったリサーチ（モメンタム、ボラティリティ、バリュー等）
- OpenAI を使ったニュース NLP（銘柄別センチメント）とレジーム判定
- Streamlit ダッシュボードによる監視データ閲覧
- テスト/ツール：Paper Trading 検証レポート生成スクリプト

## セットアップ手順（開発用）

1. リポジトリをクローン / 作業ディレクトリへ移動

2. Python 仮想環境を作成・有効化（例）
   - Unix/macOS:
     - python -m venv .venv
     - source .venv/bin/activate
   - Windows (PowerShell):
     - python -m venv .venv
     - .\.venv\Scripts\Activate.ps1

3. 必要パッケージをインストール
   - 最低限必要になる外部ライブラリ（ソースの import を参照）:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   （本リポジトリに requirements.txt が無い場合は、実行環境に合わせて追加してください。）

4. データディレクトリの作成（デフォルト）
   - mkdir -p data

5. 環境変数設定
   - プロジェクトルートに `.env`（または `.env.local`）を置くと自動ロードされます（既存の OS 環境変数は上書きされません。`.env.local` は上書き）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_FILL_MODE=instant|partial|never|reject
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - MONITOR_POLL_INTERVAL=60

   - `.env` の書式は bash の export/KEY=val 等に対応します。`Settings` モジュールが読み込みとバリデーションを行います。

## 使い方（実行例）

基本的にはパッケージ内のスクリプトを Python モジュールとして実行します。

- 監視（Monitoring）プロセス起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - python -m kabusys.run_monitoring
  - 実行はプロセス優先度を "high" に設定する試みを行います（プラットフォーム依存で失敗することがあります）。
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（KABUSYS_ENV に依存しません）。
  - 停止: プロジェクトルートの data/stop_requested.flag を作成するとポーリングループが終了します。

- ExecutionEngine 起動（取引エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient が使用され、paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。
  - 実行中は data/execution.pid ファイルが使われます。stop/kill 用フラグ（data/stop_requested.flag / data/kill.flag）で外部から停止できます。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 既存の monitoring.db を読み取り専用で開きます。MonitoringEngine を先に起動してデータを作成してください。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプションで日付レンジを指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを直接指定できます（デフォルト: data/paper_trading.db または env の PAPER_TRADING_SQLITE_PATH）。

- AI モジュール（OpenAI）
  - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)
  - OpenAI API キー（環境変数 OPENAI_API_KEY または引数）を必ず指定してください。API 呼び出しはリトライやフェイルセーフを備えていますが、キーの未設定は例外になります。

## 停止 / kill シグナル・ファイル

- デーモン的スクリプト（run_monitoring / run_execution）はプロジェクトルートの data/stop_requested.flag を見ることで自身を安全に停止します。
- KillSwitch は data/kill.flag（Settings.kill_flag_path、デフォルト）を書き込むことで ExecutionEngine に対して停止シグナルを送ります（原因をファイルに書き込みます）。
- ExecutionEngine は data/execution.pid を PID 管理に使用します。

## 重要な設定とデフォルト

- KABUSYS_ENV: 実行環境を表す（development / paper_trading / live）。Settings.env がバリデーションを行います。
  - is_paper（paper_trading のとき True）や is_live などでコードの分岐があります。
- PAPER_FILL_MODE: paper_trading のモック約定方式（instant|partial|never|reject）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60 秒）
- DB パス:
  - sqlite_path: data/monitoring.db（Monitoring 用）
  - paper_sqlite_path: data/paper_trading.db（Paper Trading 専用）
  - duckdb_path: data/kabusys.duckdb（リサーチ・タイムシリーズの格納）
- ログレベル: LOG_LEVEL（DEBUG/INFO/...）

## ディレクトリ構成（主要ファイル）

以下はソースツリーの主要モジュールと役割の概観（抜粋）：

- src/kabusys/
  - __init__.py — パッケージ情報
  - config.py — 環境変数・設定ロード（.env 自動読み込み、Settings クラス）
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite 監視 DB 層（init / MonitoringDB）
    - system_monitor.py — システム状態・データ鮮度監視
    - trade_monitor.py — 注文滞留・約定異常監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE への通知（push）
    - monitoring_engine.py — 各モニタを束ねるランナー
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py — 発注の外向き API（OrderManager）
    - reconciler.py — 起動時の自動復旧・リコンシリエーション
    - （その他、broker_factory や execution_engine 等は実装ファイルが存在する前提）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 数量決定・リスク制限
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン計算・IC 等
    - __init__.py
  - ai/
    - news_nlp.py — raw_news を OpenAI でスコアリングして ai_scores に書き込む
    - regime_detector.py — ETF MA と LLM マクロセンチメントから市場レジーム判定
    - __init__.py
  - utils/
    - process_priority.py — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

（上記は抜粋です。実際のリポジトリには execution のほか多数のモジュールが含まれます。）

## 注意点 / ベストプラクティス

- データベースの分離
  - Paper Trading（検証）時は本番 DB と完全に分離することを推奨（Settings.is_paper を利用）。
- 環境変数の管理
  - 機密値（API トークン等）は .env を使う場合でも適切に管理してください。`.env.example` を作成して必要なキーをドキュメント化すると良いです。
- OpenAI API
  - API キーは環境変数 OPENAI_API_KEY に設定するか、該当関数に明示的に渡してください。
  - API 呼び出しはリトライやバックオフを実装していますが、コストやレート制限に注意してください。
- 権限・優先度設定
  - set_process_priority は OS と権限に依存します。権限不足や未対応プラットフォームでは警告を出してスキップします。
- フェイルセーフ
  - AI 呼び出し失敗時や DB の不足データはフェイルセーフ（スコア 0.0、スキップ、ログ出力など）で継続する設計を採っていますが、重要な運用判断は人がレビューしてください。

## 追加情報 / 参照

- Settings・.env パーシングは `src/kabusys/config.py` を参照してください。自動読み込みはプロジェクトルート（.git または pyproject.toml を基準）を探索します。
- 監視 DB のスキーマ初期化・マイグレーションは `monitoring_db.init_monitoring_db()` を参照してください。
- Streamlit ダッシュボードは監視 DB を read-only で開くため、MonitoringEngine を起動してデータを生成してから見ると良いです。

---

この README はソースコードのコメントや docstring に基づいて作成しています。より詳しい仕様書や運用手順（例: broker の設定、J-Quants API の利用方法、実運用での監視ルール等）は別途作成することを推奨します。必要であればサンプル .env.example や systemd / Supervisor 用のユニットファイルのテンプレートも作成できます。希望があれば教えてください。