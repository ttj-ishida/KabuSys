# KabuSys

日本株自動売買システムのサブセット実装。ポートフォリオ構築、発注エンジン、監視、リサーチ、AIベースのニュースセンチメント評価などのユーティリティ群を含みます。

> バージョン: 0.1.0（src/kabusys/__init__.py）

---

## プロジェクト概要

本リポジトリは以下の主要機能を持つモジュール群で構成されています。

- ExecutionEngine（発注実行エンジン）: kabuステーション等のブローカークライアントを介した注文発行ロジック（`run_execution.py`）
- Monitoring（監視）: システム稼働性、データ鮮度、注文ログ、リスク（ドローダウン・ポジション上限）を定期チェックしアラート・Kill Switch を管理（`run_monitoring.py`、`monitoring/*`）
- Portfolio コンポーネント: 銘柄選定、重み計算、ポジションサイズ計算、セクターキャップ等（`portfolio/*`）
- Research / Factor 計算: DuckDB 上の時系列データからファクター等を算出（`research/*`）
- AI モジュール: ニュース NLP による銘柄センチメント評価、レジーム判定（`ai/*`）
- ツール: .env 対話生成ウィザード、設定検証、Paper Trading レポート等（`config_setup.py`, `validate_config.py`, `tools/*`）
- 共通ユーティリティ: ロギング設定、プロセス優先度設定、環境設定読み込み等（`utils/*`, `config.py`）

設計方針として、本番環境とペーパートレードを明確に分離し、DuckDB/SQLite を使った分析・監視データの永続化を行います。

---

## 主な機能一覧

- 設定管理
  - 自動的な .env 読み込み（プロジェクトルート検出）
  - 設定ウィザード（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）
- 実行エンジン
  - 本番 / ペーパートレード分離（環境変数 `KABUSYS_ENV`）
  - ブローカークライアントファクトリ（Mock / 実ブローカー）
  - リスク管理（レート制限、drawdown、position limit 等）
- 監視
  - SystemMonitor: CPU/メモリ/ディスク、プロセス生存、データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常検出（trade_logs）
  - RiskMonitor: ハイウォーターマークとドローダウンの監視、リスクログ記録
  - KillSwitch: 条件に応じて `data/kill.flag` を書き込み ExecutionEngine 停止指令
  - MonitoringEngine: 上記を定期ポーリングしてアラート発動
- リサーチ
  - Momentum/Volatility/Value 等のファクター計算（DuckDB）
  - Forward return / IC / 統計サマリー
- AI（OpenAI）連携
  - ニュース記事の銘柄別センチメント評価（`kabusys.ai.news_nlp.score_news`）
  - 市場レジーム判定（`kabusys.ai.regime_detector.score_regime`）
  - （API 呼び出しは OpenAI API キーが必要）
- ツール
  - Paper Trading 検証レポート生成（`kabusys.tools.paper_verification_report`）
- ロギング・運用
  - 統一的なログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度設定ユーティリティ（Windows/Linux 対応）

---

## セットアップ手順（ローカル・開発向け）

以下は開発環境での基本的な準備手順の例です。環境によって適宜調整してください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - requirements.txt がある場合はそれを使用してください。無ければ少なくとも以下のパッケージが必要になります:
     - duckdb
     - psutil
     - openai
     - PyYAML (設定検証時に利用)
   - 例:
     - pip install duckdb psutil openai PyYAML

4. .env の用意
   - 対話式ウィザードで作成:
     - python -m kabusys.config_setup
   - または手動でプロジェクトルートに `.env` を作成（例は次項参照）

5. 初期ディレクトリ作成（ログ・データ用）
   - mkdir -p data logs

6. （任意）環境変数の自動ロードを無効化する場合:
   - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定

注意:
- 実ブローカーや OpenAI を使う機能は適切な API キーや資格情報が必要です。
- psutil の一部操作（プロセス優先度設定など）は権限が必要な場合があります。

---

## 必須 / 主要な環境変数（抜粋）

- 必須:
  - JQUANTS_REFRESH_TOKEN — J-Quants API リフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 動作環境:
  - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
    - paper_trading の場合、専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用します

- DB / ファイルパス:
  - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
  - PID_FILE_PATH — ExecutionEngine PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch ファイル（デフォルト: data/kill.flag）

- その他:
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
  - LOG_DIR — ログ出力ディレクトリ（デフォルト: logs/）
  - PAPER_FILL_MODE — Paper Trading 時の Fill モード（instant/partial/never/reject、デフォルト: instant）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60。0以下はデフォルトにフォールバック）
  - OPENAI_API_KEY — OpenAI API キー（AI 機能利用時）

例（`.env` の最小例）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

---

## 使い方（主要なコマンド）

- 設定ウィザード（対話式 .env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い（exit code 1）

- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 備考:
    - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、データは `data/paper_trading.db`（既定）に記録されます
    - 起動時に `data/stop_requested.flag` が存在すると起動をスキップします
    - 起動中は PID を `data/execution.pid` に書き込みます

- 監視ループ（Monitoring）起動
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）
  - 監視は環境にかかわらず本番用 SQLite（Settings.sqlite_path）を使用して監視テーブルを初期化します
  - 監視停止: プロセス側は `data/stop_requested.flag` を検知してループを抜けます

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（プログラムから呼び出す）
  - ニューススコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)
      - api_key が None の場合は環境変数 OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

注意:
- AI 機能は OpenAI API への呼び出しを伴います。API キーの設定とコストに注意してください。
- DuckDB 接続は duckdb.connect(path) で作成して渡します。

---

## 運用上のポイント / 注意事項

- Kill Switch
  - `kabusys.monitoring.kill_switch.KillSwitch` は `data/kill.flag` を書き込み ExecutionEngine に停止シグナルを送ります。
  - 本番環境では `KILL_FLAG_CLEAR_ON_START=0` を推奨（自動クリアを無効化）。
- ペーパートレード分離
  - `KABUSYS_ENV=paper_trading` の場合、発注ログ等は `PAPER_TRADING_SQLITE_PATH` に保存され本番 DB と分離されます。
- ログ
  - デフォルトで console (stdout) と `logs/<app_name>.log`（日次ローテート、30日保持）へ出力されます。
  - ログディレクトリ作成に失敗するとファイル出力はスキップしてコンソールのみになります。
- プロセス優先度
  - 起動スクリプトは `set_process_priority("high")` を呼び出します。権限が無い場合は警告ログが出ますが処理は継続します。
- DB マイグレーション
  - monitoring DB の初期化（`init_monitoring_db`）は冪等であり、既存スキーマに不足カラムがある場合は必要に応じて ALTER を実行します。
- 環境変数の自動ロード
  - `config.py` はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を検出して `.env` / `.env.local` を自動で読み込みます。自動読み込みを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ディレクトリ構成

（src/kabusys 以下を抜粋）

- kabusys/
  - __init__.py
  - config.py                 — 環境変数・設定管理（.env 自動ロード含む）
  - config_setup.py           — .env 対話式ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - news_nlp.py             — ニュースセンチメント評価（OpenAI 連携）
    - regime_detector.py      — 市場レジーム判定（OpenAI 連携）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py (参照されるが未リスト化の可能性あり)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - broker_factory.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/                     — 実行時生成される想定ディレクトリ（data/*.db, flags, pid など）
  - logs/                     — ログ出力先（デフォルト）

---

## よくある操作例まとめ

- .env 作成
  - python -m kabusys.config_setup

- 設定チェック
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 監視プロセス開始（バックグラウンド等で実行）
  - python -m kabusys.run_monitoring

- 発注エンジン開始（当日セッションを起動）
  - python -m kabusys.run_execution

- Paper Trading レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## トラブルシューティング / Tips

- MONITOR_POLL_INTERVAL は正の整数で指定してください。0 や負値、非整数の場合はデフォルト（60秒）にフォールバックします。
- psutil の一部機能（プロセス優先度・CPU affinity）は OS と権限に依存します。権限不足だと警告ログが出ますが処理自体は継続されます。
- OpenAI 関連は API レートや一時エラーに対して指数バックオフでリトライ実装がありますが、API キーや使用料に注意してください。
- 本番環境（KABUSYS_ENV=live）では Kill Switch や LINE 通知設定などを必ず確認してください（validate_config の live チェックが役立ちます）。

---

これで README の基本項目は以上です。必要があれば以下を追加できます:
- 依存パッケージの正確な requirements.txt（pip freeze / 手動編集）
- CI/CD・デプロイ手順
- 詳細な API ドキュメント（各モジュールの関数シグネチャ、戻り値仕様）
- サンプル .env.example（機密情報を含まないテンプレート）

どの追加情報が必要か教えてください。