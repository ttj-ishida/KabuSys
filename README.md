# KabuSys

日本株向け自動売買システム（ライブラリ / 実行コンポーネント群）

このリポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・検証ツール・研究用ユーティリティ（DuckDB ベース）や、LLM を用いたニュースセンチメント / レジーム判定を含むモジュール群で構成されています。

概要 / 目的
- 日本株の自動売買ワークフローを構成するコンポーネント群を提供します。
- DuckDB を用いたファクター計算・研究ツール、SQLite による監視ログ・発注ログの永続化、OpenAI API を用いたニュース NLP とレジーム検出などを含みます。
- 本番 (live)、ペーパートレード (paper_trading)、開発 (development) を環境変数で切り替え可能です。

主な機能
- ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカークライアント生成（実口座 / モック分離）
  - 発注管理、リスク管理、リコンシリエーション、PID / 停止フラグ連携
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システム状態（CPU/メモリ/ディスク）・データ鮮度・注文滞留・ドローダウン監視
  - 永続化: monitoring.db（SQLite）
  - LINE による通知 (AlertManager)
  - kill.flag による外部停止（KillSwitch）
  - Streamlit ダッシュボード（監視データ可視化）
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、等比重／スコア重み、リスク調整（セクター制限、レジーム乗数）、株数決定（単元丸め・上限・aggregate キャップ）
- リサーチ / ファクター計算（research パッケージ）
  - Momentum / Volatility / Value ファクター計算（DuckDB 経由）
  - 将来リターン、IC、統計サマリー等
- AI 関連（ai パッケージ）
  - news_nlp: raw_news から OpenAI を用いて銘柄別センチメント算出（ai_scores へ書き込み）
  - regime_detector: ma200 とマクロニュースセンチメントを合成して market_regime を計算・永続化
- ツール
  - paper_verification_report: ペーパートレード DB を集計して PASS/FAIL 判定レポートを表示

セットアップ手順（開発環境想定）
1. Python（推奨 3.10+）を用意
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （必要に応じて他の依存を追加）
   - 補足: sqlite3 は標準ライブラリ。OpenAI は openai パッケージ、LINE 通知には requests を使用します。
4. プロジェクトルートに .env（または .env.local）を配置
   - 自動ロードの仕組み上、プロジェクトルートは .git または pyproject.toml によって検出されます。
   - 必須（運用上必要となる主要環境変数の例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=... （AI 機能を使う場合）
   - 任意 / デフォルトあり:
     - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
     - LOG_LEVEL (DEBUG|INFO|...)
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB、デフォルト: data/paper_trading.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH, KILL_FLAG_PATH, MONITOR_POLL_INTERVAL 等
   - .env の読み込みルール:
     - OS 環境変数 > .env.local > .env（自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）
5. data ディレクトリを作成（実行時に自動作成される箇所もありますが事前作成推奨）
   - mkdir -p data

使い方（よく使うコマンド）
- 監視ループを起動（本番監視プロセス）
  - KABUSYS_ENV=production 等の設定にかかわらず、monitoring は sqlite_path を使用します
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  - 停止は data/stop_requested.flag ファイルを作成して行います

- ExecutionEngine 起動（発注エンジン）
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading にした場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH に記録し、本番 DB と分離されます
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします
  - 実行中に停止したい場合は data/stop_requested.flag を作成するとエンジンにシグナルを送り停止します

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - データベースを読み取り専用で開きます（監視エンジンが稼働していることが前提）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - デフォルト DB: data/paper_trading.db（環境変数 PAPER_TRADING_SQLITE_PATH で変更可）

- AI 機能（コードから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)  — OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

重要な運用ファイル / フラグ
- data/stop_requested.flag — run_*.py がポーリング / 実行ループ終了を検知するための停止フラグ
- data/execution.pid — ExecutionEngine の PID ファイル（SystemMonitor が参照）
- data/kill.flag — KillSwitch により書かれる停止理由ファイル（ExecutionEngine 停止トリガー）
- SQLite / DuckDB ファイル（デフォルト）
  - data/monitoring.db
  - data/paper_trading.db
  - data/kabusys.duckdb

設定（Settings）について（概要）
- 設定は環境変数 / .env ファイルから取得されます。自動読み込みはプロジェクトルートの検出に依存します。
- 主なプロパティ:
  - env: KABUSYS_ENV (development | paper_trading | live)
  - sqlite_path / paper_sqlite_path / duckdb_path
  - pid_file_path / kill_flag_path / kill_flag_clear_on_start
  - PAPER_FILL_MODE: ペーパートレードの挙動（instant | partial | never | reject）
  - CPU/MEMORY/DISK しきい値等

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / .env 読み込み・Settings 定義
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - monitoring/
    - __init__.py
    - monitoring_db.py — SQLite スキーマ & DB ラッパー
    - system_monitor.py — CPU/メモリ/ディスク・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常チェック
    - risk_monitor.py — ドローダウン・ポジション上限モニター
    - kill_switch.py — kill.flag 処理
    - alert_manager.py — LINE Push 送信
    - monitoring_engine.py — 各 Monitor を束ねる
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py, ...（発注関連）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
  - data/ （実行時に DB・フラグが置かれる想定のディレクトリ）

開発 / テスト向けメモ
- Settings は .env ファイルの自動ロードを提供しますが、テスト実行時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセットして自動ロードを無効化できます。
- DuckDB 接続は SQL を直接実行する設計で、prices_daily / raw_financials / raw_news 等のテーブルを用いてファクター計算・AI 前処理を行います。
- AI 呼び出し部分は外部ネットワーク依存・レート制限を考慮したリトライ実装と、部分失敗時のフェイルセーフ（スコア 0 で継続、既存スコアを保護する書込み戦略）を備えています。
- process_priority.set_process_priority() を run_* スクリプトで最初に実行し、プロセス優先度を設定します（psutil に依存）。

よくある運用手順（例）
1. 監視を起動:
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
2. ペーパートレード実行:
   - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
3. 検証レポート:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
4. Streamlit ダッシュボード:
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

ライセンス / 責任範囲
- ここに掲載したのは内部実装の抜粋です。実運用に移す際は各モジュールの挙動を十分に理解し、テスト・監査を行ってください。実行による損失や第三者への影響については利用者側の責任となります。

補足 / 参照
- 各モジュールの docstring に設計方針や注意点が記載されています。実装を変更する際は docstring を参照してください。
- .env のサンプル（.env.example）がある場合はそれを参考に設定してください（README に同梱している場合もあります）。

問題・改善提案・バグ報告
- 実装や挙動に関する質問やバグはイシューで報告してください。可能であれば再現手順とログを添えてください。

---

必要なら、README に追加したい具体的なコマンド例や .env のテンプレートを作成します。どの情報をより詳細に載せたいか教えてください。