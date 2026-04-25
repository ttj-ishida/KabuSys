# KabuSys

日本株自動売買システム (KabuSys) のリポジトリ向け README（日本語）。

このドキュメントはコードベースから読み取れる機能・使い方・セットアップ手順・ディレクトリ構成を説明します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム（研究・ポートフォリオ構築・発注エンジン・監視・AI 補助機能を含む）です。  
主な設計方針は以下の通りです。

- DuckDB を用いたファクター計算・リサーチ（prices_daily / raw_financials など）
- SQLite を用いた監視ログ・発注ログ（本番/ペーパートレードで DB 分離可能）
- ExecutionEngine による発注管理（本番: kabuステーション / ペーパー: MockBroker）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- ニュース NLP（OpenAI）を用いたセンチメント評価・市場レジーム判定
- ロギングは統一的に設定（console + 日次ローテートファイル）

注意: 実際の発注機能や外部 API を利用する部分は本番環境では慎重に設定してください。

---

## 機能一覧（主要コンポーネント）

- 実行 / 発注
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading をサポート）
  - ブローカーファクトリにより本番/Mock 切り替え
  - OrderManager / RiskManager / Reconciler 等

- 監視
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
  - MonitoringEngine: System / Trade / Risk 各 Monitor を束ねてポーリング
  - MonitoringDB: SQLite スキーマ生成・永続化
  - KillSwitch: データフォルダのフラグファイルで Execution を停止

- ポートフォリオ構築（純粋関数）
  - portfolio.select_candidates / calc_equal_weights / calc_score_weights
  - position_sizing.calc_position_sizes（単元株丸め・利用可能現金に基づくスケール）
  - risk_adjustment.apply_sector_cap / calc_regime_multiplier

- リサーチ
  - research.factor_research: momentum / volatility / value 等のファクター計算（DuckDB）
  - research.feature_exploration: 将来リターン、IC、ファクター統計

- AI（OpenAI）
  - ai.news_nlp: raw_news を LLM でセンチメント評価 → ai_scores に書き込み
  - ai.regime_detector: ETF MA とマクロ記事センチメントから市場レジーム判定

- ユーティリティ
  - utils.logging_setup: コンソール + TimedRotatingFileHandler による統一ログ設定
  - utils.process_priority: プラットフォーム依存処理を吸収してプロセス優先度設定
  - config.py / config_setup.py / validate_config.py: 環境変数管理、.env ウィザード、設定検証
  - tools.paper_verification_report: ペーパートレード検証レポート生成

---

## セットアップ手順（ローカル開発向け）

以下は最低限の手順例です。プロジェクトに requirements.txt 等がある場合はそちらを優先してください。

1. リポジトリをクローンし、作業ディレクトリをプロジェクトルートにする（src がある場所）。
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール（最低限）
   - pip install duckdb psutil openai
   - 追加で YAML 検証やツールを使う場合:
     - pip install pyyaml

   ※ sqlite3 は標準ライブラリ、DuckDB は外部パッケージです。OpenAI クライアントは ai 機能を使う場合に必要です。

4. Python パスの設定（開発実行時）
   - プロジェクトはソースが `src/` 下にあるため、実行時に PYTHONPATH を通す必要があります。
     - Unix/macOS:
       - export PYTHONPATH=src
     - Windows (PowerShell):
       - $env:PYTHONPATH = "src"

   もしくはパッケージとしてインストール可能な場合は `pip install -e .` を行ってもよいです（プロジェクトにセットアップ情報がある前提）。

5. .env の作成
   - まずウィザードで作成するのが簡単です:
     - PYTHONPATH=src python -m kabusys.config_setup
   - 手動で作る場合はプロジェクトルートに `.env` を配置。例（最小）:
     - JQUANTS_REFRESH_TOKEN=your_token_here
     - KABU_API_PASSWORD=your_kabu_password
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - LOG_LEVEL=INFO

   - 自動ロードを無効にしたい場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

6. 設定検証（起動前のチェック）
   - PYTHONPATH=src python -m kabusys.validate_config
   - --strict をつけると警告もエラー扱いになります。

7. データフォルダやログフォルダの作成（通常自動作成されますが手動で用意しておくと確実）
   - mkdir -p data logs

---

## 使い方（起動方法・主要スクリプト）

前提: PYTHONPATH=src を設定しているものとします。

- 実行エンジン（ExecutionEngine）起動
  - paper_trading（ペーパートレード）:
    - export KABUSYS_ENV=paper_trading
    - PYTHONPATH=src python -m kabusys.run_execution
    - ペーパートレード時は MockBrokerClient を使用し、デフォルトで data/paper_trading.db を使います。
  - 本番 / 開発:
    - export KABUSYS_ENV=live   または development
    - PYTHONPATH=src python -m kabusys.run_execution

  ポイント:
  - 起動時に停止フラグ (data/stop_requested.flag) が存在すると起動しません。
  - 実行中は data/execution.pid に PID を書きます。
  - 終了は停止フラグを作成するか、実行プロセスに対して正常な停止呼び出しを行います。

- 監視プロセス起動
  - PYTHONPATH=src python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` (秒) でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は Settings の sqlite_path（デフォルト data/monitoring.db）に接続してログを保存します。

- Kill Switch（強制停止）
  - KillSwitch は `data/kill.flag` を生成して ExecutionEngine に停止シグナルを送ります。
  - KillSwitch は RiskMonitor の結果（ドローダウンやポジション超過）を評価してフラグを書き込みます。
  - ExecutionEngine は起動時に `KILL_FLAG_CLEAR_ON_START=1` の場合、kill.flag を自動でクリアする設定があります（本番では 0 推奨）。

- .env ウィザード
  - PYTHONPATH=src python -m kabusys.config_setup
  - 対話式で .env を生成・更新します。

- 設定検証
  - PYTHONPATH=src python -m kabusys.validate_config
  - 起動前に必須環境変数や config/*.yaml をチェックします（PyYAML が無い場合は YAML 検証はスキップ）。

- ペーパートレード検証レポート
  - PYTHONPATH=src python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - `--db` オプションで SQLite パスを指定できます。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可能。

---

## 重要な環境変数（抜粋・デフォルト）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視用) (デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (デフォルト: data/paper_trading.db) — paper_trading 用 DB
- LOG_LEVEL (デフォルト: INFO)
- LOG_DIR (デフォルト: logs/)
- OPENAI_API_KEY — ai.news_nlp / ai.regime_detector を利用する場合に必要
- PAPER_FILL_MODE (paper_trading 時の約定動作): instant | partial | never | reject (デフォルト: instant)
- MONITOR_POLL_INTERVAL (秒): run_monitoring.py 内で使用（デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 0/1（本番では 0 推奨）

詳細は `src/kabusys/config.py` を参照してください。

---

## ログ・データ・フラグファイル

- ログ
  - デフォルト出力先: logs/<app_name>.log
  - console 出力は stdout、ファイルは日次ローテート（30日保持）

- データ
  - DuckDB: data/kabusys.duckdb
  - 監視 SQLite: data/monitoring.db
  - ペーパートレード SQLite: data/paper_trading.db

- 停止・キルフラグ
  - data/stop_requested.flag: run_execution / run_monitoring が監視している停止フラグ
  - data/kill.flag: KillSwitch が書き込む ExecutionEngine 停止用フラグ
  - data/execution.pid: ExecutionEngine の PID ファイル

---

## 開発時のヒント / 注意点

- 実行前に `PYTHONPATH=src` を通すか、プロジェクトを editable install しておくと便利です。
- OpenAI を使う機能は API キーと呼び出し回数・費用に注意してください。API エラーは多くの箇所でフェイルセーフ（スコア 0 など）になっていますが、本番設定は慎重に。
- 本番環境 (KABUSYS_ENV=live) では `KILL_FLAG_CLEAR_ON_START` を 0 にすることを推奨します（自動クリアは危険）。
- validate_config で設定を事前検証してください（必須 env の未設定や .yaml の欠落を検出できます）。
- DuckDB / psutil / openai 等のバージョン依存に注意。ローカルで問題がある場合は対応するパッケージのドキュメントを参照してください。
- コードは多くの箇所で「フェイルセーフ」や冪等性を意識して実装されていますが、実際の発注・金銭的リスクが絡む場面は十分テストの上で稼働させてください。

---

## ディレクトリ構成（抜粋・説明）

プロジェクトの主要ファイル・ディレクトリ:

- src/
  - kabusys/
    - __init__.py
    - config.py                — 環境変数 / Settings
    - config_setup.py          — .env 対話生成ウィザード
    - validate_config.py       — 設定検証 CLI
    - run_execution.py         — ExecutionEngine 起動スクリプト
    - run_monitoring.py        — SystemMonitor 起動スクリプト
    - data/                    — （データアクセス・パイプライン）※ prices_daily 等はここに実装想定
    - execution/
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - broker_factory.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py
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
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - config/                   — 設定テンプレート YAML（system_config.yaml 等、生成スクリプト参照）
- data/                        — 実行時 DB / フラグファイル（例: monitoring.db, paper_trading.db, kill.flag）
- logs/                        — ログ出力先（デフォルト）

（上記は主要ファイルの抜粋です。詳細はソースツリーを参照してください。）

---

この README はコード内容の要約です。実際の運用・本番導入にあたっては個別ドキュメント・運用手順を整備し、十分なテストと安全対策（アクセス制御、バックアップ、アラート設定）を行ってください。質問や追加で README に含めたい情報があれば教えてください。