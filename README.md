KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買 / 研究 / 監視を目的とした小規模なPythonアプリケーション群です。
主な機能は以下のとおりです。

- 実行エンジン (ExecutionEngine) による注文発行・リスク管理・再同期（reconciliation）
- 監視サブシステム（System / Trade / Risk）による稼働・注文・ドローダウン監視とアラート
- Paper Trading 用の分離されたDBでの検証モード
- ニュースを用いたAI（OpenAI）によるセンチメントスコア算出（ai.news_nlp）
- レジーム判定（ai.regime_detector）
- 研究用ファクター計算・特徴量解析モジュール（research）
- ポートフォリオ構築ユーティリティ（portfolio）
- 運用監視用の Streamlit ダッシュボード と 検証レポート生成ツール

主要な設計方針:
- DuckDB を用いた時系列データ処理、SQLite を用いた軽量永続化
- 環境ごとの DB 分離（paper_trading は専用 SQLite）
- OpenAI 呼び出しはフェイルセーフ設計（失敗時はフォールバック）
- .env ファイル自動ロード（必要に応じて無効化可能）

機能一覧
--------
- 実行 (src/kabusys/run_execution.py)
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading DB（data/paper_trading.db 等）に記録
  - リコンシリエーション（再起動後の注文・ポジション同期）
  - リスクマネージャ／オーダーマネージャ統合

- 監視 (src/kabusys/run_monitoring.py, monitoring/*)
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度チェック
  - TradeMonitor: 滞留注文・約定価格異常チェック
  - RiskMonitor: ドローダウン・ポジション上限チェック
  - KillSwitch: 条件成立で data/kill.flag を書き込み ExecutionEngine 停止シグナルを送信
  - AlertManager: LINE Messaging API による通知（オプション）
  - Streamlit ダッシュボード (monitoring/streamlit_dashboard.py)

- 研究 (research/*)
  - ファクター計算（momentum / volatility / value）
  - 将来リターン / IC / 統計サマリ等

- AI（ai/*）
  - news_nlp: ニュース記事から銘柄ごとにセンチメントを算出して ai_scores テーブルへ書き込み（OpenAI）
  - regime_detector: ETF とマクロニュースを組み合わせた日次レジーム判定

- ポートフォリオ構築（portfolio/*）
  - 候補選定 / 重み計算 / セクター調整 / ポジションサイズ計算

- ツール
  - paper_verification_report: Paper Trading DB から検証レポート生成（運用可否判定）

セットアップ手順
----------------
1. リポジトリをクローン
   - 例: git clone <repo-url>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要なパッケージをインストール
   - 本リポジトリに requirements.txt があると想定する場合:
     - pip install -r requirements.txt
   - 主要依存（最小例）:
     - pip install duckdb psutil requests streamlit openai

   ※ 実際の requirements はプロジェクトに合わせて調整してください。

4. 環境変数設定
   - プロジェクトルートに .env または .env.local を配置すると自動で読み込まれます（Settings モジュール）。
   - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
   - 代表的な環境変数:
     - KABUSYS_ENV: development | paper_trading | live  (デフォルト: development)
     - OPENAI_API_KEY: OpenAI API キー（ai モジュール利用時必須）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
     - PAPER_FILL_MODE: instant | partial | never | reject （paper_trading の約定動作）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: AlertManager 用
     - MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60）

5. データディレクトリ
   - デフォルトで data/ 配下に各種DB・フラグファイル・PIDが置かれます。必要に応じて作成してください:
     - data/monitoring.db (監視 SQLite)
     - data/paper_trading.db (paper_trading 用 SQLite)
     - data/kabusys.duckdb (DuckDB)
     - data/execution.pid, data/kill.flag, data/stop_requested.flag

使い方
------
- 監視プロセス起動
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（秒、デフォルト 60）
  - 監視は常に本番 SQLITE_PATH（Settings.sqlite_path）を使用（KABUSYS_ENV に依存しない）
  - 実行:
    - python -m kabusys.run_monitoring
  - 停止: data/stop_requested.flag を作成するとループが終了します（または Ctrl+C）

- 実行エンジン起動（注文処理）
  - paper_trading モード:
    - KABUSYS_ENV=paper_trading を設定すると MockBrokerClient を使用し、paper_trading 用 SQLite に記録されます（本番 DB と分離）
  - 実行:
    - python -m kabusys.run_execution
  - 実行中に data/stop_requested.flag を作成すると実行エンジンを停止します
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）
  - 起動時に KILL フラグ（data/kill.flag）があれば起動を中止します（安全機構）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パスは --db オプションまたは環境変数 PAPER_TRADING_SQLITE_PATH で指定可能

- Streamlit ダッシュボード
  - 起動方法（例）:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - ダッシュボードは監視DBを読み取り専用で開きます。監視プロセスが先に DB を初期化している必要があります。

- AI モジュール（news_nlp / regime_detector）
  - OPENAI_API_KEY が必要（引数で明示することも可能）
  - news_nlp.score_news は DuckDB 接続を受け取り、ai_scores テーブルへ書き込みます
  - regime_detector.score_regime は prices_daily と raw_news に基づき market_regime テーブルへ書き込みます

注意事項 / 運用上のポイント
----------------------------
- Settings は .env 自動ロードを行います。OS 環境変数が優先され、.env.local は上書きされます。
- PAPER_TRADING モードでは本番の SQLite を使わないよう設計されています。必ず PAPER_TRADING_SQLITE_PATH を確認してください。
- OpenAI 呼び出しはリトライやフォールバックが実装されていますが、API キー未設定では例外が発生します（明示的にチェックされます）。
- process_priority（utils.process_priority.set_process_priority）が起動時に呼ばれ、可能であればプロセス優先度を上げます。権限やOSにより失敗する可能性がありますが安全にスキップされます。
- kill.flag / stop_requested.flag / execution.pid 等のフラグ・ファイルは data/ 以下にあります。運用時にこれらを用いてプロセス制御を行ってください。

ディレクトリ構成（抜粋）
-----------------------
src/kabusys/
- __init__.py
- config.py                     — 環境/設定管理（.env 自動ロード / Settings）
- run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py              — ExecutionEngine 起動スクリプト

- ai/
  - news_nlp.py                  — ニュース NLP スコアリング（OpenAI）
  - regime_detector.py           — 市場レジーム判定（ETF + マクロニュース）

- monitoring/
  - monitoring_db.py             — monitoring 用 SQLite 永続化層
  - system_monitor.py            — システム / データ鮮度監視
  - trade_monitor.py             — 注文滞留・約定異常監視
  - risk_monitor.py              — ドローダウン / ポジション上限監視
  - kill_switch.py               — Kill Switch（flag ファイル書込）
  - alert_manager.py             — LINE Push 通知
  - monitoring_engine.py         — 各モニタを束ねるエンジン
  - streamlit_dashboard.py       — Streamlit ダッシュボード

- execution/
  - order_manager.py             — 注文管理
  - reconciler.py                — 起動時リコンシリエーション
  - （その他 broker / engine / order_repository 等）

- portfolio/
  - portfolio_builder.py         — 候補選定・重み計算
  - position_sizing.py           — 株数決定・スケーリング
  - risk_adjustment.py           — セクターキャップ・レジーム乗数

- research/
  - factor_research.py           — ファクター計算（momentum/volatility/value）
  - feature_exploration.py       — IC / forward returns / 統計サマリ

- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成

- utils/
  - process_priority.py          — プロセス優先度 / CPU affinity 設定ユーティリティ

ライセンス / 貢献
-----------------
コードベースのライセンスや貢献ガイドラインはリポジトリルートの LICENSE / CONTRIBUTING を参照してください（存在しない場合はプロジェクト所有者に確認してください）。

サポート / 問い合わせ
---------------------
不具合や質問はリポジトリの Issues を使用してください。利用時のログや再現手順、環境変数の設定情報を添えていただくと助かります。

以上。必要であれば README に含める具体的な .env.example のテンプレートや systemd ユニット例、運用手順（ローテーション・バックアップ）も追記できます。どの情報を追加しますか？