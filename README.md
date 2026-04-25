# KabuSys

日本株自動売買システムのコアライブラリ群。本リポジトリはトレード実行エンジン、監視、ポートフォリオ構築、研究用ファクター計算、AI ベースのニュース分析等を含むモジュール群を提供します。

## 概要

KabuSys は以下の目的を持つモジュール群を提供します。

- 実行エンジン（ExecutionEngine）：ブローカークライアントを通じて発注・注文管理を行う
- 監視（Monitoring）：システム稼働・注文状況・リスク（ドローダウン・ポジション上限）を監視し、Kill Switch を発動できる
- ポートフォリオ構築：候補選定、重み付け、ポジションサイズ決定、セクターキャップ調整
- 研究（Research）：DuckDB を用いたファクター計算、将来リターン・IC 計算など
- AI（OpenAI）連携：ニュースのセンチメント計算、マクロセンチメントによる市場レジーム判定
- 各種ユーティリティ：設定読み込み、ログ設定、プロセス優先度設定など

この README はローカルでのセットアップと基本的な使い方を説明します。

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - 環境変数 `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading DB に完全分離して記録
  - PID ファイル管理、外部停止フラグ（data/stop_requested.flag）監視
- 監視ループ起動スクリプト（run_monitoring.py）
  - システムリソース（CPU/メモリ/ディスク）やプロセス状態、データ鮮度を定期チェック
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）
- 設定ウィザード（config_setup.py）
  - 対話式で `.env` を生成 / 更新
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本チェック、警告 / エラー表示
- Paper Trading 検証レポート（tools/paper_verification_report.py）
  - ペーパートレード DB を解析して稼働率や注文成功率、レイテンシ等のレポートを出力
- ポートフォリオ関連（kabusys.portfolio）
  - 候補選定、等配分／スコア配分、ポジションサイズ計算、セクター上限・レジーム乗数
- AI モジュール（kabusys.ai）
  - news_nlp: OpenAI を用いたニュースセンチメント集計と ai_scores への書き込み
  - regime_detector: ETF とマクロニュースを合成して市場レジーム判定
- 監視永続化（kabusys.monitoring.monitoring_db）
  - SQLite に監視ログ、注文ログ、ポジション、リスクログ、ダッシュボードを格納
- ユーティリティ（kabusys.utils）
  - ログ設定（ファイル + コンソール、日次ローテート）
  - プロセス優先度 / CPU affinity 設定

---

## 前提・依存

- Python 3.10+（ソースの型注釈に | 演算子が使用されているため）
- 必要パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config YAML の検証を行う場合）
- SQLite（標準ライブラリ）
- ネットワーク接続（OpenAI を使う場合）

インストール例:
pip install duckdb psutil openai pyyaml

（プロジェクトに requirements.txt があればそれを使用してください）

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローンして作業ディレクトリへ移動

2. Python 仮想環境を作成・有効化し依存をインストール
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
   - pip install duckdb psutil openai pyyaml

3. 対話式で .env を作成（推奨）
   - python -m kabusys.config_setup
   - ウィザードが .env を生成します（`.env` は絶対に Git にコミットしないでください）

   主要な環境変数（代表例）:
   - JQUANTS_REFRESH_TOKEN（必須）
   - KABU_API_PASSWORD（必須）
   - KABUSYS_ENV（development / paper_trading / live。デフォルト development）
   - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
   - SQLITE_PATH（デフォルト data/monitoring.db）
   - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
   - OPENAI_API_KEY（AI モジュール利用時に必須）
   - LOG_LEVEL（DEBUG/INFO/...）

4. 設定の検証（起動前チェック）
   - python -m kabusys.validate_config
   - --strict を付けると警告もエラー扱い（exit 1）

5. データ / ログフォルダを作成（必要に応じて）
   - mkdir -p data logs

6. 必要であれば DuckDB / SQLite のテーブル初期化は実行スクリプトが自動で行います（初回接続時に作成されます）

---

## 使い方

### 実行エンジンの起動

- 本番／ペーパー問わず設定に応じた DB に接続して実行エンジンを起動します。

起動:
python -m kabusys.run_execution

挙動のポイント:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 専用の SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）に記録します。本番 DB と分離されます。
- 起動時に data/stop_requested.flag が既に存在する場合は起動せず終了します。
- 実行中に data/stop_requested.flag が作成されるとエンジンは停止します。
- 実行時に PID ファイル（デフォルト data/execution.pid）を作成します。

停止方法:
- data/stop_requested.flag を作成する（プロセス監視側や手動で）。監視ループが検知して安全に停止します。
- Kill Switch（監視コンポーネントが条件を満たした場合、data/kill.flag を出力）でも停止されます。

### 監視ループの起動

起動:
python -m kabusys.run_monitoring

主な設定:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を指定可能。デフォルト 60 秒。
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 監視は実行環境にかかわらず本番用の sqlite_path を参照して監視テーブルを初期化します（init_monitoring_db）。
- 停止フラグ: run_monitoring はプロジェクトルート/data/stop_requested.flag を監視してループを抜けます。

監視内容:
- SystemMonitor: CPU/メモリ/ディスク/プロセス状態/データ鮮度
- TradeMonitor: 注文の滞留や約定異常検出（TradeCheckResult）
- RiskMonitor: ドローダウン・ポジション上限
- KillSwitch: リスク条件に応じて data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送信

### Paper Trading 検証レポート生成

Paper Trading の DB を解析して検証レポートを出力します。

実行例:
python -m kabusys.tools.paper_verification_report
追加オプション:
--from YYYY-MM-DD --to YYYY-MM-DD --db PATH

デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）

### AI（OpenAI）モジュール

- ニューススコアリング:
  - 関数: kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
  - 必要: OpenAI API キー（api_key 引数または環境変数 OPENAI_API_KEY）
  - raw_news テーブルを読み、ai_scores テーブルにスコアを書き込みます（部分失敗時の冪等性を考慮した実装）

- レジーム判定:
  - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - ETF（1321）の MA200 乖離とマクロニュースセンチメントを合成して market_regime テーブルに書き込みます

注意:
- OpenAI 呼び出しは API レート制限や一時エラーを考慮してリトライ実装が組み込まれています。ただし API キーの設定が必要です。

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV: execution モード (development, paper_trading, live)
- JQUANTS_REFRESH_TOKEN: J-Quants API
- KABU_API_PASSWORD: kabuステーション API パスワード
- KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
- DUCKDB_PATH: デフォルト data/kabusys.duckdb
- SQLITE_PATH: 監視 DB（data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB
- OPENAI_API_KEY: OpenAI 利用時に必要
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/...）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=クリア、0=そのまま）

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                    — 環境変数/.env の読み込みと Settings クラス
- config_setup.py              — .env 対話式ウィザード
- validate_config.py           — 起動前設定検証 CLI
- run_execution.py             — ExecutionEngine 起動スクリプト
- run_monitoring.py            — Monitoring ポーリングループ起動スクリプト

subpackages:
- ai/
  - news_nlp.py                — ニュースセンチメントスコアリング
  - regime_detector.py        — 市場レジーム判定
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- monitoring/
  - monitoring_db.py           — SQLite 永続化層
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py
- utils/
  - logging_setup.py           — ログ設定ユーティリティ
  - process_priority.py        — プロセス優先度 / CPU affinity
- tools/
  - paper_verification_report.py

補足:
- data/ ディレクトリ: デフォルトの SQLite / PID / flag ファイルを格納
- logs/ ディレクトリ: ログファイル（app_name によるファイル名）

---

## 運用時の注意・トラブルシューティング

- .env 自動読み込み:
  - config.py はプロジェクトルート（.git または pyproject.toml があるディレクトリ）を探索して `.env` / `.env.local` を自動読み込みします。
  - 自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- 権限・優先度設定:
  - set_process_priority は OS により権限が必要な場合があります（psutil の AccessDenied 警告）。失敗した場合は警告を出して継続します。

- ログディレクトリ作成失敗:
  - 権限などで logs/ の作成に失敗した場合、ファイルハンドラはスキップされコンソール出力のみになります。警告が出力されます。

- OpenAI 利用:
  - API キーが未設定だと例外になります。AI 関連処理は必須ではありませんが、score_news / score_regime を使う場合は設定してください。

- DB 互換性:
  - monitoring_db.init_monitoring_db はマイグレーション処理（列の追加など）を含み、冪等にテーブルを初期化します。

---

## 例: 開発用の簡単な起動フロー

1. .env を作成:
   - python -m kabusys.config_setup

2. 設定検証:
   - python -m kabusys.validate_config

3. 監視プロセス起動（別ターミナル）:
   - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring

4. 実行エンジン起動（別ターミナル）:
   - python -m kabusys.run_execution

5. ペーパートレード検証レポート:
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はコードベースの主要な用途と運用上のポイントをまとめたものです。詳細は各モジュールの docstring を参照してください（kabusys/*.py および各サブモジュールに詳細コメントが記載されています）。必要であれば、特定モジュールの使い方（API 例やパラメータ説明）を別途作成します。