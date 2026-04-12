KabuSys — 日本株自動売買システム
================================

このリポジトリは日本株向けの自動売買 / 研究 / 監視ユーティリティ群を集めた Python パッケージです。
README はコードベース（src/kabusys 以下）の公開 API と実行方法、設定、ディレクトリ構成をまとめたものです。

要約
----
- 言語: Python（3.10 以上を推奨）
- 主な依存: duckdb, psutil, requests, openai, streamlit（用途により optional）
- データ永続化:
  - DuckDB: 時系列価格やファクターデータ（デフォルト data/kabusys.duckdb）
  - SQLite: 監視ログ（data/monitoring.db）、Paper Trading 用 DB（data/paper_trading.db）

主な機能
--------
- 実行エンジン起動（run_execution.py）
  - ブローカークライアント生成（paper_trading 環境では MockBroker を使用）
  - 注文管理、リスク制御、リコンシリエーション（再起動時の自動復旧）
  - ExecutionEngine のセッション実行
- 監視（run_monitoring.py / monitoring パッケージ）
  - システム状態監視（CPU / メモリ / ディスク / プロセス死活）
  - 注文滞留・約定異常検出
  - ドローダウン・ポジション過多の監視と kill.flag による停止指示
  - LINE へアラート送信（AlertManager）
  - streamlit による監視ダッシュボード
- Paper Trading 検証レポート生成ツール（tools/paper_verification_report.py）
  - 稼働率、注文成功率、送信率、レイテンシ（P95）などを集計して出力
- ポートフォリオ構築（portfolio パッケージ）
  - 候補選定、重み計算（等金額・スコア加重）
  - セクター上限適用、レジーム乗数、株数算出（単元丸め・aggregate cap）
- 研究（research パッケージ）
  - モメンタム / バリュー / ボラティリティ等のファクター計算（DuckDB ベース）
  - 将来リターン・IC 計算、特徴量統計
- AI 補助（ai パッケージ）
  - ニュースを LLM（OpenAI）でセンチメント化して ai_scores に書込む
  - 市場レジーム判定（ma200 とマクロセンチメントの合成）
  - (OpenAI API キー必要)

セットアップ
-----------
前提:
- Python 3.10+
- 仮想環境の利用を推奨

例（venv を使う）:
1. 仮想環境作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（用途に応じて変更）
   - pip install duckdb psutil requests openai streamlit

   ※ パッケージ一覧が requirements.txt にある場合はそれを使ってください。
   ※ AI 機能を使う場合は openai パッケージ、ダッシュボードは streamlit が必要です。

3. パッケージを開発インストール（任意）
   - pip install -e .

設定（環境変数 / .env）
---------------------
自動で .env/.env.local をプロジェクトルートから読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

主な環境変数とデフォルト:
- KABUSYS_ENV: 起動環境。valid: development | paper_trading | live。デフォルト: development
- JQUANTS_REFRESH_TOKEN: （必須）J-Quants 用トークン
- KABU_API_PASSWORD: （必須）kabuステーション API パスワード
- OPENAI_API_KEY: OpenAI を利用する場合に必要
- DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE: Paper Trading の約定挙動（instant|partial|never|reject、デフォルト instant）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（デフォルト data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

実行方法 / 使い方
-----------------

1) 監視ループを起動（Monitoring）
- コマンド:
  - python -m kabusys.run_monitoring
- 仕様:
  - MONITOR_POLL_INTERVAL（秒）でポーリング。デフォルト 60 秒。
  - 監視は常に本番用の sqlite_path（SQLITE_PATH）を使用します（環境にかかわらず）。
  - 実行開始時にプロセスを high 優先度へ設定しようとします（psutil 必須）。
  - monitoring DB の初期化（テーブル作成・マイグレーション）を行います。

2) 実行エンジンを起動（ExecutionEngine）
- コマンド:
  - python -m kabusys.run_execution
- 仕様:
  - KABUSYS_ENV=paper_trading のときは paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBroker を使用し、本番 DB と完全分離されます。
  - Execution 起動時にプロセス優先度を high に設定します。
  - duckdb 接続を受けてファクター等を参照します。
  - PID ファイルのパス: Settings.pid_file_path（デフォルト data/execution.pid）

3) Streamlit ダッシュボード
- コマンド:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- 仕様:
  - 監視 SQLite を読み取り専用で開いてダッシュボードを表示します。
  - MonitoringEngine を動かしておく必要があります（DB が存在すること）。

4) Paper Trading 検証レポート
- コマンド:
  - python -m kabusys.tools.paper_verification_report
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - オプション: --db PATH で DB ファイルを指定（デフォルト env または data/paper_trading.db）
- 出力:
  - 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、P95 レイテンシなどのサマリと PASS/FAIL 判定

5) AI 関連（ニュース NLP / レジーム判定）
- 関数 API:
  - from kabusys.ai import score_news
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - 市場レジーム: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意:
  - OPENAI_API_KEY が必要（api_key 引数でも指定可）。
  - ネットワークエラーや API の一時失敗はリトライ・フォールバック処理がありますが、API キー未設定だと例外になります。

プロセス管理 / 停止
------------------
- PID ファイル（Settings.pid_file_path）を利用して ExecutionEngine の生存を監視します。
- KillSwitch は data/kill.flag を書き込み、ExecutionEngine に停止を促します（存在確認・削除機能あり）。
- Settings.kill_flag_clear_on_start を使い、起動時に既存の kill.flag をクリアする挙動が利用できます（実装されている設定項目です。起動スクリプト側で利用されます）。

データベース / マイグレーション
------------------------------
- monitoring_db.init_monitoring_db(conn) は冪等でテーブル・インデックスを作成します。起動時に自動実行されます。
- 既存テーブルにカラムがない場合の簡単なマイグレーション（例: dashboard.peak_value, trade_logs.latency_ms）を行います。

ディレクトリ構成
----------------
（主なファイルのみ抜粋）

src/
  kabusys/
    __init__.py
    config.py                       — 環境変数 / Settings 管理
    run_monitoring.py               — Monitoring ポーリングループ起動
    run_execution.py                — ExecutionEngine 起動スクリプト

    ai/
      __init__.py
      news_nlp.py                   — ニュースの LLM スコアリング
      regime_detector.py            — 市場レジーム判定

    monitoring/
      __init__.py
      monitoring_db.py              — SQLite 監視 DB レイヤ
      system_monitor.py             — システム / データ鮮度監視
      trade_monitor.py              — 注文滞留 / 約定異常検出
      risk_monitor.py               — ドローダウン / ポジション上限監視
      kill_switch.py                — kill.flag 管理
      alert_manager.py              — LINE 送信ラッパ
      monitoring_engine.py          — 各 Monitor の統合ループ
      streamlit_dashboard.py        — Streamlit ダッシュボード

    execution/
      order_manager.py              — 注文管理（Order State Machine 外向け）
      reconciler.py                 — 再起動時のリコンシリエーション
      (その他 broker_factory, order_repository 等)

    portfolio/
      portfolio_builder.py          — 候補選定 / 重み
      position_sizing.py            — 株数算出・aggregate cap
      risk_adjustment.py            — セクター制限・レジーム乗数
      __init__.py

    research/
      factor_research.py            — ファクター計算 (momentum/value/volatility)
      feature_exploration.py        — IC / forward returns / 統計
      __init__.py

    tools/
      __init__.py
      paper_verification_report.py   — Paper Trading 検証レポート

    utils/
      __init__.py
      process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ

運用上の注意 / ベストプラクティス
--------------------------------
- KABUSYS_ENV を paper_trading にすると、発注や DB 書き込みが本番と分離されるため検証に便利です。
- AI 機能を利用する際は OPENAI_API_KEY を必ず設定してください。API コールは課金対象になります。
- run_monitoring は監視ログ（監視 DB）を使って運用状況を記録します。監視は常に SQLITE_PATH（デフォルト data/monitoring.db）を参照します。
- PID ファイル・kill.flag の扱いに注意してください。kill.flag は運用者が発火したら ExecutionEngine を安全に停止させるための仕組みです。
- streamlit の読み込みは DB を読み取り専用で開きます。MonitoringEngine を稼働させて DB を作成／更新しておく必要があります。

貢献 / 開発
------------
- フォーク → ブランチ作成 → プルリクエスト
- テストや CI を整備し、特に DB マイグレーション / AI 呼び出し部は外部依存があるためモックを用いた単体テストを推奨します。

ライセンス
----------
- この README ではライセンス情報を記載していません。リポジトリのトップレベルで LICENSE を確認してください。

補足（よく使うコマンド）
-----------------------
- 監視起動:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- Paper レポート:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- Streamlit:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

必要な追加情報や README の改善点があれば教えてください。実行スクリプトの挙動や環境変数のサンプル .env テンプレートも作成できます。