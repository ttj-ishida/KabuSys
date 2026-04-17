# KabuSys

日本株向け自動売買システムのリファレンス実装（ライブラリ + 起動スクリプト群）。  
このリポジトリは取引実行エンジン、監視（モニタリング）、ポートフォリオ構築／サイズ決定ロジック、研究用ファクター計算、LLM を用いたニュースセンチメント／レジーム判定などのモジュールで構成されています。

概要・目的
- 証券ブローカー API と連携して自動で発注を行う ExecutionEngine（本番 / Paper Trading 切替対応）
- 実行状況やシステム状態を定期的に記録・監視し、閾値超過時にアラートや Kill Switch を発動
- ポートフォリオ構築・配分・ポジションサイズ計算の純粋関数実装（テスト容易）
- DuckDB を使った研究向けファクター計算・特徴量解析モジュール
- OpenAI（gpt-4o-mini）を利用したニュース NLP（センチメント）とマクロレジーム判定
- 開発／検証用ツール（Paper Trading 検証レポート、Streamlit ダッシュボード等）

主な機能一覧
- Execution
  - ExecutionEngine の起動スクリプト（run_execution.py）
  - Broker クライアント抽象化（実ブローカー / MockBroker の切替）
  - OrderManager / OrderRepository / Reconciler による状態管理と起動時復旧
  - Paper Trading モード：実 DB と完全分離した data/paper_trading.db を使用
- Monitoring
  - SystemMonitor：CPU / メモリ / ディスク / プロセス健全性 / データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch：閾値到達時に data/kill.flag を書き込みエンジン停止を促す
  - AlertManager：LINE Messaging API によるプッシュ通知（クールダウン付き）
  - Streamlit ダッシュボード（read-only で monitoring DB を可視化）
- Portfolio
  - 銘柄候補選定、等分／スコア加重配分、セクター制約、レジーム乗数
  - ポジションサイズ計算（単元株対応、aggregate cap）
- Research
  - ファクター計算（Momentum, Volatility, Value）
  - 将来リターン計算、IC（Spearman）計算、ファクター統計要約
- AI
  - news_nlp: raw_news を集約して LLM に投げ、銘柄別センチメントを ai_scores に記録
  - regime_detector: ETF（1321）の MA200 とマクロ記事の LLM センチメントを合成して日次レジーム判定
- Tools
  - paper_verification_report: Paper Trading DB を解析して Pass/Fail 判定付き検証レポートを生成

セットアップ手順（ローカル開発）
前提
- Python 3.10+
- SQLite（標準ライブラリ）
- 推奨: 仮想環境（venv/virtualenv）

例:
1. リポジトリをクローン / ディレクトリへ移動
   - git clone ...
   - cd <repo_root>

2. 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb psutil requests openai streamlit
   - （requirements.txt があれば: pip install -r requirements.txt）

環境変数（主なもの）
- KABUSYS_ENV: 実行環境。development | paper_trading | live（デフォルト: development）
  - paper_trading の場合、run_execution は専用の paper_sqlite_path を使い MockBrokerClient が使われる（本番 DB と分離）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須プロパティから参照される）
- KABU_API_PASSWORD / KABU_API_BASE_URL: kabuステーション API
- OPENAI_API_KEY: OpenAI API を使う処理（news_nlp / regime_detector）で必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager が LINE へ通知するために使用
- SQLITE_PATH: 監視用 SQLite のパス（デフォルト: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: Paper Trading の約定モード（instant|partial|never|reject、デフォルト instant）
- PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START など（Settings 参照）

.env 自動読み込み
- リポジトリルートに .env / .env.local があれば Settings モジュールが自動で読み込みます（OS 環境変数を上書きしない保護付き）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env.example を参考に .env を作成してください（リポジトリに例ファイルがあれば利用）。

使い方（起動例）
- 監視ループ（Monitoring）
  - デフォルトのポーリング間隔 60 秒。環境変数で MONITOR_POLL_INTERVAL を上書き可。
  - 起動:
    - python -m kabusys.run_monitoring
  - 停止:
    - プロジェクトルートの data/stop_requested.flag を作成すると監視ループが検知して終了します。

- 実行エンジン（Execution）
  - 本番 or paper_trading に応じて DB と Broker クライアントが切り替わる
  - 起動:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - または KABUSYS_ENV=live python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると実行エンジンのスレッドが停止処理を行います。
  - 実行時に data/execution.pid ファイルへ PID を書き、pid を監視して stale PID を検出する仕組みがあります。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - フィルタ期間:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは環境変数 PAPER_TRADING_SQLITE_PATH または --db オプションで指定可能。

- Streamlit ダッシュボード（監視用）
  - 起動:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視 DB を読み取り専用で表示します（データがない場合は起動前に MonitoringEngine を実行してください）。

運用ノート / 実装上の重要点
- 監視（Monitoring）は KABUSYS_ENV にかかわらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。監視データは本番 DB と分離しない設計です（ただし paper_trading の Execution は専用 DB を使用）。
- run_execution は起動時に stop flag が既に立っていれば起動しない安全仕様。
- Process 優先度の設定（set_process_priority）や CPU affinity の補助関数を備え、実行開始時に優先度を high に設定します。権限不足時は警告を出してスキップします。
- LLM 絡み（news_nlp, regime_detector）は OpenAI API の失敗に耐える設計で、失敗時はフェイルセーフ（0.0 等）で継続するようになっています。ただし API キーは必須設定で未設定時は例外を投げる箇所があります。
- monitoring_db.init_monitoring_db はマイグレーション（列追加）を簡単に行う処理を含みます（冪等）。
- Paper Trading では fill モード（PAPER_FILL_MODE）に従って MockBroker の動作を変更できます。

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — 環境変数 / 設定管理（.env 自動読み込みロジック含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - execution/
    - execution_engine.py — 実行エンジン本体（起動・セッション管理）
    - broker_factory.py, broker_api.py — ブローカークライアント関連
    - order_manager.py — OrderStateMachine の外向け API
    - order_repository.py — SQLite ベースの注文永続化
    - reconciler.py — 起動時の自動復旧（リコンシリエーション）
    - その他 order_record 等
  - monitoring/
    - monitoring_db.py — 監視用 SQLite の読み書きレイヤ
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 制御（Execution 停止）
    - alert_manager.py — LINE 通知
    - monitoring_engine.py — 各 Monitor を束ねるエンジン
    - streamlit_dashboard.py — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数算出（単元・リスク等）
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — Momentum/Volatility/Value 等のファクター計算（DuckDB）
    - feature_exploration.py — 将来リターン / IC / 統計サマリ
  - ai/
    - news_nlp.py — ニュースの LLM センチメント集計・ai_scores 書込
    - regime_detector.py — マクロ + MA200 を合成したレジーム判定
  - data/  (実行時に使用されるファイル群)
    - monitoring.db (SQLITE_PATH のデフォルト)
    - kabusys.duckdb (DUCKDB_PATH のデフォルト)
    - paper_trading.db (Paper Trading 用 DB)
    - kill.flag / stop_requested.flag / execution.pid などのフラグや PID ファイル
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

開発・貢献
- 各モジュールは極力副作用を持たない「純粋関数」として設計している箇所（portfolio, research）と、DB を直接扱う永続層（monitoring_db, order_repository）に分離しています。ユニットテストは pure な箇所から着手すると容易です。
- LLM 呼び出しや外部 API 呼び出しはラッパー関数を通しているため、テスト時は patch / mock しやすい設計です（README に含めた関数名でパッチ可能）。

トラブルシュート（よくある項目）
- 「DB ファイルが見つかりません」: monitoring 用 DB が存在しない場合、monitoring の起動や Streamlit はエラーを出します。init_monitoring_db を呼ぶか、run_monitoring を先に実行してください（run_execution でも起動時に init_monitoring_db が呼ばれます）。
- OpenAI API 関連の例外: OPENAI_API_KEY が正しく設定されているか確認してください。API エラーはログに出力されますが、多くの処理はフェイルセーフで継続します。
- 権限エラーでプロセス優先度が変更できない: 実行ユーザーの権限や OS のポリシーを確認してください。権限不足時は警告が出ますが処理は継続されます。

ライセンス・その他
- 本リポジトリのライセンスや著作権についてはルートの LICENSE ファイルをご確認ください（存在する場合）。

以上が README のサマリです。必要であれば、README に含めるサンプル .env.example、requirements.txt、または起動スクリプトの詳しい動作フロー（シーケンス図）を追加で作成します。どの情報を優先して補足しますか？