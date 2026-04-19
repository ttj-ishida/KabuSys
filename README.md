# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買システム（KabuSys）のコアライブラリ群です。戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視・アラート、AI を使ったニュース解析などのコンポーネントを含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の機能を分離したモジュールで提供します。

- 戦略・リサーチ: DuckDB 上の株価データを使ったファクター計算、将来リターン解析、統計解析
- ポートフォリオ構築: 候補選定、重み付け、ポジションサイズ計算（単元・キャップ・集計上限を考慮）
- 発注エンジン (Execution): ブローカークライアントを通じた発注管理、リスク管理、再同調 (reconciler)
- 監視 (Monitoring): システム・注文・リスク監視、Kill Switch、アラート送信
- AI ユーティリティ: ニュースの NLP スコアリング、レジーム判定（OpenAI）
- ツール: ペーパートレード検証レポート生成など
- ユーティリティ: ロギング設定、プロセス優先度設定、設定読み込みウィザード/検証

---

## 主な機能一覧

- config 管理
  - .env 自動ロード（`.env`, `.env.local`）と Settings クラス
  - 対話式ウィザードで .env を生成（`kabusys.config_setup`）
  - 設定検証 CLI（`kabusys.validate_config`）

- 実行: ExecutionEngine
  - 本番 / ペーパートレード切替（`KABUSYS_ENV=paper_trading` で MockBroker を使用）
  - Paper トレード用に別 SQLite DB（デフォルト `data/paper_trading.db`）
  - PID・停止フラグ対応（`data/execution.pid`, `data/stop_requested.flag`）

- 監視: Monitoring
  - System / Trade / Risk の各モニタと MonitoringEngine
  - Kill Switch（条件成立時に `data/kill.flag` を作成し Execution を停止）
  - 監視 DB（SQLite）初期化と永続化レイヤ（`monitoring_db.py`）
  - ポーリング間隔を環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）
  - Monitoring は環境にかかわらず本番 `sqlite_path` を使用（監視は常に本番 DB を参照）

- 研究・ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン、IC 計算、統計サマリー

- AI
  - ニュースを OpenAI (gpt-4o-mini 等) でスコアリングし `ai_scores` テーブルへ書き込み
  - 市場レジーム判定（ETF MA200 とマクロニュースの LLM スコアを合成）

- ツール
  - Paper Trading 検証レポート生成スクリプト（`kabusys.tools.paper_verification_report`）

---

## セットアップ手順

前提: Python 3.10 以上を推奨（型ヒントに `|` を使用）。

1. リポジトリをクローンし仮想環境を作成・有効化
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージをインストール
   - 最低限必要なパッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイル検証を行う場合に必要）
   - 例:
     - pip install duckdb psutil openai pyyaml

   （プロジェクトに requirements.txt があればそちらを利用してください）

3. 初期 .env の準備（対話式ウィザード推奨）
   - ウィザードを実行して `.env` を生成:
     - python -m kabusys.config_setup
   - もしくは手動で `.env` を作成（プロジェクトルートに配置）

   代表的な環境変数（.env に設定する例）
   - JQUANTS_REFRESH_TOKEN=your_token_here
   - KABU_API_PASSWORD=your_password_here
   - KABU_API_BASE_URL=http://localhost:18080/kabusapi
   - DUCKDB_PATH=data/kabusys.duckdb
   - SQLITE_PATH=data/monitoring.db
   - KABUSYS_ENV=development  # development | paper_trading | live
   - LOG_LEVEL=INFO
   - OPENAI_API_KEY=sk-...

4. 設定検証
   - python -m kabusys.validate_config
   - 警告もエラー扱いにするには `--strict` を付与

5. データベースの初期化
   - Execution / Monitoring の起動時に SQLite / DuckDB は必要に応じて作成されます。
   - DuckDB ファイル（`data/kabusys.duckdb`）や SQLite の親ディレクトリが存在することを確認してください（`logs/` も同様）。

---

## 使い方（起動 / 実行）

※ 各コマンドはプロジェクトルートで実行してください。

- ExecutionEngine を起動（本番 / ペーパートレードを .env の KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - ペーパートレードは `KABUSYS_ENV=paper_trading` を設定すると MockBroker が使われ、DB は `PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）に分離されます。
  - 停止: プロセスは `data/stop_requested.flag` の存在を監視して安全停止します。停止したい場合はファイルを作成してください（例: touch data/stop_requested.flag）。

- Monitoring を起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔は環境変数で上書き可能:
    - export MONITOR_POLL_INTERVAL=30  # 秒
  - Monitoring は常に production 用の `SQLITE_PATH` を使います（`KABUSYS_ENV` に関係なし）。

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH
  - 環境変数: PAPER_TRADING_SQLITE_PATH（--db より優先されない、優先順位は: --db > env > デフォルト）

- ログ
  - デフォルトログディレクトリ: logs/
  - 各プロセスは `logs/<app_name>.log` に日次ローテートで出力します（`kabusys.utils.logging_setup`）。

停止シグナル / Kill Switch の動作
- 手動停止（全体停止）: `data/stop_requested.flag` を作成すると run_execution/run_monitoring のループが検出して終了します。
- 自動停止（Kill Switch）: 監視が条件（ドローダウン超過、ポジション上限超過など）を満たすと `data/kill.flag` を書き込み、ExecutionEngine の停止を誘導します。`KillSwitch.clear()` を使うかファイルを削除してクリアします。

---

## 主要な環境変数

必須
- JQUANTS_REFRESH_TOKEN（J-Quants API）
- KABU_API_PASSWORD（kabuステーション API）

重要（デフォルトあり）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（1=クリア、0=しない。production では 0 推奨）

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主要ファイル・モジュールの概観です。

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings
  - config_setup.py              — .env 対話ウィザード
  - validate_config.py           — 設定検証 CLI

  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring ポーリング起動スクリプト

  - execution/                   — 発注エンジン関連（broker_factory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - risk_manager.py
    - reconciler.py
    - broker_factory.py
    - ...（実装ファイル）

  - monitoring/
    - monitoring_db.py            — SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py

  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py

  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py

  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py

  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py

  - tools/
    - paper_verification_report.py
    - __init__.py

- data/                          — 実行時に生成されることが多い（DB・flag・pid 等）
  - monitoring.db (SQLITE_PATH のデフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
  - kabusys.duckdb (DUCKDB_PATH のデフォルト)
  - execution.pid
  - stop_requested.flag
  - kill.flag

- logs/                          — デフォルトログ出力先（設定可能）

---

## 注意事項 / 運用上のポイント

- 本番起動前に必ず `python -m kabusys.validate_config` で設定検証を行ってください。
- `.env` は決して Git にコミットしないでください（ウィザードの出力ヘッダにも注意喚起あり）。
- OpenAI など外部 API を使う機能は API キーの設定が必要です。API エラー時はフォールバック挙動を取る実装になっていますが、運用時はレート制限・コストに注意してください。
- Monitoring は監視用 DB（`SQLITE_PATH`）を参照します。監視は常に「本番」DB を見るので、ペーパートレードの監視用 DB と混同しないでください。
- 停止フラグ（`data/stop_requested.flag`）、Kill Switch（`data/kill.flag`）の扱いには注意してください。特に本番環境では `KILL_FLAG_CLEAR_ON_START=0` を推奨します。

---

## さらに詳しく

コード内の docstring / コメントに設計意図やアルゴリズムの詳細が記載されています。各モジュール（portfolio, research, execution, monitoring, ai）の実装を参照してください。質問や補足ドキュメントが必要であれば教えてください。