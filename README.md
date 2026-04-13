KabuSys — 日本株自動売買システム
==============================

概要
----
KabuSys は日本株向けの自動売買システムのコアライブラリ群です。  
本リポジトリは下記の機能群を純粋関数／モジュール単位で提供し、Execution（発注実行）、Monitoring（監視・アラート）、Research（ファクター計算・特徴量解析）、Portfolio（銘柄選定・資金配分）、AI（ニュース NLP / レジーム判定）、およびユーティリティを含みます。

主な特徴
--------
- Execution:
  - 起動時リコンシリエーション（Reconciler）
  - 注文状態管理（OrderManager / OrderRepository）
  - paper_trading モード（本番 DB と完全分離、MockBroker を利用）
- Monitoring:
  - システム状態（CPU/メモリ/ディスク）・プロセス生存チェック
  - 注文滞留・約定異常価格監視
  - ドローダウン / ポジション上限の検出と kill.flag による停止シグナル
  - LINE へのアラート送信（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Research:
  - Momentum / Volatility / Value 等のファクター計算（DuckDB を用いた SQL + Python 実装）
  - 将来リターン計算、IC（Information Coefficient）などの統計ユーティリティ
- AI:
  - raw_news を LLM（OpenAI）でセンチメント化して ai_scores に格納（news_nlp）
  - マクロニュース + ETF MA200 を使った市場レジーム判定（regime_detector）
- Portfolio:
  - 候補選定、等配分・スコア加重、ポジションサイズ計算、セクター上限・レジーム調整
- 実運用配慮:
  - プロセス優先度・CPU affinity のユーティリティ
  - .env 自動読込（Settings）、環境ごとの DB 分離（paper_trading）

セットアップ
------------
前提:
- Python 3.9+（typing / pathlib 等を利用）
- DuckDB、SQLite を使用（ローカルファイル DB）

推奨手順:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストール
   - 主要依存（例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt があれば pip install -r requirements.txt）

3. 環境変数 / .env
   - プロジェクトルートの .env（または .env.local）で設定できます。Settings モジュールは自動的に .env を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
   - 必須項目（本番で必要）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY
   - 代表的なオプション例 (.env):
     - KABUSYS_ENV=development
     - LOG_LEVEL=INFO
     - SQLITE_PATH=data/monitoring.db
     - DUCKDB_PATH=data/kabusys.duckdb
     - PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     - OPENAI_API_KEY=sk-...
     - LINE_CHANNEL_ACCESS_TOKEN=...
     - LINE_USER_ID=...
     - MONITOR_POLL_INTERVAL=60
     - PAPER_FILL_MODE=instant
     - KILL_FLAG_CLEAR_ON_START=1

4. データディレクトリ作成
   - mkdir -p data

使い方
------
起動用スクリプト（モジュールとして実行可能）:

- ExecutionEngine を起動（本番 / paper_trading 切替）
  - python -m kabusys.run_execution
    - 環境変数 KABUSYS_ENV=paper_trading にすると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使い MockBrokerClient で動作します。
    - 起動時にプロセス優先度を "high" に設定します。
    - PID ファイルは Settings.pid_file_path（デフォルト data/execution.pid）に書きます。
    - KILL_FLAG_CLEAR_ON_START=1 を設定しておくと起動時の kill.flag を削除できます（実行時の設定に依存）。

- Monitoring のポーリングループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書きできます（デフォルト 60）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path）を使用して監視ログを記録します。

- Paper Trading 検証レポート生成ツール
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
    - デフォルト DB は data/paper_trading.db。--db で別パス指定可。
    - 出力: 稼働率、注文成功率、送信率、P95 レイテンシ等と PASS/FAIL 判定。

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
    - 監視 DB を読み取り専用で開いてダッシュボードを表示します。

- AI モジュール呼び出し（プログラム内）
  - ニュースのスコアリング:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key=None)  # api_key を与えない場合 OPENAI_API_KEY を参照
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key=None)

環境変数のポイント
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading の場合、発注は paper_trading DB に記録され、本番 DB と完全に分離されます。
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading のフィルモード）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（正の整数、デフォルト 60）
- OPENAI_API_KEY: OpenAI 呼び出しで使用（AI モジュール）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager が LINE に通知するために使用
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を削除するかどうか（"1" で削除）

実装上の注意・設計メモ
- Settings モジュールはプロジェクトルート（.git または pyproject.toml）を探して .env / .env.local を自動で読み込みます。テスト中は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を使って無効化可能です。
- Monitoring の DB 初期化は init_monitoring_db() で冪等に行います。マイグレーション処理（カラム追加）も一部ハンドリングしています。
- OpenAI API 呼び出しはリトライ戦略を備え、失敗時はフェイルセーフ（スコアを 0 にフォールバックする等）の実装があります。
- プロセス優先度・CPU affinity は utils/process_priority.py で抽象化され、Windows / POSIX の差分を吸収します。
- ファイルベースの kill.flag による外部停止シグナル機構があります（KillSwitch）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py                            — パッケージ定義（__version__ 等）
  - config.py                              — 環境変数 / Settings 管理、.env 読込
  - run_execution.py                       — ExecutionEngine 起動スクリプト（メイン）
  - run_monitoring.py                      — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py         — Paper Trading 検証レポート CLI
  - execution/
    - order_manager.py                     — 注文の外向き API（状態遷移・送信）
    - reconciler.py                        — 起動時リコンシリエーション（同期）
    - ...                                  — broker_factory 等（ブローカ抽象化）
  - monitoring/
    - monitoring_db.py                     — SQLite 永続化層（system_status / trade_logs / positions / risk_logs / dashboard）
    - system_monitor.py                    — システム状態・データ鮮度チェック
    - trade_monitor.py                     — 注文滞留・約定異常検出
    - risk_monitor.py                      — ドローダウン / ポジション上限監視
    - kill_switch.py                       — kill.flag 制御
    - alert_manager.py                     — LINE 通知
    - monitoring_engine.py                 — 各監視を束ねるループ
    - streamlit_dashboard.py               — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py                 — 候補選定・重み算出
    - position_sizing.py                   — 株数計算、コストバッファ・スケーリング
    - risk_adjustment.py                   — セクター上限・レジーム乗数
  - research/
    - factor_research.py                   — Momentum / Volatility / Value 等
    - feature_exploration.py               — forward returns / IC / rank / stats
  - ai/
    - news_nlp.py                          — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py                   — レジーム判定（MA200 + マクロ NLP）
  - data/                                   — （想定）DB ファイル格納場所（data/*.db, data/*.duckdb）
  - utils/
    - process_priority.py                  — プロセス優先度 / CPU affinity

ライセンス・貢献
----------------
- （ここではライセンスファイルは省略）実プロジェクトでは LICENSE を追加してください。  
- バグ報告・改善提案は Issue を作成してください。大きな変更は PR をお願いします。

補足
----
- 本 README はコードベース内のドキュメント文字列および設計コメントに基づいて作成しています。実際の運用前に .env の設定、OpenAI / ブローカー API キー、DB バックアップ等を整えてください。  
- 実行コマンドや依存パッケージはプロジェクトで管理する requirements.txt / pyproject.toml に合わせて調整してください。

以上。必要であればサンプル .env テンプレートや起動例を追記します。どの情報を優先して詳述しますか？