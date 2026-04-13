KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買・リサーチ・監視ツール群です。
主な機能は以下のとおりです：

- シグナルからの発注／注文状態管理（ExecutionEngine）
- リコンシリエーション（再起動後の注文同期・ポジション差分検出）
- ポートフォリオ構成（候補選定・重み計算・ポジションサイジング・セクター制約）
- ファクター計算・リサーチユーティリティ（モメンタム／ボラティリティ／バリュー等）
- ニュースを利用した LLM ベースのセンチメント評価（OpenAI 経由）
- 監視（システム状態、注文滞留、リスクアラート、kill-switch）
- モニタリング用 Streamlit ダッシュボード
- Paper Trading 検証レポート生成ツール

本リポジトリはライブラリ群と、起動用スクリプト（run_execution, run_monitoring 等）・ユーティリティを含みます。

主要な機能一覧
---------------
- Execution（src/kabusys/run_execution.py, execution/*）
  - Broker クライアントの抽象化（本番 / Paper Trading 切り替え）
  - OrderManager、RiskManager、Reconciler、ExecutionEngine の組み合わせによる注文実行
  - Paper Trading 環境では mock broker を使用し DB を分離（data/paper_trading.db）

- Monitoring（src/kabusys/run_monitoring.py, monitoring/*）
  - SystemMonitor：CPU/Memory/Disk・プロセス生存・データ鮮度監視
  - TradeMonitor：滞留注文／約定価格異常検出
  - RiskMonitor：ドローダウンやポジション上限監視（kill-switch 連携）
  - AlertManager：LINE への通知（クールダウン機能）
  - streamlit_dashboard：監視情報可視化（Streamlit）

- Research / Portfolio
  - research.factor_research：モメンタム/ボラティリティ/バリュー等のファクター計算（DuckDB 経由）
  - research.feature_exploration：将来リターン・IC 計算、統計サマリ
  - portfolio：候補選定、重み計算、ポジションサイズ算出、セクター制約、レジーム乗数

- AI（src/kabusys/ai/*）
  - news_nlp.score_news：ニュース記事をまとめて OpenAI に送り、銘柄ごとのセンチメントを ai_scores に書き込む
  - regime_detector.score_regime：ETF とマクロニュースを組み合わせて市場レジーム判定を行う

セットアップ手順
----------------
前提
- Python 3.9+ を想定（DuckDB / psutil / openai 等が動作する環境）
- Git などでリポジトリを取得済み

1. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   典型的な依存パッケージ（requirements.txt がない場合は個別インストール）：
   - pip install duckdb psutil requests openai streamlit

   ※ 実行環境によっては追加パッケージ（例えば各ブローカークライアントなど）が必要です。

3. 環境変数 / .env ファイル
   - プロジェクトルートに .env / .env.local を置くと自動で読み込まれます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 最低限設定が必要な環境変数（用途）：
     - JQUANTS_REFRESH_TOKEN — J-Quants API トークン
     - KABU_API_PASSWORD — kabuステーション API のパスワード
     - OPENAI_API_KEY — OpenAI API キー（AI 機能使用時）
     - KABUSYS_ENV — 環境 ("development" | "paper_trading" | "live")
     - DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE — Paper Trading の約定挙動 ("instant" | "partial" | "never" | "reject")
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知
     - PID_FILE_PATH / KILL_FLAG_PATH — PID / kill flag のパス
     - その他しきい値等（CPU_THRESHOLD_PCT 等）は必要に応じて設定可能

   例（.env）:
   ```
   KABUSYS_ENV=paper_trading
   OPENAI_API_KEY=sk-...
   PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
   DUCKDB_PATH=data/kabusys.duckdb
   ```

使い方（主要コマンド）
--------------------

1. ExecutionEngine（実行エンジン）起動
   - Paper Trading:
     - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
       → MockBroker を使い data/paper_trading.db に書き込みます（本番 DB と分離）。
   - 本番:
     - KABUSYS_ENV=live python -m kabusys.run_execution
   - 補足: 起動時にプロセス優先度を "high" に設定し、pid ファイル（Settings.pid_file_path）を使用します。

2. Monitoring（監視ループ）起動
   - python -m kabusys.run_monitoring
   - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔（秒）を指定可能（デフォルト 60）。
     例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

3. Streamlit ダッシュボード
   - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   - 監視 DB を読み取り専用で開き、Overview / Positions / Orders / System タブで可視化します。

4. Paper Trading 検証レポート
   - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
   - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   - デフォルト DB: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH 環境変数で上書き可能）
   - レポートでは稼働率、注文成功率、送信率、P95 レイテンシなどを表示し PASS/FAIL を判定します。

5. AI 関連（ニューススコア / レジーム判定）
   - プログラム的に利用する API（関数）:
     - from kabusys.ai.news_nlp import score_news
     - from kabusys.ai.regime_detector import score_regime
   - どちらも DuckDB 接続と target_date（date オブジェクト）を受け取り、OPENAI_API_KEY が必要です。
   - 例（簡易スニペット）:
     ```
     import duckdb
     from datetime import date
     from kabusys.ai.news_nlp import score_news

     conn = duckdb.connect("data/kabusys.duckdb")
     cnt = score_news(conn, date(2026, 4, 10), api_key="sk-...")
     print("written:", cnt)
     ```

注意事項 / 運用メモ
-----------------
- Settings は .env / 環境変数から読み込みます。プロジェクトルートの検出は .git または pyproject.toml を基準とします。
- Monitoring は Settings.env にかかわらず（常に）本番 sqlite_path を使用します（監視ログは本番 DB に集約する設計）。
- Paper Trading は本番 DB と完全に分離するよう paper_sqlite_path を使用します。
- PID ファイルが stale（プロセスが存在しない）場合、SystemMonitor はファイルを削除してリスクイベントを記録します。
- kill.flag による停止は KillSwitch が管理します。ExecutionEngine 側はこのフラグの存在を見て停止を行う想定です（詳細は ExecutionEngine 実装に依存します）。
- OpenAI 呼び出しはリトライやバックオフを行いますが、API キー未設定時は例外を投げます。API コール失敗時はフェイルセーフで処理を継続する箇所が多くあります（スコアをスキップ / 0 にフォールバック等）。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                     — 環境変数 / 設定管理
- run_execution.py              — ExecutionEngine 起動スクリプト
- run_monitoring.py             — SystemMonitor ポーリング起動スクリプト

パッケージ
- ai/
  - news_nlp.py                  — ニュース NLU / OpenAI 経由スコアリング
  - regime_detector.py           — マクロ + MA200 によるレジーム判定
- execution/
  - order_manager.py
  - reconciler.py
  - order_repository.py (参照あり)
  - execution_engine.py (参照あり)
  - broker_factory.py / broker_api.py (参照あり)
- monitoring/
  - monitoring_db.py             — SQLite スキーマ / 永続化 API
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py
- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py
- research/
  - factor_research.py
  - feature_exploration.py
- tools/
  - paper_verification_report.py  — CLI レポート生成
- utils/
  - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
- data/ (想定される出力ディレクトリ)
  - kabusys.duckdb
  - monitoring.db
  - paper_trading.db
- その他
  - __version__ 等

開発 / テスト
--------------
- モジュールは可能な限り純粋関数（副作用最小）に分割されています。ユニットテストは関数単位で行いやすい設計です。
- OpenAI など外部 API 呼び出しは個別関数（_call_openai_api 等）でラップされているため、unit test ではモック替えが容易です（unittest.mock.patch を推奨）。

ライセンス / 貢献
-----------------
- この README ではライセンス表記を含めていません。実際のプロジェクトルートに LICENSE ファイルや CONTRIBUTING.md を置いてください。

補足
----
- 実運用前に .env.example を用意し必要な環境変数をドキュメント化することを推奨します。
- 本 README はコードベースから推測可能な範囲での説明です。実際のブローカー連携や ExecutionEngine の細かな挙動は execution パッケージの実装に依存しますので、そちらのドキュメントも併せて参照してください。