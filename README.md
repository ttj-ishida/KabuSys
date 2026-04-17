KabuSys — 日本株自動売買システム
======================

このリポジトリは、日本株の自動売買に必要な実行エンジン、監視・アラート機構、ポートフォリオ構築、リサーチ／ファクター計算、及びニュースNLP を含む補助ツール群をまとめた Python パッケージです。本 README はローカルでのセットアップと主要な実行方法、構成の概要を日本語でまとめたものです。

プロジェクト概要
--------------
KabuSys は次のような機能を持つモジュール群で構成されています：

- Execution：ブローカーとのやり取りを行い、注文発行・状態管理を行う実行エンジン（ExecutionEngine、OrderManager など）。
- Monitoring：システム状態・注文状態・リスク（ドローダウン／ポジション上限等）を定期監視し、ログ保存・アラート・Kill Switch を提供。
- Portfolio：銘柄選定、重み付け、ポジションサイズ計算、セクター制限等のポートフォリオ構築ロジック（純粋関数群）。
- Research：DuckDB を用いたファクター計算（モメンタム、ボラティリティ、バリュー）や特徴量解析ユーティリティ。
- AI：OpenAI（gpt-4o-mini）を用いるニュースセンチメント（news_nlp）と市場レジーム判定（regime_detector）。
- Tools：Paper Trading の検証用レポートなど、運用補助スクリプト。
- Utils / Config：環境変数読み込み、プロセス優先度設定などユーティリティ。

主な特徴（機能一覧）
------------------
- 実行エンジン（ExecutionEngine）:
  - ブローカークライアント（本番 or paper_trading 用の Mock）を切替可能。
  - リコンシリエーション（再起動後の注文同期）、Order State Machine、リスク管理を実装。
- 監視（Monitoring）:
  - CPU/メモリ/Disk、Execution プロセス生存、株価データ鮮度を定期ログ化。
  - 注文滞留・約定異常価格・ドローダウン・ポジション上限の監視およびリスクログ記録。
  - LINE プッシュ通知（AlertManager）、Kill Switch（ファイル書き込みで Execution を停止）をサポート。
  - Streamlit ベースの監視ダッシュボード（read-only DB 接続）を提供。
- Portfolio ツール:
  - 候補選定、等配分・スコア加重、リスクベースのポジションサイジング等。
  - セクターキャップ適用、レジーム乗数の導入。
- Research:
  - DuckDB を利用した高速なファクター計算（momentum/value/volatility）と IC / 統計サマリ。
- AI:
  - ニュース集約 → LLM によるセンチメントスコア化 → ai_scores テーブルへ書込。
  - マクロ記事から市場レジーム（bull/neutral/bear）を推定して永続化。
- 運用ツール:
  - Paper Trading 検証レポート生成スクリプト（kabusys.tools.paper_verification_report）。
  - 環境変数自動読み込み（.env / .env.local）、設定管理クラス Settings。

セットアップ手順
----------------

前提
- Python 3.9+（typing の構文等に依存）
- Git（任意）

1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - （requirements.txt がない場合）最低限の依存:
     pip install duckdb psutil openai requests streamlit
   - 他にテスト/開発用パッケージがあれば適宜インストールしてください。

4. パッケージを編集モードでインストール（任意）
   - プロジェクトルートで:
     pip install -e src

   （pip install -e しない場合は実行時に PYTHONPATH を src に向ける必要があります:
   export PYTHONPATH=$(pwd)/src  → Windows: set PYTHONPATH=%CD%\src）

5. データディレクトリ
   - デフォルトでは data/ 配下に DB 等を作成します（例: data/monitoring.db, data/kabusys.duckdb）。
   - 必要に応じてディレクトリを作成してください:
     mkdir -p data

環境変数（主なもの）
- 必須（Settings クラスから参照されるため、本番的に使用する場合は設定が必要）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード

- 動作モード
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
    - paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB に記録する。

- データベース / ファイルパス（省略時はデフォルト）
  - DUCKDB_PATH（例: data/kabusys.duckdb）
  - SQLITE_PATH（監視ログ、例: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、例: data/paper_trading.db）
  - PID_FILE_PATH（実行エンジン PID ファイル、例: data/execution.pid）
  - KILL_FLAG_PATH（Kill Switch 用フラグ、例: data/kill.flag）
  - PAPER_FILL_MODE（paper 塗り具合: instant | partial | never | reject、デフォルト: instant）

- 監視・実行関連
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 — .env の自動読み込みを無効化

Settings モジュールはプロジェクトルートの .env / .env.local を自動で読み込みます（OS 環境変数が優先）。.env がない場合は .env.example を参考に作成してください。

使い方（主要コマンド）
--------------------

注: パッケージを pip install -e src している前提のコマンド例。していない場合は PYTHONPATH を設定して python -m を実行してください。

1. 監視ループの起動
   - 監視プロセスを起動して system_status / trade_logs / risk_logs / dashboard を更新します。
   - コマンド:
     python -m kabusys.run_monitoring
   - オプション:
     - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。
   - 停止:
     - data/stop_requested.flag を作成するとループは安全に終了します（スクリプト内で参照）。

2. 実行エンジン（Execution）の起動
   - ブローカー接続・注文処理を行う実行プロセスです。
   - コマンド:
     python -m kabusys.run_execution
   - 動作モード:
     - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を利用し、data/paper_trading.db に記録します（本番 DB と分離）。
   - 停止/制御:
     - data/stop_requested.flag を作成すると起動中のエンジンに停止を指示します。
     - kill.flag は KillSwitch が書き込み、ExecutionEngine 側で検出して停止する仕組み（運用上の自動停止トリガー）。

3. Streamlit ダッシュボード（監視画面）
   - コマンド:
     streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、ダッシュボード表示します（MonitoringEngine が DB を更新している必要があります）。

4. Paper Trading 検証レポート
   - コマンド（期間指定可）:
     python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - DB が別パスの場合:
     python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

5. AI 関連
   - ニューススコア付け:
     - kabusys.ai.news_nlp.score_news(conn, target_date, api_key=...)
       （DuckDB 接続を渡して呼び出すユーティリティ関数）
   - レジーム判定:
     - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用上の注意
-------------
- paper_trading モードは実際のブローカーと完全に分離して検証可能です。データベースも data/paper_trading.db に分離されます。
- Settings は .env の自動読み込みを行いますが、CI / テストで不要なときは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化できます。
- Kill Switch（KillSwitch） はデータベース上の閾値検出（ドローダウン等）に応じて data/kill.flag を書き込み、ExecutionEngine を安全に停止させるために用います。手動で停止したい場合は stop_requested.flag を作成してください（run_* スクリプトはそれを検出して終了します）。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）を必要とします。API 呼び出しはリトライやフェイルセーフを備えていますが、料金やレート制限に注意してください。

ディレクトリ構成（主要ファイル）
------------------------------

概略ツリー（src/kabusys 以下、抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                    — 環境変数 / Settings 管理
  - run_monitoring.py            — SystemMonitor ポーリング起動スクリプト
  - run_execution.py             — ExecutionEngine 起動スクリプト
  - data/                        — （実運用で使用するデータフォルダ）
  - utils/
    - process_priority.py        — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py           — SQLite 永続化層（system_status, trade_logs, ...）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py
    - kill_switch.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - execution_engine.py       （実行エンジン本体は該当ファイル）
    - broker_factory.py
    - ...（OrderRecord / broker API 抽象等）
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

各ファイルの docstring に機能・設計方針・注意点が書かれているため、詳細な実装意図はソース内コメントも参照してください。

開発・拡張のヒント
-------------------
- DuckDB を使ったデータ処理は接続を関数に渡す設計。テスト用に小さな DuckDB ファイルを用意すると便利です。
- AI 呼び出し部分は _call_openai_api を通しているため、テストではこれをモックすることで外部 API 依存を切れます。
- Settings は .env/.env.local をプロジェクトルートから自動読み込みします。CI や一時的に自動ロードを防ぎたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
- 監視・実行プロセス間はファイル（PID / stop / kill flag）と DB で疎結合に設計されています。運用時は data/ 以下のパーミッション・バックアップを考慮してください。

ライセンス・貢献
----------------
（ここにプロジェクトのライセンスやコントリビューション手順があれば追記してください）

以上。必要であれば README にチュートリアル的な実行例（環境変数ファイルのテンプレート、よくあるトラブルシュート、ユニットテスト実行方法等）を追加できます。どの情報を補足したいか教えてください。