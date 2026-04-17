# KabuSys

日本株自動売買システムの一部コードベース（ライブラリ＋実行スクリプト群）の README です。  
このドキュメントはコード（src/kabusys 以下）を元に作成しています。

目次
- プロジェクト概要
- 主な機能一覧
- 必要要件
- セットアップ手順
- 使い方（主要コマンド／スクリプト）
- 環境変数一覧（主要なもの）
- データ・フラグファイル
- ディレクトリ構成（概略）
- 開発メモ・注意点

---

## プロジェクト概要
KabuSys は日本株の自動売買／研究用ユーティリティ群をまとめたプロジェクトです。  
主な要素は以下です：
- 実行エンジン（ExecutionEngine）とモニタリング（Monitoring）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ決定）
- 研究用ファクター計算（DuckDB を利用）
- ニュース NLP（OpenAI を用いたセンチメント評価）およびレジーム判定
- 監視ログの永続化（SQLite）
- 各種 CLI（環境設定ウィザード、設定検証、レポート生成）

設計上、研究処理は DuckDB、監視／注文ログは SQLite を使用します。  
Paper Trading モード時は本番 DB と分離された専用の SQLite（data/paper_trading.db）を使用します。

---

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し本番 DB と分離
  - 起動時にプロセス優先度を調整、PID ファイル管理、停止フラグ監視
- 監視ループ起動スクリプト（run_monitoring.py）
  - システム状態、注文滞留、リスク（ドローダウン等）監視
  - 監視ログを SQLite に永続化
  - MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）
- 監視永続化レイヤ（monitoring_db.py）
  - system_status, trade_logs, positions, risk_logs, dashboard テーブルを管理
  - マイグレーション（カラム追加）のロジックあり
- ポートフォリオ構築（portfolio/*）
  - 候補抽出、等比率／スコア加重、リスク調整、ポジションサイズ算出
- 研究モジュール（research/*）
  - momentum / volatility / value ファクター計算（DuckDB 利用）
  - 将来リターン計算、IC（Information Coefficient）など
- AI 関連（ai/*）
  - news_nlp: OpenAI を用いたニュースセンチメントスコアリング（ai_scores へ保存）
  - regime_detector: ma200 とマクロニュースで市場レジーム判定
- CLI ツール
  - 環境設定ウィザード（kabusys.config_setup）
  - 設定検証（kabusys.validate_config）
  - Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 必要要件
- Python 3.10 以上（型注釈で | 演算子を使用）
- 主要パッケージ（最低限）
  - duckdb
  - psutil
  - openai
  - requests
- 任意（機能による）
  - PyYAML（config/*.yaml 検証を行う場合）
- (推奨) 仮想環境を利用してください。

インストール例（venv + pip）:
```
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai requests PyYAML
```

---

## セットアップ手順（簡易）
1. リポジトリをチェックアウト／配置
2. Python 環境を用意（上記依存パッケージをインストール）
3. 環境変数の設定
   - .env を作成する（手動か CLI を使用）
   - 推奨: `python -m kabusys.config_setup` を実行して対話的に .env を生成
4. 設定検証
   - `python -m kabusys.validate_config` を実行して設定のチェック
   - 問題があれば .env を修正
5. データディレクトリの準備（省略可、スクリプトは必要に応じて作成します）
   - デフォルトでは data/*.db, data/*.flag, data/execution.pid などを使用

---

## 使い方（主要コマンド）
以下はいずれもプロジェクトルート（pyproject.toml/.git を含むルート）から実行する想定です。

- 環境設定ウィザード（.env を生成／更新）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  # 警告もエラー扱いにする strict モード
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン起動（ExecutionEngine）
  - 本番／開発は KABUSYS_ENV に依存
  ```
  python -m kabusys.run_execution
  ```
  - 注意: KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用します。

- モニタリングループ起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔を上書き:
  ```
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- ライブラリ関数（コード内利用）
  - AI スコアリング:
    - kabusys.ai.score_news(conn, target_date, api_key=None)
      - conn: duckdb connection、target_date: datetime.date、api_key: OpenAI API key（省略時は環境変数 OPENAI_API_KEY）
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 環境変数（主要）
自動読み込み:
- プロジェクトルートが検出される場合、.env を自動で読み込みます（.env.local は上書き有効）。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

必須（起動前に設定が推奨／必要なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要な任意／設定項目（デフォルト値を併記）
- KABUSYS_ENV: execution の動作モード
  - 有効値: development, paper_trading, live
  - default: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PAPER_FILL_MODE: paper trading 時の填埋動作（instant, partial, never, reject）。default: instant
- OPENAI_API_KEY: OpenAI API キー（ai.news_nlp / regime_detector で使用）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE通知）用
- LOG_LEVEL: INFO 等
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID_FILE_PATH / KILL_FLAG_PATH: デフォルトは data/execution.pid / data/kill.flag
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動でクリア（1 を設定するとクリアされる）

詳細はコード中の Settings クラス（src/kabusys/config.py）を参照してください。

---

## データ・フラグファイル
プロジェクトで参照／生成される代表的なファイル（デフォルトパス）:
- data/kabusys.duckdb — DuckDB（分析用）
- data/monitoring.db — SQLite（監視ログ）
- data/paper_trading.db — SQLite（Paper Trading 専用）
- data/execution.pid — ExecutionEngine の PID（存在するかでプロセス検知）
- data/stop_requested.flag — run_monitoring/run_execution 停止の外部フラグ（スクリプトで参照）
- data/kill.flag — Kill Switch（監視が一定条件を満たした場合に作成される）

Kill Switch の操作や清掃は KillSwitch クラス / Settings.kill_flag_path を参照してください。

---

## ディレクトリ構成（src/kabusys の主要ファイル）
以下はコードベース（抜粋）の概略ツリーです（重要モジュールのみ）:

- src/kabusys/
  - __init__.py
  - config.py               # 環境変数 / Settings
  - config_setup.py         # .env 対話式ウィザード
  - validate_config.py      # 設定検証 CLI
  - run_execution.py        # ExecutionEngine 起動スクリプト
  - run_monitoring.py       # Monitoring 起動スクリプト
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
    - alert_manager.py
    - kill_switch.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - utils/
    - process_priority.py
  - execution/               # 実行エンジン周り（OrderManager, BrokerFactory 等）
    - (多数のモジュールが想定)

（注）上記はコードの一部を抜粋した構成です。実装の詳細や追加モジュールはリポジトリの完全ツリーを参照してください。

---

## 開発メモ・注意点
- 自動 .env ロードはプロジェクトルート（.git や pyproject.toml）を探索して行われます。テスト時や意図しない読み込みを避けたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- run_monitoring は MONITOR_POLL_INTERVAL によってポーリング間隔を制御できます。0 以下や不正値は無効扱いでデフォルト（60 秒）にフォールバックします。
- 監視系（monitoring）は KABUSYS_ENV にかかわらずデフォルトの sqlite_path（本番）を使う設計になっている箇所があります。Paper Trading と本番を明確に分離したい場合は設定値を確認してください。
- AI 関連 API 呼び出しは OpenAI を使用。API キーの管理・呼び出しのレートリミットに注意してください。失敗時はフェイルセーフで継続する実装例が多く含まれますが、ログを確認してください。
- process priority / cpu affinity 設定は psutil を利用します。権限や OS によっては設定できない場合があり、その場合は警告ログを出してスキップします。
- monitoring_db にマイグレーションロジック（カラム追加）が含まれており、既存 DB に対して安全に実行されるよう配慮されています。

---

必要であれば、README に実行例（systemd や Supervisor 用の起動ユニット例）、より詳しい環境変数の説明、API 使用例（DuckDB 接続の作り方や ai.score_news の呼び出しサンプル）などを追加できます。どの情報を詳しく載せたいか教えてください。