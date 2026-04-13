# KabuSys

日本株向け自動売買システムのコアライブラリ群。このリポジトリは取引実行・監視・ポートフォリオ構築・リサーチ・AI（ニュースセンチメント等）などの主要機能を持つモジュール群を提供します。

## 概要
KabuSys は以下の責務を分離して実装したモジュール群です。
- 実行エンジン（ExecutionEngine）とブローカーインターフェース（paper/live 切替）
- 監視（System / Trade / Risk）とアラート（LINE）
- ポートフォリオ構築（候補選定、重み付け、株数決定）
- リサーチ（ファクター計算・将来リターン・IC 等）
- AI 補助（ニュースの NLP による銘柄スコアリング、レジーム判定）
- 検証ツール（Paper Trading レポート生成、Streamlit ダッシュボード）

設計方針の主な点：
- DB は DuckDB（時系列・ファクターテーブル等）と SQLite（監視ログ・注文ログ等）を併用
- Paper Trading（検証）用に本番 DB と分離可能
- 外部 API（OpenAI 等）呼び出しは可搬性とリトライ処理を考慮
- 自動環境変数ロード（.env / .env.local）をサポート（必要なら無効化可能）

## 機能一覧
- 実行
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - paper_trading モードで MockBroker を使用し DB を分離
  - リコンシリエーション（再起動時の注文/ポジション同期）
- 監視
  - SystemMonitor：CPU/メモリ/ディスク/プロセス/PID/データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン / ポジション上限監視
  - KillSwitch：条件に応じてフラグファイルを書いて ExecutionEngine 停止シグナル
  - AlertManager：LINE への一方向プッシュ通知（クールダウン制御）
  - MonitoringEngine：各 Monitor を束ねてポーリング
  - Streamlit ダッシュボード（監視 DB 可視化）
- ポートフォリオ構築
  - 候補選定（スコア順、上位 N）
  - 重み計算（等配分、スコア加重）
  - リスク調整（セクター上限、レジーム乗数）
  - ポジションサイズ計算（リスクベース、等配分、単元株丸め、aggregate cap）
- リサーチ
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン、IC（Spearman）、統計サマリー
- AI（OpenAI）
  - ニュース記事を銘柄ごとに集約してセンチメントをスコアリング（ai_scores テーブルへ）
  - 市場レジーム判定（ETF MA とマクロセンチメントの合成）
  - API 呼び出しはリトライ・バリデーション・部分書込みで堅牢化
- ユーティリティ
  - 環境変数読み込み・設定管理（.env/.env.local 自動ロード）
  - プロセス優先度 / CPU affinity 設定ユーティリティ
  - 監視 DB 永続化実装（テーブル作成・マイグレーション対応）
- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）

## セットアップ手順（開発/実行環境）
前提
- Python 3.9+（実際の要件に合わせて調整してください）
- 任意の OS（Linux / macOS / Windows） — プロセス優先度/affinity はプラットフォーム差分あり

1. リポジトリをクローン
   git clone <repo-url>
   cd <repo-root>

2. 仮想環境作成（推奨）
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate

3. 依存パッケージをインストール
   必要な主なパッケージ（例）:
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit

   pip install duckdb psutil requests openai streamlit

   （開発用に setuptools 等を追加して pip install -e . できるようにするのがおすすめです）

4. 環境変数 / .env の準備
   プロジェクトルートに .env/.env.local を置くと自動で読み込まれます（OS 環境変数が優先）。
   自動ロードを無効化する場合:
   export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - OPENAI_API_KEY (AI 機能を使う場合必須)
   - LINE_CHANNEL_ACCESS_TOKEN (アラート送信に使用)
   - LINE_USER_ID (アラート送信先)
   - KABUSYS_ENV = development | paper_trading | live  (デフォルト: development)
   - PAPER_FILL_MODE = instant | partial | never | reject  (paper_trading 時の挙動)
   - PAPER_TRADING_SQLITE_PATH (paper_trading 用 SQLite、デフォルト data/paper_trading.db)
   - DUCKDB_PATH (デフォルト data/kabusys.duckdb)
   - SQLITE_PATH (監視 DB デフォルト data/monitoring.db)
   - PID_FILE_PATH, KILL_FLAG_PATH, LOG_LEVEL 等

   Settings モジュールは .env のパースで
   - export KEY=val 形式
   - クォートやコメント行の処理
   をサポートします。

5. データディレクトリ作成
   デフォルトでは data/ 配下に DB や PID/FLAG を書き込みます。
   mkdir -p data

## 使い方（主要スクリプト・操作例）
- 監視ループを起動
  MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  python -m kabusys.run_monitoring

  補足:
  - 監視 DB（SQLite）は Settings.sqlite_path を使用（KABUSYS_ENV にかかわらず本番 sqlite_path を使用）
  - 起動直後にプロセス優先度を "high" に設定しようとします（権限がない場合は警告のみ）

- 実行エンジンを起動
  本番/ペーパートレード切替は KABUSYS_ENV で制御。
  KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、データは PAPER_TRADING_SQLITE_PATH に記録されます。
  python -m kabusys.run_execution

- Paper Trading 検証レポートを生成
  python -m kabusys.tools.paper_verification_report
  オプション:
    --from YYYY-MM-DD --to YYYY-MM-DD
    --db PATH（PAPER_TRADING_SQLITE_PATH より優先）
  例:
    python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- Streamlit ダッシュボード起動（監視 DB を可視化）
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- AI 機能（プログラムから利用）
  - ニューススコアリング:
    from kabusys.ai.news_nlp import score_news
    score_news(conn, target_date, api_key="...")

  - レジーム判定:
    from kabusys.ai.regime_detector import score_regime
    score_regime(conn, target_date, api_key="...")

  いずれも DuckDB 接続（kabusys.config.Settings.duckdb_path を経由して開く）を渡して使用します。
  OpenAI API キーは引数または環境変数 OPENAI_API_KEY を使用します。

- ライブラリ的利用（リサーチ / ポートフォリオ）
  - ファクター計算:
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    results = calc_momentum(duckdb_conn, date(2026,4,1))

  - ポートフォリオ構築ユーティリティ:
    from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes

## 環境変数の読み込みルール
- 自動ロード順序（デフォルト）: OS 環境変数 > .env.local > .env
- 自動ロードを無効にする:
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- .env のパースはエクスポート行、クォート、インラインコメント等に対応（Settings モジュール参照）。

## 主要設定の一覧（Settings）
主なプロパティ名と説明:
- jquants_refresh_token — J-Quants API トークン（必須）
- kabu_api_password — kabuステーション API パスワード（必須）
- kabu_api_base_url — kabu API のベース URL（デフォルト http://localhost:18080/kabusapi）
- line_channel_access_token / line_user_id — LINE 通知用
- duckdb_path — DuckDB パス（デフォルト data/kabusys.duckdb）
- sqlite_path — 監視用 SQLite（デフォルト data/monitoring.db）
- paper_sqlite_path — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- paper_fill_mode — Paper Trading の約定挙動（instant|partial|never|reject）
- pid_file_path / kill_flag_path — PID / kill flag パス
- cpu_threshold_pct / memory_threshold_pct / disk_threshold_pct — 監視しきい値
- env — KABUSYS_ENV（development|paper_trading|live）
- log_level — ログレベル（DEBUG, INFO, ...）

Settings クラスは必要な必須値が未設定の場合 ValueError を投げます。

## ディレクトリ構成（抜粋）
src/kabusys/
- __init__.py
- config.py  — 環境変数・設定管理
- run_monitoring.py  — SystemMonitor ポーリングループ起動
- run_execution.py   — ExecutionEngine 起動
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート
- monitoring/
  - __init__.py
  - monitoring_db.py      — SQLite 永続化層（テーブル作成・CRUD）
  - system_monitor.py     — システム / データ鮮度監視
  - trade_monitor.py      — 注文滞留 / 約定異常監視
  - risk_monitor.py       — ドローダウン・ポジション上限監視
  - monitoring_engine.py  — 各 Monitor を束ねる
  - alert_manager.py      — LINE 送信（クールダウン）
  - kill_switch.py        — kill.flag 書込ロジック
  - streamlit_dashboard.py
- execution/
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - ... (ブローカー関連、エンジン等)
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
  - __init__.py
- research/
  - factor_research.py
  - feature_exploration.py
  - __init__.py
- ai/
  - news_nlp.py
  - regime_detector.py
  - __init__.py
- utils/
  - process_priority.py
  - __init__.py
- data/ (runtime に作成される想定)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db

（上記は主要ファイルの抜粋です。実際のリポジトリにはさらに実行ロジックやブローカー実装等が含まれます）

## 注意事項 / 運用メモ
- Paper Trading（KABUSYS_ENV=paper_trading）は本番 DB と完全分離されるように設計されています。必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- Monitoring サービスはデフォルトで本番 sqlite_path を使う設計になっています（環境にかかわらず）。
- KillSwitch はデフォルトでファイルベースのフラグを使用します（data/kill.flag）。Engine 側はこのフラグを見てシャットダウンします。
- OpenAI API を使う機能は API 呼び出しのリトライや部分失敗時の保護（部分書込み）を備えていますが、API キーやコスト管理には注意してください。
- process_priority / cpu_affinity の設定は権限が必要だったり OS に依存します。エラーはログに記録され、処理は継続されます。

## 開発者向けヒント
- Settings は実行時に .env ファイルを自動ロードします。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続は read-only URI（Path.as_uri() + "?mode=ro"）で開くと監視ダッシュボードから安全に参照できます。
- テストの際は外部 API 呼び出し（OpenAI 等）をモックすることを推奨します。モジュール内で _call_openai_api を明示的に分離している箇所が多く、パッチしやすくなっています。

---

この README はコードベースの主要な使い方と構成をまとめたものです。より詳細な仕様（StrategyModel.md、PortfolioConstruction.md 等）が別途ある想定です。具体的な運用やデプロイ手順は実環境に合わせて追記してください。