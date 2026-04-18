README
=====

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコードベースです。本システムは以下の主要機能を持ちます。

- 発注エンジン（ExecutionEngine）: 実際のブローカーまたはモックブローカーを介して注文を管理・実行します。  
  KABUSYS_ENV=paper_trading の場合、MockBrokerClient を用いて data/paper_trading.db に記録し、本番 DB と完全分離します。
- 監視（Monitoring）: システム状態・データ鮮度・注文状況・リスク指標を定期ポーリングして SQLite に永続化し、アラートや Kill Switch を評価します。
- ポートフォリオ構築: 候補選定、重み計算、ポジションサイズ計算、セクターキャップやレジーム乗数などの純粋関数群を提供します。
- リサーチ: DuckDB 上の時系列データを用いたファクター計算（モメンタム、ボラティリティ、バリュー等）や特徴量探索ユーティリティ。
- AI モジュール: OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント（news_nlp）や市場レジーム判定（regime_detector）。
- 運用ツール: .env 対話式設定ウィザード、設定検証 CLI、Paper Trading 検証レポート生成スクリプトなど。

主な特徴
--------
- 環境分離: paper_trading と live を明確に区別。paper_trading 時は専用 SQLite に記録。
- フェイルセーフ: AI 呼び出しや外部依存の失敗はスキップ／フォールバックしてシステム継続を狙う設計。
- 冪等性を考慮した DB 書き込み（必要箇所で BEGIN/COMMIT/ROLLBACK を使用）。
- ログはコンソール + 日次ローテートファイル出力（logs/）に統一。
- プロセス優先度・CPU affinity 設定ユーティリティ（psutil ベース）。

セットアップ手順
----------------

前提
- Python 3.10+（コードは型注釈・記述スタイルからこの世代を想定）
- システムに応じたパッケージ（主に duckdb, psutil, openai, PyYAML が利用される）

1. リポジトリを取得
   - git clone ... または適切に展開してください。

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 主要パッケージを個別にインストールする一例:
     - pip install duckdb psutil openai PyYAML

4. 環境変数設定（.env）
   - 対話式ウィザードで .env を作成:
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動で作成してください。
   - 自動ロード: 起動時に .env がプロジェクトルートにあれば自動的に読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

5. 設定検証
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いになります:
     - python -m kabusys.validate_config --strict

6. データディレクトリ等
   - デフォルトでは data/ と logs/ を利用します。権限・ディスク容量に注意してください。

主な環境変数（抜粋）
--------------------
（Settings クラスで参照・デフォルトが指定されています）

必須
- JQUANTS_REFRESH_TOKEN : J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD     : kabuステーション API パスワード

任意／デフォルト
- KABUSYS_ENV           : 実行環境 (development | paper_trading | live)（デフォルト: development）
- LOG_LEVEL             : ログレベル（DEBUG/INFO/...）（デフォルト: INFO）
- DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH           : 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE       : ペーパートレードの約定モード（instant | partial | never | reject）（デフォルト: instant）
- OPENAI_API_KEY        : OpenAI API キー（news_nlp, regime_detector で使用）
- MONITOR_POLL_INTERVAL : 監視ループのポーリング間隔（秒、監視スクリプト用。デフォルト 60）
- KILL_FLAG_CLEAR_ON_START : Kill Flag を起動時に自動クリアするか（0/1）（本番では 0 推奨）

注意事項
- 監視（monitoring）は説明通り「環境にかかわらず」本番 sqlite_path を使用する設計箇所があります（安全上の意図により）。Execution は KABUSYS_ENV に応じて paper_sqlite_path を使用します。
- .env は絶対にコミットしないでください（シークレット情報を含む）。

使い方
------

1. ExecutionEngine の起動（通常運用）
   - python -m kabusys.run_execution
   - 仕様:
     - 起動時にプロセス優先度を "high" に設定し、ブローカークライアント等を構築して実行スレッドを開始します。
     - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH に記録されます。
     - 起動中に data/stop_requested.flag または data/kill.flag を作成すると停止処理が走ります（stop flag は run_execution 内のループで検知）。

2. Monitoring の起動
   - python -m kabusys.run_monitoring
   - 仕様:
     - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可（デフォルト 60 秒）。
     - SystemMonitor / TradeMonitor / RiskMonitor を初期化して定期実行し、結果を monitoring.db (SQLITE_PATH) に保存します。
     - 停止は data/stop_requested.flag の作成で検知します。

3. .env 設定ウィザード
   - python -m kabusys.config_setup
   - 対話的に .env を作成・更新できます。

4. 設定検証
   - python -m kabusys.validate_config
   - 起動前に必須 env や config/*.yaml の存在・パーサチェックを行います（PyYAML があれば内容検証も実施）。

5. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report
   - オプション:
     - --from YYYY-MM-DD
     - --to YYYY-MM-DD
     - --db PATH  (PAPER_TRADING_SQLITE_PATH より優先して指定可能)
   - 出力: 稼働率、注文成功率、レイテンシ指標などのサマリと PASS/FAIL 判定。

6. AI 関連
   - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)
   - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
   - OpenAI キーは OPENAI_API_KEY 環境変数、または関数引数で渡します。API 呼び出し失敗時はフォールバック動作（スコア 0 等）を行います。

運用用フラグ / ファイル
-----------------------
- data/execution.pid (デフォルト PID ファイル) — 実行エンジンが PID を書き込みます
- data/stop_requested.flag — run_execution / run_monitoring が存在をチェックして優雅に停止します
- data/kill.flag — KillSwitch による強制停止シグナル（監視が検知して Execution を止めるために用いる）
- logs/ — 日次ローテートされるログファイルが出力されます（app_name によりファイル名が変わります）

ディレクトリ構成
----------------

概要（src/kabusys 以下の主要ファイル・モジュール）
- __init__.py
  - バージョンなど
- config.py
  - 環境変数の読み込みと Settings クラス
  - .env 自動ロード機能（プロジェクトルート検出）
- config_setup.py
  - .env を対話的に生成するウィザード
- validate_config.py
  - 起動前の設定検証 CLI
- run_execution.py
  - ExecutionEngine 起動スクリプト
- run_monitoring.py
  - SystemMonitor のポーリング起動スクリプト
- utils/
  - logging_setup.py : 統一的なログ設定
  - process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティ
- monitoring/
  - monitoring_db.py : SQLite テーブル初期化と永続化 API（MonitoringDB クラス）
  - system_monitor.py : システム状態・データ鮮度の監視
  - risk_monitor.py : ドローダウン・ポジション上限の監視
  - trade_monitor.py : （注文監視ロジック：コードベースに含まれる部分に依存）
  - kill_switch.py : kill.flag の書き込み・評価
  - monitoring_engine.py : 各 Monitor を束ねるエンジン
  - alert_manager.py : （アラート送信機能：LINE 等との連携を想定）
- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, order_repository.py, reconciler.py, risk_manager.py
  - （実際の発注フロー、ブローカラッパー、リスク管理等）
- portfolio/
  - portfolio_builder.py : 候補選定、重み計算
  - position_sizing.py : 発注株数計算
  - risk_adjustment.py : セクターキャップ、レジーム乗数
- research/
  - factor_research.py : ファクター計算（momentum, volatility, value）
  - feature_exploration.py : 将来リターン計算、IC、統計サマリ等
- ai/
  - news_nlp.py : ニュースセンチメントスコアリング（OpenAI）
  - regime_detector.py : 市場レジーム判定（OpenAI + ETF MA）
- tools/
  - paper_verification_report.py : Paper Trading の検証レポート生成ツール

開発／デプロイ上の注意
---------------------
- 本番環境（KABUSYS_ENV=live）では LINE トークンや kill flag の設定等、運用上の注意が多数あります。validate_config の WARN を必ず確認してください。
- .env の自動読み込み機構はプロジェクトルート検出ロジック（.git または pyproject.toml）に依存します。配布後やテスト環境で正しく動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用して手動で env を管理してください。
- OpenAI の呼び出しは外部 API に依存します。API レートや課金、秘密情報管理に注意してください。
- プロセス優先度設定や CPU affinity はプラットフォームや権限により失敗する場合があります（ログに警告を出して継続します）。

追加情報 / よくある操作
----------------------
- ログ設定をカスタマイズするには kabusys.utils.logging_setup.setup_logging の引数（app_name, log_dir, level）を参照してください。
- 監視ポーリング間隔を一時的に変更するには MONITOR_POLL_INTERVAL を設定して run_monitoring を起動してください。
- Kill Switch を手動で解除したい場合:
  - data/kill.flag を削除するか、設定で KILL_FLAG_CLEAR_ON_START を使って起動時に自動クリアする（本番では非推奨）。

ライセンス / 貢献
-----------------
- 本 README はコードベースから自動生成された説明です。実際のライセンスや貢献ルールはリポジトリの LICENSE / CONTRIBUTING ファイルを参照してください。

お問い合わせ
------------
- 開発・運用に関する質問はリポジトリのイシューやチーム内チャネルへお願いします。README に書ききれない運用手順やチェックリストは別途運用ドキュメントにまとめることを推奨します。

以上。README に含めたい追加の内容（サンプル .env、起動スクリプトの systemd ユニット例、より詳しい API ドキュメント等）があれば教えてください。必要に応じて追記します。