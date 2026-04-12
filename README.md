# KabuSys

バージョン: 0.1.0

KabuSys は日本株自動売買のための小規模なトレーディングフレームワークです。本リポジトリはシグナル→ポートフォリオ構築→発注（ExecutionEngine）と、稼働監視・アラート（Monitoring）・研究用モジュール（factor/research）・AI（ニュースセンチメント/レジーム判定）等を含みます。DB に DuckDB / SQLite を利用し、外部 API（kabuステーション、J-Quants、OpenAI 等）と連携する設計です。

主な特徴
- ExecutionEngine: ブローカークライアント経由での発注フロー、リスク管理、リコンシリエーション
- Monitoring: システム状態・データ鮮度・注文滞留・リスクを定期チェックして DB 保存・LINE 通知・kill フラグ発行
- Portfolio モジュール: 候補選定、重み算出、ポジションサイズ計算（等金額・スコア加重・リスクベース）
- Research モジュール: ファクター計算（Momentum/Value/Volatility 等）、IC計算、将来リターン計算
- AI モジュール: ニュースの LLM（OpenAI）によるセンチメントスコアリング、マクロニュースを使った市場レジーム判定
- Tools: Paper Trading 検証レポート生成や Streamlit ダッシュボード等のユーティリティ

サポート環境（目安）
- Python 3.10+
  - 本コードは PEP 604 の型記法（X | Y）などを使用しているため Python 3.10 以上を想定します。
- 主な依存パッケージ:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
（プロジェクトに requirements.txt / pyproject.toml がある場合はそれを使用してください）

───

機能一覧
- execution/
  - 注文作成→送信→状態同期の OrderManager、order_repository、reconciler（起動時自動復旧）
  - リスク管理（RiskManager）・注文ログの永続化
- monitoring/
  - SystemMonitor: CPU/MEM/Disk、プロセス生存確認、株価データ鮮度チェック
  - TradeMonitor: 滞留注文、約定価格異常の検出
  - RiskMonitor: ドローダウン・ポジション上限の監視と kill.flag 発行
  - AlertManager: LINE Push による通知（クールダウン付き）
  - MonitoringDB: SQLite を使った監視ログ永続化（テーブル作成・マイグレーション含む）
  - Streamlit ダッシュボード（監視データ閲覧用）
- portfolio/
  - 候補選定 / 重み計算 / セクター制限 / ポジションサイズ決定（ロット丸め、スケールダウン処理）
- research/
  - ファクター計算（momentum, volatility, value）
  - 将来リターン、IC、統計サマリ
- ai/
  - news_nlp: raw_news を集約して OpenAI に投げ、銘柄別センチメントを ai_scores に保存
  - regime_detector: ETF MA + マクロセンチメントの合成による日次レジーム判定
- tools/
  - paper_verification_report: Paper Trading DB のパフォーマンス（稼働率 / 成立率 / レイテンシ等）を集計してレポート出力

───

セットアップ手順（開発 / 実行前準備）
1. リポジトリをクローン
   - 例: git clone <repo-url>

2. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存パッケージのインストール
   - pip install duckdb psutil requests openai streamlit
   - （ある場合は）pip install -r requirements.txt

4. data ディレクトリ作成
   - mkdir -p data

5. 環境変数の設定
   - プロジェクトルートに .env / .env.local を配置して設定できます（本ライブラリは自動で読み込みます。CWD ではなくパッケージの場所からプロジェクトルートを検出します）。
   - 代表的な環境変数:
     - JQUANTS_REFRESH_TOKEN (必須)
     - KABU_API_PASSWORD (必須)
     - OPENAI_API_KEY (AI モジュール使用時に必須)
     - KABUSYS_ENV = development | paper_trading | live (デフォルト: development)
     - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
     - SQLITE_PATH (監視用 DB, デフォルト: data/monitoring.db)
     - PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
     - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (LINE 通知用)
     - PID_FILE_PATH (デフォルト: data/execution.pid)
     - KILL_FLAG_PATH (デフォルト: data/kill.flag)
     - PAPER_FILL_MODE (paper_trading 動作モード: instant | partial | never | reject。デフォルト "instant")
     - MONITOR_POLL_INTERVAL (監視ポーリング間隔秒。run_monitoring の場合。デフォルト 60)
   - 必須の環境変数がないと Settings が ValueError を投げます。 .env.example を参照してください（存在する場合）。

6. DB 初期化
   - 多くの起動スクリプトは起動時に必要なテーブルを自動で作成します（monitoring の init_monitoring_db 等）。初期化を手動で行う必要は基本的にありません。

───

使い方（主要スクリプト）
- ExecutionEngine を起動（本番/ペーパートレード切替）
  - Paper Trading（ローカル検証）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - Paper トレードは専用 SQLite（PAPER_TRADING_SQLITE_PATH）に書き込まれ、本番 DB と分離されます。
  - 本番/その他:
    - KABUSYS_ENV=live python -m kabusys.run_execution
  - 補足:
    - 起動直後にプロセス優先度を "high" に設定します（失敗しても継続）。
    - ExecutionEngine は duckdb と sqlite の接続を使用します。設定に応じてブローカークライアントを選択します。

- Monitoring を起動（ポーリングループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書きできます（例: MONITOR_POLL_INTERVAL=30）。
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を使用します（監視ログは production DB に集約される想定）。
  - run_monitoring は SystemMonitor.check_once() を定期実行し、MonitoringDB に状態を保存します。

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数より優先）
  - 出力: 標準出力に集計・判定（PASS/FAIL）を表示します。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ブラウザで監視用ダッシュボード（Overview / Positions / Orders / System）を確認できます。
  - ダッシュボードは監視 DB を読み取り専用で開きます（?mode=ro）。

- AI モジュール（ニューススコア / レジーム判定）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
    - DuckDB 接続と target_date を渡すと ai_scores テーブルへ銘柄スコアを保存します。OPENAI_API_KEY が必要。
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
    - ETF MA とマクロニュースを組み合わせて market_regime テーブルへ書き込みます。

注意点 / 動作仕様
- run_monitoring における MONITOR_POLL_INTERVAL が 0 以下または不正な値の場合はデフォルト 60 秒にフォールバックします。
- paper_trading モードは本番 DB と分離されます（PAPER_TRADING_SQLITE_PATH を使用）。
- いくつかのモジュールは外部 API キー（OPENAI_API_KEY、JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を要します。これらが未設定の場合は該当機能が例外を投げるか（必須項目）、フェイルセーフでスキップする実装があります（ソースの docstring を参照）。
- Process priority / CPU affinity の設定は psutil を使ってプラットフォーム差分を吸収しますが、権限不足や未対応 OS の場合は警告を出してスキップします。
- DuckDB と SQLite を組み合わせて使用します。DuckDB は主にリサーチ・価格データ集計に使用され、SQLite は監視ログや注文履歴の永続化に使われます。

───

ディレクトリ構成（抜粋）
- src/kabusys/
  - __init__.py
  - config.py              — 環境変数／設定管理
  - run_execution.py       — ExecutionEngine 起動スクリプト
  - run_monitoring.py      — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - reconciler.py
    - (その他ブローカー連携・order_repository 等)
  - utils/
    - process_priority.py

───

よくある質問 / トラブルシューティング
- 「.env を置いているのに値が読み込まれない」
  - このプロジェクトは .git または pyproject.toml を探索してプロジェクトルートを自動判定します。配置場所を確認してください。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 「OpenAI 呼び出しで 429 やタイムアウトが出る」
  - news_nlp/regime_detector は一部のエラーで指数バックオフとリトライを実装していますが、API キーのレート上限やネットワーク状態を確認してください。
- 「monitoring が監視データを書き込まない」
  - run_monitoring は Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。パス・権限を確認、ログを確認してください。

───

開発者向けメモ
- 多くのモジュールは「DB 接続を受け取る」「副作用を極力減らす」設計（純粋関数と副作用分離）を意識しています。ユニットテストが書きやすい構造になっています。
- DuckDB の SQL はモジュール内で直接組み立てられているため、データスキーマ（prices_daily / raw_financials / raw_news 等）に合わせた事前データ投入が必要です。

───

貢献・ライセンス
- README にライセンス情報がないため、内部ポリシーに従ってください。貢献の際は Pull Request と詳細な説明をお願いします。

問題報告・質問がある場合は README を更新して issue を立ててください。