KabuSys — 日本株自動売買システム
================================

この README はリポジトリ内の主要な起動スクリプト・ユーティリティ群をまとめた簡易ドキュメントです。プロジェクト全体像、セットアップ手順、実行方法、およびディレクトリ構成を日本語で記載しています。

概要
----
KabuSys は日本株の自動売買・研究フレームワークです。主な責務は次の通りです。

- 実行エンジン（ExecutionEngine）：発注・オーダー管理・リスク制御
- 監視（Monitoring）：システム状態・注文・リスク監視、Kill Switch の発動
- 研究モジュール（research）：ファクター計算・特徴量解析
- ポートフォリオ構築（portfolio）：候補選定・重み計算・ポジションサイズ算出
- AI 統合（ai）：ニュース NLP によるセンチメント評価とレジーム判定
- 運用補助ツール：.env ウィザード、設定検証、ペーパートレード検証レポート等

特徴一覧
--------
- 環境変数ベースの設定（.env 自動ロード / 対話ウィザード）
- 実行環境の切り替え（development / paper_trading / live）
  - paper_trading 時は MockBroker を使用し、本番 DB と分離（data/paper_trading.db）
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch による安全停止
- DuckDB を用いた研究データ分析（prices_daily / raw_financials 参照）
- OpenAI を用いたニュースセンチメント（gpt-4o-mini を想定）
- ログは stdout と日次ローテーション（logs/<app>.log）で出力
- 各種ユーティリティ（設定ウィザード、設定検証、ペーパートレード検証レポート）

前提条件
--------
- Python 3.9+（ソースが型ヒントで Path|None、typing の現代的な記法を使用）
- 推奨パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config 検証時に使用）
- ネットワーク接続（kabuステーション API、OpenAI を使う場合）

（依存関係は requirements.txt 等で別途管理してください）

セットアップ手順
----------------

1. リポジトリをクローン・作業ディレクトリへ移動
   - git clone ...
   - cd <project_root>

2. Python 仮想環境を作る（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install duckdb psutil openai PyYAML
   - （プロジェクトで提供される requirements.txt があればそれを使用）

4. データ / ログ ディレクトリの作成（通常はコードで自動作成されますが手動で作る場合）
   - mkdir -p data logs

環境変数設定 (.env)
-------------------
プロジェクトは .env（および .env.local）を自動的に読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
対話式ウィザードで .env を生成できます：

- 実行:
  - python -m kabusys.config_setup
  - 対話に従って必要項目を入力して .env を保存します

主要な環境変数（デフォルト値はソースに記載）:
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABU_API_BASE_URL (default: http://localhost:18080/kabusapi)
- DUCKDB_PATH (default: data/kabusys.duckdb)
- SQLITE_PATH (default: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (default: data/paper_trading.db)
- PAPER_FILL_MODE (instant|partial|never|reject; default: instant)
- KABUSYS_ENV (development | paper_trading | live; default: development)
- LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL; default: INFO)
- KILL_FLAG_CLEAR_ON_START (0|1; default: 0)
- OPENAI_API_KEY (AI 機能を使う場合必須)

設定検証
--------
.env と config/*.yaml（存在する場合）をチェックするユーティリティがあります：

- 実行:
  - python -m kabusys.validate_config
  - 警告をエラーとして扱う strict モード:
    - python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------

1. ExecutionEngine 起動
   - python -m kabusys.run_execution
   - 特記事項:
     - 起動時にプロセス優先度を "high" に設定し、PID ファイル（data/execution.pid）を使います
     - KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離
     - data/stop_requested.flag が存在すると起動をスキップ・停止処理を行います
     - Kill Switch（data/kill.flag）はこのエンジンを停止させるために monitoring が書き込みます
     - 起動時に KILL_FLAG_CLEAR_ON_START=1 の場合、kill.flag を自動でクリアする設定もあります（本番では 0 推奨）

2. Monitoring 起動
   - python -m kabusys.run_monitoring
   - 特記事項:
     - デフォルトのポーリング間隔: 60秒（環境変数 MONITOR_POLL_INTERVAL で上書き可）
     - 監視ログは SQLite（settings.sqlite_path）へ書き込みます（監視は本番 sqlite_path を常に使用）
     - data/stop_requested.flag を検知すると監視ループを終了します

   例（ポーリング間隔を30秒に変更）:
   - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

3. ペーパートレード検証レポート生成
   - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - オプション --db で PAPER_TRADING_SQLITE_PATH を上書き可

4. AI（ニュース NLP / レジーム判定）
   - OPENAI_API_KEY 環境変数を設定してから呼び出します
   - モジュール関数を直接呼ぶ例（スクリプト内で）:
     - from kabusys.ai.news_nlp import score_news
     - score_news(duckdb_conn, target_date, api_key=None)  # api_key が None の場合は env を使う
   - レジーム判定:
     - from kabusys.ai.regime_detector import score_regime
     - score_regime(duckdb_conn, target_date, api_key=None)

運用上のフラグ/ファイル
--------------------
- data/execution.pid : ExecutionEngine の PID（Execution 側で使用）
- data/stop_requested.flag : 起動スクリプト（run_execution/run_monitoring）同梱の停止フラグ。存在するとループを終了。
- data/kill.flag : KillSwitch が書き込む停止シグナル（ExecutionEngine 停止のため）。存在するとエンジンが安全に停止されます。
- logs/ : ログファイルは logs/<app_name>.log に日次ローテートで出力

開発者向け：ライブラリ利用例
--------------------------
研究・ポートフォリオ関数はプログラムから直接利用できます。例：

- DuckDB 接続を渡してファクター計算:
  - from kabusys.research import calc_momentum
  - records = calc_momentum(duckdb_conn, date(2026, 4, 10))

- ポートフォリオ構築:
  - from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  - candidates = select_candidates(signals, max_positions=10)
  - weights = calc_score_weights(candidates)
  - sizes = calc_position_sizes(weights, candidates, portfolio_value=1e7, available_cash=5e6, ...)

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                — 環境変数 / Settings
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py            — ニュース NLP（OpenAI）
  - regime_detector.py     — 市場レジーム判定（MA + LLM 合成）
- monitoring/
  - monitoring_db.py       — SQLite 永続化レイヤ
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py
- execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - broker_factory.py
  - risk_manager.py
  - reconciler.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py
  - process_priority.py
  - その他ユーティリティ

注意事項 / 運用のヒント
-----------------------
- 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを強く推奨します。1 にすると kill.flag が自動クリアされ、Kill Switch が無効化される可能性があります。
- paper_trading モードは発注ロジックをモックし、DB を data/paper_trading.db に分離します。ペーパートレード実行時は本番 DB に影響しません。
- OpenAI を使う機能は API リクエスト制限やコストが発生します。API 呼び出しのリトライロジックがありますが、運用時はレートとコストに注意してください。
- 監視は常に sqlite_path（Settings.sqlite_path）を参照します。監視データを永続化するための場所に注意してください。
- ログディレクトリ（LOG_DIR）はデフォルト logs/。権限や容量管理（ローテーション: 30日分）を行ってください。

トラブルシューティング
---------------------
- .env の読み込みに問題がある場合:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか確認
  - config_setup で再生成して validate_config で検証
- DuckDB / SQLite ファイルが存在しない場合:
  - 多くのコードは起動時にテーブルを作成しますが、初回は data ディレクトリが存在するか確認
- OpenAI 呼び出しで例外が出る場合:
  - OPENAI_API_KEY を確認、API のレスポンスや料金上限を確認
  - ネットワークタイムアウトや 429 に対してはリトライロジックが働きますが、継続障害はログを参照

ライセンス / バージョン
-----------------------
- パッケージバージョンは src/kabusys/__init__.py の __version__ を参照してください（例: 0.1.0）

最後に
------
この README はコードベースの主要点をまとめた概要です。各モジュールの詳細な仕様・設計メモ（PortfolioConstruction.md、StrategyModel.md 等）がリポジトリにある場合はそれらも参照してください。必要であれば README に追加したい項目（例えば実行例のログ抜粋、詳細な env 変数一覧など）を指示してください。