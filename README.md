# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ用 README（日本語）

この README はリポジトリ内の主要スクリプト・ユーティリティ群に基づいて、導入・起動方法、機能概要、ディレクトリ構成をまとめたものです。

注意: 実行には外部 API キー（J-Quants / kabuステーション / OpenAI 等）や DB ファイルの準備が必要です。本番運用時は設定値を慎重に管理してください。

## プロジェクト概要

KabuSys は日本株向けの自動売買・リサーチ基盤です。  
主な役割は次のとおりです。

- 戦略（シグナル）・ポートフォリオ構築ロジック
- ExecutionEngine による発注管理（本番 / ペーパートレード対応）
- 監視 (Monitoring)：システム稼働、注文・約定ログ、リスク監視、Kill Switch
- 研究用ユーティリティ（ファクター計算、特徴量解析）
- AI 補助機能（ニュース NLP によるセンチメント、レジーム検出）
- ペーパートレード検証レポート生成ツール

設計方針の一部:
- DuckDB / SQLite によるローカル DB 保持（分析用 / 監視用 / ペーパートレード別DB）
- .env ベースの設定管理（プロジェクト内の簡易ウィザードあり）
- OpenAI（gpt-4o-mini）を使ったニュース解析機能（API キー必須）
- monitoring は環境設定に関わらず「本番」監視 DB（monitoring.db）を使用

## 機能一覧

主な機能（実装済みモジュール抜粋）:

- 実行系
  - run_execution.py: ExecutionEngine の起動スクリプト（KABUSYS_ENV により本番 / paper_trading 切替）
  - BrokerClientFactory により本番 or MockBrokerClient を選択（paper_trading は data/paper_trading.db に分離）

- 監視系
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔調整可）
  - MonitoringEngine: SystemMonitor / TradeMonitor / RiskMonitor を束ねてアラート発行、Kill Switch 評価
  - MonitoringDB: SQLite を用いた監視ログ保存（system_status, trade_logs, positions, risk_logs, dashboard）

- リスク管理
  - RiskMonitor: ドローダウンやポジション上限を監視し、risk_logs / dashboard を更新
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み ExecutionEngine を停止させる

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定、等分配・スコア加重配分
  - portfolio.position_sizing: 株数算出（lot 単位丸め、risk-based 等）
  - portfolio.risk_adjustment: セクター上限やレジーム乗数

- 研究・解析
  - research.factor_research: Momentum / Volatility / Value ファクター計算（DuckDB 上で SQL 実行）
  - research.feature_exploration: 将来リターン計算、IC（情報係数）計算、統計要約

- AI 関連
  - ai.news_nlp: raw_news を LLM に投げて銘柄ごとのセンチメント（ai_scores）を生成
  - ai.regime_detector: ETF（1321）の MA 乖離 + マクロニュースの LLM センチメントを合成し市場レジーム判定（market_regime テーブルへ書込）

- ユーティリティ
  - config_setup.py: .env 初期作成・更新の対話型ウィザード
  - validate_config.py: .env / config/*.yaml の起動前検証 CLI
  - tools.paper_verification_report: ペーパートレード DB から合否判定レポートを生成

## 前提 / 必要ライブラリ

推奨 Python バージョン: 3.10+

主な依存ライブラリ（抜粋）:
- duckdb
- psutil
- openai
- sqlite3（標準）
- (任意) PyYAML — validate_config の YAML 内容検証に必要

インストール例（仮に pyproject.toml / requirements.txt があればそれを使用）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
# 必要パッケージを個別にインストールする例
pip install duckdb psutil openai
# optional
pip install pyyaml
# プロジェクトをローカルインストール可能なら
pip install -e .
```

## セットアップ手順

1. リポジトリをクローンして、仮想環境を作る。
2. 必要パッケージをインストール（上記参照）。
3. .env を作成
   - 対話ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
     ウィザードは .env をデフォルトでプロジェクトルートに保存します。
   - 必須環境変数
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - 主要なデフォルトパス
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
     - LOG_DIR: logs/
4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合
   python -m kabusys.validate_config --strict
   ```
5. データディレクトリ & ログディレクトリの作成（多くは自動作成されますが手動で整備しておくと良いです）
   ```bash
   mkdir -p data logs
   ```

環境変数自動読み込みについて:
- .env 自動ロードはデフォルトで有効。プロジェクトルート（.git または pyproject.toml）を基準に .env（および .env.local）を読み込みます。
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 とすると自動ロードを無効化できます（テスト向け）。

## 使い方

主な起動コマンド（パッケージを PYTHONPATH に含めた状態で実行）:

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）
  ```bash
  python -m kabusys.run_execution
  ```
  挙動:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag があれば起動を中止します。
  - 実行中は data/execution.pid に PID を書きます（設定により PID ファイルパスを変更可能）。

- Monitoring を起動（SystemMonitor のポーリングループ）
  ```bash
  # デフォルトポーリング間隔 60 秒。環境変数で上書き可:
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  挙動:
  - Settings から sqlite_path（monitoring DB）/ duckdb_path を参照して接続します。
  - 常に「本番」monitoring DB を使います（KABUSYS_ENV に依存しない）。
  - data/stop_requested.flag が存在するとループを終了します。

- .env の作成/更新（ウィザード）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポートの生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI / 研究系はライブラリ関数として呼び出す設計です（CLI ではなく Python API）
  - 例: news_nlp.score_news, ai.regime_detector.score_regime など。これらをスクリプトや cron、Airflow タスク等から呼ぶことを想定しています。

運用に関するポイント:
- Kill Switch: monitoring 側の条件により data/kill.flag が書き込まれると ExecutionEngine は終了シグナルを受けます。kill.flag は Settings.kill_flag_clear_on_start に注意して扱ってください（本番では 0 推奨）。
- PID / stop flag: 停止を要求する際は data/stop_requested.flag を作成することで監視ループや実行スレッドを停止できます（スクリプトは定期的にこのファイルの存在をチェックします）。
- ログ: logs/<app_name>.log に日次ローテートで出力されます（デフォルト 30 日保持）。

## 主要設定（.env で管理する主なキー）

- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（default: development）
- OPENAI_API_KEY — OpenAI を使う機能で必要
- DUCKDB_PATH — DuckDB ファイルパス（default: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（monitoring.db）パス（default: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（本番は 0 推奨）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング秒数（環境変数で上書き可）

（config_setup ウィザードを使うと主要項目を対話的に作成できます）

## ディレクトリ構成（主要ファイル）

以下はパッケージ内部の主要構成（src/kabusys 配下）です。実際のリポジトリルートに pyproject.toml/.git などがある想定です。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI 経由）
    - regime_detector.py     — レジーム判定（MA + マクロ NLP）
  - monitoring/
    - monitoring_db.py       — SQLite 用永続層
    - system_monitor.py
    - trade_monitor.py       — （存在、ログ参照）
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py       — （アラート送信管理、LINE など）
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - logging_setup.py
    - process_priority.py

プロジェクトルートに想定されるディレクトリ/ファイル:
- data/                      — DB / PID / flag ファイルが格納される（例: data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag, data/stop_requested.flag）
- logs/                      — ログファイル保存先（logs/execution.log, logs/monitoring.log 等）
- config/                    — YAML 設定テンプレート群（system_config.yaml など）

## 運用上の注意

- 本番運用 (KABUSYS_ENV=live) の場合は LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID）や kill flag の扱いを慎重に確認してください。validate_config は live 向けの追加警告を出します。
- OpenAI API を使う機能はコスト・レイテンシ・レート制限に注意してください。news_nlp/regime_detector はリトライ・バックオフや最大記事数の制約を実装していますが、運用設定を確認してください。
- DB マイグレーション: monitoring_db.init_monitoring_db は冪等にテーブル追加 / カラム追加を行います。既存 DB のバックアップを運用で考慮してください。
- process priority / CPU affinity: 起動スクリプトは set_process_priority("high") を呼びますが、権限や OS により設定できない場合があります（警告でスキップされます）。
- テスト環境向け: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化できます（ユニットテスト等で有用）。

---

この README はコードベースから読み取れる内容をまとめたもので、実際の詳細実装や外部モジュール（execution.*, trade_monitor.* 等）の具体的振る舞いはリポジトリ内の該当ファイルを参照してください。追加で README に含めたい具体的なコマンド例や運用手順があれば教えてください。