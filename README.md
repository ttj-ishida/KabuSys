README — KabuSys（日本株自動売買システム）
====================================

概要
----
KabuSys は日本株の自動売買・研究・監視を目的とした Python パッケージ群です。  
このリポジトリには主に以下の機能が含まれます。

- 発注エンジン（ExecutionEngine） — 本番 / ペーパートレードに対応
- 監視プロセス（Monitoring） — システム稼働性・データ鮮度・リスク監視、Kill Switch
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・ポジションサイズ計算）
- 研究用モジュール（ファクター計算、特徴量探索）
- AI 支援モジュール（ニュースの NLP 評価・市場レジーム判定）
- 運用補助ツール（.env ウィザード・設定検証・Paper Trading 検証レポート）

主な特徴
-------
- 環境分離:
  - KABUSYS_ENV による実行モード切替（development / paper_trading / live）。
  - paper_trading モードは専用の SQLite DB を使用して本番 DB と完全分離。
- フェイルセーフ設計:
  - Kill Switch（data/kill.flag）により外部から ExecutionEngine を停止可能。
  - API 呼び出しはリトライやフェイルオープンで安全に処理。
- ロギング:
  - 統一された logging 設定（コンソール + 日次ローテートファイル）。
- DuckDB を用いた分析用 DB レイヤ（prices_daily / raw_financials 等を想定）。
- AI（OpenAI）を利用したニュースセンチメント集計・レジーム検出（API キー必須）。

前提（推奨）
-----------
- Python（推奨 3.10+）
- 依存パッケージ（例）: duckdb, psutil, openai（AI 機能を使う場合）、PyYAML（設定ファイルの検証時）
  - 依存関係は別途 requirements.txt や pyproject.toml を参照してください。

セットアップ手順
----------------
1. リポジトリをクローンして作業ディレクトリへ移動。
2. 仮想環境を作成して有効化（任意だが推奨）。
3. 必要パッケージをインストール:
   - 例: pip install duckdb psutil openai
   - PyYAML をインストールすると config/*.yaml の検証が有効になります。
4. .env を作成（ウィザード推奨）:
   - 対話式ウィザード: python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 推奨/設定例:
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY=（AI 機能を使う場合）
5. 設定検証（起動前チェック）:
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit 1）になります。
6. （必要に応じて）データディレクトリやログディレクトリを作成:
   - デフォルト DB/ログは data/ と logs/ 配下に作成されます。自動作成されることが多いですが権限等で失敗する場合があります。

主要な環境変数（代表）
---------------------
- KABUSYS_ENV: 実行環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
- LOG_LEVEL / LOG_DIR
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（コマンド／モジュール）
-----------------------------
- 環境ウィザード（.env の初期作成／更新）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 備考:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して PAPER_TRADING_SQLITE_PATH（data/paper_trading.db など）に記録します。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中は data/execution.pid に PID を書きます。停止は stop flag / kill.flag による制御やプロセス終了で行います。

- Monitoring（簡易 SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を変更できます（秒、デフォルト 60）。
  - 監視は本番 sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず本番監視 DB を参照）。

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 機能（プログラムから呼び出す）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と日付を渡してニュースセンチメントを ai_scores テーブルへ書き込みます。
    - api_key を明示的に渡すか環境変数 OPENAI_API_KEY を設定してください。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - 市場レジーム（bull/neutral/bear）を判定して market_regime テーブルへ書き込みます。

注意点 / 運用に関する情報
------------------------
- Kill Switch:
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）を作成して ExecutionEngine に停止を促します。
  - KillSwitch の判定は監視コンポーネント（RiskMonitor など）が行います。
- 停止フラグ:
  - run_execution.py / run_monitoring.py は data/stop_requested.flag を監視してループを抜けます。
- ログ:
  - ログファイルは logs/<app_name>.log に日次ローテートで出力されます（デフォルト keep 30 日）。
- Paper Trading と本番 DB の分離:
  - paper_trading 環境は settings.paper_sqlite_path を使用（デフォルト data/paper_trading.db）。
- AI 呼び出し:
  - OpenAI API 呼び出しはリトライ・バックオフを組み込んでいますが、API キー・利用制限に注意してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は起動時に必要なテーブルと一部カラム追加を行う（冪等）。

ディレクトリ構成（主なファイル）
------------------------------
- src/kabusys/
  - __init__.py
  - config.py — 環境変数・設定管理（.env 自動ロード含む）
  - config_setup.py — .env 作成ウィザード（対話式）
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading の検証レポート生成ツール
  - ai/
    - news_nlp.py — ニュースの NLP スコアリング（OpenAI 依存）
    - regime_detector.py — レジーム判定（AI + 価格）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 永続層（テーブル作成・CRUD）
    - system_monitor.py — システム・データ鮮度監視
    - trade_monitor.py — 発注ログ監視（存在）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - monitoring_engine.py — Monitor を束ねるエンジン
    - kill_switch.py — kill.flag 書込ユーティリティ
    - alert_manager.py — アラート送信管理（存在）
  - execution/
    - execution_engine.py — 実行エンジン本体（存在）
    - broker_factory.py — ブローカークライアント生成（Mock / 実装）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注関連ロジック
  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 株数計算・集約キャップ処理
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum / value / volatility）
    - feature_exploration.py — 将来リターン・IC 等の分析ユーティリティ
  - utils/
    - logging_setup.py — ログ設定ユーティリティ
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

その他・開発者向けメモ
--------------------
- テスト時は .env 自動ロードを無効化できます:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してプロセスを起動してください。
- YAML 検証は PyYAML がインストールされている場合のみ行います（validate_config.py）。
- OpenAI 呼び出し周りはレスポンス検証や部分書き込み（成功したコードのみ INSERT）で安全性を高めています。
- ローカル開発では KABUSYS_ENV=development を使用し、発注処理が実際に行われないように設計できます。

ライセンス / バージョン
----------------------
パッケージバージョンは src/kabusys/__init__.py に定義されています（現状 __version__ = "0.1.0"）。

お問い合わせ / 貢献
------------------
バグ報告・改善提案はリポジトリの issue を利用してください。プルリク歓迎です。README にない追加の運用手順や運用時の注意点はドキュメントに追記してください。

以上。必要であれば導入手順の具体的なコマンド一覧（requirements の例、systemd ユニット例、デプロイ手順）や各モジュールの API リファレンスを別途作成します。どの情報を優先して追加しますか？