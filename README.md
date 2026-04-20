README — KabuSys（日本株自動売買システム）
=================================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群のミニマムな実装です。  
主な目的は株価データの集計・ファクター計算、ポートフォリオ構築ロジック、実行エンジン（発注ロジック）およびシステム監視／リスク管理を提供することです。  
コードベースはモジュール化されており、以下の主要コンポーネントを含みます:

- 実行エンジン（ExecutionEngine）起動スクリプト
- 監視ループ（Monitoring）起動スクリプト
- 環境設定ウィザード / 設定検証 CLI
- Paper Trading 検証レポート生成ツール
- ファクター計算・リサーチユーティリティ
- ニュースNLP（OpenAI）を用いたセンチメントスコアリング
- ポートフォリオ構築（候補選定・重み付け・株数算出）
- ユーティリティ（ログ設定、プロセス優先度設定 等）

主な機能一覧
--------------
- 環境設定ウィザード（対話形式で .env を作成）
- 設定検証ツール（必須環境変数・YAML 設定の存在チェック、--strict モード）
- ExecutionEngine 起動（本番 / ペーパートレード切替、別 DB に分離）
- Monitoring 起動（システム健全性・データ鮮度・注文状況・リスク監視）
- Kill Switch（一定条件で data/kill.flag を書いて Execution を停止）
- Paper Trading 検証レポート（稼働率・注文成功率・レイテンシ等の集計）
- AI モジュール：ニュースを LLM に投げて銘柄センチメントを ai_scores に格納（OpenAI）
- レジーム判定（ETF の MA200 とマクロニュースで bull/neutral/bear を判定）
- ポートフォリオ構築用の純粋関数群（候補選定、重み算出、株数算出、セクター制約等）
- ロギング設定ユーティリティ（コンソール + 日次ローテートファイル）

前提 / 推奨環境
----------------
- Python >= 3.10（Union 演算子や型ヒントにより）
- SQLite（標準モジュール）
- 推奨パッケージ（少なくとも実行時に必要なもの）:
  - duckdb
  - psutil
  - openai（AI 機能を使う場合）
  - PyYAML（config ファイルの内容検証を行う場合に任意）
- OS: Linux / macOS / Windows（プロセス優先度設定は OS に依存）

セットアップ手順
----------------
1. レポジトリをクローンしてソースルートへ移動
   (例)
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. 仮想環境作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows (PowerShell: .venv\Scripts\Activate.ps1)
   ```

3. 必要パッケージをインストール
   - 最低限（AI や YAML を使用する場合は追加してください）:
     ```
     pip install duckdb psutil openai PyYAML
     ```
   - 実行環境に合わせて requirements.txt があればそれを利用してください。

4. .env の準備（対話式ウィザード推奨）
   ```
   python -m kabusys.config_setup
   ```
   - ウィザードで J-Quants トークンや kabuステーション API パスワードなどを設定します。
   - .env は絶対に Git にコミットしないでください。

5. 設定検証
   ```
   python -m kabusys.validate_config
   ```
   - 問題があればメッセージに従って修正してください。
   - 警告を厳密チェックする場合:
     ```
     python -m kabusys.validate_config --strict
     ```

主な環境変数（抜粋）
--------------------
- 必須:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 推奨 / 任意:
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading の場合、MockBrokerClient を使用しデータは data/paper_trading.db に保存されるように設計されています（production DB と分離）。
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 SQLite、デフォルト: data/paper_trading.db）
  - LOG_LEVEL（DEBUG|INFO|...）
  - OPENAI_API_KEY（AI モジュール使用時）
  - PAPER_FILL_MODE（paper_trading 用: instant | partial | never | reject）
  - MONITOR_POLL_INTERVAL（監視ループの秒間隔、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等（監視・停止制御）

使い方（起動・主要コマンド）
----------------------------
- ExecutionEngine を起動（通常はデーモン的に実行）
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBroker が使われ paper_trading DB に記録されます。
  - 起動時に data/stop_requested.flag が存在すると起動しません。
  - 実行中は data/execution.pid に PID を書きます（設定で変更可）。

- Monitoring を起動（監視ポーリングループ）
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数で間隔を秒単位で上書きできます（例: export MONITOR_POLL_INTERVAL=30）。
  - 監視は Settings.sqlite_path（監視用 DB）を用い、KABUSYS_ENV に依らず本番 sqlite_path を使用します。
  - 監視は data/stop_requested.flag を検知するとループを終了します。

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（コマンドラインツール）
  ```
  python -m kabusys.tools.paper_verification_report
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（プログラム的に利用）
  - ニュース NLP（銘柄別スコアを ai_scores に書き込む）
    ```
    from kabusys.ai.news_nlp import score_news
    score_news(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```
  - レジーム判定
    ```
    from kabusys.ai.regime_detector import score_regime
    score_regime(duckdb_conn, target_date, api_key="YOUR_OPENAI_KEY")
    ```

- リサーチ関数群（プログラムから呼び出し）
  - 機能例:
    - calc_momentum(conn, date)
    - calc_volatility(conn, date)
    - calc_value(conn, date)
    - calc_forward_returns(conn, date)
    - calc_ic(...), factor_summary(...)
  - モジュール:
    ```
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    ```

- ポートフォリオ関数（純粋関数、テストしやすい）
  - 候補選定・重み付け:
    ```
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights
    ```
  - 株数決定:
    ```
    from kabusys.portfolio import calc_position_sizes
    ```

監視・停止フラグについて
------------------------
- 停止フラグ（run_monitoring / run_execution）:
  - data/stop_requested.flag を作成すると run_monitoring・run_execution のループが検知して終了・停止します。
- Kill Switch:
  - KillSwitch は条件（ドローダウンやポジション上限）を満たした場合に data/kill.flag を書き込みます。ExecutionEngine は KILL FLAG を検知して安全に停止するよう設計されています。
- KILL_FLAG_CLEAR_ON_START 環境変数が 1 の場合、Execution 起動時に kill.flag を自動クリアする設定があります（本番では 0 推奨）。

ログ設定
-------
- 共通ユーティリティ: kabusys.utils.logging_setup.setup_logging(app_name="...")  
  - コンソール（stdout）と日次ローテーションファイル（logs/<app_name>.log）を設定します。
  - LOG_LEVEL / LOG_DIR 環境変数で上書き可能。

プロセス優先度
--------------
- 起動スクリプトは最初に kabusys.utils.process_priority.set_process_priority("high") を呼び出してプロセス優先度を上げようとします（権限がない場合は警告してスキップ）。

ディレクトリ構成（主要ファイル）
------------------------------
以下は src/kabusys 以下の主要ファイルと簡単な説明です（完全なツリーではなく抜粋）。

- kabusys/__init__.py
  - パッケージ定義（__version__ 等）

- 起動スクリプト
  - run_execution.py — ExecutionEngine 起動
  - run_monitoring.py — Monitoring ポーリングループ起動

- 設定関連
  - config.py — Settings クラス（環境変数読み込み・検証、自動 .env ロード）
  - config_setup.py — 対話式 .env 作成ウィザード
  - validate_config.py — 設定検証 CLI

- monitoring/
  - monitoring_db.py — SQLite 用永続化層（テーブル作成・ログ書き込み等）
  - system_monitor.py — システムリソース・データ鮮度監視
  - trade_monitor.py — （注文監視ロジック）
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — kill.flag 書込みロジック
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py — （アラート送信管理、実装による）

- execution/
  - broker_factory.py — ブローカークライアント生成（本番 / mock 切替）
  - execution_engine.py — ExecutionEngine（取引実行フロー）
  - order_manager.py / order_repository.py / reconciler.py / risk_manager.py — 実行関連コンポーネント

- portfolio/
  - portfolio_builder.py — 候補選定・重み算出
  - position_sizing.py — 株数算出（単元丸め・aggregate cap）
  - risk_adjustment.py — セクターキャップ・レジーム乗数

- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン計算・IC 等
  - __init__.py — API エクスポート

- ai/
  - news_nlp.py — ニュース NLP（OpenAI）を用いた銘柄スコア化
  - regime_detector.py — レジーム判定（MA200 + マクロセンチメント）

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

- utils/
  - logging_setup.py — ログ設定ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

運用上の注意
---------------
- .env は秘匿情報（API トークン等）を含むため、Git にコミットしないでください。
- KABUSYS_ENV=live の場合は本番環境になるため、設定（LINE 通知や kill flag 設定等）を慎重に確認してください。
- AI（OpenAI）を利用する機能は API 利用料金が発生します。API キーの管理と呼び出し回数に注意してください。
- run_monitoring は監視 DB（監視テーブル）を常に Settings.sqlite_path に対して初期化します。Execution は paper_trading の場合に別 DB を使いますが、監視は常に監視 DB を使用します。
- DuckDB / SQLite のファイルパスは環境変数で変更できます（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH）。

開発・拡張のヒント
-------------------
- モジュールは比較的純粋関数（副作用の少ない実装）と DB ラッパーに分離されています。ユニットテストが書きやすい設計です。
- AI 呼び出し部分は _call_openai_api を内部で分離しているため、テスト時はパッチしてモック化できます。
- DuckDB を使ったファクター計算は SQL ベースなので大きなデータでも高速です。prices_daily / raw_financials 等のテーブルスキーマに依存します。

ライセンス / 貢献
-----------------
- （ここにプロジェクトのライセンスや貢献方法を追記してください）

お問い合わせ
------------
- 実装や設計に関する質問・改善提案はリポジトリの Issue を通して行ってください。

以上がこのリポジトリの README です。疑問点や追加したいドキュメント（API リファレンス、起動スクリプトの systemd / service 化手順 等）があれば教えてください。