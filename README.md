KabuSys — 日本株自動売買システム
===============================

概要
----
KabuSys は日本株向けの自動売買システム用ライブラリ兼実行スクリプト群です。  
本リポジトリは以下の目的のモジュールを含みます:

- 注文実行エンジン（ExecutionEngine）とブローカ抽象（実口座 / ペーパートレード切替）
- 監視周り（System / Trade / Risk の監視、Kill Switch、アラート連携）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出・リスク制約）
- リサーチ（ファクター計算・特徴量探索）
- ニュース NLP / レジーム判定（OpenAI を使ったセンチメント集約）
- 開発用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

主な設計方針は「実行系と解析系を分離」「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアスの排除」「フェイルセーフ（API 失敗時はスキップ）」です。

主な機能
--------
- Execution
  - 本番/ペーパートレード切替（KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用）
  - 注文管理／リスク管理／リコンサイル機能
- Monitoring
  - CPU / メモリ / ディスク / プロセス生存監視
  - 注文滞留・約定異常・ドローダウン・ポジション上限監視
  - Kill Switch（条件を満たしたら data/kill.flag を作成して実行エンジン停止を促す）
- Portfolio
  - シグナル候補選定、等金額／スコア重み配分、ポジション・サイズ算出
  - セクター上限適用、レジーム乗数
- Research
  - Momentum / Volatility / Value などファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- AI
  - ニュースのセンチメント集約（OpenAI によるスコアリング）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
- ツール
  - .env 対話ウィザード（kabusys.config_setup）
  - 設定検証 CLI（kabusys.validate_config）
  - ペーパートレード検証レポート出力（kabusys.tools.paper_verification_report）

前提 / 必要な依存
-----------------
（実装から推測される主要パッケージ）

- Python 3.10+
- duckdb
- psutil
- openai (AI 機能を利用する場合)
- PyYAML（設定検証で YAML の検証を行う場合）

インストール例（ローカル開発）
- 仮想環境を作成してアクティベート
  - python -m venv .venv && source .venv/bin/activate  (Windows は .venv\Scripts\activate)
- 必要ライブラリをインストール（requirements.txt がない場合は以下を目安に）
  - pip install duckdb psutil openai PyYAML

セットアップ手順
----------------

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成して有効化
3. 依存をインストール（上記参照）
4. .env ファイルの作成
   - 対話式で作る: python -m kabusys.config_setup
   - 手動で作る: プロジェクトルートに .env を作成し、.env.example を参照して設定
   - 重要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
     - OPENAI_API_KEY（AI 機能使用時）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB。デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード用 DB。デフォルト: data/paper_trading.db）
     - LOG_LEVEL（デフォルト: INFO）
     - PAPER_FILL_MODE（instant / partial / never / reject。デフォルト: instant）
     - KILL_FLAG_CLEAR_ON_START（本番での自動クリア防止のためデフォルト 0）
5. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - 警告も FAIL 扱いにしたい場合: python -m kabusys.validate_config --strict

使い方（主要スクリプト）
-----------------------

- Execution Engine を起動（本番または paper_trading に応じて挙動が変わる）
  - python -m kabusys.run_execution
  - 実行時は data/execution.pid を使用し、data/stop_requested.flag が存在すると起動しない／停止する
  - paper_trading 環境では MockBrokerClient を使用し、デフォルトで data/paper_trading.db に記録します

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可（デフォルト 60）
  - 監視は実環境の sqlite_path を使用（KABUSYS_ENV に依らない）
  - 終了: data/stop_requested.flag を作成するか Ctrl+C

- 設定ウィザード（対話）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - --strict を指定すると警告があっても exit(1)

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH（デフォルト: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db）

停止 / Kill スイッチ
-------------------
- 実行停止用フラグ:
  - data/stop_requested.flag — run_execution / run_monitoring が監視している停止フラグ（起動/実行ループの終了トリガー）
  - data/kill.flag — KillSwitch によって作成される停止フラグ（ExecutionEngine 側で検出される）
- KillSwitch の評価条件にはドローダウン・ポジション上限などがあり、条件を満たすと data/kill.flag が作成されます
- Kill flag を自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）がありますが、本番では 0 を推奨します

ログ
----
- ログは標準出力（stdout）とファイル（logs/<app_name>.log）に出力されます
- ログディレクトリは LOG_DIR 環境変数で上書き可能（デフォルト logs/）
- ログレベルは LOG_LEVEL 環境変数で設定（DEBUG/INFO/WARNING/ERROR/CRITICAL）

主要ファイル / ディレクトリ構成
-----------------------------
（src/kabusys 以下の主要構造を抜粋）

- kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数／設定読み込み・Settings
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - execution/  — 注文実行エンジン関連（BrokerFactory, ExecutionEngine, OrderManager, Reconciler, RiskManager 等）
  - monitoring/
    - monitoring_db.py — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py — 注文滞留・約定チェック（実装ファイルあり）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — フラグファイルによる停止シグナル
    - monitoring_engine.py — 監視コンポーネントの統合ループ
    - alert_manager.py — アラート通知（実装箇所あり）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数算出・aggregate cap
    - risk_adjustment.py — セクター上限、レジーム乗数
  - research/
    - factor_research.py — Momentum / Volatility / Value 計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計
  - ai/
    - news_nlp.py — raw_news を集約して OpenAI でスコアリングし ai_scores へ書込む
    - regime_detector.py — ETF MA とマクロセンチメントを合成して market_regime を書込む
  - data/ (実行時生成)
    - monitoring.db（デフォルト sqlite path）
    - paper_trading.db（ペーパートレード DB）
    - kill.flag / stop_requested.flag / execution.pid など

補足 / 注意点
-------------
- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml が存在するディレクトリ）から .env を自動的に読み込みます
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等的にテーブル作成と簡易マイグレーション（カラム追加）を行います
- OpenAI の利用:
  - AI 機能（news_nlp / regime_detector）を使う場合は OPENAI_API_KEY を設定してください
  - API エラーはリトライやフェイルセーフを組み込んでいますが、キーやレート制限には注意
- 権限:
  - set_process_priority の呼び出しは OS によって権限エラーが出る場合があります（警告を出してスキップします）
- ペーパートレード:
  - KABUSYS_ENV=paper_trading に設定すると実口座 API 呼び出しはモック化され、data/paper_trading.db に記録されます（本番 DB と完全分離）

簡単な開始例
--------------
1. .env を作成
   - python -m kabusys.config_setup
2. 設定検証
   - python -m kabusys.validate_config
3. 監視プロセス起動（別ターミナルで）
   - python -m kabusys.run_monitoring
4. 実行プロセス起動（別ターミナルで）
   - python -m kabusys.run_execution

ライセンス / バージョン
-----------------------
- パッケージバージョンは kabusys.__version__ で管理（現状 "0.1.0"）

問い合わせ / 貢献
-----------------
- バグ報告や機能提案は Issue を作成してください。Pull Request も歓迎します。README の補足やドキュメント化も助かります。

以上がこのコードベースの概要と使用方法のまとめです。必要があればセクションごとに詳しい使い方（コマンド例、環境変数一覧のテンプレート、開発用テスト方法など）を追記します。どの部分を詳細に出力しますか？