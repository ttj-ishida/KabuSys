# KabuSys — README (日本語)

概要
----
KabuSys は日本株自動売買向けの軽量なバックエンドライブラリ群です。  
戦略（ファクター計算・特徴量探索）、ポートフォリオ構築、注文発行/管理、実行エンジン、監視・アラート、研究用ユーティリティ、そしてニュース解析（OpenAI）連携を含みます。  
設計方針としては、安全性（クラッシュ耐性・リコンシリエーション）、テスト容易性（paper trading モードの完全分離）、および DuckDB/SQLite を用いたローカルデータ操作に重きを置いています。

主な機能
--------
- 研究（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB を使用）
  - 将来リターン計算、IC（Information Coefficient）計算、統計サマリー
- ポートフォリオ構築（portfolio）
  - 候補選定、等重・スコア加重、ポジション決定（リスクベース含む）
  - セクター上限適用、レジーム乗数
- 実行（execution）
  - Order 管理（DB 永続化、状態遷移、送信/同期）
  - ブローカー抽象化（本番 / Mock に対応）、リコンシリエーション（再起動時自動復旧）
  - リスク管理（ポジション比率、投下上限等）
- 監視（monitoring）
  - CPU / メモリ / ディスク、プロセス生存、データ鮮度監視
  - 注文滞留・約定異常検出、ドローダウン・ポジション数監視
  - Kill switch（フラグファイルによる ExecutionEngine 停止）、LINE 通知によるアラート
  - Streamlit ダッシュボード（監視データの可視化）
- AI（ai）
  - ニュース記事を OpenAI（gpt-4o-mini 等）でセンチメント評価して ai_scores に保存
  - マクロニュース + ETF MA200 を組み合わせた市場レジーム判定
- ツール
  - Paper Trading 検証レポート生成スクリプト（期間指定可）

前提・依存
-----------
主な依存パッケージ（例）
- Python 3.8+
- duckdb
- psutil
- requests
- openai
- streamlit (ダッシュボード利用時)
※ 実際のプロジェクトでは requirements.txt / pyproject.toml を参照してください。

セットアップ手順
----------------
1. リポジトリをクローン / ソースを配置
2. 仮想環境を作成して依存をインストール
   - 例:
     - python -m venv .venv
     - source .venv/bin/activate (Windows: .venv\Scripts\activate)
     - pip install duckdb psutil requests openai streamlit
3. 環境変数を設定（.env / .env.local をプロジェクトルートに配置可能）
   - 主要な環境変数（必須／推奨）
     - JQUANTS_REFRESH_TOKEN — J-Quants API（必須）
     - KABU_API_PASSWORD — kabuステーション API パスワード（必須）
     - OPENAI_API_KEY — OpenAI API キー（ai 機能を使う場合）
     - KABUSYS_ENV — 実行環境: development / paper_trading / live（デフォルト: development）
     - LOG_LEVEL — ログレベル（例: INFO）
     - SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
     - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH — paper trading 用 SQLite（paper_trading 環境時に利用）
     - PAPER_FILL_MODE — paper trading の fill 動作（instant|partial|never|reject、デフォルト: instant）
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID — LINE 通知用
     - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START — プロセス管理・停止フラグ
   - 自動読み込み:
     - プロジェクトルートにある `.env` / `.env.local` は Settings モジュールで自動読み込みされます（OS 環境変数優先）。
     - 自動ロードを無効にする場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
4. データディレクトリ作成
   - data/ 以下（デフォルト DB パス）を作成しておくと便利です。

基本的な使い方
--------------

- 実行エンジン（ExecutionEngine）を起動する
  - production / development / paper_trading に応じて KABUSYS_ENV を設定します。
  - paper_trading の場合、MockBrokerClient が使われ、デフォルトで data/paper_trading.db に記録され、本番 DB と分離されます。
  - 起動例:
    - KABUSYS_ENV=development python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 実行時、プロセス優先度を "high" に設定します（プラットフォームに依存して可能な範囲で）。

- 監視ループ（SystemMonitor）を起動する
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト: 60）
  - 起動例:
    - python -m kabusys.run_monitoring
  - 監視は settings の sqlite_path（本番 DB）を常に参照します（環境にかかわらず）。

- Streamlit ダッシュボード
  - 起動例:
    - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - read-only で SQLite を開き、ダッシュボードを表示します。

- Paper Trading 検証レポート
  - 起動例:
    - python -m kabusys.tools.paper_verification_report
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - デフォルト DB: data/paper_trading.db（--db オプションで上書き可能）

- AI（ニュースセンチメント / レジーム判定）
  - OpenAI API キーが必要（OPENAI_API_KEY 環境変数または関数引数）。
  - ニューススコア付与:
    - kabusys.ai.score_news(conn, target_date, api_key=...)
  - レジーム判定:
    - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=...)

運用上の注意
------------
- Paper trading は本番データベースと完全に分離するよう設計されています（Settings.paper_sqlite_path を使用）。
- run_monitoring は KABUSYS_ENV に依らず本番 sqlite_path を参照するため、監視は常に本番 DB を見る点に注意してください。
- モジュールの多くが DB スキーマ（prices_daily、raw_financials、raw_news、ai_scores、market_regime 等）を前提に動作します。研究・AI 機能を利用する際には DuckDB のテーブルを準備してください。
- プロセス優先度・CPU affinity 設定は psutil を経由して行います。権限や OS により設定が適用されない場合があります（警告ログが出ます）。
- kill.flag による停止は KillSwitch によるチェックで行われます。ExecutionEngine 側は起動時のフラグクリア設定（Settings.kill_flag_clear_on_start）を利用できます。

主要ファイルとディレクトリ構成
----------------------------
（抜粋・説明付き）

- src/kabusys/
  - __init__.py — パッケージ定義、バージョン
  - config.py — Settings クラス（環境変数/.env 読み込み、各種パス・閾値の取得）
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — Paper Trading 検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュースを OpenAI でスコアリングして ai_scores に保存
    - regime_detector.py — マクロ+ETF MA200 で市場レジーム判定し market_regime に書込
  - research/
    - factor_research.py — モメンタム / ボラティリティ / バリュー算出
    - feature_exploration.py — 将来リターン、IC、統計サマリー等
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・単元丸め・資金配分
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - execution/
    - order_manager.py — 発注ワークフロー（作成・送信・同期）
    - reconciler.py — 起動時のリコンシリエーション
    - ...（ブローカー抽象やリポジトリ等）
  - monitoring/
    - monitoring_db.py — SQLite スキーマ初期化 + 永続化 API
    - system_monitor.py — CPU/メモリ/ディスク/プロセス/データ鮮度監視
    - trade_monitor.py — 注文滞留 / 約定異常 監視
    - risk_monitor.py — ドローダウン / ポジション上限監視
    - kill_switch.py — kill.flag 管理
    - alert_manager.py — LINE 通知ラッパー
    - monitoring_engine.py — 複数モニタの統合ループ
    - streamlit_dashboard.py — Streamlit ベースの監視ダッシュボード
  - utils/
    - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

サンプルコマンド
----------------
- 実行エンジン（デフォルト環境）
  - python -m kabusys.run_execution
- 実行エンジン（Paper Trading）
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視ループ（ポーリング間隔 30 秒）
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- Streamlit ダッシュボード
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper Trading 検証レポート（期間指定）
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

付録：よくある環境変数（早見）
--------------------------------
- KABUSYS_ENV=development|paper_trading|live
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI機能利用時)
- SQLITE_PATH (data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (data/paper_trading.db)
- DUCKDB_PATH (data/kabusys.duckdb)
- MONITOR_POLL_INTERVAL (run_monitoring 用、秒)
- PAPER_FILL_MODE (instant|partial|never|reject)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID (アラート送信)

最後に
------
この README はコードベースの主要な振る舞いと実行方法をまとめたものです。実際の運用やデプロイ時はログ設定、権限、バックアップ、監視ポリシー等を適切に整備してください。必要であれば、用途に応じた例（systemd ユニット、Dockerfile、CI ワークフロー）も追加で作成できます。質問や追加要望があればお知らせください。