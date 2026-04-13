KabuSys — 日本株自動売買システム
==============================

本ドキュメントは、ソースツリー（src/kabusys 以下）に含まれる主要モジュールを対象とした README です。  
このリポジトリは自動売買エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI 補助（ニュース NLP / レジーム判定）などのコンポーネント群で構成されています。

概要
----
KabuSys は日本株の自動売買に関する各種機能を含む Python ベースのシステムです。  
主な目的は以下です：

- シグナルを元に発注を行う ExecutionEngine（本番 / Paper Trading 切替可能）
- 実行系の状態・注文・リスクを監視する Monitoring（ログ・アラート・kill switch）
- ポートフォリオ構築（候補選定・重み付け・株数決定）
- リサーチ（ファクター計算、IC 等）
- ニュースを LLM でスコアリングして AI スコアを生成するモジュール
- 起動・運用に便利なツール（Paper Trading 検証レポート、Streamlit ダッシュボード 等）

主な機能一覧
--------------
- Execution
  - ExecutionEngine 起動（run_execution.py）
  - ブローカークライアントの抽象化（実際のブローカー or Mock）
  - 発注管理（OrderManager / OrderRepository / Reconciler）
  - リスク管理（RiskManager）
- Monitoring
  - 定期ポーリングによる監視ループ（run_monitoring.py）
  - SystemMonitor（CPU/メモリ/ディスク/プロセス/データ鮮度）
  - TradeMonitor（滞留注文 / 約定異常）
  - RiskMonitor（ドローダウン／ポジション上限監視）
  - KillSwitch（フラグファイルで ExecutionEngine 停止指示）
  - AlertManager（LINE Push による通知）
  - Streamlit ダッシュボード（監視データの可視化）
- Portfolio
  - 銘柄候補選定（スコア順）
  - 等金額／スコア加重の重み計算
  - セクター上限適用、レジーム乗数
  - ポジションサイズ算出（リスクベース・単元丸め・集約キャップ）
- Research
  - Momentum / Volatility / Value ファクター計算（DuckDB SQL + Python）
  - 将来リターン、IC（Spearman）や統計サマリー
- AI
  - ニュースを LLM（OpenAI）でスコアリングし ai_scores に書き込む（news_nlp）
  - マクロニュース + ETF MA200 乖離で市場レジーム判定（regime_detector）
- ツール
  - paper_verification_report: Paper Trading DB を解析して検証レポートを出力
  - streamlit_dashboard: 監視 DB を可視化（streamlit）

セットアップ手順
----------------
1. リポジトリをクローン／チェックアウト
   - git clone … && cd your-repo

2. Python 環境
   - Python 3.10+ を推奨
   - 仮想環境の作成（例）
     - python -m venv .venv
     - source .venv/bin/activate（Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - 必要な主なパッケージ（一例）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit (ダッシュボード利用時)
   - 例:
     - pip install duckdb psutil requests openai streamlit
   - （プロジェクトに requirements.txt がある場合はそちらを使用してください）

4. 環境変数 / .env
   - プロジェクトルート (.git または pyproject.toml が基準) に .env / .env.local を置くと自動で読み込まれます。
   - 自動読み込みを無効にする場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
   - 重要な環境変数（代表例）:
     - JQUANTS_REFRESH_TOKEN — J-Quants API 用
     - KABU_API_PASSWORD — kabuステーション API 用パスワード
     - OPENAI_API_KEY — OpenAI 呼び出しに必要（AI 機能）
     - KABUSYS_ENV — 起動環境: development | paper_trading | live（デフォルト: development）
     - PAPER_FILL_MODE — Paper Trading の約定モード（instant / partial / never / reject）
     - PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
     - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH — PID／kill.flag のパス
     - LOG_LEVEL — ログレベル（DEBUG, INFO, ...）
   - .env の書式は一般的な KEY=VALUE 形式に対応（コメントやクォートも扱います）。

使い方
-----
起動スクリプト（例）

- 監視ループを起動（Monitoring）
  - python -m kabusys.run_monitoring
  - 説明:
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒単位で上書き可能（デフォルト 60 秒）
    - run_monitoring は Monitoring 用の SQLite（settings.sqlite_path）を使用します（KABUSYS_ENV に依らず本番 sqlite_path を参照します）
    - 起動時にプロセス優先度を "high" に設定しようとします（権限によってはスキップ）

- 実行エンジンを起動（Execution）
  - python -m kabusys.run_execution
  - 説明:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し、Paper Trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録します（本番 DB と完全に分離）
    - 起動時にプロセス優先度を "high" に設定します
    - エンジンは EngineConfig(target_date=date.today()) でセッション実行

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - --db /path/to/paper_trading.db

- Streamlit 監視ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - DB は読み取り専用で開かれます（?mode=ro）。MonitoringEngine を先に起動してデータを用意してください。

運用上のポイント / 注意点
-----------------------
- モード切替:
  - KABUSYS_ENV により挙動が変わります（development / paper_trading / live）。paper_trading はブローカー呼び出しをモック化し DB を分離します。
- kill.flag / PID:
  - ExecutionEngine は起動時に PID を書き、kill.flag ファイル存在を監視して安全停止を行います。KillSwitch は一定条件（ドローダウン等）で kill.flag を書きます。起動前に必要に応じて kill.flag を削除してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db() は冪等でテーブル・インデックスを作成し、既存 DB に対して必要なカラム追加も行います（簡易マイグレーション処理あり）。
- OpenAI（AI 機能）:
  - OPENAI_API_KEY が必要です。API 呼び出しはリトライ / バックオフを実装していますが、コスト・レート制限に注意してください。
- ユーザー通知:
  - LINE 通知は LINE_CHANNEL_ACCESS_TOKEN と LINE_USER_ID が必要。設定なければログのみ。

主要ファイル / ディレクトリ構成
------------------------------
以下は src/kabusys 配下の主要モジュールと説明です（抜粋）。

- src/kabusys/
  - __init__.py — パッケージ定義
  - config.py — 環境変数 / 設定読み込み・Settings クラス
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
  - run_execution.py — ExecutionEngine 起動スクリプト

- monitoring/（監視）
  - monitoring_db.py — SQLite による永続層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態・データ鮮度監視
  - trade_monitor.py — 注文滞留・約定異常監視
  - risk_monitor.py — ドローダウン／ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - alert_manager.py — LINE への通知送信
  - monitoring_engine.py — 各 Monitor を束ねるループ
  - streamlit_dashboard.py — Streamlit を使ったダッシュボード

- execution/（発注）
  - order_manager.py — 発注ワークフロー（作成 → 送信 → 同期）
  - order_repository.py — SQLite ベースの注文永続化（省略ファイル末尾）
  - reconciler.py — 起動時のリコンシリエーション（ブローカー同期）
  - execution_engine.py, broker_factory.py, broker_api.py ...（実行周りの実装）

- portfolio/（ポートフォリオ構築）
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数決定・単元丸め・集約キャップ
  - risk_adjustment.py — セクター上限・レジーム乗数

- research/（リサーチ）
  - factor_research.py — Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計サマリー

- ai/（LLM を使う処理）
  - news_nlp.py — raw_news を LLM でセンチメント評価して ai_scores に書き込む
  - regime_detector.py — マクロニュース + ETF MA200 で日次レジーム判定

- tools/
  - paper_verification_report.py — Paper Trading DB の検証レポート出力

環境変数（主なもの）
-------------------
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- SQLITE_PATH: 監視 DB（default: data/monitoring.db）
- DUCKDB_PATH: DuckDB ファイル（default: data/kabusys.duckdb）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 DB（default: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定挙動）
- JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須の場合あり）
- KABU_API_PASSWORD: kabu ステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用
- PID_FILE_PATH: PID ファイルパス（default: data/execution.pid）
- KILL_FLAG_PATH: kill.flag のパス（default: data/kill.flag）
- MONITOR_POLL_INTERVAL: Monitoring のポーリング秒数（run_monitoring で利用）
- LOG_LEVEL: ログレベル（INFO 等）

開発者向けメモ
---------------
- .env の自動読み込み:
  - config.py はプロジェクトルートを自動検出し、.env/.env.local を読み込みます（既存 OS 環境変数は保護されます）。テスト等で無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- DuckDB を使ったリサーチ:
  - research モジュールは DuckDB 接続（prices_daily, raw_financials 等テーブル）を前提としています。データ準備は別途 ETL パイプラインで行う想定です。
- ロギング/例外ハンドリング:
  - 主要ループは基本的に例外を捕捉して継続する設計です（MonitoringEngine.run など）。致命的な失敗はログに残るよう設計されています。

ライセンス / 貢献
-----------------
—（ここにプロジェクトのライセンスや貢献方法を追記してください）—

最後に
-------
この README はコード内の docstring・コメントを元に要点をまとめたものです。実運用前に .env の設定、DB のバックアップ、OpenAI/API キーのセキュアな管理、監視・アラートの動作確認を十分に行ってください。疑問点や実装の細部については該当モジュール（上記ファイル）を参照してください。