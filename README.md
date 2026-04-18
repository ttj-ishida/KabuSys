# KabuSys — 日本株自動売買システム

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリ群です。戦略の研究用モジュール、ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）および補助ツールを含みます。

README は主に開発者・運用担当者向けに、プロジェクト概要、機能一覧、セットアップ方法、使い方、ディレクトリ構成をまとめています。

## プロジェクト概要
- 戦略研究（DuckDB を用いたファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイジング）
- ExecutionEngine（ブローカークライアント経由の注文管理、ペーパートレード分離）
- 監視 (SystemMonitor / TradeMonitor / RiskMonitor) と Kill Switch（リスク発生時に発注エンジン停止）
- AI モジュール（ニュース NLP によるセンチメント評価、レジーム判定）
- 運用用 CLI ツール（.env ウィザード、設定検証、Paper Trading 検証レポート生成）

## 主な機能一覧
- 環境設定ウィザード（`.env` の対話的生成）: kabusys.config_setup
- 設定検証 CLI（環境変数・config/*.yaml のチェック）: kabusys.validate_config
- ExecutionEngine 起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用、paper_trading 用 SQLite に記録
  - 実行中は PID ファイルを書き出し、data/stop_requested.flag で停止制御
- Monitoring 起動スクリプト: run_monitoring.py
  - SystemMonitor 等を定期ポーリングして監視ログを保存、Kill Switch 評価を行う
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
- 監視永続層（SQLite）: monitoring_db (system_status, trade_logs, positions, risk_logs, dashboard)
- Risk モニタ、Kill Switch（data/kill.flag に理由を書き込み ExecutionEngine を停止）
- ロギングユーティリティ（コンソール + 日次ローテーションファイル）
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil ベース）
- Research モジュール
  - factor_research: モメンタム・ボラティリティ・バリュー等の計算（DuckDB 上で SQL 実行）
  - feature_exploration: 将来リターン、IC、統計サマリー等
- Portfolio モジュール
  - 候補抽出、等額/スコア重み付け、ポジションサイジング、セクターキャップ、レジーム乗数
- AI モジュール
  - news_nlp: OpenAI を使ったニュースセンチメント集計（ai_scores テーブルへ書き込み）
  - regime_detector: ETF MA 乖離 + マクロニュースで市場レジーム判定
- 運用ツール
  - paper_verification_report: ペーパートレード DB から各種指標（稼働率、成功率、レイテンシ等）を集計してレポート出力

## 前提条件（依存関係）
最低限必要なパッケージ（例）
- Python 3.9+
- duckdb
- psutil
- openai
- （任意）PyYAML — config/*.yaml のパース検証を行う場合

インストール例（仮想環境推奨）:
pip install -r requirements.txt
（requirements.txt が無い場合は上記パッケージを個別インストールしてください）

## セットアップ手順（開発・ローカル実行向け）
1. リポジトリをクローンし、仮想環境を作成・有効化する
2. 依存パッケージをインストール（duckdb, psutil, openai 等）
3. `.env` の準備
   - 対話式ウィザードを利用する:
     - python -m kabusys.config_setup
   - もしくはプロジェクトルートに `.env` を手動で配置
   - 自動ロード: `src/kabusys/config.py` はプロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）
4. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い（exit 1）
5. データディレクトリの作成
   - デフォルトで `data/` に SQLite / pid / flag 等が置かれます。必要なら手動で作成してください（logging のデフォルトは `logs/`）。
6. DuckDB / SQLite のパスは .env で指定（未指定時はデフォルトを使用）

## 主要な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - paper_trading: ExecutionEngine はペーパートレード用 DB に記録
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 SQLite、デフォルト: data/paper_trading.db）
- LOG_LEVEL（デフォルト: INFO）
- LOG_DIR（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START（0/1。起動時に kill.flag を自動でクリアするか）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔（秒））
- OPENAI_API_KEY（AI モジュール利用時に必要）

注意: `.env` は機密情報を含むため絶対に Git にコミットしないでください。

## 使い方（主な起動・コマンド例）

- .env を対話的に作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- Monitoring 起動（常駐的にポーリング）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（例: MONITOR_POLL_INTERVAL=30）

  実行中の停止方法:
  - プロジェクトルート `data/stop_requested.flag` を作成すると監視ループは検知して終了します（run_monitoring.py の停止フラグ）。
  - Kill switch（risk により発動）で ExecutionEngine 停止を指示するには `data/kill.flag` が書き込まれます。

- Execution エンジン起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録され、本番 DB と分離されます。
  - 起動時に `data/stop_requested.flag` が存在すると起動せず終了します。
  - 実行中の停止:
    - `data/stop_requested.flag` を作成 -> エンジンが検知して停止処理を行います。
    - Kill Switch によって `data/kill.flag` が作成されると ExecutionEngine を停止するよう設計されています。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で SQLite ファイルを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH の指定優先）

- AI / Research の呼び出し（スクリプトや REPL から）
  - 例: DuckDB 接続を作成してレジーム判定を呼ぶ
    - from datetime import date
      import duckdb
      from kabusys.ai.regime_detector import score_regime
      conn = duckdb.connect("data/kabusys.duckdb")
      score_regime(conn, date.fromisoformat("2026-04-01"), api_key="YOUR_OPENAI_KEY")
  - news_nlp の score_news も同様に DuckDB 接続と API キーを渡して利用可能

## 運用メモ / 実装上の注意点
- 監視 DB（monitoring）: run_monitoring は KABUSYS_ENV に関係なく本番の sqlite_path（Settings.sqlite_path）を使用します。監視データは単一ファイルに蓄積されるため注意してください。
- ExecutionEngine と paper_trading:
  - KABUSYS_ENV=paper_trading を指定すると ExecutionEngine は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離されます。
- Kill Switch:
  - risk アラート等により Kill Switch が発動すると `data/kill.flag` に理由が書き込まれます。既に存在する場合は上書きされません（冪等）。
  - 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると kill.flag を自動でクリアしますが、本番では推奨されません（デフォルト 0）。
- ログ:
  - ログはデフォルト `logs/<app_name>.log` に日次ローテーションで出力されます。ログディレクトリを作成できない場合はコンソール出力のみになります。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。管理者権限や OS によっては設定に失敗する場合があります（その場合は警告ログ）。

## ディレクトリ構成（主要ファイル）
プロジェクトルート（`pyproject.toml` / `.git` が存在する階層）
- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数・設定管理
    - config_setup.py          — .env 対話式ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — Monitoring ポーリングループ起動スクリプト
    - utils/
      - logging_setup.py       — 一元的なロギング設定
      - process_priority.py    — プロセス優先度・CPU affinity
    - monitoring/
      - monitoring_db.py       — SQLite 永続層
      - system_monitor.py
      - trade_monitor.py       — （コード一覧では省略）
      - risk_monitor.py
      - monitoring_engine.py
      - kill_switch.py
      - alert_manager.py       — （コード一覧では省略）
    - execution/
      - execution_engine.py    — 発注エンジン本体（主要ロジック）
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
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
    - data/                     — 実行時に利用するデータディレクトリ（logs/, data/ 下に DB・pid・flag など）
    - tools/
      - paper_verification_report.py

（注）上記は本 README に含まれる主要ファイルの抜粋です。実行に必要なモジュールは src/kabusys 以下にまとまっています。

## トラブルシューティング
- DuckDB / SQLite のパスが見つからない:
  - `.env` の DUCKDB_PATH / SQLITE_PATH を確認してください。`kabusys.validate_config` は親ディレクトリの存在を確認します。
- OpenAI API 呼び出しで失敗する:
  - OPENAI_API_KEY が設定されているか確認。API のレート制限や一時的なネットワークエラーは内部でリトライしますが、最終的に失敗すると該当処理はスキップします（例外は基本的に上位に伝播しない設計）。
- プロセス優先度の設定に失敗する:
  - 権限不足や未対応 OS の可能性。警告ログが出力されますが処理自体は継続します。
- kill.flag / stop_requested.flag / execution.pid:
  - `data/kill.flag` は Kill Switch が書き込む停止指示ファイルです。`data/stop_requested.flag` は手動でプロセスを停止させたいときに使用するフラグ（run_execution/run_monitoring が参照）。`data/execution.pid` は ExecutionEngine の PID を保持する目的で使われます。

## 開発向けヒント
- テストを容易にするため、config.py の自動 env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- ai.news_nlp モジュールや regime_detector は API 呼び出し部分をテスト用に patch しやすい構造（_call_openai_api を差し替え）になっています。
- DuckDB を使った research モジュールは外部 API に依存せず SQL と Python の組み合わせで完結するように設計されています。データを整備すればローカルで高速に解析できます。

---

ご不明点や追加で README に載せたい事項（例: デプロイ手順、systemd ユニット例、Dockerfile、CI 設定など）があれば教えてください。必要に応じてサンプルコマンドや systemd ユニットのテンプレートを追加します。