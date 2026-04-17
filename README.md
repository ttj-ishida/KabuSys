# KabuSys

KabuSys は日本株自動売買システムのコアライブラリ群です。モニタリング、注文実行、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント／レジーム判定）など、運用に必要なコンポーネントを含みます。

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（起動例）
- 環境変数（主なキー）
- フラグ／PID ファイルについて
- ディレクトリ構成

---

プロジェクト概要
- 日本株向けの自動売買システム向けユーティリティ群（監視、実行エンジンの起動補助、ポートフォリオ構築ロジック、ファクター計算、ニュース NLP 等）。
- 主要言語: Python（型ヒントにより Python 3.10+ を想定）。
- DB: SQLite（監視・注文ログ等）および DuckDB（時系列価格／リサーチ用集計）。

---

主な機能
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番／ペーパー取引を切り替え可能。KABUSYS_ENV=paper_trading 時は MockBroker を使い data/paper_trading.db に分離して記録。
  - 実行中は PID ファイルを扱い、外部フラグで停止可能。
- Monitoring（run_monitoring.py / MonitoringEngine 等）
  - CPU / メモリ / ディスク / プロセス稼働状態、注文滞留・約定異常、ドローダウン・ポジション上限等を定期監視。
  - 監視ログを SQLite に永続化（init_monitoring_db）。
  - LINE 連携によるプッシュ通知（AlertManager）。
  - kill switch（条件に応じて停止フラグを出す仕組み）。
  - Streamlit ベースの監視ダッシュボード（streamlit_dashboard.py）。
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、重み付け（等金額・スコア重み）、セクター制限、ポジションサイズ算出（単元丸め・利用可能現金でのスケーリング等）。
- リサーチ（research）
  - ファクター計算（モメンタム・ボラティリティ・バリュー）、将来リターン、IC 計算、統計サマリー等（DuckDB 経由で prices_daily/raw_financials を参照）。
- AI（ai）
  - news_nlp: raw_news を LLM（OpenAI）に投げて銘柄ごとにセンチメントスコアを ai_scores に書き込み。
  - regime_detector: ETF（1321）MA200 とマクロ記事の LLM スコアを合算して市場レジーム（bull/neutral/bear）判定し保存。
- ツール
  - paper_verification_report: Paper Trading DB の指標（稼働率、注文成功率、レイテンシ等）を集計してレポート出力。

---

セットアップ手順（開発 / 実行環境）
1. Python のインストール
   - Python 3.10 以上を推奨。

2. 依存パッケージのインストール
   - 代表的な依存:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   ※ プロジェクトに requirements.txt があればそれを使用してください。

3. プロジェクトルート
   - この README が置かれたリポジトリをプロジェクトルートとして扱います。
   - .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（OS 環境変数が優先）。自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

4. データディレクトリ
   - data ディレクトリを作成（自動作成される場合もありますが権限等の理由で事前作成を推奨）。
   - デフォルト DB パス:
     - DuckDB: data/kabusys.duckdb
     - Monitoring SQLite: data/monitoring.db
     - Paper Trading SQLite: data/paper_trading.db

5. 初期 DB 作成
   - run_monitoring.py / run_execution.py 起動時に init_monitoring_db が自動で呼ばれ、監視テーブルを作成します。手動操作は不要です。

---

使い方（コマンド例）
- モニタリングループ起動（本番 monitoring DB を使用）
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能。デフォルト: 60。
  - 実行:
    - KABUSYS_ENV=development python -m kabusys.run_monitoring
  - 実行中は data/stop_requested.flag が存在するとループが終了します。

- ExecutionEngine 起動（本番/ペーパー）
  - Paper Trading 実行（MockBroker、DB を分離）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - Live 実行:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 起動時に data/execution.pid（デフォルト）に PID を扱います。外部から停止させるには stop フラグ（data/stop_requested.flag）を作成します。

- Streamlit ダッシュボード（監視結果の可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db で指定、未指定なら環境変数 PAPER_TRADING_SQLITE_PATH / data/paper_trading.db が用いられます。

- AI 関連（ニューススコア／レジーム判定）
  - OpenAI API キー（OPENAI_API_KEY）を設定する必要があります。
  - 直接モジュール呼び出し:
    - from kabusys.ai.news_nlp import score_news
    - from kabusys.ai.regime_detector import score_regime

---

主な環境変数（抜粋）
- 必須（使用する機能により必須）
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン
  - KABU_API_PASSWORD — kabuステーション API パスワード
- OpenAI
  - OPENAI_API_KEY — OpenAI API キー（ai モジュールで必須）
- 実行環境フラグ
  - KABUSYS_ENV — "development" | "paper_trading" | "live"（デフォルト: development）
- DB / ファイルパス
  - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視用、デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH（ペーパー取引用、デフォルト: data/paper_trading.db）
  - PID_FILE_PATH（Execution PID ファイル、デフォルト: data/execution.pid）
  - KILL_FLAG_PATH（kill switch 用フラグ、デフォルト: data/kill.flag）
- Paper Trading
  - PAPER_FILL_MODE — "instant" | "partial" | "never" | "reject"（デフォルト: "instant"）
- ログ/挙動
  - LOG_LEVEL — "DEBUG" | "INFO" | "WARNING" | "ERROR" | "CRITICAL"（デフォルト: INFO）
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト: 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 1 にすると .env 自動読み込みを無効化

（README に記載の変数は利用シーンに応じて適宜設定してください。Settings クラスで詳しいデフォルト・検証を行っています。）

---

フラグ / PID ファイル
- data/execution.pid — 実行エンジンの PID 管理
- data/stop_requested.flag — run_monitoring / run_execution が参照する停止要求フラグ（存在するとループを中断）
- data/kill.flag — KillSwitch が書き込む停止理由（Alert 送信や人による確認用）
- Settings.kill_flag_clear_on_start が 1 の場合、起動時に kill flag を自動クリアできます。

（注意）フラグファイルの具体的な運用ルールは環境に合わせて統一してください。

---

注意事項 / 運用ヒント
- Monitoring はコード上で「環境にかかわらず本番 sqlite_path を使用する」と明記されています。開発環境で誤って本番 DB を上書きしないよう .env 設定に注意してください。
- Paper Trading モードでは ExecutionEngine が paper_sqlite_path（デフォルト data/paper_trading.db）を使用し、本番 DB と分離します。ペーパー検証時はこの DB を参照してください。
- OpenAI（LLM）を利用する処理は API 呼び出し失敗時にフォールバックやリトライロジックが組まれていますが、API 利用量には留意してください。
- DuckDB のクエリは prices_daily / raw_financials / raw_news 等のテーブルに依存します。これらのデータ投入・更新パイプラインは別途用意する必要があります。

---

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings 管理（.env 自動ロード機能含む）
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト
  - ai/
    - news_nlp.py — ニュースセンチメント取得（OpenAI）
    - regime_detector.py — 市場レジーム判定（MA + LLM）
  - monitoring/
    - monitoring_db.py — SQLite テーブル定義・永続化 API
    - system_monitor.py — CPU/メモリ/データ鮮度 / PID チェック
    - trade_monitor.py — 注文滞留 / 約定異常検出
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - alert_manager.py — LINE Push 通知
    - kill_switch.py — 停止フラグ管理
    - monitoring_engine.py — 各モニタの統合実行ループ
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - execution/
    - order_manager.py, reconciler.py, ...（注文管理 / 同期ロジック）
  - portfolio/
    - portfolio_builder.py — 候補選定 / 重み計算
    - position_sizing.py — 株数計算・単元処理・利用可能現金でのスケーリング
    - risk_adjustment.py — セクターキャップ / レジーム乗数
  - research/
    - factor_research.py — ファクター計算（momentum, volatility, value）
    - feature_exploration.py — 将来リターン / IC / 統計サマリー
  - tools/
    - paper_verification_report.py — Paper Trading 向け検証レポート生成
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

---

最後に
- ここに記載したコマンド例・デフォルト値はソースコードに基づく抜粋です。運用前に .env の確認・バックアップ・テスト環境での動作確認を行ってください。
- 追加の README や運用手順（デプロイ、サービス化、監視アラート運用ルール等）は運用ポリシーに合わせて別途作成することを推奨します。

必要であれば、.env のサンプルや systemd unit / docker-compose のテンプレート、運用チェックリストの雛形も作成します。希望があれば教えてください。