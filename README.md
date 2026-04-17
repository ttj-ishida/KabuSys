# KabuSys (簡易 README)

このリポジトリは日本株向けの自動売買・研究・監視ユーティリティ群をまとめた Python パッケージです。モジュール群は注文実行、監視（モニタリング）、ポートフォリオ構築、リサーチ（ファクター計算）、AI によるニュース NLP 等を含みます。

以下は開発者／運用者向けの概要・セットアップ・使い方の簡潔な説明です。

## プロジェクト概要
- 名称: KabuSys
- 目的: 日本株の自動売買システムのコア機能（注文実行、リコンシリエーション、監視、ポートフォリオ構築、研究用ファクター計算、ニュースのセンチメント評価など）を提供するライブラリ兼実行スクリプト群。
- 設計方針:
  - DuckDB / SQLite を用いたデータ永続化（prices_daily 等は DuckDB、監視ログは SQLite）。
  - Paper trading（テスト用）と live（本番）を環境変数で切り替え。Paper trading は本番 DB と分離（data/paper_trading.db がデフォルト）。
  - OpenAI を用いたニュースセンチメント・レジーム判定機能を備える（API キー必須）。
  - 監視コンポーネントはファイルフラグ（kill.flag / stop_requested.flag）や LINE 通知で運用できる。

## 主な機能一覧
- 実行エンジン起動スクリプト（run_execution.py）
  - Broker クライアント生成、OrderManager、RiskManager、ExecutionEngine の起動・監視
  - KABUSYS_ENV=paper_trading 時は MockBroker を使用し paper_trading 用 DB に記録
  - 起動時に実行中プロセス PID を書き / stop フラグで停止制御
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor（CPU/Mem/Disk、プロセス生存、データ鮮度）、TradeMonitor、RiskMonitor を定期実行
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可（デフォルト 60 秒）
  - 監視ログは SQLite（settings.sqlite_path）に永続化（monitoring は環境にかかわらず本番 sqlite を使用）
- Monitoring ダッシュボード（Streamlit）
  - src/kabusys/monitoring/streamlit_dashboard.py から起動し、監視DBの状態を可視化
- Paper Trading 検証レポート生成ツール
  - src/kabusys/tools/paper_verification_report.py
  - 運用検証（稼働率、注文成功率、P95 レイテンシ等）を集計して標準出力へレポートを出力
- Portfolio 構築ユーティリティ
  - 候補選定、等重・スコア重み付け、セクターキャップ、ポジションサイズ計算等
- Research（ファクター計算 / 探索）
  - Momentum / Volatility / Value 等のファクター計算、将来リターン計算、IC（スピアマン）計算等
- AI モジュール
  - news_nlp: raw_news を集約して OpenAI に送り、銘柄ごとのセンチメントを ai_scores に保存
  - regime_detector: ETF (1321) の MA200 とマクロニュースを合成して日次レジーム判定を行い market_regime テーブルへ保存
- ユーティリティ
  - process_priority: OS に依存せずプロセス優先度や CPU affinity を設定
  - 設定管理 (kabusys.config.Settings): .env 自動読み込み、環境変数のバリデーション、各種パス・閾値定義

## セットアップ手順（ローカル開発／実行環境）
1. リポジトリをクローンし、Python 仮想環境を作成・有効化します。
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージをインストールします（requirements.txt がない場合は主要依存を個別に入れる）。
   - 主要依存例:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

3. 環境変数 / .env の準備
   - Settings はプロジェクトルートの `.env` / `.env.local` を自動でロードします（既存 OS 環境変数が優先）。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
   - 重要な環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 関連を使う場合必須）
     - KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
     - PAPER_FILL_MODE（paper_trading 時の約定挙動: instant | partial | never | reject）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト data/paper_trading.db）
     - SQLITE_PATH（監視 DB、デフォルト data/monitoring.db）
     - DUCKDB_PATH（DuckDB ファイル、デフォルト data/kabusys.duckdb）
     - LOG_LEVEL（DEBUG|INFO|...）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（通知用）
     - MONITOR_POLL_INTERVAL（run_monitoring のポーリング秒数、デフォルト 60）
   - 例 .env の一部（参考）:
     - JQUANTS_REFRESH_TOKEN=your_jquants_token
     - KABU_API_PASSWORD=your_kabu_password
     - OPENAI_API_KEY=sk-...
     - KABUSYS_ENV=development
     - DUCKDB_PATH=data/kabusys.duckdb
     - SQLITE_PATH=data/monitoring.db

4. データディレクトリ作成
   - data/ 以下に DB や pid/flag を置くことが想定されています。存在しない場合は手動で作成してください:
     - mkdir -p data

5. 初期 DB スキーマは各スクリプトが自動で作成します（例: init_monitoring_db が monitoring DB のテーブルを作る）。

## 基本的な使い方（実行例）
- 監視ループ（Monitoring）を起動:
  - KABUSYS_ENV は問わず監視 DB は設定された sqlite_path を使用します。
  - 実行:
    - python -m kabusys.run_monitoring
  - オプション:
    - 環境変数 MONITOR_POLL_INTERVAL=30 などでポーリング間隔を上書き可能（秒）。
  - 停止:
    - コントロール+C（KeyboardInterrupt）で停止。
    - もしくはプロジェクトルートの data/stop_requested.flag を作成するとループが検知して終了します。

- 実行エンジン（ExecutionEngine）を起動:
  - Paper trading モード（本番 DB と完全分離）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
    - Paper trading の DB は環境変数 PAPER_TRADING_SQLITE_PATH またはデフォルト data/paper_trading.db に記録されます。
  - Live（実運用）:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - 停止:
    - data/stop_requested.flag を作成すると実行中スレッドが検知して安全に停止します。
  - ExecutionEngine は起動時に高優先度設定（set_process_priority("high")）を試みます。

- Streamlit ダッシュボード（監視可視化）起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - もしくは --db オプションで別パスを指定できます。

- Paper Trading 検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db を指定すると PAPER_TRADING_SQLITE_PATH より優先して DB を指定できます。

- AI モジュールの利用（スクリプト／バッチで呼ぶ場合）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは引数で渡すか環境変数 OPENAI_API_KEY を設定してください。
  - AI 呼び出しはリトライ・フォールバック実装あり（失敗時は部分的にスキップして継続します）。

- Kill Switch / 停止フロー
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）にリスクトリガー理由を書き込むことで ExecutionEngine に停止シグナルを与えます（ファイルが存在すると起動を回避／停止させる仕組み）。
  - 削除（クリア）する場合は手動でファイルを削除するか、KillSwitch.clear() を呼ぶ実装を使用します。

## 注意点 / 実運用上のヒント
- 監視（monitoring）は設定にかかわらず monitoring.sqlite_path（= settings.sqlite_path）を使用する設計です。Paper trading でも監視ログは production 相当の sqlite を見る点に注意してください（run_execution は paper_trading 時に専用 DB を使う）。
- .env の自動ロードはプロジェクトルートを .git または pyproject.toml で探索して行われます。環境変数が優先されます。
- OpenAI 関係は API 呼び出しに伴う料金・レート制限があるため、API キー管理と利用頻度の設計に注意してください。
- process priority / cpu affinity の設定は psutil に依存し、権限不足や未対応 OS の場合は警告を出してスキップします。

## ディレクトリ構成（抜粋）
以下は主要ファイル・モジュールの構成（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py                      - 環境変数 / 設定管理
  - run_monitoring.py              - SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py               - ExecutionEngine 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py  - Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                   - ニュース NLP / ai_scores 書込み
    - regime_detector.py            - 市場レジーム判定
  - monitoring/
    - __init__.py
    - monitoring_db.py              - SQLite 監視 DB レイヤ
    - system_monitor.py             - システム状態・データ鮮度監視
    - trade_monitor.py              - 注文滞留 / 約定異常監視
    - risk_monitor.py               - ドローダウン・ポジション上限監視
    - kill_switch.py                - kill.flag 書込みユーティリティ
    - alert_manager.py              - LINE Push 通知ラッパ
    - monitoring_engine.py          - 各 monitor を束ねるエンジン
    - streamlit_dashboard.py        - Streamlit ダッシュボード
  - execution/
    - (OrderManager, Reconciler, ExecutionEngine, BrokerFactory などの実装)
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - process_priority.py
    - __init__.py
  - data/ (運用側に作成するディレクトリ、DB・PID・FLAG 等を配置)
    - monitoring.db (デフォルト)
    - paper_trading.db (paper_trading 用デフォルト)
    - kabusys.duckdb (デフォルト)
    - execution.pid, stop_requested.flag, kill.flag 等

（ライブラリ内にはさらに細かいモジュールや補助クラスが多数あります。上は主要なファイルの抜粋です。）

## 開発・運用でのよくあるコマンドまとめ
- 監視起動:
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
- 実行エンジン起動（paper_trading 例）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Streamlit ダッシュボード:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- AI スコア実行（Python スクリプト内で）:
  - from kabusys.ai import score_news
  - score_news(duckdb_conn, date(2026,4,1), api_key="sk-...")

---

追加の README 要素（例: API リファレンス、設計ドキュメント、DB スキーマ詳細、運用手順、エラーハンドリングポリシー等）を加えたい場合は、目的（運用マニュアル / 開発者向け設計書 等）を指定してください。必要に応じてサンプル .env.example の雛形や systemd / supervisor 用のユニット定義、Dockerfile の例も作成できます。