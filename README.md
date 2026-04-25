README — KabuSys
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ基盤のコアライブラリ群です。  
主な目的は以下の通りです。

- システム監視（Monitoring）
- 注文実行エンジン（ExecutionEngine） — 実口座 / ペーパートレード対応
- ポートフォリオ構築（候補選定・重み付け・株数計算）
- リサーチ（ファクター計算・特徴量探索）
- ニュース NLP / レジーム検出（OpenAI を利用したセンチメント評価）
- ユーティリティ（ログ設定、プロセス優先度など）
- ペーパートレード検証レポート生成ツール

本リポジトリはライブラリとして利用できると同時に、パッケージ内の起動スクリプトで実稼働プロセスを起動できます。

主な機能
--------
- 実行エンジン起動スクリプト: run_execution.py
  - KABUSYS_ENV=paper_trading の際は MockBrokerClient を用い、data/paper_trading.db に記録して本番 DB と分離
  - 停止フラグ（stop_requested.flag）の検出、PID ファイル書き込み、リソース制限（リスク管理）連携
- 監視ループ起動スクリプト: run_monitoring.py
  - システム状態（CPU, メモリ, ディスク）、データ鮮度、取引ログの監視
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）
- 設定ウィザード: config_setup.py
  - .env を対話式に生成・更新
- 設定検証 CLI: validate_config.py
  - 必須環境変数、config/*.yaml の存在や基本整合性チェック（--strict オプションあり）
- Paper Trading レポート: tools/paper_verification_report.py
  - ペーパートレード DB から稼働率、注文成功率、レイテンシ等を集計し PASS/FAIL 判定を出力
- ポートフォリオ構築モジュール（pure functions）
  - 候補選定、等配分・スコア加重、セクターキャップ適用、ポジションサイジング（lot 単位丸め等）
- リサーチモジュール
  - Momentum / Volatility / Value 等ファクター計算、前方リターン、IC 計算、統計サマリー
- AI モジュール
  - news_nlp: OpenAI でニュース記事を銘柄別にセンチメント評価して ai_scores に書き込み
  - regime_detector: MA 乖離 + LLM によるマクロセンチメントで日次レジーム判定
- ユーティリティ
  - logging_setup: console + 日次ローテートログを一元設定
  - process_priority: プラットフォーム差を吸収して優先度 / CPU affinity の設定

前提（必須 / 推奨）
-------------------
- Python 3.9+（ソースは型注釈を使用）
- 必要な Python パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config/*.yaml のパース検証に任意）
- DuckDB（Python パッケージで十分）
- （実際にブローカー連携をする場合は kabuステーション等の API 環境）

セットアップ手順
----------------

1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージのインストール（pip）
   - pip install duckdb psutil openai PyYAML
   - 実行環境にあわせて必要な依存を追加してください。

3. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - 対話で J-Quants トークンや KABU_API_PASSWORD などを入力し .env を生成できます。
   - 重要: .env を絶対に Git にコミットしないでください（ウィザード内にも注意書きあり）。

4. 設定検証（起動前チェック）
   - python -m kabusys.validate_config
   - すべて OK であれば 0 を返します。警告を FAIL 扱いにしたい場合は --strict を付与。

5. データディレクトリ / ログディレクトリの確認
   - デフォルト:
     - SQLite (監視): data/monitoring.db
     - ペーパートレード SQLite: data/paper_trading.db
     - DuckDB: data/kabusys.duckdb
     - ログ: logs/
   - .env で上書き可能（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, LOG_DIR 等）

使い方
------

起動スクリプト（プロダクション / 手動起動）
- 実行エンジン（ExecutionEngine）起動
  - python -m kabusys.run_execution
  - 挙動:
    - Settings に基づいて本番 DB / paper_trading DB を選択
    - BrokerClientFactory により適切なブローカークライアント（Mock / 実装）を生成
    - ExecutionEngine をバックグラウンドスレッドで run_session 実行
    - data/stop_requested.flag が存在するとエンジン停止
    - PID ファイル: data/execution.pid（設定で変更可）
- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL によりポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視用 DB（monitoring.db）へ system_status 等を書き込む
    - data/stop_requested.flag が存在すると監視ループ終了

ツール
- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH （PAPER_TRADING_SQLITE_PATH より優先）
  - 出力: コンソールにサマリと PASS/FAIL 判定

ライブラリ利用（例）
- ポートフォリオ構築
  - from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
- リサーチ
  - from kabusys.research import calc_momentum, calc_volatility, calc_value
- AI スコアリング（ニュース）
  - from kabusys.ai.news_nlp import score_news
  - OpenAI API キーが必要（api_key 引数または環境変数 OPENAI_API_KEY）

主要な環境変数（抜粋）
---------------------
- 必須（最低限）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 動作モード
  - KABUSYS_ENV: development | paper_trading | live（デフォルト development）
- DB 関連
  - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
  - SQLITE_PATH (監視用デフォルト data/monitoring.db)
  - PAPER_TRADING_SQLITE_PATH (ペーパートレード用デフォルト data/paper_trading.db)
  - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 用）
- ログ
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
  - LOG_DIR: ログ保存ディレクトリ（デフォルト logs/）
- AI
  - OPENAI_API_KEY: OpenAI の API キー（news_nlp / regime_detector で使用）
- 監視・停止関連
  - MONITOR_POLL_INTERVAL: run_monitoring のポーリング秒（デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1 = クリア）
  - PID_FILE_PATH, KILL_FLAG_PATH: Settings で参照されるファイルパス
- デバッグ / テスト
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると .env の自動読み込みを無効化

ログ・データファイル
-------------------
- デフォルトのログは logs/<app_name>.log に日次ローテートで出力されます（30日保持）。
- 監視データ: data/monitoring.db（SQLite）
- ペーパートレードデータ: data/paper_trading.db（SQLite）
- DuckDB 分析データ: data/kabusys.duckdb
- 停止フラグファイル:
  - data/stop_requested.flag — 起動スクリプトが監視している停止トリガー（存在するとループを終了）
  - data/kill.flag — KillSwitch が書き込む停止理由（Execution 側で参照）

ディレクトリ構成（抜粋）
----------------------
以下は src/kabusys 以下の主なファイルとサブパッケージのツリー（抜粋）です。

- src/
  - kabusys/
    - __init__.py
    - config.py                  # 環境変数・設定ロード
    - config_setup.py            # .env 対話式ウィザード
    - validate_config.py         # 設定検証 CLI
    - run_execution.py           # ExecutionEngine 起動スクリプト
    - run_monitoring.py          # Monitoring 起動スクリプト
    - utils/
      - logging_setup.py         # ログ初期化ユーティリティ
      - process_priority.py      # プロセス優先度 / CPU affinity
    - execution/                 # 注文実行関連（Engine, order_manager など）
      - (複数ファイル)
    - monitoring/
      - monitoring_db.py         # SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
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
    - tools/
      - paper_verification_report.py

開発者向けメモ / 注意点
---------------------
- .env の自動読み込み
  - config.py はプロジェクトルート（.git または pyproject.toml を探索）から .env を自動ロードします。
  - 自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション
  - monitoring_db.init_monitoring_db は必要なテーブル/カラムを冪等に作成します。既存 DB に新しいカラムがない場合は ALTER TABLE を試みます。
- AI モジュール
  - OpenAI API 呼び出しはリトライやレスポンス検証を行いますが、API キーが未設定の場合は例外を発生させます。テスト時は外部呼び出し部分（_call_openai_api）をモックすることを推奨します。
- 停止フラグ
  - 運用では data/stop_requested.flag（または設定で指定したパス）を作成することでプロセスを安全に停止できます。KillSwitch は条件に応じて data/kill.flag を書き込み、アラートや手動介入を促します。

トラブルシューティング
---------------------
- logs/ にファイルが出力されない場合
  - LOG_DIR のパーミッションや作成権限を確認してください。logging_setup はディレクトリ作成に失敗するとコンソール出力のみで継続します。
- .env を読まない / 値が反映されない場合
  - KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されていないか、プロジェクトルート（.git または pyproject.toml）が正しく検出されているか確認してください。
- OpenAI 呼び出しで JSON パースエラーが出る場合
  - モデルの出力が期待した JSON 形式でない可能性があります。ログに出力されるレスポンス確認と、プロンプト（SYSTEM_PROMPT）の調整を検討してください。

ライセンス / 貢献
-----------------
（この README にはライセンス情報は含まれていません。必要に応じて LICENSE ファイルを追加してください。）

最後に
------
この README はリポジトリ内の主要モジュール・スクリプトに基づく概要ドキュメントです。各モジュールの詳細（関数引数や内部仕様）はソースコードの docstring / コメントを参照してください。追加で欲しい情報（例: API の詳しい使い方、実行フロー図、設計ドキュメントなど）があれば教えてください。