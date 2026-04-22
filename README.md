# KabuSys

日本株向け自動売買システムの一部モジュール群。ポートフォリオ構築、リスク制御、監視、Paper Trading 検証、LLM を用いたニュース評価などのユーティリティを含みます。

この README はリポジトリ内の主要スクリプト・ライブラリの使い方、セットアップ手順、ディレクトリ構成をまとめたものです。

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール群で構成されたシステムです。

- ポートフォリオ構築（候補選定、重み計算、銘柄ごとの株数決定）
- リスク調整（セクター上限、レジーム乗数）
- 監視（システム状態、注文状況、リスク監視）と Kill Switch（フラグファイルによる停止信号）
- 実行エンジン起動スクリプト（本番 / ペーパートレード分離）
- Paper Trading 検証レポート生成ツール
- リサーチ用ファクター計算・特徴量解析（DuckDB を前提）
- OpenAI を用いたニュース NLP（銘柄別センチメント）および市場レジーム判定

多くの処理はデータベース（SQLite / DuckDB）と環境変数設定に依存します。

---

## 主な機能一覧

- portfolio
  - select_candidates（スコア上位選定）
  - calc_equal_weights / calc_score_weights（配分重み）
  - calc_position_sizes（株数決定、lot 単位丸め・aggregate cap）
  - apply_sector_cap（セクター集中の除外）
  - calc_regime_multiplier（市場レジームに応じた投下資金乗数）

- monitoring
  - SystemMonitor：CPU/メモリ/ディスク、データ鮮度、Execution プロセス監視
  - TradeMonitor / RiskMonitor：注文滞留・約定異常、ドローダウン・ポジション上限監視
  - MonitoringDB：監視ログ（SQLite）への永続化
  - KillSwitch：条件により data/kill.flag を書き込み Execution を停止

- execution
  - run_execution.py：ExecutionEngine を起動（KABUSYS_ENV=paper_trading の場合はモックブローカーを使用し paper_trading DB に分離）

- monitoring
  - run_monitoring.py：SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔を上書き可能）

- ai
  - news_nlp.score_news：OpenAI を用いた銘柄別ニュースセンチメント
  - regime_detector.score_regime：マクロセンチメントと ETF MA 乖離から市場レジーム判定

- tools
  - paper_verification_report：Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等を評価）

- 設定・ヘルパー
  - config_setup.py：.env 初期ウィザード（対話式）
  - validate_config.py：.env と config/*.yaml の事前検証
  - utils.logging_setup：統一ログ設定（stdout + 日次ローテーション）
  - utils.process_priority：プロセス優先度の設定（Windows / POSIX 対応）

---

## セットアップ手順（ローカル開発用）

1. リポジトリをクローンして作業ディレクトリへ移動
   (ここでは src/ 配下にパッケージがあることを前提)

2. Python 仮想環境作成・有効化
   - Unix/macOS:
     ```
     python -m venv .venv
     source .venv/bin/activate
     ```
   - Windows (PowerShell):
     ```
     python -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```

3. 必要なパッケージをインストール
   - 本コードで参照している主な外部依存:
     - duckdb
     - psutil
     - openai
     - PyYAML（config の YAML 検証に任意で使用）
   - 例:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - （プロジェクトに requirements.txt があれば `pip install -r requirements.txt` を使用）

4. .env の準備
   - 対話式ウィザードで作成:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは .env.example を参照して手動作成してください。
   - 自動読み込み: 起動時に .env, .env.local が自動ロードされます（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。

5. デフォルトのデータディレクトリ
   - SQLite / DuckDB のデフォルトパス:
     - DUCKDB_PATH: data/kabusys.duckdb
     - SQLITE_PATH: data/monitoring.db
     - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード用、KABUSYS_ENV=paper_trading 時に使用）
   - ログ: logs/（setup_logging により自動作成を試みます）

---

## 必須／主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- OPENAI_API_KEY（AI 機能を使う場合に必須）
- DUCKDB_PATH, SQLITE_PATH（DB パスを上書きする場合）
- LOG_LEVEL（例: INFO, DEBUG）
- PAPER_FILL_MODE（paper_trading 用: instant | partial | never | reject、デフォルト "instant"）
- KILL_FLAG_CLEAR_ON_START（本番での自動クリア回避に注意）

.env の例（config_setup で生成される項目）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_value_here
KABU_API_PASSWORD=your_value_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方（起動例）

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も失敗扱い
  ```

- .env 作成ウィザード
  ```
  python -m kabusys.config_setup
  ```

- ExecutionEngine の起動
  - 本番 / ペーパーは KABUSYS_ENV による
  ```
  python -m kabusys.run_execution
  ```
  - 挙動のポイント:
    - 起動直後にプロセス優先度を "high" に設定しようとします（プラットフォーム依存で失敗する場合は警告）。
    - KABUSYS_ENV=paper_trading のとき、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - 停止シグナル: プロジェクトルート/data/stop_requested.flag を作成するとエンジンは停止します。ExecutionEngine は起動時に kill.flag のクリア設定などを参照します（Settings.kill_flag_clear_on_start）。

- Monitoring の起動（SystemMonitor のポーリング）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - Monitoring は KABUSYS_ENV にかかわらず Settings.sqlite_path（本番監視 DB）を使用します。
  - 停止シグナル: data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db オプションで SQLite パスを指定可能。環境変数 PAPER_TRADING_SQLITE_PATH でも指定可。
  - レポートは標準出力に表示され、稼働率・注文成功率・送信率・レイテンシ等を評価して PASS/FAIL を出します。

- AI 関連（ニュース NLP / レジーム判定）
  - 実行時は OPENAI_API_KEY 環境変数を設定してください。
  - 関数をプログラムから呼ぶ例（DuckDB 接続を渡す）:
    ```py
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime
    # duckdb_conn: duckdb.connect(...)
    # target_date: datetime.date(...)
    score_news(duckdb_conn, target_date, api_key=None)     # 環境変数 OPENAI_API_KEY を使用
    score_regime(duckdb_conn, target_date, api_key=None)
    ```
  - 注意点:
    - API 呼び出しはリトライロジックを含むが、API キー未設定時は例外になります。
    - レスポンスのバリデーション・部分失敗時の保護ロジックが組み込まれています。

---

## 運用上の注意

- Kill Switch / stop フラグ
  - KillSwitch は Conditions を満たすと data/kill.flag に理由を書き込みます。ExecutionEngine 起動時や監視からこのファイルの存在を参照して安全停止します。
  - validate_config は本番環境（KABUSYS_ENV=live）で KILL_FLAG_CLEAR_ON_START=1 が設定されている場合に警告を出します（自動クリアは危険）。

- データベースマイグレーション
  - monitoring_db.init_monitoring_db は初回作成と簡易マイグレーション（カラム追加）を行います。既存 DB に新カラムがなければ ALTER TABLE による追加を試みます。

- ロギング
  - setup_logging を各起動スクリプトが呼び出しており、標準出力に加えて logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成に失敗した場合はコンソール出力のみになります。

---

## ディレクトリ構成（主要ファイル）

（パッケージルートは src/kabusys を想定）

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理（.env 自動読み込みロジック含む）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - (trade_monitor.py, alert_manager.py 等、監視関連モジュールが参照される)
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py

- config/
  - system_config.yaml
  - data_config.yaml
  - strategy_config.yaml
  - risk_config.yaml
  - execution_config.yaml
  - monitoring_config.yaml
  (validate_config.py で参照)

- data/
  - (デフォルトで DB やフラグファイルが置かれる想定: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid 等)

- logs/
  - (ログファイルがここへ出力される: execution.log, monitoring.log, ...)

---

## 開発者向けメモ

- DuckDB を使ったリサーチ/ファクター計算は、prices_daily / raw_financials / raw_news 等のテーブルが前提です。
- LLM 呼び出し部分（news_nlp / regime_detector）は外部 API（OpenAI）に依存しています。単体テストでは API コール部をモックする設計になっています（内部呼出し関数を差し替え可能）。
- 設定の自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。CWD に依存しない探索アルゴリズムを採用しています。

---

必要であれば README に「運用手順（systemd / supervisor 用の unit 例）」「Dockerfile / compose サンプル」「より詳細な設定例（.env.example の全文）」など追加できます。どの情報を優先的に追加しますか？