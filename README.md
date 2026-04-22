# KabuSys

日本株向けの自動売買／リサーチ基盤の一部を実装した Python パッケージです。本リポジトリは注文実行エンジン、監視（Monitoring）、ポートフォリオ構築・ポジションサイズ計算、ファクター計算、ニュース NLP（OpenAI を利用）などのモジュール群を含みます。

## 概要

- 実運用を想定した設計（プロセス優先度設定、ログローテーション、SQLite/DuckDB を用いた永続化など）
- ペーパートレード（KABUSYS_ENV=paper_trading）に対応し、本番 DB と分離
- 監視コンポーネントでドローダウンや滞留注文等を検出し、必要に応じて kill.flag による停止シグナルを発行
- DuckDB を使ったリサーチ／ファクター計算モジュール（モメンタム、ボラティリティ、バリュー等）
- OpenAI（gpt-4o-mini 想定）を使ったニュースセンチメント評価・レジーム判定（オプション）

## 主な機能一覧

- ExecutionEngine（発注エンジン）
  - live / paper_trading / development 切替
  - RiskManager（ポジション上限・ドローダウン等）
  - OrderManager / Reconciler / OrderRepository
- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/Disk、データ鮮度、プロセス稼働監視
  - TradeMonitor: 注文・約定ログの監視（滞留注文・異常約定など）
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件を満たすと data/kill.flag を書き込み実稼働エンジンを停止
  - MonitoringEngine: 各監視コンポーネントのポーリング集約
- Portfolio（ポートフォリオ構築）
  - 候補選定、等配分／スコア配分、リスク制約（セクターキャップ）、ポジションサイズ計算（単元丸め）
- Research（リサーチ）
  - DuckDB を使ったファクター計算（momentum, volatility, value）
  - 将来リターン計算 / IC（Information Coefficient）評価 / 統計サマリー
- AI（オプション）
  - news_nlp: raw_news を LLM で評価し ai_scores を作成
  - regime_detector: マクロニュース＋ETF MA を合成して market_regime を判定
- ツール
  - config_setup: 対話式 .env 生成ウィザード
  - validate_config: 起動前の環境変数 / config/*.yaml の整合性チェック
  - tools.paper_verification_report: Paper Trading 検証レポート生成

## 必要条件 / 依存ライブラリ

- Python 3.10+
- 必要なパッケージ（例）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（validate_config で YAML 検証をする場合）
- 標準ライブラリ: sqlite3, logging, pathlib など

インストール例（仮想環境推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install duckdb psutil openai pyyaml
```

## セットアップ手順

1. リポジトリをクローン／配置
2. Python 仮想環境を作成して依存関係をインストール（上記参照）
3. .env を作成
   - 推奨: 対話式ウィザードで作成
   ```
   python -m kabusys.config_setup
   ```
   - 手動で作る場合は最低限以下の必須環境変数を設定してください:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - オプション:
     - OPENAI_API_KEY（ニュース NLP / レジーム判定に必要）
     - KABUSYS_ENV: development / paper_trading / live
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - その他 README 内の Keys を参照

4. 必要に応じて logs/ と data/ ディレクトリに書き込み権限を付与（setup_logging が自動作成を試みますが、権限によっては失敗することがあります）。

### 例: 最小 .env（参考）
（.env は絶対に Git にコミットしないでください）
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_api_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
```

## 起動・使い方

主要なエントリポイントはモジュール実行です。プロジェクトルート（pyproject.toml や .git がある位置）から実行してください。

- 環境設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証（起動前チェック）
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict   # 警告も FAIL 扱い
  ```

- ExecutionEngine（発注エンジン）起動
  ```
  python -m kabusys.run_execution
  ```
  動作内容:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ書き込みします。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid に PID を出力します。
  - process priority を "high" に設定しようとします（権限がない場合は警告ログ）。

- Monitoring（監視）を単体で起動
  ```
  python -m kabusys.run_monitoring
  ```
  動作内容:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き（デフォルト 60 秒）
  - 監視は本番 sqlite_path を使用（KABUSYS_ENV に依存せず）
  - data/stop_requested.flag が作られるとループを終了
  - logging は logs/monitoring.log 日次ローテーションで出力

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - --db で別の SQLite ファイルを指定できます（PAPER_TRADING_SQLITE_PATH 環境変数でも指定可能）

- AI 関連（ニュース NLP / レジーム判定）
  - OpenAI API キーが必要（環境変数 OPENAI_API_KEY または関数引数で渡す）
  - これらはライブラリ関数として呼び出すことを想定しています。例:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, target_date=date(2026,4,1), api_key="sk-...")
    ```
  - 実行中の API 呼び出しはレート制限や接続エラーに対してエクスポネンシャルバックオフでリトライします。失敗してもフェイルセーフで処理継続します。

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視用 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading の専用 DB）
- OPENAI_API_KEY（AI 機能で必要）
- LOG_LEVEL（DEBUG / INFO / WARNING / ERROR / CRITICAL）
- MONITOR_POLL_INTERVAL（run_monitoring のポーリング間隔秒数）
- KILL_FLAG_CLEAR_ON_START（Execution 起動時に kill.flag を自動クリアするか、"1" で有効）

## ファイル・フラグの意味

- data/stop_requested.flag
  - run_monitoring / run_execution が監視している「プロセス停止要求」フラグ。存在するとループ／エンジンが終了する。
- data/kill.flag
  - KillSwitch が書き込むフラグ。存在すると ExecutionEngine の停止トリガーになる（本番での非常停止用）。
- data/execution.pid
  - ExecutionEngine が起動時に PID を書き込むファイル。
- data/monitoring.db（デフォルト SQLITE_PATH）
  - 監視ログ（system_status / trade_logs / risk_logs / positions / dashboard）を保存する SQLite DB
- data/paper_trading.db
  - ペーパートレード時の発注ログ保存先（paper_trading モード）
- logs/
  - logs/<app_name>.log に TimedRotatingFileHandler（日次）でログが保存される

## ディレクトリ構成（主要ファイル）

リポジトリ内の主要なパッケージ構成（src/kabusys）:

- kabusys/
  - __init__.py
  - config.py                — 環境変数/設定ロード
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
  - execution/
    - execution_engine.py
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
  - data/
    - pipeline.py (prices_daily 等の取り回し)
  - utils/
    - logging_setup.py
    - process_priority.py

（上記は代表的ファイル群で、詳細はソースツリーを参照してください。）

## 開発 / トラブルシューティング

- validate_config を先に実行して設定漏れや YAML ファイルの不整合を検出してください。
- ログディレクトリの作成に失敗するとファイルハンドラは無効化され、コンソールログのみになります。パーミッションを確認してください。
- OpenAI 関連の API 呼び出しではレート制限や一時的なネットワーク障害に対して内部でリトライしますが、API キーの制限・料金には注意してください。
- duckdb / psutil 等のネイティブ依存でプラットフォーム差分がある場合は、該当パッケージのインストールエラーやシステム要件（lib を要するケース）を確認してください。
- KABUSYS_ENV=live の場合は設定ミスが致命的になり得るため、validate_config を入念に確認してください。

## ライセンス / バージョン

- パッケージバージョンは kabusys.__version__ で参照できます（例: "0.1.0"）。
- ライセンス情報はリポジトリの LICENSE ファイル（存在する場合）を参照してください。

---

この README はコードベースの重要な運用ポイントをまとめたものです。個別のモジュール（例えば ExecutionEngine の API、OrderRepository の仕様、AI モジュールの入出力フォーマットなど）については、該当ソースファイルの docstring / コメントを参照してください。必要であれば各モジュールの詳細ドキュメント（使用例・API シグネチャ）を別途作成できます。