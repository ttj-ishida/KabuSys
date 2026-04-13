KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買プラットフォームの一部実装です。本リポジトリは以下の主要機能を含みます。

- 注文発行・状態管理（ExecutionEngine、OrderManager / OrderRepository）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / MonitoringEngine）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算、セクター制約）
- リサーチ（ファクター計算、将来リターン、IC 計算 等）
- AI モジュール（ニュースのセンチメント、レジーム判定、OpenAI を利用）
- 運用補助ツール（Paper Trading 検証レポート、Streamlit ダッシュボード）

主な設計方針：
- 本番データと Paper Trading を分離（Paper Trading は専用 SQLite DB を使用）
- ルックアヘッドバイアス防止（日付参照を直接使わない設計）
- 外部 API 呼び出しのリトライ・フェイルセーフ処理を実装
- DB は SQLite（監視ログ）/ DuckDB（時系列・リサーチ用）を併用

機能一覧
--------
主要コンポーネント（抜粋）：

- Execution
  - ExecutionEngine（run_execution.py から起動）
  - OrderManager / Reconciler / RiskManager / OrderRepository
  - BrokerClientFactory によるブローカークライアント生成（paper_trading 用 Mock あり）
- Monitoring
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度）
  - TradeMonitor（滞留注文・約定価格異常検出）
  - RiskMonitor（ドローダウン・ポジション上限検出、kill.flag 書き込み）
  - AlertManager（LINE push による通知）
  - MonitoringEngine（各 Monitor を束ねる）
  - Streamlit ダッシュボード（監視情報の可視化）
- Portfolio
  - 候補選定、等/スコア重み、ポジションサイズ計算、セクターキャップ、レジーム乗数
- Research
  - ファクター計算（momentum, volatility, value）
  - 特徴量探索（forward returns, IC, summary）
- AI
  - news_nlp.score_news（OpenAI を使ったニュースセンチメント）
  - regime_detector.score_regime（MA + マクロ NLP を合成したレジーム判定）
- Tools
  - paper_verification_report（Paper Trading 結果から検証レポートを生成）

セットアップ手順
----------------

必須（代表的な）システム要件:
- Python 3.9+（コードの型アノテーション等を想定）
- DuckDB, SQLite 利用可能な環境

依存パッケージ（例）
- duckdb
- psutil
- requests
- streamlit
- openai

インストール例（仮想環境推奨）:
1. リポジトリをクローン
   - git clone <リポジトリ URL>
2. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール（requirements.txt があればそれを使う）
   - pip install duckdb psutil requests streamlit openai

環境変数・設定
- 設定は環境変数またはプロジェクトルートの .env/.env.local から読み込まれます（自動ロード）。自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をセット。
- 主要な環境変数（Settings クラス参照）:

  - KABUSYS_ENV: 起動環境。development / paper_trading / live（デフォルト: development）
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
  - KABU_API_PASSWORD: kabuステーション API 用（必須）
  - KABU_API_BASE_URL: デフォルト http://localhost:18080/kabusapi
  - OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合に必須）
  - PAPER_FILL_MODE: paper_trading の fill 動作（instant|partial|never|reject、デフォルト: instant）
  - PAPER_TRADING_SQLITE_PATH: PaperTrading 用 SQLite（デフォルト: data/paper_trading.db）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
  - PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH: kill.flag（デフォルト: data/kill.flag）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト: 60）
  - LOG_LEVEL: ログレベル（DEBUG/INFO/...、デフォルト: INFO）

注意点：
- Paper Trading（KABUSYS_ENV=paper_trading）は broker クライアントが Mock を使い、データは data/paper_trading.db に記録され、本番 DB と分離されます。
- .env.example を参照して必要なキーを設定してください。必須環境変数が未設定の場合、Settings は ValueError を投げます。

使い方（主要スクリプト）
------------------------

1) 監視ループ起動（Monitoring）
- 説明: SystemMonitor を定期実行して system_status / risk_logs などに書き込みます。プロセス優先度を "high" に設定します。
- 起動:
  - python -m kabusys.run_monitoring
- 環境変数:
  - MONITOR_POLL_INTERVAL でポーリング間隔（秒）を上書き可能（デフォルト 60）。
  - 監視は KABUSYS_ENV に関わらず sqlite_path の本番設定を使用します（監視ログは本番 DB を想定）。

2) Execution 起動（注文実行）
- 説明: ブローカークライアントを生成して ExecutionEngine を起動します。paper_trading では MockBrokerClient を使用し、Paper DB に記録されます。
- 起動:
  - python -m kabusys.run_execution
- 注意:
  - KABUSYS_ENV=paper_trading にすると PAPER_TRADING_SQLITE_PATH が使用されます。
  - 起動時に PID ファイル（Settings.pid_file_path）を書き、停止時に削除する動作があります。

3) Streamlit ダッシュボード
- 説明: 監視 DB を読み取り専用で表示するダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

4) Paper Trading 検証レポート
- 説明: paper_trading DB を集計して稼働率・注文成功率・レイテンシ等を表示
- 起動例:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db オプションで DB パスを指定可能（環境変数 PAPER_TRADING_SQLITE_PATH より優先）

5) AI 機能（ニュースセンチメント / レジーム判定）
- これらはライブラリ関数として利用できます（DuckDB 接続と target_date を渡す）。
- 例（Python スクリプト内）:
  - from openai import OpenAI  # SDK と API キーを設定した上で
  - import duckdb
  - from kabusys.ai.news_nlp import score_news
  - conn = duckdb.connect("data/kabusys.duckdb")
  - score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
- OpenAI API キーが未設定のまま呼ぶと ValueError が発生します。API 呼び出しはリトライ・フェイルセーフ実装あり（失敗時はスコアをスキップまたはフォールバック）。

運用上のポイント
----------------
- プロセス優先度: run_monitoring / run_execution は起動直後に set_process_priority("high") を試行します。権限不足などで失敗した場合はログに警告が出ますが処理は継続します。
- Kill Switch: RiskMonitor が閾値超過 (ドローダウンやポジション上限) を検出すると kill.flag を書き、ExecutionEngine を停止させる運用が組み込まれています（フラグの存在チェックは ExecutionEngine 側で行われます）。
- DB マイグレーション: monitoring_db.init_monitoring_db() は起動時に冪等でテーブル作成と簡易マイグレーション（カラム追加など）を行います。
- Paper Trading 分離: Paper 環境は sqlite ファイルを分けているので本番 DB を上書きすることはありません（ただし設定ミスに注意）。

ディレクトリ構成
----------------
（主要ファイルのみ抜粋）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数 / Settings
    - run_monitoring.py         — SystemMonitor ポーリングループ起動スクリプト
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - execution/
      - order_manager.py
      - reconciler.py
      - order_repository.py
      - execution_engine.py
      - broker_factory.py
      - ...
    - monitoring/
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
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

追加情報 / ベストプラクティス
----------------------------
- ログレベルや API キーなどの機密値は .env ファイルまたは CI/CD のシークレットで管理してください。Settings._require は必須変数が未設定だと起動時に例外を投げます。
- OpenAI を利用する処理はトークン数やコストに注意してください。news_nlp は入力文字数を制限するロジックを備えていますが、運用時はバッチサイズやトークン上限を調整してください。
- DuckDB / SQLite のファイルパスは Settings で変更可能です。バックアップやファイルローテーション運用を検討してください。
- 実運用では systemd や supervisor 等でプロセス管理（自動再起動、ログ管理、リソース制限）を行うことを推奨します。

ライセンス / 貢献
-----------------
- 本 README はコードベースの説明であり、実装の詳細や追加のライセンス情報はリポジトリの LICENSE を参照してください。
- バグ報告・機能提案は Issue を立ててください。

以上が本コードベースの概要・セットアップ・使い方です。必要であればサンプル .env.example のテンプレートや systemd ユニット例、よくあるトラブルシュート（DB 破損、OpenAI エラーへの対処）なども追記します。どの情報を追加希望か教えてください。