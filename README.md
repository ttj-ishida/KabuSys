README
======

概要
----
KabuSys は日本株の自動売買・リサーチ・監視を行うための軽量なプラットフォームです。本リポジトリは以下の主要機能を提供します。

- 注文作成・発注管理・リコンサイルを含む Execution エンジン
- システム稼働状況・注文異常・リスク監視の Monitoring 機能（SQLite 永続化）
- ポートフォリオ構成・銘柄選定・株数決定などの Portfolio ロジック（純粋関数）
- DuckDB を用いたファクター計算・リサーチユーティリティ
- ニュース NLP を用いた銘柄センチメント評価（OpenAI）
- Paper Trading 検証用のレポート生成ツール
- Streamlit を用いた監視ダッシュボード

主な設計方針として「本番 API へのアクセスとリサーチ処理を分離」「外部 API 呼び出しは明示的に行う」「環境変数 / .env による設定管理」を採用しています。

機能一覧
--------
- Execution
  - Broker クライアントの切り替え（本番 / paper_trading）
  - OrderManager による発注・状態管理
  - Reconciler による起動時リコンシリエーション（ブローカーとローカル DB の同期）
  - RiskManager（発注前チェック）など（実装の一部が該当）
- Monitoring
  - SystemMonitor：CPU/メモリ/ディスク、Execution プロセスの PID、データ鮮度監視
  - TradeMonitor：滞留注文・約定価格異常検出
  - RiskMonitor：ドローダウン・ポジション数監視、ダッシュボード更新
  - KillSwitch：閾値超過時に data/kill.flag を書いて Execution を停止
  - AlertManager：LINE へ通知（オプション）
  - Streamlit ダッシュボード（読み取り専用）
- Portfolio
  - 銘柄選定（スコア順／等分配）
  - 重み計算（等分配・スコア重み）
  - セクターキャップ適用、レジーム乗数
  - 単元株丸めを考慮した株数決定（risk_based / equal / score）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB）
  - 将来リターン・IC（Information Coefficient）・統計サマリー
- AI
  - news_nlp: raw_news を OpenAI に投げて銘柄ごとの ai_score を作成
  - regime_detector: ETF の MA200 とマクロニュースを合成して市場レジーム判定
- Tools
  - paper_verification_report: Paper Trading の検証レポートを生成

セットアップ手順
----------------
前提
- Python 3.10+ を推奨（typing の union シンタックスや型注釈に依存）
- Git リポジトリのルートに移動して作業すること（.env 自動ロードはプロジェクトルート検出に依存）

1. 必要パッケージのインストール（最低限）
   - duckdb
   - psutil
   - requests
   - openai
   - streamlit
   インストール例:
   ```
   pip install duckdb psutil requests openai streamlit
   ```
   （実際の requirements.txt がある場合はそれを使用してください）

2. 環境変数の設定
   - プロジェクトルートに .env を置くと自動で読み込まれます（.env.local は .env の上書き）。
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

   主な環境変数（例）
   - JQUANTS_REFRESH_TOKEN (必須)
   - KABU_API_PASSWORD (必須)
   - KABU_API_BASE_URL (任意, デフォルト: http://localhost:18080/kabusapi)
   - OPENAI_API_KEY (AI 機能を使う場合必須)
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID (AlertManager を使う場合)
   - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
   - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL
   - DUCKDB_PATH: デフォルト data/kabusys.duckdb
   - SQLITE_PATH: デフォルト data/monitoring.db
   - PAPER_TRADING_SQLITE_PATH: デフォルト data/paper_trading.db
   - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の挙動）
   - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、run_monitoring で使用）

3. データディレクトリ
   - デフォルトで data/ 以下に DB やフラグファイルが作られます。必要なら事前に作成してください。

使い方
------
以下はよく使うコマンドの例です。

1. 監視ループを起動（Monitoring）
   - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
   - 停止はプロジェクトルートから data/stop_requested.flag を作成するか、Ctrl+C。

   実行:
   ```
   python -m kabusys.run_monitoring
   ```
   例: 30 秒間隔で実行する場合:
   ```
   MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
   ```

   補足:
   - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（SQLITE_PATH）を用いて監視テーブルを作成します。
   - 停止フラグ file: data/stop_requested.flag を検知してループを終了します。

2. Execution エンジンを起動
   - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_sqlite_path（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に書き込みます。本番 DB と分離されます。
   - 起動時、data/execution.pid に PID を書き込み、停止は data/stop_requested.flag を作成するか KillSwitch による kill.flag によって行われます。

   実行:
   ```
   python -m kabusys.run_execution
   ```

3. Streamlit 監視ダッシュボード
   - 監視 DB を読み取り専用で開いてダッシュボードを表示します。
   実行:
   ```
   streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
   ```

4. Paper Trading 検証レポート生成
   - Paper Trading DB（data/paper_trading.db）からレポートを生成します。
   実行例:
   ```
   python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
   ```
   オプション:
   - --db PATH : DB パスを指定（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

5. AI 機能（ニュース NLP / レジーム判定）
   - OPENAI_API_KEY を環境変数か関数引数で指定する必要があります。
   - 関数呼び出しベースなので、スクリプトから呼ぶか Python REPL で利用します。
     例（モジュール API）:
     from kabusys.ai.news_nlp import score_news
     from kabusys.ai.regime_detector import score_regime

運用上の注意
-------------
- .env の自動読み込み
  - .env と .env.local をプロジェクトルートから自動で読み込みます。OS 環境変数は上書き保護されます。
  - 自動読み込みを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

- DB 分離
  - 本番実行時は SQLITE_PATH（監視）と PAPER_TRADING_SQLITE_PATH（paper_trading）が分離されています。paper_trading による誤操作が本番データに影響を与えないよう設計されています。

- 停止・強制停止
  - Execution 側は KillSwitch によって data/kill.flag が書き込まれると安全に停止します（評価条件は RiskMonitor 等の閾値）。
  - 管理運用では kill.flag を検査し、必要に応じて clear()（KillSwitch.clear）を使ってフラグをクリアしてください。

- プロセス優先度
  - run_monitoring / run_execution 起動時に set_process_priority("high") が呼ばれます。実行環境によっては権限が必要な場合があります（失敗しても警告で続行します）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / .env 読み込み・設定ラッパー
  - run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               — ExecutionEngine 起動スクリプト
  - utils/
    - process_priority.py          — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - __init__.py
    - monitoring_db.py             — SQLite テーブル作成・永続化層
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
    - (その他: broker_factory, execution_engine, order_repository など)
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
  - data/                            — 実行時に生成される想定 (DB / pid / flag ファイル)
  - tools/
    - paper_verification_report.py

よく使うファイル / フラグ
- data/monitoring.db (デフォルト SQLITE_PATH)
- data/kabusys.duckdb (デフォルト DUCKDB_PATH)
- data/paper_trading.db (PAPER_TRADING_SQLITE_PATH)
- data/execution.pid (ExecutionEngine の PID 保存)
- data/kill.flag (KillSwitch が作成する停止フラグ)
- data/stop_requested.flag (手動で作成すると run_monitoring/run_execution が停止)

環境変数の主要な取り扱い
- KABUSYS_ENV: development | paper_trading | live
  - paper_trading の場合、run_execution は MockBroker を使い paper_trading DB に書き込みます
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant/partial/never/reject）
- OPENAI_API_KEY: AI 機能を利用する際に必要
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager（LINE 通知）を使う場合に設定

付記（開発者向け）
- .env のパースは config._parse_env_line にて厳密に実装されており、シングル/ダブルクォートやエスケープを扱います。OS 環境変数は .env による上書きから保護されます。
- DuckDB 接続は research / ai モジュールで多数使われます。prices_daily / raw_financials / raw_news 等のテーブルを用意してください。
- OpenAI API 部分はエラー時にフェールセーフ（スコア 0 やスキップ）で継続するよう設計されていますが、API キーは必須です。

ライセンス / 貢献
----------------
本 README はコードベースの説明を目的としています。実際のライセンス・貢献方法はリポジトリの LICENSE / CONTRIBUTING を参照してください。

問題報告 / 質問
--------------
不具合や質問は issue を立ててください。README やコード中のドキュメント文字列（docstring）にも多くの使用例と注意書きを記載しています。