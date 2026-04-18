# KabuSys

日本株向け自動売買システムのコードベース（軽量版ドキュメント）。

この README はリポジトリ内の主要スクリプトと設定方法、起動手順、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視機能を備えたシステム群です。  
主な役割は以下の通りです。

- 戦略に基づく銘柄選定・ポートフォリオ構築（portfolio モジュール）
- 発注実行エンジン（ExecutionEngine）および発注管理（execution パッケージ）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor）と Kill Switch
- 研究用ファクター計算・特徴量探索（research パッケージ）
- ニュース NLP を用いたセンチメントスコアリング（AI モジュール）
- ペーパートレード検証レポートなどのツール類

設計方針の特徴：
- 多くのロジックは純粋関数または DB ベースの読み書きに分離
- 実行環境（development / paper_trading / live）に応じた挙動切替
- 各種設定は `.env` で管理。対話式ウィザードと検証ツールあり
- ロギングは統一的に設定（コンソール + 日次ローテートファイル）

---

## 機能一覧

- 環境設定ウィザード（.env の生成・更新）
  - `python -m kabusys.config_setup`
- 設定検証ツール（.env / config/*.yaml の検証）
  - `python -m kabusys.validate_config`
- 発注実行起動スクリプト
  - `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使用し、paper DB に分離して記録
- 監視ループ起動スクリプト
  - `python -m kabusys.run_monitoring`
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で変更可能（デフォルト 60 秒）
- 監視 DB 永続化（SQLite）
  - system_status / trade_logs / positions / risk_logs / dashboard
- リスク監視（ドローダウン、ポジション上限）・Kill Switch（`data/kill.flag`）
- Paper Trading 検証レポート生成ツール
  - `python -m kabusys.tools.paper_verification_report`
- 研究モジュール（DuckDB に対するファクター計算・特徴量解析）
- ニュース NLP（OpenAI を用いたセンチメント計算）
  - `kabusys.ai.news_nlp.score_news`
  - `kabusys.ai.regime_detector.score_regime`

---

## セットアップ手順

1. Python 仮想環境の作成（任意）
   - python3 -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必要パッケージ（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config YAML 検証で任意）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ 実際の requirements.txt / setup はプロジェクトに合わせて用意してください。

3. データ・ログディレクトリ準備（通常は自動で作成されますが、手動で作ることも可能）
   - data/
   - logs/

4. 環境変数設定
   - .env を作成する方法（対話式ウィザード推奨）
     - python -m kabusys.config_setup
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 代表的な設定項目（デフォルト値）:
     - KABUSYS_ENV=development | paper_trading | live (default: development)
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - LOG_LEVEL=INFO
     - OPENAI_API_KEY（AI 機能を使う場合必須）
     - KILL_FLAG_CLEAR_ON_START=0 (起動時に kill.flag を自動クリアするか)

5. 設定検証（推奨）
   - python -m kabusys.validate_config
   - `--strict` を付けると警告があるとエラー扱いになります

---

## 使い方（起動例・実行方法）

- 発注エンジン（ExecutionEngine）起動
  - 簡易:
    - python -m kabusys.run_execution
  - 動作ポイント:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使い paper DB（PAPER_TRADING_SQLITE_PATH）へ記録
    - 本番（live）の場合は本番 sqlite_path を使用
    - 起動時に `data/execution.pid`（デフォルト）などに PID ファイルを書きます
    - 停止: プロセスに KeyboardInterrupt（Ctrl+C） または監視側からの停止フラグ（data/stop_requested.flag）

- 監視ループ起動
  - python -m kabusys.run_monitoring
  - 環境変数:
    - MONITOR_POLL_INTERVAL=30 などでポーリング間隔（秒）を上書き可
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず本番 DB に書き込む実装）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプションで `--db PATH` を指定可能（なければ PAPER_TRADING_SQLITE_PATH 環境変数またはデフォルト）

- AI（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数）
  - 例（スクリプト呼び出し例はユーティリティ関数を直接呼ぶ実装に依存）
    - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

- Kill Switch / 停止フラグ
  - KillSwitch は `Settings.kill_flag_path`（デフォルト `data/kill.flag`）を作成して ExecutionEngine に停止シグナルを送ります
  - ExecutionEngine / Monitoring のポーリングループは `data/stop_requested.flag` / `data/stop_requested.flag` 等のフラグをチェックして停止する設計です（スクリプト内のフラグパスを参照）

---

## 主要環境変数（主なもの）

- KABUSYS_ENV: execution 挙動を切り替え（development / paper_trading / live）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（paper_trading の場合に使用）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログの出力先ディレクトリ（デフォルト logs/）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（1 = クリアする）

---

## ログについて

- ログ設定は `kabusys.utils.logging_setup.setup_logging` で行います。
- 出力:
  - コンソール（stdout）
  - ファイル: `<LOG_DIR>/<app_name>.log`（日次ローテーション、30日保持）
- LOG_DIR が作成できない場合はファイル出力をスキップしてコンソールのみで継続します。

---

## ディレクトリ構成（主なファイル・モジュール）

リポジトリの主要なソースは `src/kabusys` 以下に格納されています。代表的な構成は以下の通りです。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数の読み込み・Settings クラス
    - 自動 .env ロード（.env / .env.local）
  - config_setup.py
    - 対話式ウィザードで .env を生成/更新
  - validate_config.py
    - 起動前検証 CLI（必須 env 等のチェック）
  - run_execution.py
    - ExecutionEngine 起動スクリプト（発注エンジン）
  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプト
  - portfolio/
    - portfolio_builder.py
      - 候補選定・等重/スコア重み計算
    - position_sizing.py
      - 発注株数計算・単元株丸め・aggregate cap
    - risk_adjustment.py
      - セクターキャップ適用・レジーム乗数
  - monitoring/
    - monitoring_db.py
      - SQLite のスキーマ初期化・永続化 API
    - system_monitor.py
      - CPU/メモリ/DISK、データ鮮度、プロセス監視
    - trade_monitor.py
      - （trade 関連監視機能）
    - risk_monitor.py
      - ドローダウン / ポジション上限監視
    - kill_switch.py
      - kill.flag 書き込みロジック
    - monitoring_engine.py
      - 複数 Monitor を束ねるエンジン
    - alert_manager.py
      - （LINE 等への通知管理）
  - execution/
    - （ExecutionEngine、OrderManager、BrokerFactory 等の実装）
  - research/
    - factor_research.py
      - momentum / volatility / value 等のファクター計算（DuckDB）
    - feature_exploration.py
      - forward returns / IC / summary 等
  - ai/
    - news_nlp.py
      - raw_news を集約して OpenAI に投げ、ai_scores を更新
    - regime_detector.py
      - MA200 とマクロ NLP を合成して market_regime を算出・永続化
  - tools/
    - paper_verification_report.py
      - ペーパートレード検証レポート生成

---

## 注意・運用上のポイント

- 本番運用時は KABUSYS_ENV=live の設定と .env 内の機密情報管理を厳重に行ってください。`.env` は絶対に Git にコミットしないでください。
- Kill Switch（`data/kill.flag`）は本番で重要なセーフティ機構です。`KILL_FLAG_CLEAR_ON_START=1` を本番で設定するのは危険です（自動クリアされるため）。
- run_monitoring は監視 DB（SQLITE_PATH）へ書き込みます。監視は KABUSYS_ENV に依存せず本番 DB を参照します（設計上の注意）。
- AI モジュールを使う場合は OpenAI の利用料がかかります。API キーの権限と費用管理に注意してください。
- DuckDB / SQLite のファイルは別プロセスから読み書きされることがあるため、バックアップ・ローテーション・アクセス制御に注意してください。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると、自動での .env ロードを抑制できます（テスト等で便利）。

---

## 参考コマンド一覧

- .env を対話式生成:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Paper 検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- （AI 機能）スコア実行例（ライブラリ呼び出し）:
  - Python コード内で `kabusys.ai.score_news(...)` / `kabusys.ai.regime_detector.score_regime(...)` を使用

---

この README はコードベースのエントリポイント・設定・運用に重点を置いています。各モジュールの詳細（ExecutionEngine の内部実装、order manager、broker client 実装など）は各ファイル内の docstring やコメントを参照してください。質問があれば具体的なファイルや機能について教えてください。