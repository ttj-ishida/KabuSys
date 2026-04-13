# KabuSys

日本株自動売買システムのサブセット実装ドキュメント（README）。  
このドキュメントはソースツリーに含まれる主要モジュールと実行方法、設定項目、ディレクトリ構成を日本語でまとめたものです。

注意: 本リポジトリは実運用を想定した構成を含みます。実際にブローカー API や決済を行うコードを実行する前に、環境変数やテスト用 DB を適切に分離・確認してください。

---

目次
- プロジェクト概要
- 主な機能一覧
- 必要要件
- セットアップ手順
- 環境変数と設定（Settings）
- 使い方（起動コマンド / ツール）
- ディレクトリ構成と主なファイル
- 開発者向けメモ / 注意点

---

プロジェクト概要
- KabuSys は日本株向けの自動売買システム（モジュール群）で、シグナル → ポートフォリオ構築 → 発注（ExecutionEngine） → 監視（Monitoring） → レポートまでのワークフローを含む構成になっています。
- DuckDB を用いたリサーチ / ファクター計算、SQLite による監視ログ・注文履歴の永続化、LINE による通知、OpenAI を用いたニュース NLP / レジーム判定などの機能を提供します。
- コードは「実行用エントリポイント」「純粋関数ライブラリ」「永続化層」「監視コンポーネント」「AI 周り」「ポートフォリオ構築」「リサーチ」など複数の関心事に分かれています。

---

主な機能一覧
- ExecutionEngine 起動（run_execution.py）
  - 本番 / PaperTrading 切り替え（KABUSYS_ENV）
  - ブローカークライアント生成（BrokerClientFactory）
  - OrderManager / RiskManager / Reconciler を組み合わせたセッション実行
- MonitoringEngine 起動（run_monitoring.py）
  - SystemMonitor / TradeMonitor / RiskMonitor を定期ポーリング
  - kill.flag による ExecutionEngine 停止シグナル生成
  - DB（SQLite）へ監視ログ永続化
- 監視ダッシュボード（Streamlit）
  - src/kabusys/monitoring/streamlit_dashboard.py で実行可能（read-only DB 表示）
- Paper Trading 検証レポート生成ツール
  - src/kabusys/tools/paper_verification_report.py：過去期間の稼働率・成功率・レイテンシ等を出力
- 研究・ファクター計算モジュール
  - kabusys.research: momentum / volatility / value などのファクター計算
  - feature exploration（forward returns, IC, summary）
- ポートフォリオ構築ライブラリ
  - 候補選定、重み計算（等分 / スコア加重）、ポジションサイズ決定、セクター制約、レジーム乗数
- AI モジュール
  - kabusys.ai.news_nlp: raw_news を OpenAI に送って銘柄ごとのセンチメントを ai_scores に書き込む
  - kabusys.ai.regime_detector: ma200 とマクロニュースの LLM 評価を組み合わせて市場レジーム判定
- ユーティリティ
  - process_priority（プロセス優先度 / CPU affinity 設定）
  - 環境変数自動読み込み (.env / .env.local) と Settings 抽象化

---

必要要件（主な Python パッケージ）
- Python 3.9+（型ヒントや構文を前提）
- duckdb
- psutil
- requests
- streamlit (ダッシュボード用)
- openai (AI モジュール用)
- sqlite3（標準ライブラリ）
- その他標準ライブラリ（logging, datetime, argparse, math 等）

（実際の requirements.txt はリポジトリに合わせて用意してください）

---

セットアップ手順（ローカル実行向け）
1. 仮想環境作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 依存パッケージインストール（例）
   - pip install duckdb psutil requests streamlit openai

3. プロジェクトルートに .env を作成（任意）
   - リポジトリ検出ロジックは .git または pyproject.toml を基準に自動で .env / .env.local を読み込みます。
   - 自動読み込みを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

4. 必須環境変数（例）
   - JQUANTS_REFRESH_TOKEN — J-Quants API 用（必須）
   - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
   - OPENAI_API_KEY — OpenAI を使う機能を利用する場合（必要に応じて）
   - KABUSYS_ENV — 環境（development | paper_trading | live）。未指定は development。
   - その他（任意・デフォルトあり）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE（paper_trading の約定挙動: instant|partial|never|reject、デフォルト: instant）
     - PID_FILE_PATH（pid ファイルパス、デフォルト: data/execution.pid）
     - KILL_FLAG_PATH（kill.flag のパス、デフォルト: data/kill.flag）
     - MONITOR_POLL_INTERVAL（監視ループのインターバル秒、デフォルト: 60）

5. データディレクトリ作成
   - mkdir -p data

6. DB 初期化
   - 各起動スクリプト run_monitoring.py / run_execution.py 内で init_monitoring_db が呼ばれるため、通常は初期化を手動で行う必要はありません。

---

設定（Settings）についての補足
- Settings クラス（kabusys.config）で主要設定を抽象化。プロパティとして各種設定値にアクセスできます（例: settings.env, settings.sqlite_path）。
- .env のパースはシェル風（export KEY=val など）をある程度サポート。クォートやインラインコメントの扱いにも配慮した実装です。
- 認証トークン等の必須値は _require() により未設定時に ValueError を投げます（.env.example を参照して設定してください）。

---

使い方（実行例）
- 監視ループ（MonitoringEngine）を単独で起動する
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能。デフォルト 60 秒。
  - run_monitoring は Monitoring 用に本番 sqlite_path を常に使用します（環境にかかわらず）。

- 実行エンジン（ExecutionEngine）を起動する
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され paper_trading 専用 DB（data/paper_trading.db）に記録され、本番 DB と分離されます。

- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only モードで監視 DB を可視化します。MonitoringEngine が書き込む data/monitoring.db を指定してください。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - オプションで期間指定:
    - --from 2026-04-01 --to 2026-04-11
    - --db /path/to/paper_trading.db で DB パスを明示可能
  - レポートは稼働率、注文成功率、送信率、レイテンシ（P95）等を算出し PASS/FAIL を表示します。

- AI 機能（プログラム的呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続を受け取り ai_scores / market_regime などのテーブルへ書き込みます。OPENAI_API_KEY を設定してください。

---

よく使う環境変数一覧（主なもの）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: J-Quants トークン（必須）
- KABU_API_PASSWORD: kabuAPI パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite パス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: instant|partial|never|reject（paper_trading 用）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: 監視ループの秒（デフォルト 60）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 1 をセットすると .env 自動ロードを無効化

---

ディレクトリ構成（主要ファイルの説明）
- src/kabusys/
  - __init__.py — パッケージ初期化（バージョン等）
  - config.py — 環境変数と Settings 管理（.env 自動ロード、検証）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト（paper_trading 切替対応）
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity のユーティリティ
  - monitoring/
    - monitoring_db.py — SQLite を使った監視ログ永続化層（テーブル初期化・CRUD）
    - system_monitor.py — システム状態・データ鮮度チェック
    - trade_monitor.py — 注文滞留・約定異常価格チェック
    - risk_monitor.py — ドローダウン・ポジション上限の監視
    - kill_switch.py — kill.flag の生成 / 削除ロジック
    - alert_manager.py — LINE Push による一方向通知（クールダウン対応）
    - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, order_repository.py 等 — 発注・リコン関連（部分抜粋）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 発注株数・調整ロジック
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — momentum / volatility / value 等のファクター計算（DuckDB ベース）
    - feature_exploration.py — forward returns, IC, 統計サマリー
  - ai/
    - news_nlp.py — raw_news を LLM で集約評価して ai_scores に書き込む
    - regime_detector.py — ma200 と LLM マクロ評価で市場レジーム判定
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI

---

開発者向けメモ / 注意点
- DB の扱い
  - monitoring（監視）は monitoring_db.init_monitoring_db によるテーブル初期化を行います。起動スクリプトで自動的に呼ばれます。
  - paper_trading モードでは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）を使用して本番データと完全に分離します。
- プロセス制御
  - 起動時に set_process_priority("high") が呼ばれます。権限不足等で失敗した場合は警告ログを出してスキップします。
- kill.flag / pid ファイル
  - KillSwitch はファイル存在で停止シグナルを送ります。ExecutionEngine 側はこれを監視して停止処理を行う想定です。
- AI 呼び出し
  - OpenAI 呼び出しはネットワークエラー・429・5xx などに対して指数バックオフでリトライロジックを組んでいます。API キーは環境変数か関数引数で渡してください。
  - レスポンスのバリデーションに厳格な実装があり、部分失敗時に DB を壊さないよう DELETE → INSERT を小分けで行います。
- テスト・フェイルセーフ
  - 多くの箇所で「失敗時はログを出して処理を継続する」設計がなされています（監視や AI 評価など）。ただし発注系は慎重に扱ってください。
- .env の自動読み込みはプロジェクトルートを .git または pyproject.toml を基準に探索します。CI/テストで固有の環境を使う場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定し、必要な環境変数を明示的に渡すことを推奨します。

---

参考コマンドまとめ
- 監視起動:
  - KABUSYS_ENV=development python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

この README はリポジトリ内のソースコードに基づいて作成しています。実際の運用やデプロイの際は、機密情報の管理（API キー / パスワード）、ログ・監査、バックアップ、権限（プロセス優先度設定の権限）等に十分注意してください。必要であれば、requirements.txt・.env.example・運用手順書を別途用意してください。