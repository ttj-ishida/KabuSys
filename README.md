# KabuSys — README (日本語)

このリポジトリは日本株向けの自動売買・研究プラットフォームの一部実装です。
主な機能はシグナル生成 / ポートフォリオ構築 / 注文実行 / 監視 / レポート生成 / ニュース NLU による市場セン勢評価などです。

下記はこのコードベースの概要・セットアップ手順・使い方・ディレクトリ構成の説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを想定したモジュール群です。主な責務は次のとおりです。

- データ取り込み・分析（DuckDB を利用したファクター計算、研究用モジュール）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算）
- 注文実行層（Broker クライアント抽象化、ExecutionEngine）
- 監視・アラート（System / Trade / Risk の監視、Kill Switch）
- AI 補助（ニュースセンチメントの LLM によるスコアリング、市場レジーム判定）
- 開発補助ツール（.env ウィザード、設定検証、Paper Trading レポート生成）

設計上の特徴：
- 本番 / ペーパートレードを環境変数 `KABUSYS_ENV` で切替可能（`development`/`paper_trading`/`live`）。
- Paper Trading（ペーパートレード）は本番 DB と分離された SQLite（デフォルト `data/paper_trading.db`）を使用。
- DuckDB を分析用データベースとして利用。
- OpenAI（gpt-4o-mini 等）を用いたニュース解析モジュールを備える（API キー必須）。

---

## 主な機能一覧

- 環境設定ウィザード（`.env` の対話式生成）
  - `python -m kabusys.config_setup`
- 設定検証 CLI
  - `python -m kabusys.validate_config [--strict]`
- Execution エンジン起動スクリプト
  - `python -m kabusys.run_execution`
  - `KABUSYS_ENV=paper_trading` の場合は MockBroker を使い DB を分離
  - 停止は `data/stop_requested.flag` / `data/kill.flag` を利用
- Monitoring 起動スクリプト
  - `python -m kabusys.run_monitoring`
  - ポーリング間隔は `MONITOR_POLL_INTERVAL` 環境変数で上書き可（デフォルト 60 秒）
- 監視コンポーネント
  - SystemMonitor（CPU/メモリ/Disk・データ鮮度・Execution プロセス死活）
  - TradeMonitor（滞留注文・約定異常など）
  - RiskMonitor（ドローダウン・保有数上限の監視）
  - KillSwitch（条件で `data/kill.flag` を書き込み Execution を停止）
- ポートフォリオ構築
  - 候補選定、重み計算（等金額/スコア加重）、ポジションサイズ計算（リスクベース等）
  - セクター制約、レジームに応じた乗数
- 研究 / ファクター計算（DuckDB ベース）
  - momentum / volatility / value 等のファクター実装
  - 将来リターン・IC 計算・統計サマリ
- AI モジュール
  - news_nlp: ニュース集合から銘柄別センチメントを LLM で算出して `ai_scores` に格納
  - regime_detector: ETF（1321）の MA200 とマクロニュースを合成して market_regime を判定
- ツール
  - Paper Trading 検証レポート生成（`python -m kabusys.tools.paper_verification_report`）

---

## セットアップ手順（開発環境向け）

以下はローカルで動かすための一般的な手順です。実際の依存関係は `requirements.txt` 等に合わせてください。

1. リポジトリをクローン、ルートに移動
   - 例: git clone ... && cd repo

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - Windows: .\.venv\Scripts\activate
   - macOS/Linux: source .venv/bin/activate

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   - ※ OpenAI、psutil、duckdb、PyYAML 等が必要です。

4. 環境変数（.env）を作成
   - 対話式ウィザードを推奨:
     - python -m kabusys.config_setup
   - あるいは手動で `.env` を作成（以下「主要な環境変数」を参照）

5. 設定検証
   - python -m kabusys.validate_config
   - 問題があれば修正

6. データディレクトリの用意（必要に応じて）
   - デフォルトの DB / log / data フォルダを作成:
     - mkdir -p data logs

7. DuckDB / SQLite の初期テーブルはスクリプト実行時に自動作成される箇所があります（例: init_monitoring_db）ので、通常は空ファイルパス指定で問題ありません。

重要:
- OpenAI を使う機能を利用する場合は環境変数 `OPENAI_API_KEY` を設定してください。
- `KABUSYS_ENV` を `live` にする場合は十分な注意を払い、LINE 通知等の設定も確認してください。

---

## 環境変数（主要なもの）

（対話式ウィザードで設定される主なキーとデフォルトの説明）

- KABUSYS_ENV: 実行環境（development / paper_trading / live） — デフォルト: development
- JQUANTS_REFRESH_TOKEN: J-Quants API 用リフレッシュトークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- KABU_API_BASE_URL: kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレードの約定モード（instant|partial|never|reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR）
- LOG_DIR: ログ保存先（デフォルト logs/）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）

参考: `python -m kabusys.config_setup` を実行すると項目ごとに説明を見ながら .env を作れます。

---

## 使い方（主要コマンド）

- 環境の対話式セットアップ
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード（警告も失敗にする）: python -m kabusys.validate_config --strict

- Execution エンジン起動（本番 / ペーパートレードを .env の KABUSYS_ENV で切替）
  - python -m kabusys.run_execution
  - 停止: プロセスに対する通常の SIGINT/Ctrl-C、または `data/stop_requested.flag` を作成すると終了処理が行われます。
  - Execution は起動時に PID ファイル（デフォルト data/execution.pid）を使用します。

- Monitoring 起動
  - python -m kabusys.run_monitoring
  - ポーリング間隔を上書き: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定: --db path/to/paper_trading.db（未指定なら環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

- AI モジュール（プログラムから利用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用

- テスト用: MonitoringEngine を単発実行する等のユーティリティはコード上に用意されています（unittest やスクリプトで呼び出す想定）。

---

## 停止 / Kill Switch の使い方

- Execution を外部から安全に停止したい場合：
  - `data/kill.flag` を作成すると、Monitoring の KillSwitch が検出して Execution に停止指示を出します（実際の停止は ExecutionEngine 側の実装に依存）。
  - `data/stop_requested.flag` は run_monitoring や run_execution の外部停止フラグとして使われます（これが存在すると起動ループが終了します）。
- KillSwitch はドローダウン超過やポジション上限超過などの条件で自動的に `data/kill.flag` を書き込むよう設計されています。

注意:
- 環境変数 `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

---

## ロギング & プロセス優先度

- logging_setup.setup_logging(app_name="...") により、標準出力（stdout）と日次ローテートのファイルログ（logs/<app_name>.log）を設定します。
- run_monitoring.py / run_execution.py は起動時に set_process_priority("high") を呼び出し、可能ならプロセス優先度を上げます（psutil を利用、権限により失敗する場合は警告）。

---

## ディレクトリ構成（重要ファイル・モジュール）

以下は `src/kabusys` 配下の主要な構成の抜粋です。実際はパッケージルートで管理されます。

- kabusys/
  - __init__.py
  - config.py                    — 環境変数 / 設定管理
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - execution/                   — 実行エンジン関連（Engine, OrderManager 等）
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
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
  - data/ (runtime 用; DB / flags 等)
  - logs/ (ログ出力先、デフォルト)

（上記は代表的ファイルです。詳細はリポジトリのソースを参照してください）

---

## 注意点・運用上のヒント

- Paper Trading は本番 DB と分離されるよう配慮されています。必ず `KABUSYS_ENV=paper_trading` を正しく設定してください。
- OpenAI 呼び出しにはネットワーク・API 失敗が起きうるため、該当モジュールは冪等性・リトライ・フェイルセーフを備えています。API キーの管理に注意してください。
- ログディレクトリ作成やプロセス優先度設定は環境依存で失敗することがあります（権限不足等）。起動時のワーニングを確認してください。
- DB マイグレーション（monitoring_db の追加カラム）は起動時に自動で行われる仕組みがありますが、念のためバックアップをとってから起動してください。
- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START` を `0` にしておくことを推奨します。

---

README は以上です。個別のモジュールや関数の詳細な使い方（API 仕様や引数の意味）はソースコードの docstring を参照してください。必要であれば、各サブモジュールごとの詳細 README を作成します。どの部分をより詳しく説明しますか？