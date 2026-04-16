KabuSys — 日本株自動売買システム
概要
- KabuSys は日本株向けの自動売買 / モニタリング / 研究用ユーティリティ群をまとめた Python コードベースです。
- 主な目的:
  - 実行エンジン（ExecutionEngine）による発注管理とリスク管理
  - 監視コンポーネント（System / Trade / Risk）による稼働監視とアラート
  - 研究用ファクター計算・特徴量評価（DuckDB ベース）
  - ニュースを用いた LLM（OpenAI）によるセンチメント評価・レジーム判定
  - Paper Trading 用の分離された DB と検証レポート生成

主な機能一覧
- 実行関連
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - OrderManager / OrderRepository による状態管理とブローカー同期（Reconciler）
  - Paper Trading モード: MockBroker を用い、paper DB に記録（本番 DB と分離）
- 監視関連
  - SystemMonitor：CPU / メモリ / ディスク / プロセス状態 / データ鮮度の監視
  - TradeMonitor：滞留注文・約定価格異常の検出
  - RiskMonitor：ドローダウンやポジション上限の監視とリスクログ
  - MonitoringEngine：各 Monitor を定期実行し、Kill Switch / AlertManager と連携
  - AlertManager：LINE Messaging API へのプッシュ通知
  - Streamlit ベースの監視ダッシュボード（読み取り専用接続）
- 研究・ポートフォリオ
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC 計算、統計サマリ
  - portfolio: 候補選定、重み算出、リスク調整、ポジションサイジング
- AI（OpenAI）
  - news_nlp.score_news: ニュース集合から銘柄別センチメントを LLM で算出して ai_scores に保存
  - regime_detector.score_regime: マクロ記事 + ETF ma200 乖離を合成して市場レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成

セットアップ手順（開発用）
1. リポジトリルートに移動
   - 本パッケージは .env / .env.local を自動で読み込みます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
2. 必須ライブラリをインストール（例）
   - pip install -r requirements.txt
   - 主要依存例: duckdb, psutil, requests, streamlit, openai
   （実際の requirements.txt がない場合は上記パッケージを手動で追加してください）
3. 環境変数（例）
   - JQUANTS_REFRESH_TOKEN=...
   - KABU_API_PASSWORD=...
   - OPENAI_API_KEY=...        （AI 機能を使う場合必須）
   - KABUSYS_ENV=development|paper_trading|live  （デフォルト: development）
   - PAPER_FILL_MODE=instant|partial|never|reject  （paper_trading 用）
   - SQLITE_PATH=data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   - DUCKDB_PATH=data/kabusys.duckdb
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID （LINE 通知を有効にする場合）
   - MONITOR_POLL_INTERVAL=60  （監視ループの秒間隔、デフォルト 60）
4. data ディレクトリ
   - デフォルトでは data/ 以下に SQLite / DuckDB / PID / フラグファイルを置きます。必要に応じ作成してください。

環境変数の自動読み込み
- リポジトリルートの .env を先に読み込み、.env.local を上書きします（ただし OS 環境変数は保護されます）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

使い方（主要コマンド）
- 監視プロセス起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明: SystemMonitor をポーリングし monitoring DB（settings.sqlite_path）にログを残します。
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）。
  - stop フラグ: プロジェクトルート/data/stop_requested.flag を作成すると安全にループを終了します。

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 説明: ExecutionEngine を別スレッドで実行。KABUSYS_ENV=paper_trading の場合は paper DB（PAPER_TRADING_SQLITE_PATH）を使用し MockBrokerClient を利用して本番 DB と分離します。
  - stop フラグ: data/stop_requested.flag を作成するとエンジンへ停止シグナルを送ります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先して DB を指定）
  - 出力: 稼働率・注文成功率・レイテンシ等のサマリと PASS/FAIL 判定

- 監視ダッシュボード（Streamlit）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 説明: 監視用 SQLite に読み取り専用で接続してダッシュボードを表示

- ライブラリとしての利用（AI・研究関数など）
  - 例: from kabusys.ai import score_news
    - score_news(conn, target_date, api_key=None)
  - 例: from kabusys.research import calc_momentum, calc_volatility, calc_value
    - DuckDB 接続を渡して使用

注意点・運用メモ
- Settings クラス（kabusys.config.Settings）は多くの設定を環境変数から取得します。必須のキー（JQUANTS_REFRESH_TOKEN や KABU_API_PASSWORD）は未設定だと例外になります。
- KABUSYS_ENV の挙動:
  - development: 開発用（デフォルト）
  - paper_trading: Execution は MockBroker を使用し、paper DB（PAPER_TRADING_SQLITE_PATH）へ書き込み。本番 DB と完全に分離されます。
  - live: 本番運用想定
- OpenAI を利用する関数は OPENAI_API_KEY を参照します。未設定の場合、score_news / score_regime 等は ValueError を投げます。
- process priority の設定は psutil を使用します。権限がないと警告を出してスキップします。
- DB 初期化: run_monitoring/run_execution の起動時に init_monitoring_db() が呼ばれ、必要なテーブルと簡易マイグレーションを行います（冪等）。

ディレクトリ構成（主要ファイル）
- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（Settings）
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  — Paper Trading 検証レポート生成
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite 永続化層（init / MonitoringDB）
    - system_monitor.py            — システム状態・データ鮮度監視
    - trade_monitor.py             — 注文滞留・約定異常監視
    - risk_monitor.py              — ドローダウン・ポジション上限監視
    - kill_switch.py               — kill.flag の生成 / 管理
    - monitoring_engine.py         — 各監視のポーリング統合
    - alert_manager.py             — LINE push 通知
    - streamlit_dashboard.py       — 監視ダッシュボード（Streamlit）
  - execution/
    - order_manager.py             — 発注管理（OrderManager）
    - reconciler.py                — 再起動時のリコンシリエーション
    - (その他 broker / engine / repository 実装ファイル)
  - portfolio/
    - portfolio_builder.py         — 候補選定 / 重み計算
    - position_sizing.py           — 株数決定・資金配分ロジック
    - risk_adjustment.py           — セクターキャップ・レジーム乗数
    - __init__.py
  - research/
    - factor_research.py           — Momentum/Volatility/Value 等の計算（DuckDB）
    - feature_exploration.py       — 将来リターン / IC / 統計サマリ
    - __init__.py
  - ai/
    - news_nlp.py                  — ニュースセンチメント取得（OpenAI）
    - regime_detector.py           — 市場レジーム判定（ma200 + LLM）
    - __init__.py
  - data/ (運用で作成されるディレクトリ)
    - monitoring.db (デフォルト SQLITE_PATH)
    - paper_trading.db (paper 用 DB)
    - kabusys.duckdb (デフォルト DUCKDB_PATH)
    - execution.pid
    - kill.flag
    - stop_requested.flag

よくある質問 / トラブルシューティング
- DB が見つからない / 参照できない:
  - run_monitoring/run_execution はデフォルトで data/*.db を使います。環境変数でパスを指定するか、該当ファイルと data/ ディレクトリを事前に作成してください。
- OpenAI でエラーになる:
  - OPENAI_API_KEY を設定してください。news_nlp/regime_detector は API 呼び出しの失敗を一部リトライやフォールバックで扱いますが、キーがない場合は明示的にエラーになります。
- LINE 通知が送れない:
  - LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID の設定を確認してください。未設定の場合は通知はスキップされます（ログに出力）。

拡張 / 開発メモ
- DuckDB を用いた研究モジュールは prices_daily / raw_financials / raw_news 等のテーブルを前提としています。データパイプライン側（kabusys.data.pipeline）を用意してデータを投入してください。
- position_sizing や risk_adjustment は現在純粋関数群です。将来的に銘柄別 lot_size などを取り込む拡張を想定しています。
- テスト可能性を意識して設計（例: OpenAI 呼び出しをラップして差し替えられる形にしてあるため unit test でモック化しやすい）。

以上がこのコードベースの概要と使い方です。必要であれば、環境変数の例 .env テンプレートや systemd / Supervisor 用の起動スクリプトの雛形、あるいは Dockerfile / docker-compose のサンプルも作成します。どちらが必要か指示してください。