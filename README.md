KabuSys — 日本株自動売買システム README
================

概要
----
KabuSys は日本株向けの自動売買および関連処理（ファクター計算、リサーチ、監視、Paper Trading 検証、AI ベースのニュースセンチメント/レジーム判定など）を行うための小規模フレームワークです。  
本リポジトリは、発注ロジック（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築・サイズ計算、ファクター計算、AI を用いたニュース解析などのモジュール群で構成されています。

主な特徴（機能一覧）
-----------------
- 発注管理（OrderManager / ExecutionEngine）:
  - ブローカー抽象化（本番 / paper_trading の切替）
  - 再起動時のリコンシリエーション（Reconciler）
  - リスク管理（RiskManager）
- 監視（Monitoring）:
  - SystemMonitor, TradeMonitor, RiskMonitor を組み合わせた MonitoringEngine
  - SQLite に監視ログを永続化（monitoring_db）
  - kill.flag による安全停止シグナル
  - LINE を用いたアラート通知（AlertManager）
  - Streamlit ダッシュボードによる可視化（streamlit_dashboard.py）
- ポートフォリオ構築（portfolio）:
  - 候補選定 / 等重・スコア重み算出 / ポジションサイズ計算
  - セクターキャップ・レジーム乗数の適用
- リサーチ（research）:
  - Momentum / Volatility / Value ファクター計算（DuckDB 使用）
  - 将来リターン計算・IC（Information Coefficient）・統計サマリ
- AI（ai）:
  - ニュースセンチメント（news_nlp）とマーケットレジーム判定（regime_detector）
  - OpenAI（gpt-4o-mini 等）との安全なバッチ呼び出しとリトライ処理
- ツール:
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）

前提（必須 / 推奨）
-----------------
- Python 3.9+（コードの型ヒント等に合わせてください）
- 必要パッケージ（代表例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit（ダッシュボード使用時）
- SQLite（標準ライブラリで利用）
- ネットワークアクセス（LINE API / OpenAI を使う場合）

セットアップ手順
----------------
1. リポジトリをクローン・チェックアウト:
   - git clone ... （通常の手順）

2. 仮想環境の作成と依存インストール（例）:
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）
   - pip install --upgrade pip
   - pip install duckdb psutil requests openai streamlit

   （プロジェクトに requirements.txt があれば pip install -r requirements.txt を実行）

3. データディレクトリ作成:
   - mkdir -p data

4. 環境変数の設定:
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（ただし KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すれば無効化可）。
   - 代表的な環境変数（サンプル）:
     - KABUSYS_ENV=development | paper_trading | live
       - paper_trading: MockBroker を使い data/paper_trading.db に記録
     - JQUANTS_REFRESH_TOKEN=...
     - KABU_API_PASSWORD=...
     - OPENAI_API_KEY=...  （AI 機能を使う場合）
     - LINE_CHANNEL_ACCESS_TOKEN=...  （アラート送信）
     - LINE_USER_ID=...  （アラート送信先）
     - DUCKDB_PATH=data/kabusys.duckdb  （DuckDB データベース）
     - SQLITE_PATH=data/monitoring.db   （監視ログ用 SQLite。production 用）
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db  （paper_trading 用 DB）
     - PAPER_FILL_MODE=instant | partial | never | reject  （paper_trading の約定モデル）
     - PID_FILE_PATH=data/execution.pid
     - KILL_FLAG_PATH=data/kill.flag
     - MONITOR_POLL_INTERVAL=60  （run_monitoring のポーリング間隔秒）
     - LOG_LEVEL=INFO | DEBUG | ...
   - 例 .env（最低限）:
     - KABUSYS_ENV=paper_trading
     - OPENAI_API_KEY=sk-...
     - KABU_API_PASSWORD=your_password

5. DB 初期化:
   - 実行スクリプト（run_execution/run_monitoring）が起動時に init_monitoring_db を呼ぶため、通常は手動での初期化は不要です。
   - 必要であれば Python REPL で init_monitoring_db を呼び出してテーブルを作成できます。

使い方（主要スクリプト）
-----------------------

- ExecutionEngine（取引エンジン）起動:
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV によって paper_trading は data/paper_trading.db を使用（本番 DB と分離）
    - プロセス優先度を high に設定し、各コンポーネント（broker, repo, risk manager, reconciler）を組み立ててセッションを実行します

- MonitoringEngine（監視ループ）起動:
  - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）
  - 挙動:
    - SystemMonitor / TradeMonitor / RiskMonitor を周期的に実行して監視ログを SQLite に保存
    - kill.flag の書き込みによる ExecutionEngine 停止シグナルや LINE 通知等を実行可能

- Streamlit ダッシュボード（監視 UI）:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで monitoring.db を開き、Overview / Positions / Orders / System タブを表示します

- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD --to YYYY-MM-DD
    - --db PATH で PAPER_TRADING_SQLITE_PATH を上書き可
  - 出力: 標準出力へ稼働率、注文成功率、レイテンシなどの集計と PASS/FAIL 判定を表示

- AI 機能（ライブラリ呼び出し）:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - いずれも OpenAI API キーを渡すか環境変数 OPENAI_API_KEY をセットする必要があります
  - 失敗時はフェイルセーフ挙動（部分的にゼロフォールバック等）が組み込まれています

注意事項 / 動作ポリシー
---------------------
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml の存在するディレクトリ）を探索し、.env と .env.local を読み込みます。OS 環境変数は保護されます。
  - 自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- KABUSYS_ENV の意味:
  - development / paper_trading / live のいずれか。paper_trading は発注をモックし DB を分離します。live は本番運用。
- OpenAI / LINE など外部 API を使う機能は API キーやトークンの設定が必要です。キー未設定時はエラーを返すか、安全にスキップする実装があります（モジュールによる）。
- process priority / affinity:
  - 実行時に set_process_priority("high") を呼びます（psutil を利用）。権限不足などで設定できない場合は警告を出してスキップします。

主要ディレクトリ構成（概要）
----------------------------
src/kabusys/
- __init__.py
  - パッケージ定義（__version__ 等）
- config.py
  - .env 自動読み込み、Settings クラス（環境変数取得・検証）
- run_execution.py
  - ExecutionEngine を起動するエントリポイント
- run_monitoring.py
  - SystemMonitor ポーリングループの起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースの LLM によるセンチメント解析、ai_scores への書き込み
  - regime_detector.py — マクロ + MA200 による市場レジーム判定
- monitoring/
  - monitoring_db.py — SQLite の監視テーブル作成／読み書きラッパー
  - system_monitor.py, trade_monitor.py, risk_monitor.py — 個別監視コンポーネント
  - monitoring_engine.py — 各 Monitor を束ねて実行
  - kill_switch.py — kill.flag の作成／評価
  - alert_manager.py — LINE へのプッシュ通知
  - streamlit_dashboard.py — ダッシュボード（Streamlit）
- execution/
  - order_manager.py, reconciler.py, ... — 発注・再同期関連ロジック（Broker 抽象化と連携）
  - broker_factory / broker_api など（ブローカー実装は environment に依存）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 発注株数計算・スケーリング
  - risk_adjustment.py — セクターキャップ・レジーム乗数
- research/
  - factor_research.py — Momentum/Volatility/Value の計算（DuckDB を使用）
  - feature_exploration.py — 将来リターン・IC・統計量
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
- utils/
  - process_priority.py — psutil を用いた優先度・CPU affinity 設定ユーティリティ

付記 / トラブルシューティング
-----------------------------
- SQLite / DuckDB のパスは Settings で設定可能（環境変数 DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）。デフォルトは data/ 配下。
- ストリームリットで DB を読み取る際は read-only モードで URI を作成しています（streamlit_dashboard.py）。
- OpenAI 呼び出し部分は JSON パースや API エラー時に冗長なログを残しつつ安全にフォールバックする設計です。テスト時は内部の API 呼び出しをモックできます（モジュール内で意図的に分離している箇所があります）。
- MONITOR_POLL_INTERVAL が 0 以下や不正な値の場合はデフォルト（60秒）にフォールバックします。

開発者向けメモ
---------------
- 設定は Settings クラスを通してアクセスしてください（kabusys.config.Settings）。
- DuckDB を直接渡してファクター計算関数を呼ぶことで、外部 API に依存せず高速にリサーチ処理を行えます。
- テストしやすくするため、AI の API 呼び出しや time.sleep 等は patch しやすい設計になっています。

ライセンス / その他
-------------------
- 本 README に記載の内容はコードベースから生成したドキュメントです。実環境で利用する際は各種 API の利用規約、セキュリティ、資金リスクに十分注意してください。

以上。README の改善要望（追加で欲しい使い方の例、より詳細な環境変数一覧、運用手順など）があれば教えてください。