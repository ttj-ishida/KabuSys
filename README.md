README
======

概要
----
KabuSys は日本株の自動売買システムのコアライブラリ群です。本コードベースは取引実行（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ（ファクター計算・特徴量解析）、AI を使ったニュース NLP / レジーム判定などの主要コンポーネントを含みます。設計上、各モジュールは現物取引ロジック（ブローカー API）とデータ処理（DuckDB / SQLite）を分離し、テストしやすい純粋関数や小さなクラスに分割されています。

主な特徴
--------
- Execution
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - ブローカー抽象（BrokerClientFactory）を通した実取引 / Paper Trading（分離された SQLite）切り替え
  - 再起動時のリコンシリエーション（Reconciler）
  - Order 管理（OrderManager / OrderRepository）
  - RiskManager による注文制限・サーキットブレーカ等
- Monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - 監視ログ永続化（SQLite、monitoring_db）
  - LINE 通知用 AlertManager（クールダウン付き）
  - kill.flag による ExecutionEngine 停止シグナル
  - streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）
- Portfolio / Risk
  - 候補選定、重み計算（等金額 / スコア加重）
  - セクター制約・レジーム乗数の適用
  - 株数算出（lot 単位丸め、aggregate cap、risk-based 方式）
- Research
  - DuckDB によるファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC、統計サマリー等の研究ユーティリティ
- AI
  - ニュース記事を OpenAI（gpt-4o-mini）でセンチメント評価し ai_scores に書き込む（news_nlp）
  - マクロニュース + ETF MA を使った市場レジーム判定（regime_detector）
  - API 呼び出しは冪等性・リトライ・部分失敗回復を考慮
- ユーティリティ
  - 環境変数 / .env 自動ロード（config.Settings）
  - プロセス優先度・CPU affinity の設定ユーティリティ（utils.process_priority）
  - Paper Trading 向け検証レポート生成ツール（tools.paper_verification_report）

セットアップ手順
----------------
1. Python 環境
   - Python 3.9+（コードは typing の新構文等を利用）
   - 推奨: 仮想環境を作成して依存を分ける
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要なパッケージをインストール
   - 代表的に必要となるパッケージ:
     - duckdb, psutil, requests, openai, streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt がない場合は上記を手動でインストールしてください。）

3. データディレクトリ作成
   - デフォルトでは data/ に DB 等を置く想定です。必要に応じて作成:
     - mkdir -p data

4. 環境変数設定
   - .env（プロジェクトルート）に環境変数を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 主に必要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...           （AI 機能を使う場合）
     - KABUSYS_ENV=development|paper_trading|live
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - LOG_LEVEL=INFO
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
   - PAPER_FILL_MODE（paper_trading 時のモック約定挙動）:
     - PAPER_FILL_MODE=instant|partial|never|reject  （デフォルト: instant）
   - MONITOR_POLL_INTERVAL：監視ポーリング間隔（秒、run_monitoring で利用）

使い方
------
- 実行（ExecutionEngine）
  - 本番 / 開発 / ペーパートレードの切替は KABUSYS_ENV で行います。
    - KABUSYS_ENV=paper_trading を指定すると MockBrokerClient が使われ、paper_trading 用の SQLite（デフォルト data/paper_trading.db）へ記録されます。本番 DB と完全分離されます。
  - 起動:
    - python -m kabusys.run_execution
  - 実行時のプロセス優先度を High に設定し、PID ファイル（Settings.pid_file_path）を利用して死活検査を行います。kill.flag（Settings.kill_flag_path）があると外部から停止シグナルできます。

- 監視（MonitoringEngine）
  - 監視ループを起動:
    - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書きできます（秒、デフォルト 60）。0 以下の値は無視されデフォルトにフォールバックします。
  - 監視は sqlite（monitoring.db）へシステム状態 / トレードログ / リスクログ / positions / dashboard を書き込みます。Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用します（意図的な設計）。

- 監視ダッシュボード（Streamlit）
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で DB を開き、Overview / Positions / Orders / System タブを提供します。

- Paper Trading 検証レポート
  - コマンド:
    - python -m kabusys.tools.paper_verification_report
    - オプションで集計期間を指定:
      - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - デフォルト DB は data/paper_trading.db。--db で上書き可能。

- AI 関連
  - ニュースセンチメント（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は OpenAI API キー（OPENAI_API_KEY）を必要とします。関数は DuckDB 接続と target_date を受け取り、テーブルへ結果を書き込みます。
  - LLM 呼び出しはリトライや JSON バリデーション等の堅牢化処理が入っていますが、API キーが未設定だと ValueError を投げます。

重要な挙動・運用メモ
--------------------
- Settings はプロジェクトルートの .env / .env.local を自動読み込みします（OS 環境変数が優先）。プロジェクトルート検出は .git / pyproject.toml を基準に行います。
- Paper Trading（KABUSYS_ENV=paper_trading）は本番の monitoring.db を上書きしないよう paper_trading 用の SQLite を使用します。
- kill.flag の書き込みは KillSwitch が行い、ExecutionEngine 側で検出して安全に停止できます。kill.flag はデフォルトで data/kill.flag（Settings.kill_flag_path）に保存されます。
- PID ファイル（Settings.pid_file_path）を用いて実行プロセスの生死判定を行い、PID が stale（存在しないプロセスを指す）場合はファイルを削除してリスクイベントを記録します。
- OpenAI や外部 API 呼び出しに関してはリトライ（指数バックオフ）やフォールバック（失敗時は 0.0 やスキップ）を実装しています。運用時は API レート制限や課金に注意してください。

ディレクトリ構成（抜粋）
-----------------------
src/
  kabusys/
    __init__.py
    config.py                      # 環境変数 / .env ローダー、Settings クラス
    run_execution.py               # ExecutionEngine 起動スクリプト
    run_monitoring.py              # SystemMonitor ポーリング起動スクリプト
    tools/
      __init__.py
      paper_verification_report.py # Paper Trading 検証レポート生成
    execution/
      order_manager.py
      order_repository.py
      reconciler.py
      execution_engine.py          # （コアエンジン、コードベース中に参照あり）
      broker_factory.py
      broker_api.py
      order_record.py
      ...
    monitoring/
      monitoring_db.py
      system_monitor.py
      trade_monitor.py
      risk_monitor.py
      kill_switch.py
      alert_manager.py
      monitoring_engine.py
      streamlit_dashboard.py
      __init__.py
    portfolio/
      portfolio_builder.py
      position_sizing.py
      risk_adjustment.py
      __init__.py
    research/
      factor_research.py
      feature_exploration.py
      __init__.py
    ai/
      news_nlp.py
      regime_detector.py
      __init__.py
    data/
      pipeline.py                   # DuckDB 周りのパイプライン（get_last_price_date 等）
      stats.py                      # zscore_normalize 等（research から import）
    utils/
      process_priority.py
      __init__.py

（上記はコードベースから抽出した主要ファイルの一覧です。実際のプロジェクトにはさらにモジュールやテストが含まれる場合があります。）

トラブルシューティング
--------------------
- DB が開けない / 存在しない:
  - デフォルトパス（data/monitoring.db, data/paper_trading.db, data/kabusys.duckdb）を確認し、必要なら作成してください。streamlit ダッシュボードは読み取り専用で開くためパスが正しいか確認してください。
- OpenAI API に関するエラー:
  - OPENAI_API_KEY が設定されていることを確認してください。API のレスポンス形式やレート制限で失敗する場合はログを確認し、必要ならリトライ設定やバッチサイズを調整してください。
- MONITOR_POLL_INTERVAL の指定が無効:
  - 環境変数は整数（>=1）で設定してください。0 や負値はデフォルト（60秒）にフォールバックします。
- プロセス優先度設定が失敗する:
  - 権限不足（Linux の nice の低い値や Windows の権限）で AccessDenied が起きることがあります。警告ログは出ますが処理は継続します。

ライセンス・貢献
----------------
- 本 README ではライセンス情報を含めていません。実際のリポジトリの LICENSE や CONTRIBUTING ドキュメントを参照してください。

補足
----
- ドキュメント内（関数 / クラス）に運用上の重要な注記や設計意図（例: ルックアヘッドバイアス防止、フェイルセーフ設計）が多数含まれています。各機能をカスタマイズする際は該当モジュールの docstring を参照してください。

以上。必要であれば別途「環境変数例のテンプレート（.env.example）」や「運用手順（Start/Stop/Backup）」のサンプルを作成しますか？