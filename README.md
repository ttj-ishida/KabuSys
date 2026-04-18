# KabuSys

日本株自動売買システムの一部を実装した Python パッケージ。データパイプライン、ファクター算出、ポートフォリオ構築、リスク管理、監視、AI を使ったニュース評価、ペーパートレード検証ツール等のコンポーネントを収めています。

## 概要
KabuSys は以下の機能群で構成される自動売買基盤のライブラリ／実行スクリプト群です。

- データ格納（DuckDB / SQLite）
- ファクター / 特徴量計算（research）
- ポートフォリオ構築・サイズ算出（portfolio）
- ExecutionEngine（発注ロジック）およびペーパートレードサポート
- 監視（System / Trade / Risk）と Kill Switch（停止フラグ）
- ニュースを LLM（OpenAI）で評価する AI モジュール
- 各種 CLI ツール（.env ウィザード・設定検証・ペーパートレード検証レポート等）

設計方針として、ルックアヘッドバイアスの排除、DB 分離（本番 / ペーパー）、冪等性、フェイルセーフやリトライ戦略が考慮されています。

## 主な機能一覧
- 環境設定ウィザード: python -m kabusys.config_setup で .env を対話作成
- 設定検証 CLI: python -m kabusys.validate_config
- ExecutionEngine 起動: python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い data/paper_trading.db に記録
- 監視プロセス起動: python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
  - 監視は常に本番の sqlite_path を利用（KABUSYS_ENV に依存しない）
- Monitoring/DB 層（SQLite）:
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理
  - マイグレーション（列追加）を自動で行う
- RiskMonitor / KillSwitch / MonitoringEngine: ドローダウンやポジション上限の監視、kill.flag 書き込みで Execution 停止
- Portfolio モジュール:
  - 候補選定、等ウェイト・スコア加重、セクターキャップ、レジーム乗数、株数計算（単元丸め）
- Research モジュール:
  - Momentum / Volatility / Value などのファクター計算、将来リターン、IC 計算、統計サマリー
- AI モジュール:
  - news_nlp: raw_news を OpenAI (gpt-4o-mini) に送り銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector: ETF とマクロニュースから市場レジーム判定（LLM を使用）
- Tools:
  - paper_verification_report: ペーパートレード DB を解析して検証レポート生成

## セットアップ手順（開発 / 実行環境）
1. Python (3.9+) を用意
2. 必要パッケージをインストール（プロジェクトに requirements.txt がある場合はそれを利用）
   - 主要依存例:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証を行う場合）
   例:
   ```
   pip install duckdb psutil openai PyYAML
   ```
3. プロジェクトルートに移動（.git または pyproject.toml を持つルートを基準に自動検出を行います）
4. 環境変数設定
   - .env を作成するにはウィザードを使うと便利:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env を直接作成してください（.env.example を参照）
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - DUCKDB_PATH（分析 DB、デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - OPENAI_API_KEY（AI モジュールを使う場合）
     - LOG_LEVEL / LOG_DIR
   - 自動ロード制御:
     - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動ロードを無効化できます
     - .env.local は .env の上書きに使えます（OS 環境変数は保護されます）
5. ディレクトリ作成（logs / data 等は自動で作成される場合がありますが、手動で作る場合）:
   ```
   mkdir -p data logs
   ```

## 使い方（主要 CLI / スクリプト）
- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```
- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  # 警告を FAIL 扱いにする場合:
  python -m kabusys.validate_config --strict
  ```
- ExecutionEngine をバックグラウンド等で起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB に記録され、本番 DB と分離されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動しません。
  - 実行中に data/stop_requested.flag を作成するとエンジンは安全に停止します。
  - PID ファイルは data/execution.pid（Settings.pid_file_path）に作成されます。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 が設定されていると kill.flag を消去します（本番では注意）。
- Monitoring（監視プロセス）起動
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング秒数を上書き可能（例: MONITOR_POLL_INTERVAL=30）
  - 監視は常に Settings.sqlite_path（本番監視 DB）を使用します（KABUSYS_ENV に依らず）
  - 停止は data/stop_requested.flag を作成すると行われます
- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```
- AI / レジーム判定等（ライブラリ関数として呼び出し）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは OpenAI API キー（OPENAI_API_KEY）を参照／引数で指定する必要があります。

## 重要な環境変数（抜粋）
- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（paper_trading 時に使用）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログ格納ディレクトリ（default: logs/）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、default: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みの無効化（1 で無効）

## 停止 / Kill Switch / フラグ
- Execution 停止（Kill）: monitoring が条件を満たすと data/kill.flag を書き込み、エンジンに停止指示を出します（ExecutionEngine は起動時に kill.flag の状態を確認）。
- 手動停止トリガ: data/stop_requested.flag を作成すると run_execution / run_monitoring のループが終了します。
- kill.flag の自動クリアは KILL_FLAG_CLEAR_ON_START により制御（本番では 0 推奨）。

## ログ
- kabusys.utils.logging_setup.setup_logging を通じて統一的にログを設定します。
- 標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力します。デフォルトで 30 日分保持。
- LOG_DIR / LOG_LEVEL 環境変数で動作を調整可能。

## ディレクトリ構成（主要ファイル）
プロジェクトルートの src/kabusys 配下の主要モジュールを抜粋します:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込み機能あり）
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - data/ (モジュール想定: データパイプライン等)
  - research/
    - factor_research.py     — モメンタム等ファクター計算（DuckDB）
    - feature_exploration.py — IC / 将来リターン / 統計サマリー
  - portfolio/
    - portfolio_builder.py   — 候補選定・重み
    - position_sizing.py     — 株数決定・単元丸め・キャップ
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - ai/
    - news_nlp.py            — ニュースを LLM でスコアリング
    - regime_detector.py     — 市場レジーム判定（ETF + マクロニュース）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（テーブル作成・Upsert 等）
    - system_monitor.py      — システム状態 / データ鮮度監視
    - trade_monitor.py       — （注文監視ロジック）※コードベースに詳細実装あり
    - risk_monitor.py        — ドローダウン・ポジション上限監視
    - kill_switch.py         — kill.flag の管理
    - monitoring_engine.py   — 各モニタ束ねる実行ループ
  - execution/               — Execution に関するモジュール群（broker, engine, order_manager など）
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity 設定ユーティリティ

（この README はコードベースの主要部分を概説したもので、全てのファイルを網羅しているわけではありません。）

## 開発上の注意
- ルックアヘッドバイアス対策のため、日付計算や DB クエリは target_date を受け取り、内部で現在日時を直接参照しない実装方針が多く採られています。
- DuckDB は分析向けに使用し、SQLite は監視・トレードログの永続化に使用します。ペーパー運用時は paper_trading 用 SQLite を使って本番 DB と完全分離されます。
- OpenAI を使う機能は API キーを必要とし、API の失敗に備えたリトライとフェイルセーフ（スコアを 0 にフォールバック等）が実装されています。
- 本番環境（KABUSYS_ENV=live）の場合は、LINE 通知設定や kill flag の取り扱い等に注意してください（validate_config は本番用の注意点を警告します）。

----

何か特定のモジュールの詳細な使い方（例: ExecutionEngine の構成、OrderRepository API、AI モデルのプロンプト調整 など）を README に追記したい場合は、対象の機能を指定してください。必要に応じてコマンド例やユースケースを追加します。