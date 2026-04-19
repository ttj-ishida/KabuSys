# KabuSys

日本株向け自動売買システムのリポジトリ（ライブラリ／実行スクリプト群）。  
このREADMEはコードベース（src/kabusys 以下）から自動作成した概要と利用方法を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は、シグナル生成 → ポートフォリオ構築 → 発注（ExecutionEngine）までを含む日本株自動売買システムのコンポーネント群です。  
主な収集・分析・発注・監視・運用補助機能を提供します。DuckDB / SQLite による履歴管理、OpenAI を用いたニュース NLP / レジーム判定、ペーパートレードの分離運用などを想定しています。

主な設計方針:
- 実運用（live）・ペーパートレード（paper_trading）・開発（development）モードを環境変数で切替。
- DuckDB を分析用、SQLite を監視・注文ログ用に利用。
- AI モジュール（ニュースセンチメント・レジーム判定）は OpenAI API に依存（環境変数でキーを指定）。
- 監視（Monitoring）でリスクやプロセス死活を検知し、Kill Switch により発注エンジンを停止可能。

---

## 機能一覧

- 実行スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV により paper_trading を分離）
  - run_monitoring.py: SystemMonitor（監視）のポーリングループを起動

- 設定管理
  - config.py: 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py: .env を対話式に作るウィザード
  - validate_config.py: 起動前検証 CLI（必須設定や config/*.yaml の存在チェック）

- 監視
  - monitoring/monitoring_db.py: SQLite 監視 DB の初期化・永続化 API
  - monitoring/system_monitor.py: CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
  - monitoring/trade_monitor.py, monitoring/risk_monitor.py, monitoring/kill_switch.py, monitoring/monitoring_engine.py: 各種モニタと通知/キルスイッチ（概略）

- 発注・実行（概念）
  - execution/*: Broker クライアントファクトリ、ExecutionEngine、OrderManager、RiskManager、Reconciler 等（実装に依存）

- ポートフォリオ構築（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定・重み計算
  - portfolio/position_sizing.py: 発注数量計算、利用キャッシュによるスケーリング
  - portfolio/risk_adjustment.py: セクター上限、レジーム乗数

- リサーチ（DuckDB ベース）
  - research/factor_research.py: Momentum / Volatility / Value 等のファクター計算
  - research/feature_exploration.py: 将来リターン計算、IC、統計サマリ

- AI（OpenAI）
  - ai/news_nlp.py: ニュースを集約してセンチメントスコアを生成し ai_scores に書き込み
  - ai/regime_detector.py: ETF とマクロニュースを組み合わせて market_regime を判定

- ユーティリティ
  - utils/logging_setup.py: 統一ロギング（コンソール + 日次ローテート）
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定

- ツール
  - tools/paper_verification_report.py: ペーパートレード DB の検証レポート生成

---

## セットアップ手順（ローカル開発向け）

以下は最小セットアップ手順の例です。プロジェクトに requirements ファイルがないため、想定される主要依存を記載しています。

1. Python 仮想環境を作成・有効化
   - python3 -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール（例）
   - pip install duckdb psutil openai PyYAML

   ※ 実行環境によっては追加の依存が必要です（requests 等）。運用では requirements.txt を用意してください。

3. リポジトリルートに移動し、.env を作成
   - python -m kabusys.config_setup
   - 対話で必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）を入力して .env を生成します。

   代表的な環境変数（.env に含まれる / 設定されるもの）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABUSYS_ENV = development | paper_trading | live
   - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
   - SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
   - LOG_LEVEL, LOG_DIR
   - OPENAI_API_KEY（AI 機能を使う場合）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります。

5. データディレクトリの作成（必要なら）
   - mkdir -p data logs

---

## 使い方（主要コマンド）

- 実行前に .env を作成・確認し、必要な DB ファイル/ディレクトリが作られていることを確認してください。

1. 監視ループを起動（SystemMonitor）
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
   - python -m kabusys.run_monitoring

   挙動:
   - process priority を "high" に設定し（可能なら）、Settings.sqlite_path を使って SQLite に接続。DuckDB にも接続します。
   - data/stop_requested.flag が存在するとループを終了します。
   - 監視は本番 sqlite_path を使用（KABUSYS_ENV にかかわらず）。

2. 発注エンジン（ExecutionEngine）を起動
   - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（既定 data/paper_trading.db）に記録します（本番 DB と分離）。
   - python -m kabusys.run_execution

   挙動:
   - process priority を "high" に設定
   - 起動時に data/stop_requested.flag があると起動を中止
   - 起動後、ExecutionEngine.run_session をデーモンスレッドで実行、停止フラグで停止

3. .env の作成／更新（対話式）
   - python -m kabusys.config_setup

4. 設定検証
   - python -m kabusys.validate_config [--strict]

5. ペーパートレード検証レポート
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB パスは --db で指定、なければ環境変数 PAPER_TRADING_SQLITE_PATH → data/paper_trading.db

6. AI / リサーチ用 API の Python 利用例（インポートして呼び出す）
   - ニューススコア (AI): from kabusys.ai.news_nlp import score_news
   - 市場レジーム判定: from kabusys.ai.regime_detector import score_regime
   - ファクター計算: from kabusys.research import calc_momentum, calc_volatility, calc_value
   - ポートフォリオ関係: from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes

   例（DuckDB 接続を渡して関数呼び出し）:
   - import duckdb
     conn = duckdb.connect("data/kabusys.duckdb")
     calc_momentum(conn, target_date)

注意点:
- OpenAI を使う場合は OPENAI_API_KEY を設定してください。
- news_nlp / regime_detector は API 呼び出し失敗時にフォールバック動作をするよう設計されていますが、API キー未設定時は ValueError を投げます。
- デバッグログは LOG_LEVEL 環境変数で指定します（デフォルト INFO）。ログは logs/<app_name>.log に日次ローテートで保存されます。

停止・Kill スイッチ:
- 実運用では data/kill.flag を書き込むことで ExecutionEngine に停止シグナルを送る（KillSwitch）。監視は必要に応じてこのフラグを作成します。
- 手動で停止したい場合: touch data/stop_requested.flag を作成すると run_monitoring / run_execution のループが終了します（実装上の停止フラグ）。

---

## よく使う環境変数（抜粋）

- KABUSYS_ENV: development | paper_trading | live
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- DUCKDB_PATH (default data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, default data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB)
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログ保存ディレクトリ（default logs/）
- OPENAI_API_KEY: OpenAI を使う場合のキー
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: instant | partial | never | reject

---

## ディレクトリ構成（抜粋）

（プロジェクトルート想定）
- .env                 — 環境変数ファイル（未コミット推奨）
- config/              — 設定テンプレート / yaml（config/*.yaml）
- data/                 — データファイル（DB, pid, flag など）
  - monitoring.db       — SQLite 監視 DB（デフォルト）
  - paper_trading.db    — Paper trading 用 SQLite（デフォルト）
  - kabusys.duckdb      — DuckDB 分析 DB（デフォルト path に配置）
  - execution.pid       — pid ファイル
  - stop_requested.flag — 停止フラグ（手動/運用で使用）
  - kill.flag           — Kill Switch フラグ
- logs/                 — ログ出力先（default）
- src/
  - kabusys/
    - __init__.py
    - run_execution.py
    - run_monitoring.py
    - config.py
    - config_setup.py
    - validate_config.py
    - utils/
      - logging_setup.py
      - process_priority.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - monitoring_engine.py
      - risk_monitor.py
      - kill_switch.py
      - trade_monitor.py
      - alert_manager.py (※実装がある想定)
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
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
    - tools/
      - paper_verification_report.py
    - data/ (データパイプライン・stats 等のモジュール群想定)

---

## トラブルシューティング（よくある問題）

- 依存モジュール不足
  - import エラーが出たら必要なパッケージ（duckdb, psutil, openai, PyYAML など）を pip でインストールしてください。

- DB/ファイルパス
  - デフォルトパスは data/*. です。環境によっては parent ディレクトリが存在しない場合があります（validate_config で警告されます）。手動で作成するか .env のパスを書き換えてください。

- OpenAI API
  - API の呼び出し制限やエラーはリトライロジックがありますが、キー未設定は即時エラーになります。AI 機能を使わない場合は OPENAI_API_KEY を設定せずスキップ可能な箇所もあります。

- ログディレクトリ作成失敗
  - ログディレクトリ作成に失敗するとファイルハンドラは無効化され、コンソール出力のみになります。権限やパスを確認してください。

---

## 開発メモ / 実装上の注意点

- Settings は .env 自動ロードを組み込んでいます（プロジェクトルートが特定できない場合はスキップ）。
- monitoring の DB 初期化は冪等（init_monitoring_db）。
- run_monitoring は監視用 DB を「本番 sqlite_path」で開く（環境に依存しない仕様）。
- run_execution は paper_trading の場合別 DB を使い、本番 DB と分離する。
- AI モジュールはレスポンスの堅牢なバリデーション、リトライ、部分成功時の DB 書き込み保護など運用上の注意を織り込んでいます。

---

必要があれば、README に含める例 .env.example、システム起動用 systemd ユニットファイル例、各モジュールの API 使用例（コードスニペット）なども作成します。どの情報を詳しく追加したいか教えてください。