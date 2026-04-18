# KabuSys

日本株自動売買システムの主要ライブラリ群と起動スクリプト群を含むリポジトリ。  
この README は、プロジェクトの概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

> 注意: 本リポジトリはライブラリと複数の起動スクリプト（ExecutionEngine / Monitoring 等）を含みます。実際のブローカー接続や API キーの扱いは環境依存です。設定ファイルや環境変数を適切に設定してから起動してください。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システム基盤（分析、ポートフォリオ構築、発注エンジン、監視、AI 支援モジュール等）を提供します。主な機能は以下の通りです。

- 戦略開発向け研究モジュール（ファクター計算、特徴量探索）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算、セクター制限）
- Execution エンジン（ブローカークライアント経由の発注ロジック、リスク管理、注文管理）
- 監視機構（システム状態、注文ログ、リスク監視、Kill Switch）
- AI モジュール（ニュース NLP によるセンチメント、レジーム判定）
- ペーパートレード用の分離された DB 機能と検証レポート

---

## 主な機能一覧

- kabusys.research
  - calc_momentum / calc_volatility / calc_value：DuckDB の prices_daily, raw_financials を使ったファクター計算
  - calc_forward_returns / calc_ic / factor_summary：特徴量評価・IC 計算等
- kabusys.portfolio
  - select_candidates / calc_equal_weights / calc_score_weights
  - calc_position_sizes：リスクベース／等配分等の株数決定
  - apply_sector_cap / calc_regime_multiplier：セクター集中制限・レジーム乗数
- kabusys.ai
  - news_nlp.score_news：ニュース記事を LLM（OpenAI）でスコア化し ai_scores に書き込む
  - regime_detector.score_regime：ETF の MA とマクロニュースで市場レジーム判定
- kabusys.monitoring
  - MonitoringDB：SQLite を使った監視ログの永続化
  - SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine：定期チェック・アラート・Kill Switch
  - KillSwitch：条件に応じて data/kill.flag を書き込むことで ExecutionEngine を停止させる
- 起動/運用ツール
  - config_setup：.env の対話式ウィザード生成
  - validate_config：環境変数・設定ファイルの事前チェック CLI
  - run_execution：ExecutionEngine 起動スクリプト
  - run_monitoring：監視ループ起動スクリプト
  - tools.paper_verification_report：ペーパートレード検証レポート生成

---

## 必須 / 推奨依存パッケージ

（最低限の例。環境により追加が必要な場合があります）

- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config 検証で YAML の検証を行う場合）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## 設定 (環境変数・.env)

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から読み込まれます。自動読み込みはデフォルトで有効です（プロジェクトルートは .git または pyproject.toml を基準に検出）。自動ロードを無効化するには:

```
export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
```

主な環境変数（一覧）:

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
- LINE_CHANNEL_ACCESS_TOKEN（任意）
- LINE_USER_ID（任意）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）
- KABUSYS_ENV（development | paper_trading | live、デフォルト: development）
- LOG_LEVEL（DEBUG|INFO|WARNING|ERROR|CRITICAL、デフォルト: INFO）
- KILL_FLAG_CLEAR_ON_START（0|1、デフォルト: 0）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト: 60）
- PAPER_FILL_MODE（paper_trading 時の約定挙動: instant|partial|never|reject）

.env の作成はウィザードで簡単に行えます（下記参照）。

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローンして移動
2. 仮想環境を作成して依存をインストール
   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb psutil openai pyyaml
   ```
3. .env を作成
   - 対話ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```
     python -m kabusys.validate_config
     # strict モード（警告も FAIL とする）:
     python -m kabusys.validate_config --strict
     ```
4. データ / ログ ディレクトリ作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要コマンド）

- ExecutionEngine の起動
  - 本番・開発・paper_trading は KABUSYS_ENV を切り替えて制御
  - Paper Trading の場合は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用
  ```
  # 例: paper_trading 環境で起動
  export KABUSYS_ENV=paper_trading
  python -m kabusys.run_execution
  ```
  - ExecutionEngine は data/stop_requested.flag の存在を監視し、停止します。
  - 実行時に `data/execution.pid`（pid ファイル）を使用します。

- Monitoring の起動
  - ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）
  ```
  python -m kabusys.run_monitoring
  # 例: 30秒間隔
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - run_monitoring は監視 DB（settings.sqlite_path）を使用します（監視は本番 DB パスを使う設計の箇所あり）。
  - 停止フラグ: data/stop_requested.flag を検出するとループを終了します。

- 設定関連
  ```
  python -m kabusys.config_setup        # .env の対話式作成/更新
  python -m kabusys.validate_config    # 設定検証（--strict オプションあり）
  ```

- Paper Trading レポート（ツール）
  ```
  python -m kabusys.tools.paper_verification_report
  # 期間指定例:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- プログラムから呼び出す例（DuckDB / SQLite 接続を渡して利用）
  ```py
  import duckdb
  from kabusys.ai.news_nlp import score_news
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  # OpenAI API キーは環境変数 OPENAI_API_KEY をセット
  score_news(conn, target_date=date(2026, 4, 11))
  ```

---

## kill/stop フラグ & PID

- 実行制御ファイル（デフォルト path）
  - data/kill.flag — Kill Switch（監視が発動するとここに理由を書き込み、Execution を停止するトリガーになる）
  - data/stop_requested.flag — run_monitoring / run_execution が監視している停止フラグ（手動で停止要求を出す際に使用）
  - data/execution.pid — ExecutionEngine の PID を格納

- KillSwitch は監視コンポーネントのチェック結果（ドローダウン超過など）により自動的に kill.flag を書き込む設計です。実運用時は kill.flag の扱いに注意してください（KILL_FLAG_CLEAR_ON_START=1 は危険な設定になる可能性があります）。

---

## その他の注意点 / 実装メモ

- DB 分離
  - ExecutionEngine は KABUSYS_ENV によって paper_trading モード時に PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）を使います。本番 DB と完全に分離されます。
  - 監視用 DB（monitoring）は monitoring 用の sqlite_path（デフォルト data/monitoring.db）を使用します。run_monitoring の実装コメントに「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」とあるため、監視側の DB の扱いに注意してください。

- ロギング
  - 共通ユーティリティ `kabusys.utils.logging_setup.setup_logging` によりコンソール（stdout）と日次ローテーションのファイルログ（logs/<app_name>.log）を設定します。LOG_DIR 環境変数または引数で保存先を変更できます。

- .env ファイル読み込みルール
  - 読み込み優先順: OS 環境変数 > .env.local > .env
  - `.env.local` は `.env` の上書きに使われます。
  - `.env` 自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

- AI 機能
  - OpenAI を利用する機能は API キー（OPENAI_API_KEY）を参照します。API の呼び出しはリトライとバックオフを組み込んでいますが、API 利用料やレート制限に注意してください。
  - news_nlp と regime_detector は LLM のレスポンスを JSON モードで期待していますが、厳密なバリデーションとフェイルセーフ処理を行います。

- Optional: PyYAML が無い場合、validate_config は config/*.yaml の内容検証をスキップします（警告）。

---

## ディレクトリ構成

リポジトリ内の主要ファイル/ディレクトリ（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - config_setup.py
    - validate_config.py
    - run_execution.py
    - run_monitoring.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py (参照実装がある想定)
    - execution/
      - execution_engine.py
      - broker_factory.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - utils/
      - __init__.py
      - logging_setup.py
      - process_priority.py
    - data/   (runtime 用: SQLite/duckdb/flag/pid 等を配置)
- logs/     (デフォルトのログ出力先)

（実際のリポジトリでは src をパッケージルートとして使うことを想定しています）

---

## よく使うコマンドまとめ

- 仮想環境作成 / 依存インストール
  ```
  python -m venv .venv
  source .venv/bin/activate
  pip install duckdb psutil openai pyyaml
  ```

- .env ウィザード / 検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

- Execution 起動
  ```
  export KABUSYS_ENV=live   # または paper_trading / development
  python -m kabusys.run_execution
  ```

- Monitoring 起動
  ```
  export MONITOR_POLL_INTERVAL=60
  python -m kabusys.run_monitoring
  ```

- Paper Trading レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

## サポート / 開発メモ

- テストや CI では `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると .env 自動ロードを無効化して静かな環境にできます。
- DuckDB コネクションを渡す設計のため、分析関数は外部副作用が少なく単体テストが容易です。
- 実稼働では kill.flag や stop_requested.flag の扱い、KILL_FLAG_CLEAR_ON_START の設定に特に注意してください。

---

必要に応じて README を拡張します。たとえば、実際の起動フロー図、各設定項目の詳細説明、サンプル .env テンプレート、CI 用の起動コマンド例などを追加できます。どの情報を優先して追加しましょうか？