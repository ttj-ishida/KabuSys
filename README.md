# KabuSys

KabuSys は日本株向けの自動売買・リサーチ基盤です。  
本リポジトリは以下の主要コンポーネントを含みます：

- Execution: 発注エンジン（本番 / ペーパートレード切替対応）
- Monitoring: システム状態・注文状況・リスクの監視と Kill Switch
- Portfolio: 銘柄選定・重み付け・ポジションサイズ計算
- Research: ファクター計算・特徴量探索（DuckDB を利用）
- AI: ニュースセンチメント（OpenAI）・市場レジーム判定
- Tools: ペーパートレード検証レポート等のユーティリティ
- Utils: ログ設定・プロセス優先度設定・設定読み込み補助 等

バージョン: 0.1.0

---

## 主な機能一覧

- 実取引 / ペーパートレード（KABUSYS_ENV により切替）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、データは `data/paper_trading.db` に保存（本番 DB と分離）
- モニタリング
  - CPU/メモリ/ディスク、Execution プロセスの生存確認、データ鮮度の監視
  - 滞留注文 / 約定価格異常 / ドローダウン監視
  - Kill Switch による自動停止（条件に応じて `data/kill.flag` を生成）
- ポートフォリオ構築
  - 候補選定、等重・スコア重み付け、セクター制約、ポジションサイズ計算（単元株丸め等）
- リサーチ
  - モメンタム/バリュー/ボラティリティ等のファクター計算（DuckDB）
  - 将来リターン計算、IC 計算、統計サマリ
- AI モジュール
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント解析 -> `ai_scores` へ保存
  - マクロニュース＋ETF MA200 を用いた市場レジーム判定
  - API レート制限 / 一時エラーに対するリトライ実装、レスポンスバリデーション
- 運用支援ツール
  - 対話式 .env 作成ウィザード（`python -m kabusys.config_setup`）
  - 設定検証 CLI（`python -m kabusys.validate_config`）
  - ペーパー検証レポート生成（`python -m kabusys.tools.paper_verification_report`）
- 一貫したログ出力（コンソール + 日次ローテートファイル）

---

## セットアップ手順（ローカル開発向け）

前提: Python 3.9+（プロジェクトの実行環境に合わせてください）

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 無ければ代表的な依存をインストール:
     - pip install duckdb psutil openai pyyaml
   - （必要に応じて他のライブラリを追加してください）

4. 環境変数の設定
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（`.env.example` を参考に）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN（J-Quants API）
     - KABU_API_PASSWORD（kabuステーション API）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 重要な設定例:
     - KABUSYS_ENV=development | paper_trading | live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB, デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB）
     - LOG_LEVEL（DEBUG/INFO/...）
     - KILL_FLAG_CLEAR_ON_START（本番での安全設定に注意）

5. 設定検証（起動前に推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は `--strict` を付ける

6. データディレクトリ等を作成（必要に応じて）
   - mkdir -p data logs

---

## 使い方（実行方法）

- ExecutionEngine（発注エンジン）起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト: `data/paper_trading.db`）へ記録
    - PID ファイル: `data/execution.pid`（Settings.pid_file_path）
    - 起動時に `data/stop_requested.flag` が存在すると起動せずに終了
    - 停止: `data/stop_requested.flag` を作成すると実行ループが検知して終了します。Monitoring 側からは `data/kill.flag` が書き込まれ Execution を停止させます。

- Monitoring（監視）起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒、デフォルト 60）で上書き可能
    - 監視は Settings.sqlite_path（monitoring DB）を利用（環境に依らず本番 sqlite_path を使用）
    - 停止: `data/stop_requested.flag` の存在でループを終了

- AI モジュール実行（プログラム的に）
  - ニュース採点:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - 注意: API キーは引数または環境変数 `OPENAI_API_KEY` を使用

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を付けると警告も失敗扱い

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH`

- ログ
  - デフォルト出力: コンソール（stdout）および `logs/<app_name>.log`（日次ローテート）
  - ログディレクトリは環境変数 `LOG_DIR` または引数 `log_dir` で変更可能

---

## 運用上のファイル・フラグ

- 停止フラグ
  - data/stop_requested.flag
    - Run スクリプト（monitoring / execution）はこのファイルの存在を見て安全に終了します（運用側が手動で停止したい場合に使用）
- Kill Switch フラグ
  - data/kill.flag
    - Monitoring の KillSwitch がトリガーした場合に作成され、ExecutionEngine に停止シグナルを送るのに使用されます
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動でクリアされますが、本番では 0 を推奨
- PID ファイル
  - data/execution.pid
    - ExecutionEngine が起動中の PID を記録

---

## ディレクトリ構成（主なファイル）

（リポジトリの `src/kabusys` 配下を抜粋）

- kabusys/
  - __init__.py
  - config.py
    - .env 自動読み込み、Settings クラス（環境変数ラッパ）
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - utils/
    - logging_setup.py — ログ設定（コンソール + 日次ローテート）
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - execution/
    - execution_engine.py, order_manager.py, order_repository.py, risk_manager.py, reconciler.py, broker_factory.py など
    - （発注ロジック、ブローカーラッパー、リスク管理）
  - monitoring/
    - monitoring_db.py — 監視用 SQLite 操作用（テーブル作成・ログ永続化）
    - system_monitor.py, trade_monitor.py, risk_monitor.py, kill_switch.py, monitoring_engine.py, alert_manager.py など
  - portfolio/
    - portfolio_builder.py, position_sizing.py, risk_adjustment.py
    - （候補選定・重み・サイズ計算・セクター制限）
  - research/
    - factor_research.py, feature_exploration.py
    - （DuckDB を使ったファクター・将来リターン・IC・統計）
  - ai/
    - news_nlp.py — ニュースセンチメント（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
  - data/ （実行時に使用する SQLite / DuckDB / フラグ / PID / etc.）
  - logs/ （デフォルトログ出力先）
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成

---

## 環境変数（主なもの）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN: J-Quants API
- KABU_API_PASSWORD: kabuステーション API
- OPENAI_API_KEY: OpenAI API（AI 機能）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（例: INFO）
- LOG_DIR: ログ出力ディレクトリ（デフォルト: logs）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定挙動（instant|partial|never|reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1"=有効）

---

## 注意事項・運用上のヒント

- 本番環境（KABUSYS_ENV=live）では `LINE_CHANNEL_ACCESS_TOKEN` / `LINE_USER_ID` を設定し、アラート通知を有効にすることを推奨します。
- `KILL_FLAG_CLEAR_ON_START=1` は便利だが本番では危険です（自動クリアで Kill Switch が無効化される可能性があるため、0 を推奨）。
- Logging はデフォルトで `logs/<app>.log` に日次ローテートで出力されます。ディスク容量に注意してください。
- AI 機能は OpenAI API を使用します。API キーの管理・コスト・レート制限に注意してください。エラー時にはフォールバックが働く設計です。
- DuckDB / SQLite のパスは設定可能です。運用上はバックアップ・パーミッション管理を行ってください。
- アプリケーションはファイルフラグ（`data/stop_requested.flag` / `data/kill.flag`）を用いた制御を行います。これらは運用手順として活用できます。

---

必要であれば README に環境変数のサンプル `.env.example` の内容や、systemd / Supervisor / Docker Compose の起動例（unit ファイルや compose サンプル）を追加します。どの形式が必要か教えてください。