# KabuSys

日本株自動売買システムの軽量実装。  
ポートフォリオ構築、発注エンジン、監視、リサーチ／ファクター計算、AI を使ったニュース NLP などを含むモジュール群で構成されています。

以下はこのリポジトリに含まれる主要な概要、機能、セットアップ方法、実行方法、およびディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群を提供します。主な役割は次の通りです。

- 発注（ExecutionEngine）とブローカークライアントの抽象化
- 監視（Monitoring）: システムリソース、データ鮮度、発注履歴やリスクを監視し、Kill Switch による停止を可能にする
- ポートフォリオ構築（選定・重み付け・ポジションサイズ計算）
- リサーチ（DuckDB を使ったファクター計算、IC 計算など）
- AI（OpenAI を用いたニュースのセンチメント評価、レジーム判定）
- ツール（ペーパートレード結果の検証レポートなど）
- 設定ユーティリティ（.env ウィザード、設定検証）

設計方針としては、「実行スクリプトから共通ユーティリティを使用して安全に運用できること」「DuckDB/SQLite を用いた分析・永続化」「本番とペーパートレードを分離」などが念頭に置かれています。

---

## 機能一覧

- 設定管理
  - .env の自動ロード（プロジェクトルート検出）と Settings クラス経由の参照
  - 対話式設定ウィザード（kabusys.config_setup）
  - 起動前の設定検証ツール（kabusys.validate_config）

- 実行エンジン
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ペーパートレード時は MockBrokerClient を使用し、data/paper_trading.db に記録して本番 DB と分離

- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログの永続化（SQLite：monitoring_db）
  - Kill Switch による安全停止（data/kill.flag）
  - run_monitoring.py によるポーリングループ起動（MONITOR_POLL_INTERVAL で間隔制御）

- ポートフォリオ構築
  - 候補選定、等重／スコア重み計算（portfolio_builder）
  - セクター上限調整、レジーム乗数（risk_adjustment）
  - ポジションサイズ計算（position_sizing）

- リサーチ
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC（Spearman）計算、統計サマリー

- AI 機能（OpenAI）
  - ニュース NLP による銘柄センチメント算出（news_nlp）
  - マクロ＋ETF MA による市場レジーム判定（regime_detector）

- ユーティリティ
  - ロギング設定ユーティリティ（logs 日次ローテート）
  - プロセス優先度 / CPU affinity 設定ユーティリティ

- ツール
  - ペーパートレード検証レポート生成（tools/paper_verification_report.py）

---

## セットアップ手順

前提:
- Python 3.9+（ソースが typing | union などを使うため推奨）
- system パッケージ: duckdb, psutil, openai, PyYAML（YAML 検証を行う場合）

1. リポジトリをクローンして作業ディレクトリへ移動
   ```
   git clone <リポジトリURL>
   cd <repo>
   ```

2. 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .\.venv\Scripts\activate   # Windows
   ```

3. 依存パッケージインストール（pip）
   ```
   pip install duckdb psutil openai PyYAML
   ```
   - もし requirements.txt があればそれを使ってください。
   - OpenAI を使わないのであれば openai は不要です（AI 機能はオプション）。

4. .env の作成
   - 対話的に作る:
     ```
     python -m kabusys.config_setup
     ```
     ウィザードに従って必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD など）を入力してください。
   - 手動で作る場合は .env.example を参考に .env を作成してください（リポジトリにない場合は config_setup の出力を参照）。

5. 設定検証（任意だが推奨）
   ```
   python -m kabusys.validate_config
   ```
   警告もエラー扱いにしたい場合は --strict を付けます。

6. データディレクトリの準備
   - デフォルトでは data/ 内に SQLite / PID / フラグが作られます。必要に応じてパスを .env で上書きしてください（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH など）。

注意:
- 本番運用（KABUSYS_ENV=live）時は .env の値を慎重に管理してください（.env を Git へコミットしない）。

---

## 必須 / 主要な環境変数

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）

主要（任意・デフォルトあり）:
- KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を利用する場合の API キー
- PAPER_FILL_MODE — ペーパートレード時の約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
- その他 monitoring/risk 等の閾値は Settings 経由で指定可能（.env）

---

## 使い方（主要コマンド）

- 環境ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動（SystemMonitor をポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視ループはプロジェクトの data/stop_requested.flag（stop フラグ）を検知すると終了します。
  - Monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番 sqlite_path）を使用します（意図的）。

- 実行エンジン起動（ExecutionEngine）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 起動時に data/stop_requested.flag があれば起動せず終了します。実行中は data/stop_requested.flag が書かれると安全に停止を試みます。
  - PID ファイル: data/execution.pid（デフォルト。Settings.pid_file_path で変更可能）

- ペーパートレード検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは環境変数 `PAPER_TRADING_SQLITE_PATH` または `--db` で指定可能。

- AI 機能（プログラム的に）
  - ニュース NLP（銘柄センチメント）:
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key=...)
  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key=...)

  これらは OpenAI API キー（OPENAI_API_KEY）を要求します。

ログ:
- ログは既定で logs/<app_name>.log に日次ローテートで出力されます。コンソール（stdout）にも出力されます。

停止 / Kill Switch:
- Kill Switch: data/kill.flag を書くことで ExecutionEngine に停止を指示できます（KillSwitch モジュール）。
- 監視停止フラグ: data/stop_requested.flag が作られると run_monitoring / run_execution のループを抜けます。

---

## ディレクトリ構成（抜粋）

以下は主要なファイルとディレクトリの概観です（src/kabusys 以下）。

- src/kabusys/
  - __init__.py  — パッケージ定義、__version__
  - config.py  — 環境変数読み込み・Settings クラス
  - config_setup.py  — .env 対話ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor 起動スクリプト

  - ai/
    - news_nlp.py — ニュース NLP（OpenAI）による銘柄スコアリング
    - regime_detector.py — レジーム判定（MA + マクロセンチメント）

  - monitoring/
    - monitoring_db.py — SQLite による監視ログ永続化
    - system_monitor.py — システム / データ鮮度監視
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - trade_monitor.py — 発注ログ監視（ファイル内で実装あり）
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - kill_switch.py — kill.flag の扱い
    - alert_manager.py — （アラート送信のラッパー、実装ファイルあり）

  - execution/
    - execution_engine.py — ExecutionEngine 本体
    - broker_factory.py — BrokerClient の生成（本番 / Mock の切替）
    - order_manager.py, order_repository.py, reconciler.py, risk_manager.py — 発注管理周り

  - portfolio/
    - portfolio_builder.py — 候補選定・重み付け
    - position_sizing.py — 発注株数決定
    - risk_adjustment.py — セクターキャップ・レジーム乗数

  - research/
    - factor_research.py — ファクター計算（momentum/value/volatility）
    - feature_exploration.py — IC / 将来リターン / 統計サマリー

  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

  - utils/
    - logging_setup.py — ログ設定ユーティリティ（Stream + TimedRotatingFile）
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

データ・ログ関連（プロジェクトルート）:
- data/ — デフォルト SQLite / PID / フラグ等を格納
  - monitoring.db (デフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH)
  - execution.pid
  - kill.flag
  - stop_requested.flag
- logs/ — ログファイル（app_name に応じて daily ローテート）

--- 

## 運用上の注意

- 本番環境（KABUSYS_ENV=live）の場合、Kill Switch（kill.flag）や KILL_FLAG_CLEAR_ON_START の設定に注意してください。validate_config が本番向けの追加チェックを行います。
- run_monitoring は監視 DB に *本番の sqlite_path* を使用します（KABUSYS_ENV に依存しない）。意図的に設計されています。
- OpenAI を利用する機能は API の課金とレイテンシ、レスポンスの堅牢性（リトライロジック）を考慮のうえ運用してください。API キーは安全に保管してください（.env は Git 管理外に）。
- DuckDB/SQLite のパスは .env で上書き可能です。分析用途の DuckDB は別ファイルにしておくことを推奨します。

---

必要があれば README を英語版に翻訳したり、運用手順（systemd / Supervisor / Docker / コンテナ化）やデプロイ手順、API の詳細ドキュメントを追加します。どの部分を詳しく書けばよいか指示してください。