# KabuSys

日本株向け自動売買システム（ライブラリ & 起動スクリプト群）

このリポジトリは、注文実行エンジン、監視コンポーネント、ポートフォリオ構築・リスク制御ロジック、リサーチ/ファクター計算、ニュースNLP（OpenAI）などを含む自動売買システムのコア実装群を収めています。

---

目次
- プロジェクト概要
- 主な機能
- 前提（依存・Python バージョン等）
- セットアップ手順
- 使い方（起動スクリプト / ツール）
- 環境変数 / .env
- 停止・Kill Switch の仕組み
- ディレクトリ構成（簡易ツリー）
- 主要モジュールの説明
- 備考

---

プロジェクト概要
- KabuSys は日本株の自動売買に関連する複数の機能群をまとめたモジュール群です。
- 注文実行（ExecutionEngine）とそれを監視する Monitoring、ポートフォリオ構築ロジック、リサーチ（DuckDB を用いたファクター計算）、ニュース NLP（OpenAI を用いたセンチメント評価）などを提供します。
- 設定は .env ファイルおよび環境変数で管理し、paper_trading（ペーパートレード）モードでは本番データベースと分離して動作します。

主な機能
- ExecutionEngine 起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用の SQLite DB（data/paper_trading.db 既定）に記録
  - プロセス優先度の設定、PID ファイル管理、停止フラグ監視
- Monitoring（run_monitoring.py / monitoring package）
  - システム稼働・リソース監視、トレードログ監視、リスク監視（ドローダウン、ポジション上限など）
  - Kill Switch（条件により data/kill.flag を書き込む）を備え、必要時に ExecutionEngine を停止可能
  - ポーリング間隔は MONITOR_POLL_INTERVAL で変更可能（デフォルト 60 秒）
- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定、等金額/スコア加重配分、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ決定
- リサーチ（kabusys.research）
  - DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー等）、将来リターン、IC 計算、統計サマリー
- AI 関連（kabusys.ai）
  - ニュースを OpenAI（gpt-4o-mini 等）でスコア化して ai_scores テーブルに格納
  - 市場レジーム判定（ETF MA とマクロニュースセンチメントの合成）
- ツール
  - 対話式の .env 作成ウィザード（config_setup.py）
  - 設定検証 CLI（validate_config.py）
  - Paper Trading の検証レポート生成ツール（tools/paper_verification_report.py）
- ロギングユーティリティ（ログのコンソール + 日次ローテーションファイル出力）
- process_priority（Windows/Linux の差分を吸収してプロセス優先度を設定）

前提（依存・Python バージョン等）
- 推奨 Python: 3.10+
  - Union 型記法（例: Path | None）やその他近年の構文を使用しています。
- 主な外部依存パッケージ（最低限）
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config バリデーションで YAML の解析を行う場合に任意）
- SQLite は標準ライブラリの sqlite3 を使用

セットアップ手順（ローカル開発向け）
1. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate （Windows の場合は .venv\Scripts\activate）
2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML
   - 実際のプロジェクトでは requirements.txt を用意している可能性があるため、存在すればそれを使用してください。
3. .env の初期作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します（.env は絶対に Git にコミットしないでください）
4. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）になります
5. データディレクトリ作成（必要に応じて）
   - デフォルトでは data/ 以下に SQLite / PID / フラグが保存されます。実行ユーザーが書き込み可能であることを確認してください。

使い方（代表的なコマンド例）
- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup
- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- ExecutionEngine を起動（本番 / paper_trading のいずれかは KABUSYS_ENV で指定）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db（既定）に記録します。
    - 起動時に data/stop_requested.flag が存在する場合は起動を行わず終了します。
    - PID ファイルは data/execution.pid（既定）に出力されます（設定で変更可能）。
- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 監視は常に Settings.sqlite_path（本番 monitoring DB）を使用します（環境に依存しない）
- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（あるいは環境変数 PAPER_TRADING_SQLITE_PATH）
- AI スコア / レジーム判定をプログラムから呼び出す（例）
  - Python スクリプト内で:
    - import duckdb
    - from kabusys.ai import score_news
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, date(2026, 4, 20), api_key="sk-...")
  - OpenAI API キーは引数渡しもしくは環境変数 OPENAI_API_KEY を使用

主要な環境変数（デフォルトや意味）
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
- KABUSYS_ENV (development | paper_trading | live, デフォルト: development)
- LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL, デフォルト: INFO)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper trading 用監視/注文 DB, デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE (paper_trading の注文約定動作: instant|partial|never|reject, デフォルト: instant)
- PID_FILE_PATH (ExecutionEngine の PID ファイル, デフォルト: data/execution.pid)
- KILL_FLAG_PATH (Kill Switch 用フラグパス, デフォルト: data/kill.flag)
- KILL_FLAG_CLEAR_ON_START (起動時に kill.flag を自動クリアするか。0/1、デフォルト 0)
- MONITOR_POLL_INTERVAL (監視ループの秒間隔、デフォルト 60)
- OPENAI_API_KEY (OpenAI 利用時に必要)

停止 / Kill Switch の仕組み
- 停止フラグ:
  - data/stop_requested.flag を作成すると run_monitoring や run_execution はそれを検知してループを終了・エンジン停止します。
- Kill Switch:
  - リスク監視（drawdown 超過やポジション上限超過など）により kill.flag（既定: data/kill.flag）を書き込むと、ExecutionEngine はそれを検知して安全にシャットダウンされます。
  - kill.flag は KillSwitch.clear() で消去できます。設定 KILL_FLAG_CLEAR_ON_START=1 にすると起動時に自動でクリアされますが、本番では 0 を推奨します。

ディレクトリ構成（主要ファイル抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/.env ロード・Settings 定義
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py       — 統一的なログ設定
    - process_priority.py    — プロセス優先度・CPU affinity ユーティリティ
  - execution/               — Execution エンジン関連（OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
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
  - tools/
    - paper_verification_report.py
  - data/ (run-time に生成される想定のディレクトリ)
    - monitoring.db (SQLite: 監視用）
    - paper_trading.db (SQLite: ペーパートレード用）
    - kabusys.duckdb (DuckDB: 時系列データ / 解析用）
    - execution.pid, stop_requested.flag, kill.flag など

（簡易ツリー）
- src/
  - kabusys/
    - run_execution.py
    - run_monitoring.py
    - config.py
    - config_setup.py
    - validate_config.py
    - ...
    - portfolio/
    - monitoring/
    - execution/
    - research/
    - ai/
    - tools/

主要モジュールの説明（抜粋）
- config.py
  - プロジェクトルートを自動検出して .env/.env.local を読み込み、Settings クラス経由で設定を提供します。
  - 自動ロードを無効にする: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- utils/logging_setup.py
  - StreamHandler（stdout）と日次ローテートファイルハンドラをルートロガーに設定します。ログディレクトリは logs/（既定）。
- monitoring/monitoring_db.py
  - monitoring 用の SQLite テーブルを初期化・操作する永続層。監視ログ、トレードログ、ポジション、リスクログ、ダッシュボード等を管理。
- portfolio/*
  - ポートフォリオ構築に必要な純粋関数群（副作用なしの計算ロジック）。
- ai/news_nlp.py / ai/regime_detector.py
  - OpenAI を使ったニュースセンチメントやマクロセンチメントの計算。API 呼び出しのリトライ・レスポンス検証を実装。
  - API キーは引数か OPENAI_API_KEY で指定。

備考 / 運用上の注意
- .env は機密情報（API キー等）を含むため、絶対にリポジトリにコミットしないでください。
- 本番（KABUSYS_ENV=live）での起動時は validate_config で設定を十分確認してください。特に LINE 通知や Kill Switch の設定は重要です。
- paper_trading モードは本番 DB と完全分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- OpenAI API 呼び出しにはコスト・レート制限があります。news_nlp/regime_detector の実行頻度は注意して運用してください。
- DuckDB の WRITE 操作や executemany に対するバージョン差異があるため、DB 操作部分は互換性に注意して実行してください。

最後に
- この README はコードベースから読み取れる設計意図・使い方をまとめたものです。実際のデプロイや本番運用の際は運用手順書・監査要件に従って追加の安全策（サンドボックス、十分なログ監視、テスト環境での検証など）を導入してください。

ご希望があれば、以下を追加で作成します:
- systemd / supervisor 用のサービスユニット例（run_monitoring / run_execution 用）
- docker-compose 例（DuckDB/SQLite はローカルファイルだが、環境構築用コンテナ例）
- より詳細な environment variable のサンプル .env.example

必要なものを教えてください。