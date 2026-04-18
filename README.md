README
======

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤です。  
戦略・ポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、監視・アラート、ペーパートレード検証、及び OpenAI を用いたニュース NLU によるスコアリング機能を備えています。  
このリポジトリは、実行エントリポイント（ExecutionEngine / Monitoring）と、それを支えるユーティリティ群・モジュール群で構成されています。

主な特徴（機能一覧）
-------------------
- Execution
  - ExecutionEngine による発注処理（本番 / ペーパートレード切替）
  - BrokerClientFactory で本番ブローカー / MockBroker の切替
  - Order 管理・リコンシリエーション・リスク管理（Rate limit / Drawdown 等）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、プロセス生存、データ鮮度監視
  - TradeMonitor / RiskMonitor：滞留注文、約定異常、ドローダウンなどの監視
  - KillSwitch：リスク条件到達時に kill.flag を書き込み ExecutionEngine を停止
  - Monitoring DB（SQLite）へのログ永続化（system_status, trade_logs, risk_logs, positions, dashboard）
- Portfolio Construction
  - 候補選定、等分配 / スコア加重配分、リスク調整（セクター上限、レジーム乗数）、ポジションサイズ計算（単元株丸め）
- Research
  - ファクター計算（モメンタム / ボラティリティ / バリュー）
  - 将来リターン計算、IC（スピアマン）や統計サマリー
- AI / NLP
  - ニュースを LLM（OpenAI）でスコア化して ai_scores テーブルへ保存
  - マクロニュース + ETF MA200 を元に市場レジーム（bull/neutral/bear）判定
- ツール
  - config_setup.py：.env の対話式ウィザードでの作成・更新
  - validate_config.py：起動前の設定チェック（必須環境変数・ファイル存在など）
  - tools/paper_verification_report.py：ペーパートレード検証レポート生成

セットアップ手順
----------------

前提
- Python 3.9+（コードは型ヒントで | 型を利用しているため、3.10+ 推奨）
- システムにより追加のネイティブライブラリが必要な場合あり（psutil 等）

1) リポジトリを取得
   - git clone ... または 展開済みのソースディレクトリを用意

2) 仮想環境作成・アクティベート（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3) 必要なパッケージをインストール
   - 例（最小限）:
     - pip install duckdb psutil openai
   - 監視・設定検証で PyYAML を使う場合:
     - pip install PyYAML
   - 実際の requirements.txt がないため、上記パッケージをプロジェクトに応じて追加してください。

4) ディレクトリ準備
   - デフォルトで使用するディレクトリ:
     - data/  （SQLite / PID / flag を置く）
     - logs/  （ログ）
   - 必要に応じて手動作成:
     - mkdir -p data logs

環境変数設定
- .env を作成する方法（対話式ウィザード）:
  - python -m kabusys.config_setup
    - 対話式に必要値を入力し .env を生成します。
- 主要な環境変数（必須）
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API パスワード）
- 運用に関する主要変数
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
    - paper_trading のときは MockBrokerClient を使用し、paper_trading 用 DB に記録
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
  - OPENAI_API_KEY（AI モジュールを使う場合）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）

設定検証
- 起動前に validate_config を実行して設定をチェックできます:
  - python -m kabusys.validate_config
  - 警告をエラーとして扱う場合（CI など）:
    - python -m kabusys.validate_config --strict

使い方（主要コマンド）
--------------------

基本的にパッケージモジュールとして実行します（プロジェクトルートが PYTHONPATH に含まれていることが前提）。

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - オプション: --strict

- 実行エンジン（ExecutionEngine）
  - python -m kabusys.run_execution
  - 特記事項:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使用し data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中に stop_requested.flag を作成すると Graceful に停止（ExecutionEngine.stop() が呼ばれる）
    - PID ファイル: data/execution.pid（Settings で変更可）

- 監視プロセス（SystemMonitor ポーリング）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト: 60）
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用します（監視ログは本番 DB に集約）

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI（ニューススコア / レジーム判定）
  - ニューススコア（ai/news_nlp.py）
    - 関数: kabusys.ai.score_news をコードから呼ぶ（duckdb 接続と target_date を渡す）
    - OPENAI_API_KEY が必要
  - レジーム判定（ai/regime_detector.py）
    - 同様に OPENAI_API_KEY が必要
  - これらはライブラリ API として利用する想定です（CLI エントリはありません）

ログ
- 共通のログ設定ユーティリティを用意しています（kabusys.utils.logging_setup.setup_logging）。
- デフォルト log_dir: logs/
- 各起動スクリプトは app_name を指定してログファイル（例: logs/execution.log, logs/monitoring.log）を出力します。

停止 / Kill Switch
- 手動停止
  - data/stop_requested.flag を作成すると run_execution/run_monitoring のループで検知して停止します。
- 自動停止（Kill Switch）
  - 監視コンポーネント（KillSwitch）が条件を満たすと data/kill.flag を書き込み、ExecutionEngine を停止するトリガーになります。
  - Settings の KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動でクリアします（本番では 0 推奨）。

ディレクトリ構成
----------------

主要ファイル・ディレクトリの概観（src/kabusys 以下を想定）:

- run_monitoring.py
  - SystemMonitor のポーリングループ起動。MONITOR_POLL_INTERVAL で間隔を指定可能。
- run_execution.py
  - ExecutionEngine の起動スクリプト。paper_trading モードをサポート。

- config.py
  - 環境変数 / .env 自動読み込み、Settings クラス（各種パス・フラグ・閾値）を提供。
- config_setup.py
  - .env 対話式作成ウィザード。

- validate_config.py
  - 起動前チェック CLI（必須環境変数・config yaml の存在チェック等）。

- utils/
  - logging_setup.py — 統一的なログ出力設定（Stream + TimedRotatingFileHandler）
  - process_priority.py — psutil を用いたプロセス優先度 / CPU affinity 設定
  - など

- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化・永続化レイヤ
  - system_monitor.py — CPU/メモリ/ディスク・データ鮮度チェック
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — kill.flag の評価と書き込み
  - monitoring_engine.py — 各 Monitor を束ねるエンジン
  - alert_manager.py（利用される想定: アラート送信ロジック）
  - trade_monitor.py（滞留注文や約定異常の検出）

- execution/
  - execution_engine.py — 実際の注文実行ロジック（EngineConfig 等）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py
  -（ブローカー抽象化・リスク制御・リポジトリ群）

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算、単元丸め、aggregate cap 調整
  - risk_adjustment.py — セクター上限、レジーム乗数

- research/
  - factor_research.py — momentum / volatility / value 計算（DuckDB を利用）
  - feature_exploration.py — forward returns / IC / 統計サマリー

- ai/
  - news_nlp.py — OpenAI を用いた銘柄別ニュースセンチメントスコア付与（ai_scores テーブルへ書き込み）
  - regime_detector.py — マクロニュース + ETF MA200 で市場レジーム判定（market_regime テーブルへ書き込み）

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成

- data/（ランタイム）
  - monitoring / execution 用の SQLite DB（デフォルト: data/monitoring.db, data/paper_trading.db）
  - execution.pid, stop_requested.flag, kill.flag など制御ファイルを配置

実運用上の注意
----------------
- 本番環境（KABUSYS_ENV=live）では設定ミスが重大なリスクを招くため、validate_config と .env の確認を必ず行ってください。
- kill.flag / stop_requested.flag の扱いには注意してください（特に KILL_FLAG_CLEAR_ON_START 設定）。
- OpenAI API を利用する処理はレートやコストに注意して運用してください。API エラーは基本的にフェイルセーフ（スコア=0 等）で扱う設計になっていますが、頻繁に失敗する場合は運用見直しが必要です。
- ログ・DB のディスク容量管理（ログローテーション・DuckDB / SQLite ファイルバックアップ・圧縮等）を検討してください。

貢献
----
- バグ報告・改善提案は Pull Request / Issue で受け付けてください。
- 新しい戦略や BrokerClient の実装、monitoring のアラート送信先の追加などは歓迎します。

ライセンス / バージョン
------------------------
- パッケージバージョンは kabusys.__version__ = "0.1.0"（src/kabusys/__init__.py）。
- ライセンスはプロジェクトルートの LICENSE を参照してください（存在しない場合はお問い合わせください）。

以上。必要であれば README に含めるコマンド例や systemd / supervisor 用のサービステンプレート、より詳細な設定例（.env.example）も追加できます。どの情報を優先的に追記しますか？