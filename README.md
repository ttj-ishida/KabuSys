# KabuSys — README (日本語)

概要
-----
KabuSys は日本株の自動売買／研究／監視を行うためのモジュール群です。  
このリポジトリには以下の主な機能群が含まれます:

- 注文発行・状態管理（Execution）
- 監視・アラート（Monitoring）
- ポートフォリオ構築・ポジション計算（Portfolio）
- ファクター計算・リサーチユーティリティ（Research）
- ニュースの LLM によるセンチメント評価（AI）
- 各種ツール（検証レポート生成等）
- 環境変数ベースの設定管理

主な特徴
-------
- モジュール設計（純粋関数／サイドエフェクト分離）によりテストしやすい実装
- DuckDB を用いたファクタ計算・履歴データ参照
- SQLite（監視用 / Paper Trading 用）による軽量な永続化
- OpenAI を利用したニュース NLP（レート制限やパースエラーに対するリトライとフェイルセーフ）
- LINE Push を使ったアラート送信（クールダウン管理）
- Monitoring 用の Streamlit ダッシュボードを備える
- 実行プロセス優先度・CPU affinity 設定ユーティリティ（psutil 利用）

動作前提（推奨）
----------------
- Python 3.10+
- 必要パッケージ（例）:
  - duckdb
  - psutil
  - openai
  - requests
  - streamlit
- SQLite（標準ライブラリで使用可）

セットアップ手順
----------------
1. リポジトリをクローン／チェックアウトします。

2. 仮想環境を作成してアクティベートします（任意）。
   - python -m venv .venv
   - source .venv/bin/activate など

3. 必要なパッケージをインストールします（requirements.txt がない場合は下記を参考に）。
   - pip install duckdb psutil openai requests streamlit

4. 環境変数の設定
   - プロジェクトルートの `.env` または `.env.local` に環境変数を記述すると自動ロードされます（CWD ではなくソース位置からプロジェクトルートを検出します）。
   - 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（主なもの）
- JQUANTS_REFRESH_TOKEN — J-Quants API 用トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- KABU_API_BASE_URL — kabuステーション base URL（省略時: http://localhost:18080/kabusapi）
- OPENAI_API_KEY — OpenAI API キー（AI モジュール使用時に必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — LINE 通知（任意）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite DB（デフォルト: data/paper_trading.db）
- KABUSYS_ENV — 実行環境: development | paper_trading | live （デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...）
- PAPER_FILL_MODE — Paper Trading の約定挙動（instant | partial | never | reject）
- PID_FILE_PATH, KILL_FLAG_PATH など監視用パス
- MONITOR_POLL_INTERVAL — Monitoring のポーリング間隔（秒、デフォルト 60）

使い方（よく使うコマンド）
-------------------------

- 監視ループ（SystemMonitor のポーリング）を起動:
  - python -m kabusys.run_monitoring
  - 環境変数 `MONITOR_POLL_INTERVAL` で間隔（秒）をオーバーライド可（デフォルト 60 秒）。
  - Monitoring は常に本番用の sqlite_path を使用します（環境に依らず）。

- 実行エンジン（ExecutionEngine）を起動:
  - python -m kabusys.run_execution
  - `KABUSYS_ENV=paper_trading` のときは MockBrokerClient を使用し、Paper Trading 用 DB（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）に記録します。本番 DB と分離されます。
  - 実行前に必要な環境変数（API キー・パスワード等）を設定してください。

- Streamlit 監視ダッシュボードを起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視用 SQLite DB を read-only で開きます。DB がない場合は MonitoringEngine を先に起動してください。

- Paper Trading 検証レポートを生成:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: data/paper_trading.db。`--db` または `PAPER_TRADING_SQLITE_PATH` で上書き可能。

- AI モジュール（ニューススコア等）を実行する場合:
  - `OPENAI_API_KEY` を設定してください。
  - kabusys.ai.score_news や kabusys.ai.regime_detector.score_regime などをコードから呼び出します（これらは CLI エントリポイントではありませんが、必要ならスクリプト化できます）。

注意点 / 運用上のメモ
- run_monitoring: 監視は常に production の sqlite_path に対して初期化（init_monitoring_db）を行います。
- run_execution: paper_trading モードでは専用 DB を使用して本番データと分離します。
- Process Priority: 起動スクリプトは最初に set_process_priority("high") を呼び出してプロセス優先度を上げようとします（psutil が必要）。アクセス権限や OS により失敗することがありますがログのみ出力して継続します。
- Kill Switch: RiskMonitor の判定で kill.flag を書き込み、ExecutionEngine に停止を促す仕組みがあります（flag の存在チェック・クリア機能あり）。
- DB マイグレーション: monitoring の初期化時にスキーマ作成と簡易マイグレーション（列追加）を行います（init_monitoring_db）。

ディレクトリ構成（主要ファイル）
------------------------------
（src/kabusys 以下の主要モジュールを抜粋）

- src/kabusys/
  - __init__.py                            — パッケージメタ情報
  - config.py                              — 環境変数 / 設定管理
  - run_monitoring.py                      — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py                       — ExecutionEngine 起動スクリプト

  - ai/
    - news_nlp.py                          — ニュースを OpenAI でスコアリング
    - regime_detector.py                   — 市場レジーム判定（MA + マクロセンチメント）
    - __init__.py

  - monitoring/
    - monitoring_db.py                     — Monitoring 用 SQLite 永続化層（init / CRUD）
    - system_monitor.py                    — システム状態・データ鮮度監視
    - trade_monitor.py                     — 注文滞留・約定異常検出
    - risk_monitor.py                      — ドローダウン・ポジション上限監視
    - kill_switch.py                       — kill.flag 制御
    - alert_manager.py                     — LINE Push アラート送信（クールダウン）
    - monitoring_engine.py                 — Monitor を束ねたポーリングエンジン
    - streamlit_dashboard.py               — Streamlit ベースの監視ダッシュボード
    - __init__.py

  - execution/
    - order_manager.py                     — 注文の外向け API（作成・送信・同期）
    - reconciler.py                         — 起動時リコンシリエーション（注文・ポジション照合）
    - order_repository.py, order_record.py  — 注文 DB / レコード（含まれない部分あり）
    - execution_engine.py, broker_*         — Broker インターフェース等（詳細は該当ファイル参照）

  - portfolio/
    - portfolio_builder.py                  — 候補選定・スコア順ソート
    - position_sizing.py                    — 株数計算・単元丸め・aggregated cap 処理
    - risk_adjustment.py                    — セクターキャップ・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py                    — Momentum / Value / Volatility ファクター計算（DuckDB）
    - feature_exploration.py                — 将来リターン計算・IC・統計サマリー
    - __init__.py

  - tools/
    - paper_verification_report.py          — Paper Trading 検証レポート生成スクリプト
    - __init__.py

  - utils/
    - process_priority.py                   — プロセス優先度 / CPU affinity ユーティリティ
    - __init__.py

補足（開発者向け）
-----------------
- .env のパースは config._parse_env_line が行い、シェル風の export やクォート・インラインコメントに対応しています。
- Research / AI 部分は外部への実際の注文を行わず、DuckDB の prices_daily/raw_financials/raw_news 等のテーブルに依存します。
- OpenAI 呼び出し部分はレスポンスのバリデーション・リトライ制御が組み込まれており、部分失敗を許容して他の処理を継続する設計です。
- 一部のモジュールは単体での CLI 起動（python -m ...）が可能です。ユニットテストや CI 実行時は環境依存の部分（OpenAI・psutil・外部 DB）をモックすることを想定しています。

ライセンス / 貢献
-----------------
この README では具体的なライセンス情報は含めていません。リポジトリのトップレベルに LICENSE ファイルがある場合はそちらを参照してください。バグ報告・改善提案は Issue を作成してください。

---

不明点や追加したい例（例: 推奨の .env テンプレートや起動スクリプトの systemd ユニット例）などがあれば教えてください。README に追記して整備します。