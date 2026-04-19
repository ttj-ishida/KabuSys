KabuSys — 日本株自動売買システム
================================

※ この README はコードベース（src/kabusys 以下）を基に作成した簡易ドキュメントです。

概要
----
KabuSys は日本株向けの自動売買フレームワークです。主な役割は以下です。

- 戦略（ファクター計算・特徴量・ポートフォリオ構築）と発注ロジックの分離
- 実行（ExecutionEngine）と監視（Monitoring）コンポーネントによる運用管理
- ペーパートレード用の分離 DB / Mock ブローカー対応
- ニュースを用いた AI（OpenAI）によるセンチメント算出・レジーム判定
- DuckDB / SQLite を用いた分析・監視データの永続化

主な機能
--------
- 環境設定ウィザード（.env 自動生成補助）: kabusys.config_setup
- 設定検証 CLI（.env と config/*.yaml の基本チェック）: kabusys.validate_config
- 実行エンジン起動スクリプト（run_execution）:
  - 本番 / ペーパートレード切替
  - ブローカークライアントのファクトリ、リスク管理、注文管理、リコンシリエーション
  - PID ファイル・停止フラグ監視
- 監視ループ起動スクリプト（run_monitoring）:
  - SystemMonitor / TradeMonitor / RiskMonitor を組み合わせたポーリング
  - Kill Switch（条件を満たすと data/kill.flag を作成）
  - モニタリングデータを SQLite へ永続化
- Portfolio モジュール:
  - 候補選定、各種重み付け、ポジションサイズ計算、セクター制限、レジーム乗数
- Research モジュール:
  - Momentum / Volatility / Value ファクター計算
  - 将来リターン、IC 計算、統計サマリ
- AI モジュール:
  - news_nlp: ニュース記事の LLM（OpenAI）による銘柄別センチメントスコア化（ai_scores へ保存）
  - regime_detector: ETF とマクロニュースを組み合わせた市場レジーム判定
- ツール:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）

前提 / 必要ライブラリ
--------------------
（プロジェクトに requirements.txt がない場合は以下を目安にインストールしてください）

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML の検証に必要だが任意）
- （sqlite3 は標準ライブラリ）

セットアップ手順
----------------
1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
   （実際はプロジェクトの requirements.txt に合わせてください）
4. 環境変数設定 (.env) を用意
   - 対話式ウィザード: python -m kabusys.config_setup
   - または .env を手動作成（.env.example を参考に）
   - 必須環境変数:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - 主な環境変数:
     - KABUSYS_ENV (development | paper_trading | live)
     - OPENAI_API_KEY (AI 機能を利用する場合)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（ペーパートレード DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR）
     - MONITOR_POLL_INTERVAL（監視ポーリング秒、デフォルト 60）
     - PAPER_FILL_MODE（instant | partial | never | reject）
5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 警告も失敗扱いにする場合は --strict を付与

使い方（実行方法）
-----------------

- 実行エンジン（Execution）
  - 用途: 発注・注文管理を行うエンジンを起動
  - ペーパートレード時は KABUSYS_ENV=paper_trading を設定すると MockBroker を使用し、data/paper_trading.db に記録されます（本番 DB と分離）。
  - 起動:
    - python -m kabusys.run_execution
  - 動作:
    - 起動時にプロセス優先度を高に設定
    - 指定の SQLite/ DuckDB に接続
    - Engine を別スレッドで実行し、data/stop_requested.flag の存在で停止をトリガー

- 監視（Monitoring）
  - 用途: SystemMonitor 等のポーリングを行い、監視データを収集・Kill Switch 判定・アラート発行
  - 起動:
    - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可（デフォルト 60 秒）
  - 注意:
    - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（data/monitoring.db 等）を使用して監視テーブルを初期化します
    - 停止フラグファイル stop_requested.flag をプロジェクト data/ 配下に置くと監視プロセスが終了します

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - もしくは --db で別 DB を指定

- AI 機能（ライブラリ呼び出し）
  - ニューススコア: from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

ログ
----
- ログ設定は kabusys.utils.logging_setup.setup_logging によって統一管理されます。
- デフォルトでは logs/<app_name>.log に日次ローテーションで出力（30 日保持）。
- コンソール出力は stdout に出ます。

データ / フラグファイル
-----------------------
- data/ ディレクトリに以下のファイルが作成・使用されます（デフォルトパス）。
  - data/monitoring.db : 監視用 SQLite DB（monitoring_db.init_monitoring_db がテーブルを作成）
  - data/paper_trading.db : ペーパートレード用 DB（KABUSYS_ENV=paper_trading 時）
  - data/kabusys.duckdb : DuckDB（分析用）
  - data/execution.pid : ExecutionEngine の PID ファイル（実行時に作成）
  - data/kill.flag / data/stop_requested.flag : 停止 / Kill Switch 制御用のフラグファイル

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys をルートにした主要モジュール）

- kabusys/
  - __init__.py                 : パッケージ定義（__version__ 等）
  - config.py                   : 環境変数 / 設定読み込みロジック（Settings クラス）
  - config_setup.py             : .env 対話型ウィザード
  - validate_config.py          : 設定検証 CLI
  - run_execution.py            : ExecutionEngine 起動スクリプト
  - run_monitoring.py           : SystemMonitor ポーリング起動スクリプト

  - ai/
    - news_nlp.py               : ニュースセンチメント（OpenAI 呼び出し、ai_scores への書込）
    - regime_detector.py        : マクロ + ETF によるレジーム判定

  - monitoring/
    - monitoring_db.py          : SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py         : システム状態・データ鮮度監視
    - trade_monitor.py          : （省略）注文滞留・約定異常検出など
    - risk_monitor.py           : ドローダウン／ポジション上限監視
    - kill_switch.py            : kill.flag 管理
    - monitoring_engine.py      : 全 Monitor を束ねるエンジン
    - alert_manager.py          : （省略）アラート送信ロジック（LINE 等）

  - execution/
    - execution_engine.py       : ExecutionEngine 実装（run_session 等）
    - broker_factory.py         : Broker クライアントの生成（Mock / 実ブローカー切替）
    - order_manager.py          : 発注管理
    - order_repository.py       : 注文永続化
    - reconciler.py             : ブローカーとの整合処理
    - risk_manager.py           : リスク管理ロジック

  - portfolio/
    - portfolio_builder.py      : 候補選定・重み計算
    - position_sizing.py        : 株数計算・集約 cap
    - risk_adjustment.py        : セクター制限・レジーム乗数

  - research/
    - factor_research.py        : Momentum / Volatility / Value 等のファクター計算
    - feature_exploration.py    : 将来リターン・IC・統計サマリ

  - data/                       : （実行時作成）DB・PID・フラグ等を格納するディレクトリ
  - logs/                       : ログファイル（logs/<app>.log）

設計上の注意点・運用メモ
----------------------
- .env は絶対にリポジトリにコミットしないでください（シークレットを含む）。
- Monitoring は監視用の sqlite_path を使用します（環境に関係なく本番用の sqlite_path を参照する挙動あり）。
- Execution は KABUSYS_ENV=paper_trading のとき paper_sqlite_path を使い、DB を完全に分離します。
- Kill Switch（kill.flag）は監視側が書き込みを行い、ExecutionEngine は起動時および実行中にフラグをチェックして安全に停止します。
- OpenAI を利用する機能は API キーが必須です。コストやレート制限に注意して運用してください。
- プロセス優先度設定（psutil を使用）や CPU affinity 設定は OS や権限により失敗する場合がありますが、フェイルセーフで続行します。

よく使うコマンドまとめ
--------------------
- .env 作成ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視ループ起動:
  - python -m kabusys.run_monitoring
- ペーパートレード検証レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

サポート / 追加情報
-------------------
この README はコードの読み取りにより自動生成した概要ドキュメントです。実運用時は以下を確認してください。

- config/ 下の YAML（system_config.yaml など）とそれらの生成スクリプト
- 実際の ExecutionEngine / Broker 実装（ブローカー API の仕様や認証方式）
- alert_manager（LINE 通知等）の設定と動作確認
- OpenAI の利用は API キー・課金の管理に注意

必要であれば、特定モジュール（ExecutionEngine の起動手順、監視アラート設定、AI スコア保存の DB スキーマなど）について詳細な README / 使用例を追加できます。必要項目を教えてください。