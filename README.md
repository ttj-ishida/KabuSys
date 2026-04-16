# KabuSys

日本株自動売買システム（ライブラリ／実行コンポーネント群）のリポジトリ用 README。

以下はこのコードベースの概要、機能、セットアップ方法、使い方、主要ディレクトリ構成を日本語でまとめたものです。

注意: 本 README はソースコード中の実装・ドキュメント文字列に基づいて作成しています。

---

## プロジェクト概要

KabuSys は日本株の自動売買および検証／監視のためのコンポーネント群です。主な要素は以下です。

- ExecutionEngine（発注エンジン） / Order 管理 / Reconciler（再起動後の復旧）
- Monitoring（システム稼働率、注文滞留、レジスク監視、アラート）
- Portfolio construction（候補選定、重み付け、ポジションサイジング）
- Research（ファクター計算、特徴量探索）
- AI モジュール（ニュースセンチメント、レジーム判定、OpenAI を利用）
- ツール: Paper Trading の検証レポート生成、Streamlit ベースの監視ダッシュボード

設計方針として、DuckDB/SQLite をデータ層に使い、外部 API （kabuステーション、J-Quants、OpenAI）は設定に応じて利用します。Paper Trading 環境は本番 DB から分離されます。

---

## 主な機能一覧

- 実行（Execution）
  - 注文作成、送信、状態同期、再起動時のリコンシリエーション
  - ブローカークライアントの抽象化（Paper/Live 切替）
  - リスク管理（ポジション上限、ドローダウン等）
- 監視（Monitoring）
  - システム状態（CPU/Mem/Disk）、データ鮮度チェック、PID 存在確認
  - 注文滞留・約定異常の検出
  - リスクイベントの永続化（SQLite）
  - LINE によるアラート送信（AlertManager）
  - kill.flag / stop_requested.flag による停止シグナル
  - Streamlit ダッシュボード（読み取り専用）
- ポートフォリオ構築
  - シグナル選定、等重・スコア重み付け、リスク調整（セクター制限、レジーム乗数）
  - ポジションサイズ計算（単元丸め、aggregate cap）
- リサーチ
  - Momentum / Volatility / Value 等ファクター計算（DuckDB ベース）
  - 将来リターン、IC 計算、統計サマリー
- AI（OpenAI）
  - ニュースを LLM でセンチメント評価して ai_scores に保存
  - マクロニュース＋ETF MA で市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成（paper_verification_report）
  - Streamlit ダッシュボード（monitoring/streamlit_dashboard.py）

---

## セットアップ手順（開発 / 実行環境）

1. Python 仮想環境（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 必要な主なパッケージ:
     - duckdb
     - psutil
     - openai
     - requests
     - streamlit
   - 例:
     - pip install duckdb psutil openai requests streamlit

   ※ requirements.txt が無い場合は上記パッケージを個別にインストールしてください。

3. 環境変数ファイルの用意（.env）
   - プロジェクトルートに `.env` / `.env.local` を置くことで自動読み込みされます（既存 OS 環境変数は上書きされません）。
   - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN
   - KABU_API_PASSWORD
   - OPENAI_API_KEY （AI 機能を使う場合）
   - その他オプション:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading の場合の DB、デフォルト: data/paper_trading.db）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信）
     - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
     - PAPER_FILL_MODE（paper_trading の fill 動作: instant | partial | never | reject）

5. データディレクトリ
   - デフォルトで `data/` 配下のファイルを使用します（DB、PID、フラグ）。
   - 例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag

---

## 使い方（主要な起動方法）

各スクリプトはモジュールとしても直接実行できます。パッケージをインストールせずにソースツリーから実行する場合は Python のモジュール指定が便利です。

1. Monitoring（監視ループ）起動
   - 既定: MONITOR_POLL_INTERVAL=60 秒
   - 実行例:
     - python -m kabusys.run_monitoring
     - あるいは直接: python src/kabusys/run_monitoring.py
   - 動作:
     - Settings から DB パスなどを読み、SQLite（monitoring DB）と DuckDB に接続して SystemMonitor をポーリングします。
     - 停止: プロジェクトの data/stop_requested.flag が存在するとループを終了します。

   - 環境変数でポーリング間隔を上書き:
     - export MONITOR_POLL_INTERVAL=30

   - 備考:
     - Monitoring は KABUSYS_ENV にかかわらず monitoring 用 SQLite（settings.sqlite_path）を使用します。

2. Execution（注文エンジン）起動
   - 実行例:
     - python -m kabusys.run_execution
   - 動作:
     - Settings に応じて paper_trading モード（KABUSYS_ENV=paper_trading）なら paper DB を使い Mock ブローカーで動作。本番（live）は実ブローカー。
     - 実行中は data/execution.pid に PID を書く設計（Engine による制御）。
     - 停止:
       - data/stop_requested.flag が存在するとエンジンを停止して終了します。

3. Paper Trading 検証レポート生成
   - 実行例:
     - python -m kabusys.tools.paper_verification_report
     - 期間指定:
       - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
     - DB を指定する場合:
       - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

   - 出力:
     - 標準出力に検証レポート（稼働率、注文成功率、レイテンシ等）を出力します。

4. Streamlit ダッシュボード（監視 UI）
   - 起動例:
     - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 説明:
     - DB を読み取り専用で開き、ダッシュボードを表示します（MonitoringEngine によりデータが書き込まれている必要があります）。

5. AI 機能（ニュース NLP、レジーム判定）
   - OpenAI API キーが必要: 環境変数 OPENAI_API_KEY を設定するか、関数引数で渡します。
   - 例（プログラム内呼び出し）:
     - from kabusys.ai import score_news
     - score_news(duckdb_conn, target_date, api_key="sk-...")

---

## 停止・強制停止の仕組み

- stop_requested.flag
  - 実行スクリプト（run_monitoring, run_execution）は `data/stop_requested.flag` の存在を監視し、検知したらグレースフルに停止します。手動で停止したい場合はファイルを作成してください。

- kill.flag
  - KillSwitch（監視側のロジック）はリスクトリガー発生時に `data/kill.flag` を書き込みます。ExecutionEngine 起動時にこのフラグのクリア動作が設定されている場合は開始時に消去されます。kill.flag の内容は理由文字列として保存されます。

---

## 設定 (Settings) の振る舞い

- .env / .env.local の自動読み込み
  - プロジェクトルート（.git または pyproject.toml を基準）にある `.env` を自動読み込みします。
  - `.env.local` は OS 環境変数より優先して上書き可能（ただし既存の OS 環境変数は保護される）。
  - 自動読み込みを無効化する: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

- 主な設定プロパティ（Settings クラス）
  - env: KABUSYS_ENV（development, paper_trading, live）
  - duckdb_path: DUCKDB_PATH（デフォルト data/kabusys.duckdb）
  - sqlite_path: SQLITE_PATH（デフォルト data/monitoring.db）
  - paper_sqlite_path: PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）
  - pid_file_path, kill_flag_path, kill_flag_clear_on_start
  - cpu_threshold_pct, memory_threshold_pct, disk_threshold_pct
  - PAPER_FILL_MODE（paper_trading 用）
  - required: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（未設定だと例外）

---

## ロギング / 優先度設定

- 起動時に set_process_priority("high") を呼んでプロセス優先度を設定します（プラットフォーム依存、psutil を使用）。
- LOG_LEVEL は環境変数で設定可能（DEBUG/INFO/...）。Settings.log_level で検証します。
- 多くのモジュールは logging.getLogger(__name__) を使ってログ出力します。

---

## 主要ディレクトリ構成

（src/kabusys をルートとする主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数 / .env ローダ、Settings
  - run_monitoring.py  — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py   — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py  — Paper Trading 検証レポート
  - monitoring/
    - monitoring_db.py    — SQLite 永続化（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py    — システム状態チェック（CPU/メモリ/ディスク/PID/データ鮮度）
    - trade_monitor.py     — 注文滞留・約定異常チェック
    - risk_monitor.py      — ドローダウン・ポジション上限監視
    - kill_switch.py       — kill.flag 管理
    - alert_manager.py     — LINE push 通知
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py  (実装一部のみ提示)
    - broker_factory.py
    - broker_api.py
    - ...
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py         — ニュース NLP（OpenAI）
    - regime_detector.py  — レジーム判定（ETF + マクロニュース）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/ (ランタイムで生成される想定)
    - monitoring.db
    - paper_trading.db
    - execution.pid
    - kill.flag
    - stop_requested.flag
    - kabusys.duckdb

---

## 開発・運用時の注意点

- Paper Trading と本番 DB は分離されます（KABUSYS_ENV=paper_trading の場合、paper_sqlite_path を使用）。
- Monitoring は常に settings.sqlite_path（監視用 DB）を使用します（環境に依存しない）。
- OpenAI 関連機能は API 呼び出しの失敗に対してフェイルセーフ（デフォルト値で継続）を採用していますが、API キーが未設定だと明示的に例外を投げる箇所があります（score_news, score_regime 等）。
- .env のパースは独自実装です（クォート、エスケープ、コメント処理を考慮）。
- DuckDB のクエリは prices_daily / raw_financials / raw_news 等のテーブルを前提としています。データの準備が必要です。
- stop/kill フラグはファイルベースです。自動化スクリプトや運用手順と合わせて使用してください。

---

## トラブルシューティングのヒント

- SQLite/DuckDB に接続できない場合はパスとパーミッションを確認してください。
- psutil による優先度設定で権限エラーが出る場合は root / 管理者権限での実行か、設定を "normal" に下げてください。
- OpenAI のレート制限や一時的なエラーは内部でリトライ実装がありますが、連続失敗時はログを確認して API キーやネットワークを確認してください。
- Streamlit ダッシュボードは DB を読み取り専用で開きます。MonitoringEngine が書き込みをしている必要があります。

---

README は以上です。必要であれば、以下の追加情報を補足できます。

- 具体的な systemd / supervisor サービスファイル例（プロダクション運用向け）
- 詳細な環境変数一覧と推奨値サンプル（.env.example）
- Dockerfile / docker-compose の雛形
- テストの実行方法（pytest など）