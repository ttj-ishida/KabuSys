# KabuSys

日本株自動売買システムの一部コードベース。ポートフォリオ構築、ポジションサイジング、モニタリング、ペーパートレード検証、AI（ニュース NLP / レジーム判定）などのユーティリティ群を含みます。

## プロジェクト概要
このリポジトリは、株式自動売買システムのコアユーティリティ群（データ処理、リサーチ、ポートフォリオ構築、実行エンジンの起動スクリプト、監視コンポーネント、AIベースのニュース解析など）を含みます。設計方針として以下を重視しています。

- 環境変数 / .env による設定管理（.env の作成支援 CLI あり）
- 本番／ペーパートレードを明確に分離（DB・ブローカーの分離）
- DuckDB を分析用 DB、SQLite を監視・発注ログ用 DB として利用
- OpenAI を用いたニューススコアリング / レジーム判定をサポート（フェイルセーフ設計）
- 監視（Monitoring）による自動停止（Kill Switch）とアラート連携

## 主な機能一覧
- 設定管理
  - .env ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
- 実行 / 監視
  - 実行エンジン起動スクリプト（kabusys.run_execution）
  - 監視ポーリングループ起動スクリプト（kabusys.run_monitoring）
  - Kill Switch（監視により停止フラグを設定）
- データベース
  - DuckDB（分析用、デフォルト: data/kabusys.duckdb）
  - SQLite（監視・発注ログ、デフォルト: data/monitoring.db、ペーパートレード時は data/paper_trading.db）
  - monitoring_db モジュールでテーブル作成・マイグレーション
- ポートフォリオ / リスク
  - 銘柄選定、等配分・スコア加重配分
  - セクター集中制限、レジーム乗数
  - ポジションサイズ計算（単元丸め、集約キャップ）
- 研究（research）
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン、IC、統計サマリー
- AI モジュール
  - ニュース NLP（OpenAI を用いたセンチメントスコア）：kabusys.ai.news_nlp
  - レジーム判定（MA + マクロセンチメント）：kabusys.ai.regime_detector
  - 両モジュールは API エラー等に対してフォールバック設計
- ツール
  - Paper Trading の検証レポート生成（kabusys.tools.paper_verification_report）

## 要件（依存ライブラリ）
README 作成時点の主な依存例（適宜 pyproject.toml / requirements に合わせてください）:
- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config 検証時にあれば config/*.yaml の中身検証を行う）

インストール例（仮）:
```
pip install duckdb psutil openai PyYAML
```

## セットアップ手順

1. リポジトリをクローン / ソース配置
2. 仮想環境の作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # Linux/macOS
   .venv\Scripts\activate      # Windows
   ```
3. 依存ライブラリをインストール
   ```
   pip install -r requirements.txt
   ```
   （requirements.txt がない場合は上記の主要パッケージを個別にインストール）

4. .env を作成する（対話ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成／更新します。生成後は設定検証を行ってください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   # 警告を FAIL 扱いにする場合:
   python -m kabusys.validate_config --strict
   ```

6. DB・ログディレクトリの確認
   - デフォルトの DB/ログパス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - ログディレクトリ: logs/
   - 必要に応じて環境変数で上書きしてください（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR）。

## 主な環境変数（抜粋）
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - paper_trading: MockBroker を使用し紙データベース（PAPER_TRADING_SQLITE_PATH）に書き込む
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（紙トレード DB）
- PAPER_FILL_MODE: instant / partial / never / reject（デフォルト: instant）
- OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
- DUCKDB_PATH, SQLITE_PATH, LOG_DIR, LOG_LEVEL
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアする（0/1、デフォルト: 0）

## 使い方（起動コマンド例）

- 実行エンジン（ExecutionEngine）を起動
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、Paper Trading DB に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
  - 実行中は data/execution.pid に PID が書かれます（設定で変更可）。

- 監視ループを起動
  ```
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（秒）。
  - 監視は常に本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。
  - data/stop_requested.flag が存在するかを監視し、存在すればループを終了します。

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能。

- 設定ウィザード / 検証
  ```
  python -m kabusys.config_setup
  python -m kabusys.validate_config
  ```

## 停止・Kill Switch
- 手動停止（監視側・実行エンジンの停止）:
  - 実行ループはプロジェクトルートの data/stop_requested.flag の存在を見て停止します。停止させたい場合はこのファイルを作成してください（またはプロセスを直接終了）。
- Kill Switch（自動停止トリガ）:
  - RiskMonitor 等が条件を満たすと Settings.kill_flag_path（デフォルト: data/kill.flag）に理由を書き込みます。ExecutionEngine 起動時にこのフラグを検査し、停止や追加処理を行います。
  - Settings.KILL_FLAG_CLEAR_ON_START が 1 に設定されている場合、起動時に kill.flag を自動クリアします（本番では 0 推奨）。

## ログ
- ログは共通の setup_logging を用いて設定されます。標準出力（stdout）と日次ローテートファイル（logs/<app_name>.log）に出力されます。
- ログレベルは LOG_LEVEL 環境変数で制御（デフォルト INFO）。
- ログディレクトリは LOG_DIR 環境変数で変更可能（デフォルト logs/）。

## データベース（概要）
- DuckDB: 分析・研究用の永続 DB（prices_daily, raw_financials, raw_news, ai_scores, market_regime 等を想定）
- SQLite (monitoring.db): monitoring_db モジュールで system_status / trade_logs / positions / risk_logs / dashboard を管理
- Paper Trading の SQLite は PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）で本番 DB と分離

注: init_monitoring_db(sqlite_conn) を呼ぶことで必要テーブルの作成・軽量マイグレーションを行います。

## ディレクトリ構成（主要ファイル）
以下は src/kabusys 以下の主要ファイルとサブパッケージ（抜粋）です。

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - config_setup.py           — .env 対話ウィザード
  - validate_config.py        — 設定検証 CLI
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
  - utils/
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照用)
  - execution/
    - execution_engine.py (参照)
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
  - data/ (実行時に生成されることが多い)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading モード)
    - stop_requested.flag / kill.flag / execution.pid

（上記はコードベースの抜粋一覧です。実際のファイル一覧はリポジトリのツリーを参照してください）

## 注意事項 / 運用メモ
- KABUSYS_ENV を `live` に設定する際は特に注意してください（本番ブローカー・実売買が行われます）。validate_config は `live` の場合に追加警告を出します。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）とコスト上の配慮が必要です。失敗時は安全にフォールバックする実装ですが、運用時は API 利用制限やレートを考慮してください。
- .env は機密情報（トークン・パスワード）を含むため、決してリポジトリにコミットしないでください。
- ローカルでのテストや開発は KABUSYS_ENV=development または paper_trading を利用して、本番資金にアクセスしないようにしてください。

---

この README はコードベースに含まれるスクリプト・モジュールの利用開始に必要な情報をまとめたものです。より詳細な設計や API 仕様（StrategyModel.md / PortfolioConstruction.md 等）があれば、そのドキュメントも併せて参照してください。必要があれば README に追記・整備します。