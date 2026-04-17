KabuSys — 日本株自動売買システム
=============================

このリポジトリは日本株向け自動売買プラットフォームのコアライブラリ群です。
監視（Monitoring）、実行（Execution）、ポートフォリオ構築、リサーチ、AI（ニュースNLP／レジーム判定）などの主要機能を含みます。

以下は本コードベースの概要・セットアップ・使い方・ディレクトリ構成の簡潔な README です。

プロジェクト概要
---------------
- 日本株自動売買のロジックや補助ユーティリティ群をモジュール化したライブラリ群。
- 大きく分けて次の機能群を提供:
  - 実行エンジン（ExecutionEngine 周辺）: ブローカー連携・注文管理・リコンシリエーション
  - 監視（Monitoring）: システム状態、注文滞留、リスク（ドローダウン・ポジション上限）監視、Kill Switch、LINE 通知、Streamlit ダッシュボード
  - ポートフォリオ構築（portfolio/*）: 候補選定、重み付け、ポジションサイズ計算、セクター制約適用
  - リサーチ（research/*）: ファクター計算、将来リターン・IC 計算、統計サマリー
  - AI（ai/*）: ニュースを LLM でスコアリングするニュースNLP、マクロ＋ETF を使ったレジーム判定
  - ツール（tools/*）: Paper Trading の検証レポートなど

主な機能一覧
-------------
- 監視
  - SystemMonitor: CPU / メモリ / ディスク、Execution プロセス生存確認、価格データ鮮度チェック
  - TradeMonitor: 注文滞留（stale orders）・約定価格異常の検出
  - RiskMonitor: ドローダウン監視、ポジション上限監視、Dashboard の更新
  - KillSwitch: 条件に応じて data/kill.flag を書き込み、Execution を停止させる仕組み
  - AlertManager: LINE Messaging API によるプッシュ通知（クールダウン管理）
  - Streamlit ベースの監視ダッシュボード
- 実行
  - ExecutionEngine（エンジン起動スクリプトあり）: ブローカークライアント、OrderManager、RiskManager、Reconciler を組み合わせてセッション実行
  - Paper Trading mode: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し DB を分離（data/paper_trading.db）
  - Reconciler: 再起動時の注文・ポジション照合（自動復旧）
- ポートフォリオ
  - 候補選定、等配分・スコア配分、リスク調整（セクター上限、レジーム乗数）、株数決定（ロット対応・aggregate cap）
- リサーチ
  - Momentum / Volatility / Value 等のファクターを DuckDB 上の prices_daily/raw_financials で計算
  - 将来リターン、IC（Spearman）や統計サマリー
- AI
  - news_nlp.score_news: raw_news を LLM（OpenAI）に送り銘柄ごとのセンチメントを ai_scores に書き込み
  - regime_detector.score_regime: ETF（1321）MA200 とマクロニュースの LLM 評価を合成して市場レジーム判定

セットアップ手順
----------------
1. Python 環境
   - Python 3.9+ を推奨（実装は近年の型ヒントを使用）
   - 仮想環境を作成して有効化:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール
   - requirements.txt がある想定で:
     - pip install -r requirements.txt
   - 主要依存（参考）:
     - duckdb, psutil, requests, openai, streamlit
     - SQLite は標準ライブラリで動作
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. データディレクトリ
   - project-root/data を作成しておくと良い:
     - mkdir -p data
   - 主要ファイル:
     - data/monitoring.db      (デフォルトの監視用 SQLite, Settings.sqlite_path)
     - data/paper_trading.db   (Paper Trading 用 SQLite)
     - data/kabusys.duckdb     (DuckDB のデータファイル, Settings.duckdb_path)
     - data/execution.pid      (Execution の PID ファイル)
     - data/kill.flag / data/stop_requested.flag — 停止用フラグ

4. 環境変数
   - .env / .env.local がプロジェクトルートにあれば自動読み込みされる（既存 OS 環境変数は保護）
   - 自動読み込みを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 主な必須/重要な変数:
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — LLM 呼び出しに必要（AI 機能を使う場合）
     - KABUSYS_ENV — development / paper_trading / live（デフォルト: development）
     - PAPER_FILL_MODE — paper_trading の Fill 動作（instant|partial|never|reject、デフォルト instant）
     - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB（デフォルト data/paper_trading.db）
     - SQLITE_PATH — 監視 DB（デフォルト data/monitoring.db）
     - DUCKDB_PATH — duckdb ファイル（デフォルト data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH / LOG_LEVEL 等

使い方（主要スクリプト・コマンド）
----------------------------

- 監視ループを起動
  - python -m kabusys.run_monitoring
  - 挙動:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト 60 秒）
    - 監視処理は monitoring DB（Settings.sqlite_path）を用いる（環境に関わらず本番 sqlite_path を使用）
    - 停止: data/stop_requested.flag を作成するとループ終了

- 実行エンジン（Execution）を起動
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合、MockBroker を使い data/paper_trading.db に記録（本番 DB と分離）
    - 起動時に data/stop_requested.flag が存在すると起動しない
    - 実行中に stop flag が作成されるとエンジンを停止する
    - 実行プロセスは data/execution.pid を利用

- Streamlit ダッシュボード（監視用）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 監視 DB を読み取り専用で開いてダッシュボードを表示

- Paper Trading 検証レポート（ツール）
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/data/paper_trading.db
  - 出力: 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを標準出力に表示し PASS/FAIL 判定

- AI 機能
  - kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime を Python から呼ぶか、呼び出し用スクリプトを作成して利用
  - 実行には OPENAI_API_KEY が必要。失敗時はフェイルセーフ（ログ出力・0.0 フォールバック等）

プロセス停止・フラグファイル
-------------------------
- data/stop_requested.flag: run_monitoring/run_execution などのスクリプトが監視している停止フラグ。存在するとループ停止。
- data/kill.flag: KillSwitch によって書き込まれ、ExecutionEngine に対する停止シグナルとして使われる。
- data/execution.pid: 実行プロセスの PID を保存するファイル（SystemMonitor は存在・生存確認を行う）

設定の自動ロード
----------------
- .env / .env.local をプロジェクトルートに置くと自動で読み込まれます（既に OS 環境変数にあるキーは上書きされません）。
- 自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

監視 DB（monitoring.db）テーブル（概要）
--------------------------------
init_monitoring_db で作成される主なテーブル:
- system_status: CPU/Mem/Disk、プロセス稼働フラグ、記録時刻
- trade_logs: 注文イベントログ（Created/Sent/Filled 等）、latency_ms カラムあり
- positions: 現在保有ポジション
- risk_logs: リスク関連イベント（DRAWDOWN_ALERT、STALE_ORDER 等）
- dashboard: 集計（portfolio_value, cash, drawdown_pct, open_order_count, position_count, peak_value）

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys をルートとした代表的な構成）
- src/kabusys/
  - __init__.py
  - config.py                — 環境設定（.env 読み込み、Settings クラス）
  - run_monitoring.py        — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py    — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py       — monitoring DB の初期化 / 永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - (その他 broker/engine 関連モジュール)
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

設計上の注意・運用上のヒント
--------------------------
- Monitoring は常に本番の monitoring.sqlite（Settings.sqlite_path）を使う設計です。環境に依らず監視は本番 DB に残す想定です（ただし paper_trading 用は別 DB を使う箇所あり）。
- run_execution は KABUSYS_ENV=paper_trading 時、paper_sqlite_path（デフォルト data/paper_trading.db）に完全分離して書き込みます。
- process_priority.set_process_priority("high") を起動時に呼んでいます。psutil の権限で失敗することがあるため警告でスキップされます。
- OpenAI 呼び出しは外部サービス依存のため、API キー管理・レート制御／エラーハンドリングに注意してください。モジュールはリトライ・フォールバックを実装していますが、コストとレート制限に注意。
- DuckDB は大規模な時系列 / ファクター計算に使います。prices_daily / raw_financials / raw_news 等のテーブルを用意してください。

サンプル .env キー（抜粋）
-------------------------
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...
- OPENAI_API_KEY=...
- KABUSYS_ENV=development|paper_trading|live
- PAPER_FILL_MODE=instant
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- SQLITE_PATH=data/monitoring.db
- DUCKDB_PATH=data/kabusys.duckdb
- PID_FILE_PATH=data/execution.pid
- KILL_FLAG_PATH=data/kill.flag
- LOG_LEVEL=INFO
- MONITOR_POLL_INTERVAL=60

ライセンス / 貢献
-----------------
- 本 README ではライセンス記載を行っていません。実運用・公開時は適切な LICENSE ファイルを追加してください。
- プロジェクトへの貢献は PR / Issue を通じてお願いします。ユニットテストとドキュメントを添えていただけると助かります。

問題が発生した場合 / よくある質問
--------------------------------
- DB が見つからない / 読み込めない:
  - data ディレクトリ・パス・権限を確認してください。Streamlit は read-only URI で接続することを推奨します。
- OpenAI 呼び出しが失敗する:
  - OPENAI_API_KEY が設定されているか、ネットワーク／レート制限を確認してください。ロギングに詳細が出ます。
- PAPER_TRADING で本番 DB に書き込まれるのでは？:
  - run_execution は Settings.is_paper に応じて paper_sqlite_path を使用します。必ず環境変数を確認してください。

---

追加で README に含めたい具体的なコマンドやサンプル .env、requirements.txt の候補があれば教えてください。必要に応じて README をさらに詳細化します。