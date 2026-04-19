# KabuSys

日本株向け自動売買システムのコードベース。戦略・ポートフォリオ構築、発注実行、監視、リサーチ、ニュースNLP（OpenAI）などの主要コンポーネントを含むモジュラーな設計です。

バージョン: 0.1.0

---

## 概要

KabuSys は以下の役割をもつコンポーネント群から構成されます：

- ExecutionEngine: 発注・注文管理・リスク制御を行う実行エンジン。paper_trading モードをサポート（モックブローカー、専用 SQLite）。
- Monitoring: システム稼働状況、データ鮮度、注文/約定の異常、ドローダウン等を定期監視し、必要に応じて Kill Switch（停止フラグ）を発動。
- Portfolio: 銘柄選定、配分重み計算、ポジションサイズ決定、セクター制約など純粋関数群。
- Research: DuckDB を用いたファクター計算（Momentum / Value / Volatility など）と特徴量解析。
- AI モジュール: ニュースを LLM（OpenAI）でスコアリングして銘柄/マクロ判定に活用。
- Tools: ペーパートレードの検証レポート生成などユーティリティスクリプト。
- 設定ユーティリティ: `.env` 作成ウィザード、設定検証ツール。

設計方針の一部：
- 本番 DB と paper_trading DB を分離。
- ルックアヘッド（datetime.today() 依存）を避ける実装方針。
- フェイルセーフ：外部 API 失敗時はデフォルト値で継続するなど。

---

## 主な機能一覧

- 実行エンジン（ExecutionEngine）
  - ブローカークライアント抽象化（本番 / Mock）
  - 注文管理、リスク管理、再整合処理（Reconciler）
  - PID / stop フラグ連携

- 監視（Monitoring）
  - システム資源（CPU/MEM/DISK）および Execution プロセス監視
  - 注文ログ / 約定の監視（滞留注文、異常約定検出）
  - ドローダウン / ポジション上限監視と Kill Switch 発動
  - アラート発行フック（LINE などの設定あり）

- ポートフォリオ構築
  - 候補選定、等分/スコア加重配分
  - セクターキャップ適用、レジーム乗数
  - リスクベースや等分によるポジションサイズ計算、単元株丸め

- リサーチ
  - DuckDB ベースのファクター計算（モメンタム、ボラティリティ、バリュー）
  - 将来リターン・IC（情報係数）計算、統計サマリ

- AI（OpenAI）
  - ニュースを LLM でセンチメント評価し ai_scores に書き込み
  - マクロニュースを用いた市場レジーム判定（regime_detector）

- ツール
  - paper_trading 検証レポート生成スクリプト

---

## 前提（Prerequisites）

- Python 3.9+
- 必須 Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - （検証用に）PyYAML（必須ではないが validate_config は YAML パースを試みる）
- SQLite（標準ライブラリの sqlite3 を使用）
- OpenAI を使用する場合は API キー（環境変数 OPENAI_API_KEY）

パッケージはプロジェクトに requirements ファイルがあればそれを利用してください。なければ pip で個別にインストールします。

---

## セットアップ手順

1. リポジトリをチェックアウト：
   - git clone ... またはプロジェクトを展開

2. 仮想環境の作成（推奨）：
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージをインストール：
   - pip install duckdb psutil openai
   - （検証・ツール用）pip install pyyaml

4. 環境変数 / .env の初期作成：
   - 対話式ウィザードで .env を生成:
     - python -m kabusys.config_setup
   - 生成後、必要なシークレット（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、OPENAI_API_KEY など）を設定してください。

5. 設定検証（任意だが推奨）：
   - python -m kabusys.validate_config
   - --strict を付けると警告もFAIL扱い（exit code 1）

6. データディレクトリ作成（必要に応じて）：
   - デフォルトで data/、logs/ が使われます。起動時に自動生成される場合がありますが、権限などに注意してください。

---

## 環境変数（主要）

主な環境変数（.env に設定）：

必須:
- JQUANTS_REFRESH_TOKEN: J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD: kabuステーション API パスワード

任意 / デフォルトあり:
- KABUSYS_ENV: 実行環境（development / paper_trading / live） default=development
  - paper_trading の場合、MockBrokerClient を使い PAPER_TRADING_SQLITE_PATH に記録
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO（DEBUG, INFO, WARNING, ERROR, CRITICAL）
- LOG_DIR: ログ出力ディレクトリ（default: logs）
- OPENAI_API_KEY: OpenAI API キー（AI関連機能で必要）
- PAPER_FILL_MODE: paper_trading 時の約定モード（instant/partial/never/reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1/0, default 0）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring 側で参照） default=60

注意:
- 本番モード（KABUSYS_ENV=live）では特に LINE 通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）や KILL_FLAG_CLEAR_ON_START の値に注意してください。

---

## 使い方（実行方法）

- 実行エンジン（本番 / paper_trading）を起動：
  - python -m kabusys.run_execution
    - 起動時に PID ファイル（data/execution.pid）や stop flag（data/stop_requested.flag）を確認します。
    - paper_trading の場合は settings.is_paper が True になり、専用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録します。

- 監視ループを起動：
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は Settings に依存して本番 sqlite_path を使用（監視ログは monitoring.db に書き込まれます）。

- 設定ウィザード（.env 生成）：
  - python -m kabusys.config_setup

- 設定検証：
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポートを生成：
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI スコアリング（プログラム的に呼び出す）：
  - from kabusys.ai import score_news
  - score_news(conn, target_date, api_key=None)
  - OPENAI_API_KEY を環境変数に設定するか、api_key 引数で渡してください。
  - market regime 関連は kabusys.ai.regime_detector モジュールの関数を直接インポートして呼び出せます（score_regime など）。

- ログ：
  - デフォルトは logs/<app_name>.log（daily rotation, 30 日保存）と stdout。
  - setup_logging(app_name="execution" | "monitoring") が起動スクリプトで呼ばれます。

- Kill / Stop フラグ：
  - 監視モジュールや外部によって data/kill.flag（KillSwitch）を書き込むと ExecutionEngine に停止シグナルを送ります。
  - 停止要求一時停止用に data/stop_requested.flag を作成すると run_* スクリプトがループを終了します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定すると kill.flag を自動クリアします（本番では推奨しません）。

---

## 重要な挙動メモ

- run_monitoring は常に本番 sqlite_path を使って監視ログを書きます（KABUSYS_ENV に依存せず）。
- run_execution は KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録します（本番 DB と分離）。
- process priority: 起動スクリプトは最初に set_process_priority("high") を試みます。権限不足や未対応 OS では警告を出してスキップします。
- OpenAI 関連機能は API キー未設定時は ValueError を送出するケースがあるため、事前に設定してください（score_news, score_regime など）。

---

## ディレクトリ構成（主要ファイル）

src/kabusys/ 以下を要約：

- __init__.py
- config.py                      — 環境変数読み込み / Settings クラス
- config_setup.py                — .env 対話式ウィザード
- validate_config.py             — 設定検証 CLI
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — Monitoring ポーリング起動スクリプト

- ai/
  - news_nlp.py                   — ニュース NLP（OpenAI）集約・スコア保存
  - regime_detector.py            — 市場レジーム判定（マクロ + MA200 合成）
  - __init__.py

- monitoring/
  - monitoring_db.py              — SQLite 用永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py             — CPU/MEM/DISK/プロセス監視、データ鮮度チェック
  - trade_monitor.py              — （注文関連監視 — リポジトリに含む）
  - risk_monitor.py               — ドローダウン / ポジション数監視
  - kill_switch.py                — flag ファイルで停止シグナルを出すユーティリティ
  - monitoring_engine.py          — 複数モニタを束ねるエンジン
  - alert_manager.py              — （アラート送信の抽象管理）

- execution/
  - execution_engine.py           — 実行エンジン本体
  - broker_factory.py             — BrokerClient の生成（Mock / Live）
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py

- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py

- tools/
  - paper_verification_report.py
  - __init__.py

- utils/
  - logging_setup.py
  - process_priority.py
  - __init__.py

- data/                          — 実行時に使用されるファイル（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag, execution.pid）
- logs/                          — ログファイル出力先（デフォルト）

---

## トラブルシューティング

- validate_config が YAML をチェックできない場合:
  - PyYAML がインストールされていないと YAML 内容の検証はスキップされ、警告が出ます。pip install pyyaml を検討してください。

- OpenAI 呼び出しで失敗する場合:
  - OPENAI_API_KEY が未設定の場合は ValueError が発生します。
  - API の一時エラー（429/ネットワーク等）はモジュール側でリトライを実装していますが、最終的に失敗したチャンクはスキップされます。

- ログファイルが作れない場合:
  - 権限やパスの問題でログディレクトリ作成に失敗するとファイルハンドラはスキップされ、コンソール出力のみになります。起動ログに注意してください。

- MONITOR_POLL_INTERVAL の設定:
  - 環境変数 MONITOR_POLL_INTERVAL を整数秒で指定できます。1 未満や不正値はデフォルト（60 秒）にフォールバックします。

---

## 開発メモ / 拡張ポイント

- position_sizing の lot_size は現在グローバルな単元株数を想定。将来的には銘柄ごとの lot_map を受け取る拡張がコメントに示されています。
- AI とモニタリングの連携（Kill Switch を含む）は設計上フェイルセーフを重視。AI の失敗が直接システム停止に繋がらないよう保護が入っています。
- DuckDB を使ったリサーチ関数は副作用を持たず、ファクター計算は prices_daily / raw_financials に依存します。データ投入パイプラインと連携して使用してください。

---

必要であれば、README に含めるサンプル .env、systemd / supervisor の起動例、あるいはユニットテストの実行方法などを追加で作成します。どの情報を優先的に追加したいか教えてください。