# KabuSys

日本株自動売買システム（ライブラリ / 実行スクリプト群）

このリポジトリは、戦略の研究・ファクター計算、ポートフォリオ構築、発注エンジン（ExecutionEngine）、およびシステム監視（Monitoring）を含む自動売買基盤の一部を実装しています。OpenAI を用いたニュース NLP / レジーム判定などの機能も含まれます。

---

## プロジェクト概要

KabuSys は概念的に以下の役割を持つコンポーネントで構成されています。

- execution: 発注ロジック（ExecutionEngine）、OrderManager、RiskManager、Reconciler 等
- monitoring: システム稼働・データ鮮度・注文状況・リスク監視、Kill Switch
- research: DuckDB を用いたファクター計算・特徴量解析
- portfolio: 候補選定、重み計算、ポジションサイズ決定、セクター調整
- ai: OpenAI を利用したニュースセンチメント（news_nlp）・市場レジーム判定（regime_detector）
- utils: ロギング設定、プロセス優先度などのユーティリティ
- tools: ペーパートレード検証レポート等のユーティリティスクリプト
- config: 環境変数/.env の自動読み込み・検証・対話式セットアップ

主に Python モジュールとして設計され、CLI（python -m ...）で各エントリポイントを起動できます。

---

## 機能一覧

- Execution
  - 実際のブローカー（または Paper Trading 用 MockBroker）とのインタフェース
  - 注文管理、リスク管理、約定照合、セッション実行
  - Paper Trading 時は本番 DB と分離した data/paper_trading.db に記録

- Monitoring
  - CPU / メモリ / ディスク / プロセス稼働チェック
  - データ鮮度（DuckDB の prices_daily 等）チェック
  - 注文滞留・約定異常の検出
  - ドローダウン監視・ポジション上限監視
  - Kill Switch（条件成立時に data/kill.flag を書き込み、Execution を停止）
  - 監視ログは SQLite（デフォルト: data/monitoring.db）に永続化

- Research
  - モメンタム / ボラティリティ / バリューなどのファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー

- Portfolio
  - 候補選定（スコア順）
  - 等比重・スコア重み計算
  - リスクに応じたポジションサイズ決定（単元丸め、aggregate cap）
  - セクター集中制限、レジーム乗数の計算

- AI
  - ニュースを OpenAI に送って銘柄ごとにセンチメントを算出し ai_scores に保存
  - ETF + マクロ記事を組み合わせた市場レジーム判定（bull/neutral/bear）

- Tools
  - Paper Trading 検証レポート生成スクリプト
  - .env 対話式セットアップ（config_setup）、設定検証（validate_config）

- Utils
  - 統一的なログ設定（コンソール + 日次ローテートファイル）
  - プロセス優先度 / CPU affinity 設定

---

## セットアップ手順

以下は最小限のセットアップ手順例です。実際の環境に合わせて調整してください。

1. Python 仮想環境を作成・有効化
   - 推奨: Python 3.9+（プロジェクトの pyproject.toml 等に合わせる）

   ```bash
   python -m venv .venv
   source .venv/bin/activate  # POSIX
   .venv\Scripts\activate     # Windows
   ```

2. 依存パッケージをインストール
   - このリポジトリで直接 requirements.txt がない場合は、主要依存をインストールしてください:

   ```bash
   pip install duckdb psutil openai
   # オプション: YAML 検証や CLI 補助
   pip install PyYAML
   ```

3. .env を作成
   - 対話式ウィザードを利用するのが簡単です:

   ```bash
   python -m kabusys.config_setup
   ```

   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - よく使う環境変数:
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH: デフォルト data/kabusys.duckdb
     - SQLITE_PATH: デフォルト data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: paper_trading 時の DB（デフォルト data/paper_trading.db）
     - LOG_LEVEL, LOG_DIR
     - OPENAI_API_KEY（AI 機能使用時）

4. 設定検証（任意だが推奨）

   ```bash
   python -m kabusys.validate_config
   # 警告をエラー扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

5. データディレクトリ等の作成は多くのコードで自動作成されますが、念のため `data/` と `logs/` を作っておくと安全です。

   ```bash
   mkdir -p data logs
   ```

---

## 使い方（主要 CLI）

- 監視ループを起動（SystemMonitor を定期実行）

  ```bash
  python -m kabusys.run_monitoring
  ```

  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用します（環境に依存せず監視用 DB は本番パス）。

  - 停止:
    - プロジェクトルートの data/stop_requested.flag が存在すると監視ループは終了します。

- ExecutionEngine を起動（発注エンジン）

  ```bash
  python -m kabusys.run_execution
  ```

  - KABUSYS_ENV によって動作モードが変わります:
    - paper_trading: MockBrokerClient を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録
    - live: 実際のブローカークライアントを使用（env 設定 & ブローカー接続設定が必要）
  - 起動前に data/stop_requested.flag が既に存在すると起動せず終了します。
  - 実行中に data/stop_requested.flag を作成するとエンジンは停止します。

- Paper Trading 検証レポートの生成

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを指定
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- .env 対話式セットアップ

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  ```

- AI 関連（プログラム的に呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)

  これらは DuckDB の接続オブジェクトを受け取り、DB へ書き込みを行います。OpenAI API キーが必要です（api_key 引数または環境変数 OPENAI_API_KEY）。

---

## 停止 / Kill Switch / PID

- 停止フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring が監視しており、存在するとループを抜けます。
- Kill Switch:
  - monitoring が条件（ドローダウン・ポジション上限等）を検出した場合、data/kill.flag を書き込みます。ExecutionEngine は Kill Flag を見て停止します。
  - Settings.kill_flag_clear_on_start (0/1) を使い、起動時に自動クリアするかどうかを制御できます（本番では 0 推奨）。
- PID ファイル:
  - ExecutionEngine はデフォルトで data/execution.pid を使用します（Settings.pid_file_path）。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 動作モード / ログ / DB
  - KABUSYS_ENV: development | paper_trading | live
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR
  - LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
  - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
  - SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
  - PAPER_FILL_MODE: paper_trading 時の約定モード（instant|partial|never|reject）
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
  - OPENAI_API_KEY: OpenAI API キー（AI 機能で必要）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（"1"で有効）

詳しくは config.py の Settings クラス、および validate_config.py を参照してください。

---

## ディレクトリ構成（主要ファイル）

以下は src/kabusys 以下の主なファイルと機能のツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                    # 環境変数/.env 自動読み込み・Settings
    - config_setup.py              # .env 対話式ウィザード
    - validate_config.py           # 設定検証 CLI
    - run_execution.py             # ExecutionEngine 起動スクリプト
    - run_monitoring.py            # SystemMonitor 起動スクリプト
    - monitoring/
      - monitoring_db.py          # SQLite 永続化層
      - system_monitor.py         # システム状態 / データ鮮度監視
      - trade_monitor.py          # 注文監視（該当ファイル群あり）
      - risk_monitor.py           # ドローダウン / ポジション上限監視
      - kill_switch.py            # Kill Switch 実装
      - monitoring_engine.py      # 各 Monitor を束ねるエンジン
      - alert_manager.py          # アラート送信（LINE など）（該当ファイルがある想定）
    - execution/
      - execution_engine.py       # ExecutionEngine（セッション実行）
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
      - news_nlp.py               # ニュース NLP（OpenAI 経由）
      - regime_detector.py
    - tools/
      - paper_verification_report.py
    - data/                        # 実行時に使用するデータ（デフォルト: data/*.db, flags, pid 等）
    - logs/                        # ログ（デフォルトログ出力先）

（注）一部のサブモジュールやファイル（TradeMonitor の実装等）はここに抜粋されていない可能性があります。詳細はソースツリー全体を参照してください。

---

## 開発時の注意点 / 補足

- DuckDB / SQLite:
  - データ読み書き先はデフォルトで data/kabusys.duckdb（DuckDB）と data/monitoring.db（SQLite）です。環境変数で変更できます。
- Paper Trading:
  - KABUSYS_ENV=paper_trading のときは本番 DB と分離された PAPER_TRADING_SQLITE_PATH を使用します。発注は MockBroker による模擬約定になります。
- OpenAI:
  - OpenAI を使う機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しはリトライやフォールバック（失敗時はスコア 0 等）を行う実装になっていますが、呼び出し頻度やコストに注意してください。
- ロギング:
  - setup_logging は stdout（StreamHandler）と日次ローテーションファイル（TimedRotatingFileHandler）を設定します。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。
- 権限:
  - set_process_priority 等は OS による権限制約を受けることがあります（Linux の nice 値変更や Windows の優先度変更が失敗する場合は警告になります）。

---

README の内容はコードコメント・実装に基づく要約です。より詳細な設計や仕様（PortfolioConstruction.md / StrategyModel.md 等）がリポジトリ内にある場合はそちらも参照してください。質問や追加のドキュメント化したい箇所があれば教えてください。