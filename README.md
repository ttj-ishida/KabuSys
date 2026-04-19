# KabuSys

日本株向け自動売買システム（ライブラリ / 実行スクリプト群）

※ この README はリポジトリ内のモジュール実装に基づいて作成しています。

## プロジェクト概要
KabuSys は日本株の自動売買・リサーチ・監視を行うためのモジュール群です。  
主な要素は次のとおりです。

- ExecutionEngine（発注エンジン） — 本番 / ペーパートレードで動作
- Monitoring（システム・取引・リスク監視） — ポーリングループで継続監視、Kill Switch を提供
- Portfolio（銘柄選定・重み付け・ポジションサイズ計算） — ポートフォリオ構築ロジック
- Research（ファクター計算・特徴量探索） — DuckDB を用いたオンメモリ／SQLベースの計算
- AI（ニュースセンチメント / レジーム判定） — OpenAI を用いたニュース解析（オプション）
- ユーティリティ（ログ設定、プロセス優先度等）
- CLI ツール（.env ウィザード、設定検証、Paper Trading 検証レポート等）

## 機能一覧
- 実行環境切替（development / paper_trading / live）
  - paper_trading では MockBroker を使用し、ペーパートレード用 DB に記録（本番 DB と分離）
- ExecutionEngine：発注管理・リスク管理・注文リコンサイル
- Monitoring：
  - システム稼働（CPU / メモリ / ディスク）とプロセス生存監視
  - データ鮮度チェック（DuckDB の prices_daily 等参照）
  - 取引ログ監視（滞留注文、約定異常等）
  - リスク監視（ドローダウン・ポジション上限）
  - Kill Switch：条件に応じてフラグを書き込み ExecutionEngine を停止
- Portfolio：
  - 候補選定・等重・スコア加重配分・リスクベースのポジションサイズ計算
  - セクター上限適用・レジーム乗数
- Research：
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン計算／IC（Information Coefficient）や統計サマリー
- AI：
  - ニュースを LLM でスコアリングし ai_scores テーブルへ保存（OpenAI 必須）
  - マクロニュースと MA200 を組み合わせた市場レジーム判定
- ツール：
  - .env 対話ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成ツール（tools/paper_verification_report）

## 要件（推奨）
- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（設定ファイル検証時にあると便利）
- （pip でのインストールを想定。実際の requirements.txt がある場合はそちらを使用してください）

## セットアップ手順（ローカル開発向けの基本手順）
1. リポジトリをクローン / チェックアウト
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 依存関係をインストール
   - pip install -r requirements.txt （無ければプロジェクトで必要なライブラリを個別に pip install）
4. 環境変数設定
   - プロジェクトルートに .env を作成するか、ウィザードを使う:
     - python -m kabusys.config_setup
   - 自動ロード:
     - デフォルトでプロジェクトルートの `.env` を自動で読み込みます（.env.local も上書き読み込み）。
     - 自動読み込みを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - 警告も厳格に扱う場合は --strict を付けます。

## 主要環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）: J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD（必須）: kabuステーション API パスワード
- KABUSYS_ENV（任意）: 実行環境。development / paper_trading / live（デフォルト: development）
- OPENAI_API_KEY: OpenAI を用いる AI 機能で必要
- DUCKDB_PATH（任意）: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（任意）: 監視 DB（monitoring）SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（任意）: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE（任意）: ペーパートレード時の約定挙動（instant|partial|never|reject、デフォルト: instant）
- LOG_LEVEL（任意）: ログレベル（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- LOG_DIR（任意）: ログ保存先ディレクトリ（デフォルト: logs/）
- MONITOR_POLL_INTERVAL（任意）: monitoring ループのポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_PATH / PID_FILE_PATH（任意）: デフォルトは data/ 以下

（各プロパティのデフォルトは `kabusys.config.Settings` を参照してください）

## 実行方法（代表的なコマンド）
- 環境作成・設定が済んでいる前提で：

1. ExecutionEngine（発注エンジン）起動
   - 本番 / ペーパートレードは KABUSYS_ENV に依存
   - 例（ペーパートレード）:
     - export KABUSYS_ENV=paper_trading
     - python -m kabusys.run_execution
   - ペーパートレードは MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ記録します。
   - 実行中は data/execution.pid に PID が書き込まれます。data/stop_requested.flag があれば起動は行わない・停止をトリガーします。

2. Monitoring（監視ループ）起動
   - MONITOR_POLL_INTERVAL（秒）でポーリング（デフォルト 60）
   - 例:
     - export MONITOR_POLL_INTERVAL=30
     - python -m kabusys.run_monitoring
   - Monitoring は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを書き込みます。
   - 停止フラグファイル data/stop_requested.flag が存在するとループを終了します。

3. 環境設定ウィザード（.env 作成）
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config
   - python -m kabusys.validate_config --strict

5. Paper Trading 検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

## 停止 / Kill Switch / フラグの扱い
- stop_requested.flag（data/stop_requested.flag）
  - run_monitoring/run_execution はこのファイルの存在を監視してプロセスを安全に終了します（運用側からの「やめて」指示用）。
- kill.flag（Settings.kill_flag_path、デフォルト data/kill.flag）
  - KillSwitch がリスクトリガー（例: ドローダウン超過、ポジション上限超過）を検出した場合に作成されます。
  - ExecutionEngine は起動時に kill.flag の存在を確認し、存在する場合は起動を行わない想定です。
  - KillSwitch は冪等にフラグを書き、既に存在する場合は上書きしません。
- PID ファイル（data/execution.pid など）
  - ExecutionEngine が起動時に書き込みます。stale PID の検出やクリーンアップロジックが含まれます。

## ログ
- 共通ログは kabusys.utils.logging_setup.setup_logging によって設定されます。
- デフォルト:
  - コンソール出力（stdout）
  - 日次ローテーションファイル: logs/<app_name>.log（30日保持）
- ログレベルは引数 / 環境変数 LOG_LEVEL で指定可能。

## ディレクトリ構成（主なファイル・モジュール）
プロジェクトルート（抜粋）
- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py            — ニュースセンチメント取得（OpenAI）
    - regime_detector.py     — マクロレジーム判定（OpenAI）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化層（監視用テーブル）
    - monitoring_engine.py   — 各 Monitor の統合
    - system_monitor.py      — システム / データ鮮度監視
    - trade_monitor.py       — （取引監視。実装参照）
    - risk_monitor.py        — ドローダウン / ポジション上限監視
    - kill_switch.py         — Kill Switch ロジック
    - alert_manager.py       — （通知管理：LINE 等。実装参照）
  - execution/
    - execution_engine.py    — ExecutionEngine 本体（実装参照）
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
- config/
  - （system_config.yaml 等の設定テンプレート / 実体）
- data/
  - （デフォルトの DB / flag / pid 保存場所）
- logs/
  - （ログファイル出力先）

## 運用上の注意
- 本番（KABUSYS_ENV=live）では .env に機密情報を含めたファイルを決してバージョン管理に入れないでください。
- 設定検証ツール（validate_config）で本番設定の警告を確認してください（LINE 通知設定や kill flag の扱い等）。
- AI 機能（news_nlp, regime_detector）は OpenAI API を使用します。APIキー（OPENAI_API_KEY）とコスト管理に注意してください。
- Monitoring は本番 sqlite_path を参照してログを残します。paper_trading は専用 DB を使用し本番データと分離します。
- process priority / cpu affinity の設定は OS により動作が制限される場合があります。権限不足時は警告を出して続行します。

---

必要があれば、README に実際の requirements.txt に基づく依存関係例やデプロイ手順（systemd ユニット例、Dockerfile など）を追加できます。どの情報を優先的に追加しますか？