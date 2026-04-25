README
======

概要
----
KabuSys は日本株の自動売買／リサーチを目的とした実装サンプル集です。  
このリポジトリには、実行エンジン（ExecutionEngine）、監視モジュール（Monitoring）、ポートフォリオ構築、ファクター計算、AI を使ったニュース解析やレジーム判定、各種ユーティリティ／CLI が含まれます。

主な設計方針:
- 本番とペーパートレードを環境変数で切り替え（KABUSYS_ENV）。
- DuckDB を分析用途に、SQLite を監視／取引ログ用に利用。
- OpenAI API を使ったニュース NLP / マクロ判定機能を備えるが、API キーは任意（未設定でも他機能は動作）。
- ロギングは統一的に設定され、ファイルは logs/<app_name>.log に日次ローテート保存。

機能一覧
--------
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合はモックブローカーを使い data/paper_trading.db に分離保存
  - 実行中は PID ファイル（data/execution.pid）を出力・監視フラグで停止可能
- 監視ポーリング（run_monitoring.py / MonitoringEngine）
  - システム状態、取引状態、リスク（ドローダウン／ポジション上限）を監視
  - Kill Switch（data/kill.flag）で ExecutionEngine 停止指示
  - MONITOR_POLL_INTERVAL でポーリング間隔を調整（デフォルト 60 秒）
- 設定ウィザード（config_setup.py）
  - .env の対話式作成 / 更新
- 設定検証 CLI（validate_config.py）
  - .env と config/*.yaml の基本チェック、--strict で警告も失敗扱い
- ポートフォリオ構築ライブラリ（portfolio/*）
  - 候補選定、等重/スコア重み、ポジションサイズ計算、セクター制限、レジーム乗数
- リサーチ（research/*）
  - ファクター計算（モメンタム・ボラティリティ・バリュー等）、前方リターン計算、IC 計算
- AI モジュール（ai/*）
  - news_nlp: OpenAI を使ってニュースを銘柄別にセンチメントスコア化し ai_scores に書き込み
  - regime_detector: MA200 とマクロセンチメントを合成して market_regime を算出
- 監視 DB 層（monitoring/monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard の作成・読み書き
- ツール
  - paper_verification_report: ペーパートレード DB を集計して検証レポートを標準出力に出力

セットアップ手順
----------------

1) Python 環境
- 推奨: Python 3.10+ を仮想環境で用意します。
  ```
  python -m venv .venv
  source .venv/bin/activate   # Windows: .venv\Scripts\activate
  ```

2) 依存パッケージをインストール
- 必要となる代表的パッケージ:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証で任意）
- 例:
  ```
  pip install duckdb psutil openai PyYAML
  ```
  （プロジェクトに requirements.txt があればそれを使用してください）

3) データディレクトリ作成
- デフォルトの各種ファイルパスは repository ルートの data/ 配下を使います:
  ```
  mkdir -p data logs
  ```

4) 環境変数 (.env) 作成
- 対話式ウィザードで .env を作成できます:
  ```
  python -m kabusys.config_setup
  ```
- 主要な環境変数（例）:
  - JQUANTS_REFRESH_TOKEN=your_token
  - KABU_API_PASSWORD=your_password
  - KABUSYS_ENV=development | paper_trading | live
  - DUCKDB_PATH=data/kabusys.duckdb
  - SQLITE_PATH=data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db (paper_trading 用)
  - OPENAI_API_KEY=sk-...
  - LOG_LEVEL=INFO

5) 設定検証
- ウィザード後は設定を検証:
  ```
  python -m kabusys.validate_config
  # 警告も失敗扱いにしたい場合:
  python -m kabusys.validate_config --strict
  ```

使い方
------

起動ポイント（主要なコマンド）:
- 実行エンジン（ExecutionEngine）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）に記録します。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行中は data/execution.pid に PID を書きます。

- 監視ループを起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します（監視は環境にかかわらず「本番」DB を参照する設計になっています）。
  - 停止するにはプロジェクトルートの data/stop_requested.flag を作成してください。run_monitoring/run_execution はこのフラグを検知して安全終了します。
  - Kill Switch（監視側）から実際の ExecutionEngine を停止させるには data/kill.flag を作成します（KillSwitch が既に存在する場合は不変）。

- .env の対話式作成:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パス指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

AI 関連
- news_nlp.score_news と regime_detector.score_regime は OpenAI API を利用します。利用する場合は OPENAI_API_KEY を .env に設定するか、api_key 引数で明示します。
- モデルは gpt-4o-mini を使う想定でプロンプト設計されています。
- API 呼び出しはリトライロジック・バリデーションを含み、失敗時は安全側にフォールバックする設計です。

ロギング
- setup_logging により logs/ ディレクトリに日次ローテートでログを保存します（デフォルト logs/<app_name>.log）。LOG_LEVEL 環境変数でログレベルを調整できます。

停止 / Kill Switch
- run_execution/run_monitoring は data/stop_requested.flag を監視して終了します（起動時に存在すれば起動しない）。
- 監視側が条件を満たすと data/kill.flag を書き込み、ExecutionEngine に停止シグナルを送ります。KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

設定例 (.env の一部)
-------------------
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
OPENAI_API_KEY=sk-...
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0

ディレクトリ構成
--------------
リポジトリ内の主要ファイル／モジュール（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理（自動 .env 読み込み機能含む）
  - config_setup.py              — .env 対話式ウィザード
  - validate_config.py           — 設定検証 CLI
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py           — ロギング共通設定
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — monitoring 用 SQLite 永続化層
    - system_monitor.py
    - trade_monitor.py           — （取引監視ロジック、ファイルは省略）
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py           — （アラート送信関連、ファイルは省略）
    - monitoring_engine.py
  - execution/
    - execution_engine.py        — 実行エンジン本体（ファイルは省略）
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
    - news_nlp.py
    - regime_detector.py
  - data/                         — データファイル置き場（非コミット推奨）
    - *.db, kill.flag, stop_requested.flag, execution.pid など

補足・運用注意
--------------
- .env は絶対にリポジトリにコミットしないでください（config_setup.py でも警告あり）。
- 本番環境（KABUSYS_ENV=live）では Kill Switch や LINE 通知設定を再確認してください。validate_config の live ガードが警告を出します。
- psutil による優先度設定や CPU affinity は権限や OS に依存するため、権限不足で失敗する可能性があります（警告ログのみ）。
- DuckDB / SQLite のスキーマ作成は起動スクリプト側で自動実行されます（冪等）。既存 DB への簡易マイグレーション処理も一部含まれます。

ライセンス・バージョン
---------------------
- パッケージバージョンやライセンス情報はプロジェクトルートの pyproject.toml / LICENSE 等を参照してください（本 README には含まれていません）。

以上がこのコードベースの概要と利用方法です。運用やカスタマイズについて具体的な質問があれば、どの部分をどう使いたいか教えてください。追加で起動例や .env のテンプレート、systemd ユニット例なども作成できます。