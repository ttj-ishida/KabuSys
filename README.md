KabuSys — 日本株自動売買システム
==============================

このリポジトリは日本株自動売買システム「KabuSys」のコアライブラリと運用用スクリプト群を含みます。  
設計は以下を念頭に置いています：安全性（起動時のリコンシリエーション・フェイルセーフ）、監視／アラート機能、ペーパートレードと本番の明確な分離、研究用ファクター計算・解析、LLM を用いたニュースセンチメント評価。

以下は本プロジェクトの概要、機能一覧、セットアップ手順、基本的な使い方、ディレクトリ構成です。

プロジェクト概要
----------------
- 言語: Python（3.10 以上推奨）
- 目的: 日本株の自動売買エンジンと、その周辺（監視、レポート、リサーチ、AI スコアリング）を提供する。
- DB:
  - SQLite: 監視ログ・オーダー履歴（monitoring.db / paper_trading.db）
  - DuckDB: 時系列データやファクター計算用（kabusys.duckdb）
- 主要モジュール:
  - execution: 発注エンジン・リコンシリエーション・リスク管理
  - monitoring: システム監視、アラート、ダッシュボード
  - portfolio: 候補選定・配分・ポジションサイズ計算
  - research: ファクター計算・探索
  - ai: ニュース NLP（OpenAI）・レジーム判定
  - tools: ペーパートレード検証レポート生成 等

主な機能一覧
-------------
- ExecutionEngine 起動スクリプト（run_execution.py）
  - 本番 / ペーパートレードの分離（KABUSYS_ENV）
  - Broker クライアント抽象化（Mock Broker / 実ブローカー）
  - リコンシリエーション（再起動時の注文同期）
  - リスク管理（ポジション上限・ドローダウン等）
- Monitoring（run_monitoring.py / MonitoringEngine）
  - システム状態（CPU/メモリ/ディスク）監視
  - 注文滞留・約定異常検出
  - リスクイベントログ、kill.flag による ExecutionEngine 停止シグナル
  - LINE によるプッシュ通知（AlertManager）
  - Streamlit ベースの監視ダッシュボード
- Portfolio construction
  - 候補選定、等金額/スコア加重、リスクベースのポジションサイズ計算
  - セクターキャップ、レジーム乗数の適用
- Research
  - Momentum/Volatility/Value 等のファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Information Coefficient）等の解析ユーティリティ
- AI モジュール
  - ニュース記事を OpenAI（gpt-4o-mini）でスコアリングし ai_scores に保存
  - マクロニュース + ETF (1321) MA200 乖離を組み合わせた市場レジーム判定
  - API 呼び出しはリトライやフェイルセーフを持つ実装
- ツール
  - Paper Trading 検証レポート生成スクリプト（tools/paper_verification_report.py）
  - DB スキーマ自動初期化／軽微マイグレーション（monitoring_db.init_monitoring_db）

セットアップ手順
----------------
1. Python 仮想環境の作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

2. 必要パッケージのインストール（例）
   - pip install duckdb psutil requests streamlit openai
   - （プロジェクトに requirements.txt がある場合は pip install -r requirements.txt）

3. データディレクトリ作成
   - mkdir -p data

4. 環境変数（.env）を用意
   - プロジェクトルートに .env または .env.local を置くと自動ロードされます（既存 OS 環境変数は保護）。
   - 主要な環境変数:
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: （必須: ファクター取得等で必要）
     - KABU_API_PASSWORD: （必須: 実ブローカー利用時）
     - OPENAI_API_KEY: （AI 機能利用時）
     - PAPER_FILL_MODE: instant | partial | never | reject（paper_trading 時の注文成行モード、デフォルト instant）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト data/paper_trading.db）
     - SQLITE_PATH: 監視 DB パス（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB パス（デフォルト data/kabusys.duckdb）
     - PID_FILE_PATH / KILL_FLAG_PATH / その他監視閾値（必要に応じて）
   - .env の書式は shell スタイル（コメント・引用・export）に対応。

5. DB 初期化
   - 監視 DB は run_monitoring/run_execution が起動時に init_monitoring_db を呼びます。手動で初期化したい場合は Python REPL で init_monitoring_db を呼び出してください。

使い方（代表的なコマンド・例）
------------------------------

- ExecutionEngine を起動（本番/ペーパーを切り替え）
  - ペーパートレード（MockBroker を使用、DB は data/paper_trading.db）
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  - 本番
    - KABUSYS_ENV=live python -m kabusys.run_execution

  注意: run_execution は起動時に set_process_priority("high") を呼びます（psutil の権限により失敗する場合は警告になります）。

- Monitoring（ポーリング監視）を起動
  - デフォルト 60 秒間隔:
    - python -m kabusys.run_monitoring
  - 短縮/延長:
    - MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
  - run_monitoring は環境にかかわらず本番 sqlite_path を監視 DB として使用します（監視は本番 DB にログを残す設計）。

- Streamlit ダッシュボード（監視可視化）
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - （--db オプションで読み込み DB を指定。デフォルトは data/monitoring.db）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB 指定:
    - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

- AI（ニューススコアリング / レジーム判定）をプログラムから利用
  - 例（Python REPL）
    - from kabusys.ai.news_nlp import score_news
    - import duckdb, datetime
    - conn = duckdb.connect("data/kabusys.duckdb")
    - score_news(conn, datetime.date(2026,4,1), api_key="YOUR_OPENAI_KEY")
  - 注意: OPENAI_API_KEY が未設定の場合、score_news/score_regime は ValueError を送出します。API 呼び出しはリトライ・フェイルセーフの実装がありますが、キーは必須です。

運用上の留意点
--------------
- KABUSYS_ENV の値
  - development: 開発向け（デフォルト）
  - paper_trading: ペーパートレード（DB と注文挙動を本番と分離）
  - live: 本番
- ペーパートレードは PAPER_TRADING_SQLITE_PATH を使用して実 DB と分離します（data/paper_trading.db がデフォルト）。
- run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用して監視ログを残す設計です（運用上の意図: 監視は実運用 DB を監視対象とする）。
- kill.flag（Settings.kill_flag_path）
  - RiskMonitor / KillSwitch により kill.flag が作成されると ExecutionEngine 停止を示すフラグとなります。ExecutionEngine 側は起動時にフラグを確認・クリアする設計（kill_flag_clear_on_start を設定可能）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等にテーブル作成と軽微マイグレーション（列追加）を行います。

ディレクトリ構成（主要ファイル）
-------------------------------
以下はリポジトリ内の主要ファイルと簡単な説明（抜粋）:

- src/kabusys/
  - __init__.py                      — パッケージ定義（バージョン等）
  - config.py                        — 環境変数設定読み込み / Settings クラス
  - run_execution.py                 — ExecutionEngine 起動スクリプト
  - run_monitoring.py                — SystemMonitor polling 起動スクリプト
  - tools/
    - paper_verification_report.py   — Paper Trading の検証レポート生成 CLI
  - execution/
    - order_manager.py               — 発注の外向き API（OrderManager）
    - reconciler.py                  — 起動時リコンシリエーション
    - (その他 execution 関連モジュール: broker_factory 等)
  - monitoring/
    - monitoring_db.py               — SQLite 永続化層（init / MonitoringDB）
    - system_monitor.py              — CPU/メモリ/ディスク/データ鮮度監視
    - trade_monitor.py               — 注文滞留・約定異常監視
    - risk_monitor.py                — ドローダウン / ポジション上限監視
    - kill_switch.py                 — kill.flag 管理
    - alert_manager.py               — LINE Push 通知
    - monitoring_engine.py           — 各 monitor の統合実行ループ
    - streamlit_dashboard.py         — Streamlit ダッシュボード
  - portfolio/
    - portfolio_builder.py           — 候補選定・重み計算
    - position_sizing.py             — 株数算出・aggregate cap ロジック
    - risk_adjustment.py             — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py             — Momentum/Volatility/Value などのファクター計算
    - feature_exploration.py         — 将来リターン・IC・summary 等
  - ai/
    - news_nlp.py                    — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py             — ETF MA + マクロニュースでレジーム判定
  - utils/
    - process_priority.py            — プロセス優先度設定ユーティリティ

（上記は主要ファイルの抜粋です。実装ファイル群は src/kabusys 以下にまとまっています）

開発・テストのヒント
--------------------
- Settings は .env/.env.local を自動で読み込みます（プロジェクトルートは .git または pyproject.toml で検出）。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。
- DuckDB と prices_daily/raw_financials 等のテーブルを用意すると research モジュールの関数を単体で試せます。
- OpenAI 呼び出し部分は内部でヘルパー関数に分離してあり、テスト時は該当関数をモックできます（例: unittest.mock.patch）。
- process_priority / cpu_affinity はプラットフォーム差異を吸収する設計だが、権限（Linux の nice 値変更や Windows の特殊定数）が必要になる場合があります。失敗時は警告を出してスキップします。

ライセンス / 貢献
-----------------
- 本 README にライセンス情報がなければ、プロジェクトルートの LICENSE を参照してください。
- バグ報告・プルリクエスト歓迎です。コードの責務分離（純粋関数 vs I/O）を尊重する設計になっていますので、ユニットテストの追加は歓迎します。

補足（よく使う環境変数一覧）
-----------------------------
- KABUSYS_ENV
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD
- OPENAI_API_KEY
- PAPER_FILL_MODE
- PAPER_TRADING_SQLITE_PATH
- SQLITE_PATH
- DUCKDB_PATH
- PID_FILE_PATH
- KILL_FLAG_PATH
- MONITOR_POLL_INTERVAL (run_monitoring のポーリング間隔 [秒]、デフォルト 60)

以上が本リポジトリの概要と運用ガイドです。詳細な実装や各関数の仕様は該当ソース（src/kabusys 以下）内の docstring / コメントを参照してください。必要であれば各機能（例: ExecutionEngine の設定項目、BrokerFactory の実装、duckdb のスキーマ）について別途詳しいドキュメントを作成します。