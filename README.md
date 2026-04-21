# KabuSys

日本株向けの自動売買システム用モジュール群。ポートフォリオ構築、ポジションサイジング、リスク制御、監視、ペーパートレード検証、LLM ベースのニュースセンチメント／レジーム判定などを含みます。

以下はリポジトリ内の主要機能、セットアップ・実行手順、使い方、ディレクトリ構成の概要です。

注意: この README はソースコード（`src/kabusys`）の実装に基づいて作成しています。

## プロジェクト概要
- 銘柄選定、重み付け、株数決定などのポートフォリオ構築ロジック（純関数群）。
- ExecutionEngine を介した発注処理群（本番 / ペーパートレード分離）。
- 監視コンポーネント（システム状態、注文ログ、リスク監視、Kill Switch、アラート管理）。
- Research / 特徴量計算、ファクター研究ユーティリティ（DuckDB を利用）。
- AI モジュール: ニュース NLP（OpenAI を用いたセンチメント）、市場レジーム判定。
- 運用支援ツール: .env 作成ウィザード、設定検証 CLI、ペーパートレード検証レポート生成スクリプト。

## 主な機能一覧
- ポートフォリオ構築
  - 銘柄選定（score / rank）
  - 等配分 / スコア加重配分
  - ポジションサイズ計算（リスクベース、ロット丸め、aggregate cap）
  - セクターキャップ適用、レジームによる投下資金乗数
- Execution
  - 本番 / ペーパートレードの分離（`KABUSYS_ENV=paper_trading` 時は専用 DB と MockBroker）
  - RiskManager、OrderManager、Reconciler 等の連携
- 監視
  - SystemMonitor（CPU / メモリ / ディスク、データ鮮度、Execution プロセス検出）
  - TradeMonitor（滞留注文、約定異常など）
  - RiskMonitor（ドローダウン、ポジション上限監視）
  - KillSwitch（フラグファイルを書き込むことで Execution を停止）
  - MonitoringEngine（複数モニタのポーリング、アラート発火）
- AI
  - news_nlp: raw_news を集約して OpenAI に送信し銘柄ごとのスコアを `ai_scores` に書き込む
  - regime_detector: ETF（1321）の MA200 乖離とマクロニュースでレジーム判定し `market_regime` に書き込む
- ユーティリティ
  - .env 対話式ウィザード（`config_setup.py`）
  - 設定検証 CLI（`validate_config.py`）
  - ペーパートレード検証レポート（`tools/paper_verification_report.py`）

## 必要条件 / 依存ライブラリ
（実行環境によって追加やバージョン管理が必要です）
- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（`validate_config.py` の YAML 検証を有効にする場合）
- その他標準ライブラリ（sqlite3 等）

依存はプロジェクトに `requirements.txt` がある想定で `pip install -r requirements.txt`、あるいは個別に `pip install duckdb psutil openai pyyaml` のようにインストールしてください。

## セットアップ手順（基本）
1. リポジトリをクローンし、プロジェクトルートに移動します（`src` の上がプロジェクトルート）。
2. Python 環境を作成・有効化（venv / pyenv など）。
3. 依存パッケージをインストールします。
   - 例: `pip install duckdb psutil openai pyyaml`
4. 環境変数設定（.env）
   - 対話式で `.env` を作成するには:
     - `python -m kabusys.config_setup`
   - 必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（`development` / `paper_trading` / `live`、デフォルト: `development`）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - デフォルト DB パス:
     - DuckDB: `data/kabusys.duckdb`
     - SQLite (monitoring): `data/monitoring.db`
     - Paper trading SQLite (paper): `data/paper_trading.db`
5. 設定検証:
   - `python -m kabusys.validate_config`（必要に応じて `--strict` を付けて警告を失敗扱いにできます）
6. データ・ログディレクトリの確認
   - ログはデフォルト `logs/` に出力されます（`LOG_DIR` で変更可）。
   - スクリプトは必要に応じてディレクトリを作成しますが、権限等に注意してください。

## 使い方（主要スクリプト / モジュール）
- 実行エンジン（ExecutionEngine）を起動
  - 本番 / 開発 / ペーパーは `KABUSYS_ENV` で切替
  - ペーパートレードでは MockBroker を使い、専用 DB（`PAPER_TRADING_SQLITE_PATH`）へ記録
  - 起動:
    - 例（デフォルト環境）:
      - `python -m kabusys.run_execution`
    - 例（ペーパートレード）:
      - `KABUSYS_ENV=paper_trading python -m kabusys.run_execution`
  - 実行中の停止方法:
    - 制御用のフラグファイル `data/stop_requested.flag` が存在すると起動を抑止/実行中のスレッドが停止します。
    - KillSwitch（`data/kill.flag`）は Kill 評価結果によって自動で書き込まれ、Execution 側での停止トリガーになります。

- 監視ループ（Monitoring）
  - 起動:
    - `python -m kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト: 60）
  - 監視は `Settings` の `sqlite_path`（monitoring.db）を使って永続化します（monitoring は環境にかかわらず本番 sqlite_path を使用する点に注意）。

- .env 作成ウィザード
  - `python -m kabusys.config_setup`
  - 対話的に `.env` を生成します（機密値はマスク表示）。

- 設定検証
  - `python -m kabusys.validate_config`
  - `--strict` を使うと警告もエラー扱いになり exit code=1 を返します。

- ペーパートレード検証レポート
  - `python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]`
  - DB パスは `--db` または環境変数 `PAPER_TRADING_SQLITE_PATH`。デフォルトは `data/paper_trading.db`。
  - 出力指標: 稼働率 (uptime)、注文成功率（fill rate）、送信率、レイテンシ (avg/max/P95)、リスク却下数 など。閾値を満たすか PASS/FAIL 判定を行います。

- AI モジュール（プログラムから呼ぶ）
  - ニューススコアリング:
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
    - `conn` は DuckDB 接続、`target_date` は日時、`api_key` が None の場合は環境変数 `OPENAI_API_KEY` を参照します。
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

  注意: OpenAI API を使う処理は料金・レート制限があります。`OPENAI_API_KEY` を設定してください。API 呼び出しはリトライやバックオフを実装していますが、キーが未設定だと例外を投げます。

## 主要環境変数（抜粋）
- KABUSYS_ENV: execution 環境（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API のパスワード（必須）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- LOG_DIR: ログ保存先（デフォルト: logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能用）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: Execution 起動時に kill.flag を自動クリアするか（'0'/'1'）

例（最小 .env の断片）:
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO

（`.env` の生成には `python -m kabusys.config_setup` を推奨）

## ログ・ファイル・フラグ
- ログ: デフォルト `logs/<app_name>.log`（`setup_logging` により stdout と日次ローテートのファイル出力が設定されます）
- PID / stop フラグ / kill フラグ:
  - Execution PID: `data/execution.pid`（Settings.pid_file_path で変更可）
  - 停止要求（外部からの停止）: `data/stop_requested.flag`（両 run スクリプトでチェック）
  - Kill Switch のトリガ: `data/kill.flag`（KillSwitch が書き込む）

## 注意事項 / 運用上のポイント
- Monitoring は環境にかかわらず `Settings.sqlite_path`（本番監視 DB）を使用します。テストやペーパートレードの分離が必要な場合は設定を確認してください。
- `KABUSYS_ENV=paper_trading` 時は発注は MockBroker に記録され、paper DB（`PAPER_TRADING_SQLITE_PATH`）を使用します。本番 DB と完全分離されています。
- OpenAI を用いる機能はネットワーク/料金の影響を受けます。API キーとコスト管理に注意してください。API 呼び出しはリトライ処理を含みますが、失敗時はフェイルセーフ（0 でフォールバックする等）を行う箇所があります。
- ログディレクトリの作成に失敗した場合はファイル出力をスキップしてコンソール出力のみになります。
- `validate_config.py` を使い起動前に必須環境変数やファイルパス等をチェックすることを推奨します。

## ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / 設定管理（自動 .env ロード等）
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - portfolio/
    - portfolio_builder.py — 銘柄選定・重み計算
    - risk_adjustment.py — セクターキャップ・レジーム乗数
    - position_sizing.py — 株数決定・aggregate cap・ロット丸め
    - __init__.py
  - execution/ (発注エンジン関連: BrokerFactory, ExecutionEngine, OrderManager等) — 実装ファイル群（省略）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文/約定監視（実装ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限チェック
    - kill_switch.py — kill.flag 書き込みロジック
    - monitoring_engine.py — 複数監視を統合してポーリング
    - alert_manager.py — アラート通知（LINE 等、実装ファイルあり）
  - data/ (runtime に生成されることが期待されるディレクトリ)
  - logs/ (デフォルトログ出力先)
  - ai/
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + 指標）
    - __init__.py
  - research/
    - factor_research.py — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
    - __init__.py
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
    - __init__.py

（上記は主要ファイルとモジュールの抜粋です。細かい実装ファイルはリポジトリを参照してください。）

## 開発・拡張のヒント
- DuckDB を用いたデータ処理や Research モジュールは副作用を持たない設計（関数が接続を受け取る）になっているため、ユニットテストやオフライン解析が行いやすいです。
- AI モジュールはレスポンスのバリデーションやリトライ制御を含んでおり、テストのために `_call_openai_api` をモックする設計になっています。
- `.env` の自動ロードはプロジェクトルート（.git 或いは pyproject.toml）を基準に行われます。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

必要であれば、README に含める具体的な `.env.example`、systemd / Supervisor 用のサンプルユニット、実行シーケンス図、よくあるトラブルシュート（ログ確認ポイント、権限問題、DB マイグレーションなど）も追記できます。どの情報を詳しく書き加えたいか教えてください。