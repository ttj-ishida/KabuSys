# KabuSys — README

本リポジトリは日本株向け自動売買システム「KabuSys」の一部実装です。本 README はコードベース（src/kabusys 以下）の使い方、セットアップ、主要コンポーネントの説明を日本語でまとめたものです。

注意: 実行には外部 API キーや DB ファイルなどが必要です。また本 README はソース内のドキュメンテーションを元に作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する以下の機能群を持つコンポーネント群です。

- 注文の生成・管理・ブローカー送信（Execution）
- 監視・アラート・Kill Switch（Monitoring）
- ポートフォリオ構築・ポジションサイジング（Portfolio）
- ファクター計算・リサーチ（Research）
- ニュースの NLP によるセンチメント評価・レジーム判定（AI）
- 運用検証用ツール（Paper Trading レポート等）
- 実行時・環境設定の抽象化（Config / Utils）

設計上のポイント:
- DuckDB / SQLite を使って履歴・ファクター・監視データを永続化
- Paper Trading（疑似実行）時は本番 DB と分離して `data/paper_trading.db` を使用
- OpenAI API を用いたニュースセンチメントやレジーム判定をサポート（API キー必須）
- プロセス優先度・CPU affinity 設定ユーティリティを提供（psutil 利用）
- streamlit による監視ダッシュボードを提供

---

## 主な機能一覧

- Execution
  - OrderManager / ExecutionEngine / Broker クライアント（本番 or モック）
  - 再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）

- Monitoring
  - SystemMonitor（CPU/Memory/Disk/プロセス生存/データ鮮度）
  - TradeMonitor（滞留注文 / 約定異常）
  - RiskMonitor（ドローダウン / ポジション上限の検出）
  - KillSwitch（条件に応じて flag ファイルを書き Execution を停止）
  - AlertManager（LINE Push による通知）
  - streamlit ダッシュボード

- Portfolio
  - 候補選定（select_candidates）
  - 重み計算（等分配 / スコア加重）
  - セクター上限適用（apply_sector_cap）
  - ポジションサイズ計算（calc_position_sizes）

- Research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC 計測、統計サマリー

- AI
  - ニュース記事の LLM によるセンチメントスコアリング（news_nlp.score_news）
  - 市場レジーム判定（regime_detector.score_regime）

- Tools
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## セットアップ手順（開発 / ローカル）

1. Python 環境を用意
   - 推奨: Python 3.10+（duckdb, psutil, openai 等に合わせる）

2. 仮想環境の作成と有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 本リポジトリに requirements.txt がない場合は主要依存をインストールしてください:
     - pip install duckdb psutil requests openai streamlit
   - 実運用ではさらに他パッケージやバージョン固定が必要になる可能性があります。

4. 環境変数（.env）の準備
   - プロジェクトルートに `.env` / `.env.local` を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主な環境変数（最低限必要なもの）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
     - KABU_API_PASSWORD — kabuステーション API（必須）
     - OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合必須）
   - 任意 / デフォルト:
     - KABUSYS_ENV — 起動環境（development / paper_trading / live）, デフォルト: development
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PID_FILE_PATH / KILL_FLAG_PATH 等多数（config.Settings を参照）

5. データディレクトリ作成
   - mkdir -p data

---

## 使い方

以下は主要な実行例です。パッケージとして実行する前提（src が PYTHONPATH にある / pip install -e . のいずれか）で説明します。

1. ExecutionEngine を起動（本番または Paper Trading）
   - Paper Trading モード:
     - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient として動作し、DB は `data/paper_trading.db` を使用して本番 DB と分離されます。
     - 実行方法:
       - python -m kabusys.run_execution
     - 事前に OPENAI_API_KEY や KABU_API_PASSWORD などが不要な場合もありますが、設定に応じて必要。
   - Live / Development:
     - KABUSYS_ENV=live などを設定して実行。

2. Monitoring を起動（ポーリング監視）
   - python -m kabusys.run_monitoring
   - 環境変数:
     - MONITOR_POLL_INTERVAL — ポーリング間隔（秒）。デフォルト 60 秒。1 以上の整数で指定。無効値は 60 にフォールバック。
   - 監視は常に production（settings.env にかかわらず）で指定された sqlite_path を使用して監視ログを書き込みます（monitoring の DB は本番を参照する仕様）。

3. Streamlit ダッシュボード
   - 起動:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 既存の監視 DB を読み取り専用で開き、ポートフォリオ / 注文 / システム状況を表示します。

4. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション:
     - --db PATH — PAPER_TRADING_SQLITE_PATH を明示的に上書き可能（指定がない場合は環境変数または data/paper_trading.db）

5. AI 機能（ニューススコア / レジーム判定）
   - OpenAI API キーが必須（環境変数 OPENAI_API_KEY または関数呼び出し時に引数で渡す）。
   - 例（モジュール経由の呼び出し）:
     - from kabusys.ai import score_news
     - score_news(conn, target_date, api_key=os.environ["OPENAI_API_KEY"])

注意点:
- 実行前に SQLite / DuckDB ファイルへの書き込み権限が必要です。
- run_monitoring は監視用 SQLite を常に production (settings.sqlite_path) で使用します。Paper Trading とは分離しているため、監視 DB を共有しない点に注意してください。
- Kill Switch は設定された `KILL_FLAG_PATH`（デフォルト data/kill.flag）にテキストを書込むことで ExecutionEngine 停止の合図を送ります。ExecutionEngine 側でこのフラグを検出して停止する仕組みが必要です。

---

## 主要な設定項目（概要）

設定は環境変数経由で行います。Settings クラス（kabusys.config）で参照・検証されます。主な項目:

- KABUSYS_ENV: 起動環境（development, paper_trading, live）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時に必須）
- DUCKDB_PATH: duckdb の DB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 sqlite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 sqlite（デフォルト data/paper_trading.db）
- PID_FILE_PATH: ExecutionEngine の PID を書くパス（デフォルト data/execution.pid）
- KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START: Kill Flag 関連
- PAPER_FILL_MODE: Paper Trading の約定動作（instant|partial|never|reject）
- CPU / MEMORY / DISK の閾値（監視用）

設定値の妥当性検証は Settings クラスが行います（不正値は ValueError を送出）。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 配下の主要ファイル・モジュールと概略です。

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env ロード / Settings
  - run_monitoring.py — SystemMonitor のポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 時は MockBroker を使用）
  - utils/
    - __init__.py
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite テーブルの初期化・読み書きラッパー
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 滞留注文 / 約定異常検出
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag 書込による停止シグナル
    - alert_manager.py — LINE プッシュ通知
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — streamlit ダッシュボード
  - execution/
    - order_manager.py — 注文ステートマシン外向き API
    - reconciler.py — 起動時の注文/ポジションリコンシリエーション
    - order_repository.py, order_record.py, broker_factory.py, broker_api.py など（省略）
  - portfolio/
    - __init__.py
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数計算 / 単元丸め / キャップ調整
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - __init__.py
    - factor_research.py — momentum/volatility/value 等の計算（DuckDB 使用）
    - feature_exploration.py — 将来リターン計算 / IC / 統計サマリ
  - ai/
    - __init__.py
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に書込
    - regime_detector.py — マクロニュース + ETF ma200 で市場レジーム判定
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading の検証レポート生成

（実装の詳細は各ファイルのドキュメンテーション文字列を参照してください）

---

## 運用上の注意 / ベストプラクティス

- Paper Trading と Monitoring DB は用途別に分離されています。Paper Trading の実行ログは data/paper_trading.db に書かれるため production の監視 DB と混ざりません。
- run_monitoring は常に監視用 sqlite_path（settings.sqlite_path）を使用するため、環境に応じた設定を忘れずに。
- MONITOR_POLL_INTERVAL は環境変数で上書き可能（秒単位、1 以上）。不正値はログを出してデフォルト（60秒）にフォールバックします。
- OpenAI を使った処理は API 呼び出しに失敗してもフェイルセーフに設計されており、「失敗時はスキップ／0.0 フォールバック」等の動作になりますが、API キーの管理は慎重に行ってください。
- psutil によるプロセス優先度設定や CPU affinity は権限や OS に依存します。権限不足の場合は警告のみでスキップされます。
- データファイルのバックアップ、DB スキーマのマイグレーション管理、秘密情報の管理（.env の取扱い）に注意してください。

---

## トラブルシューティング

- .env が読み込まれない / テストで無効化したい場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動読み込みを無効化します。
- streamlit が DB を開けない:
  - monitoring DB が存在するか、読み取り専用 URI を正しく渡しているか確認してください。
  - 例: streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- OpenAI 呼び出し時に JSON パースエラーが出る場合:
  - API のレスポンスが想定と異なるケースをハンドリングする実装があります。ログを確認して失敗チャンクを特定してください。

---

もし README に追加したいコマンドやサンプル設定（.env.example）などがあれば、必要に応じて追記します。