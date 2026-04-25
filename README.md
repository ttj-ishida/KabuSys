README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のサンプル実装です。  
主な機能は以下の通りです:

- 発注エンジン（ExecutionEngine）とそれを監視する Monitoring 系ユーティリティ
- ペーパートレード用の分離された DB とモックブローカーサポート
- ポートフォリオ構築（候補選定、重み付け、ポジション算出、セクター制限など）
- ファクター計算・研究モジュール（momentum / volatility / value 等）
- ニュース NLP によるセンチメント評価（OpenAI API を利用）
- 設定ウィザードおよび起動前検証ツール
- 各種ログ・監視（SQLite / DuckDB / ログローテーション）

主要提供物（実行スクリプト）
- python -m kabusys.run_execution : ExecutionEngine を起動
- python -m kabusys.run_monitoring : SystemMonitor のポーリングループを起動
- python -m kabusys.config_setup : 対話式 .env 作成ウィザード
- python -m kabusys.validate_config : 環境・設定ファイルの検証
- python -m kabusys.tools.paper_verification_report : ペーパートレード検証レポート生成

機能一覧
--------
- 環境設定管理
  - .env, .env.local を自動読み込み（プロジェクトルートを自動検出）
  - 設定ウィザード（config_setup）で .env を対話的に生成・更新
- 実行・監視
  - ExecutionEngine（本番 / ペーパートレード切替）
  - MonitoringEngine（System / Trade / Risk の監視、Kill Switch、アラートハンドリング）
  - stop/kill フラグ（data/stop_requested.flag / data/kill.flag）で外部から停止・シャットダウン制御
- データ永続化
  - DuckDB（分析データ: デフォルト data/kabusys.duckdb）
  - SQLite（監視・発注ログ: デフォルト data/monitoring.db、ペーパートレード時は data/paper_trading.db）
- ポートフォリオ構築
  - 候補選定、等金額/スコア重み付け、リスクベースのポジション決定、セクター制限、レジーム乗数
- リサーチ
  - momentum / volatility / value 等のファクター計算（DuckDB 上の prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI 関連
  - ニュースをまとめて OpenAI に投げ、銘柄毎にセンチメントを ai_scores に保存
  - マクロセンチメント + ETF MA 乖離を組み合わせた市場レジーム判定
- ロギング
  - 統一された logging セットアップ（コンソール stdout + 日次ローテーションファイル → logs/<app>.log）
- プロセス優先度 / CPU affinity 設定ユーティリティ（psutil 利用）

セットアップ手順
----------------

1. Python 環境を用意
   - Python 3.10+ を推奨
   - 仮想環境作成例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（最低限）
   - duckdb
   - psutil
   - openai
   - PyYAML（validate_config の YAML 検証を利用する場合）
   例:
     pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を使用してください）

3. .env の作成
   - 対話式ウィザード：
     python -m kabusys.config_setup
   - もしくは環境変数で直接設定（下記「重要な環境変数」を参照）

   自動読み込み:
   - プロジェクトルート（.git または pyproject.toml を含むディレクトリ）を基準に .env, .env.local を自動読み込みします。
   - 自動読み込みを無効化する場合:
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

4. 設定の検証（起動前チェック）
   python -m kabusys.validate_config
   - 警告もエラーにしたい場合: python -m kabusys.validate_config --strict

5. データディレクトリやログディレクトリの作成は通常自動で行われます（logs/、data/ 等）。権限がない場合ファイル出力が失敗することがありますので注意してください。

重要な環境変数（抜粋）
---------------------
必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API のリフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

動作モード:
- KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
  - paper_trading のときは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録します

データベース:
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — SQLite（監視）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）

ログ:
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）
- LOG_DIR — ログディレクトリ（デフォルト: logs/）

AI:
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp, ai.regime_detector で使用）

その他:
- PAPER_FILL_MODE — paper_trading 時の約定モード（instant/partial/never/reject、デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" でクリア、デフォルト: "0"）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD — "1" を設定すると .env の自動読み込みを無効化

使い方（主要コマンド）
--------------------

1) 環境ファイル作成（対話式）
   python -m kabusys.config_setup

2) 設定検証
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱いにする:
   python -m kabusys.validate_config --strict

3) ExecutionEngine 起動（本番・ペーパートレードは KABUSYS_ENV で制御）
   python -m kabusys.run_execution
   - ペーパートレード時は Settings の is_paper により paper_sqlite_path を使います
   - 起動時に data/stop_requested.flag が存在すると起動を中止します
   - 実行中は data/execution.pid に PID を書き込む（設定次第）

4) Monitoring 起動（ポーリングループ）
   python -m kabusys.run_monitoring
   - MONITOR_POLL_INTERVAL 環境変数で間隔を上書き可能（秒、デフォルト 60）
   - data/stop_requested.flag が出現するとループを終了します
   - Monitoring は常に本番の sqlite_path を参照して監視ログを記録します

5) Paper Trading レポート生成
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - --db オプションまたは PAPER_TRADING_SQLITE_PATH 環境変数で DB パス指定可

6) AI スコア生成（ライブラリ関数として利用）
   - kabusys.ai.score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   これらは DuckDB 接続を受け取り、ai_scores / market_regime などのテーブルに書き込みます。

停止 / Kill Switch
------------------
- 手動で ExecutionEngine を停止したい場合は data/kill.flag を作成します（KillSwitch が検出すると ExecutionEngine を停止させる設計です）。KillSwitch は監視結果（ドローダウン / ポジション上限など）から自動で kill.flag を書き込むこともあります。
- stop_requested.flag（data/stop_requested.flag）は run_* スクリプトを外部から安全に終了させるために用います。存在すると監視ループや実行スレッドが終了します。
- 起動時に kill.flag を自動クリアしたい場合は KILL_FLAG_CLEAR_ON_START=1 を設定できます（本番では注意推奨: デフォルトは 0）。

ログ
----
- デフォルトで console (stdout) にログを出力し、さらに logs/<app_name>.log に日次ローテーションで保存します（30日保持）。
- ログ出力先は LOG_DIR 環境変数または setup_logging の引数で変更できます。

ディレクトリ構成
----------------
以下は主要なコード位置のサマリ（パッケージルートは src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings 管理、自動 .env 読み込み
  - config_setup.py          — .env の対話式ウィザード
  - validate_config.py       — 起動前の設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - news_nlp.py            — ニュース NLP（OpenAI 呼び出しなど）
    - regime_detector.py     — 市場レジーム判定
  - portfolio/
    - portfolio_builder.py   — 候補選定、等重・スコア重み
    - position_sizing.py     — 株数計算・スケーリング・単元丸め
    - risk_adjustment.py     — セクターキャップ、レジーム乗数
  - research/
    - factor_research.py     — momentum/volatility/value 等のファクター計算
    - feature_exploration.py — 将来リターン、IC、統計サマリ
  - monitoring/
    - monitoring_db.py       — SQLite テーブル初期化 / 永続化 API
    - monitoring_engine.py   — 複数 Monitor を束ねるエンジン
    - system_monitor.py      — システム／データ鮮度監視
    - trade_monitor.py       — （存在する想定: 発注ログ監視）
    - risk_monitor.py        — ドローダウン・ポジション数監視
    - kill_switch.py         — kill.flag 書き込みロジック
    - alert_manager.py       — （存在する想定: 通知送信ロジック）
  - utils/
    - logging_setup.py       — 共通ログ設定
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/              — 上記
  - portfolio/, research/, ai/ — 上記

注意点 / 実運用での留意事項
---------------------------
- 本サンプルは教育目的の実装であり、本番環境へ導入する際はさらに安全性（例: トランザクション整合性、API エラー処理、認証管理、秘密情報保護、冪等性の厳密化等）を強化してください。
- OpenAI API を用いる箇所は API レート制限や課金に注意してください。API キーは厳重に管理し、.env を絶対にリポジトリにコミットしないでください。
- ペーパートレード時は本番 DB と完全に分離されるよう設計されていますが、環境変数の設定ミスで本番 DB を使ってしまわないよう注意してください（validate_config で KABUSYS_ENV/DB パス等を確認してください）。

サポート / 変更
----------------
- この README はコードベース（src/kabusys 以下）を元に生成しています。実際の追加ファイル（data/, logs/, config/*.yaml など）や外部モジュールに依存する部分はプロジェクトの他のドキュメントやスクリプトを参照してください。

以上。必要であれば、README にさらに詳細な実行例（.env の雛形、サンプルコマンド、各モジュールの API リファレンス）を追加できます。どの情報を追加希望か教えてください。