KabuSys — 日本株自動売買システム（README）
======================================

概要
----
KabuSys は日本株の自動売買・バックテスト・モニタリングを目的とした Python ベースの小規模なシステム群です。本リポジトリは以下の主要機能群を含みます。

- 実行エンジン（ExecutionEngine）: ブローカーへ注文を出し、注文状態管理・リスク管理を行う
- 監視サブシステム（MonitoringEngine）: システム状態、注文の異常、リスク指標を定期チェックしログ化／アラート送信する
- ポートフォリオ構築ユーティリティ: 候補選定・重み付け・株数算出・セクターキャップ等の純粋関数群
- リサーチ用モジュール: ファクター計算・将来リターン・IC 計算など
- AI 周り: ニュースを LLM(OpenAI) でスコア化する機能、市場レジーム判定
- ツール: Paper Trading 検証レポート生成、Streamlit ベースの監視ダッシュボード

主な特徴
---------
- 環境変数 / .env(.env.local) による設定管理（自動ロード機能）
- 本番 / Paper Trading の DB 分離（paper_trading 環境では専用 SQLite を使用）
- DuckDB を使ったリサーチ・ファクター計算
- OpenAI を用いたニュースセンチメント / レジーム判定（API キー必要）
- LINE による監視アラート送信機能
- 停止用フラグファイル（data/kill.flag 等）による安全停止メカニズム
- Streamlit での監視ダッシュボード表示

前提・依存パッケージ（例）
-------------------------
以下は主要な依存例です（プロジェクトの pyproject.toml/requirements.txt を参照してください）。

- Python 3.9+
- duckdb
- psutil
- requests
- openai
- streamlit

インストール例（仮）
- 仮想環境作成・有効化後:
  pip install duckdb psutil requests openai streamlit

設定（環境変数）
----------------
- 自動ロード: プロジェクトルートに .env / .env.local を置くと自動で読み込みます（OS 環境変数優先）。テスト等で無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- 主な環境変数:
  - KABUSYS_ENV: 起動環境（development / paper_trading / live）。デフォルト: development
  - JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
  - KABU_API_PASSWORD: kabuステーション API 用（必須）
  - OPENAI_API_KEY: OpenAI 呼び出しに必要（AI 機能を使う場合）
  - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE アラート送信用（任意）
  - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH: paper_trading 時の専用 SQLite（デフォルト: data/paper_trading.db）
  - DUCKDB_PATH: DuckDB 用ファイルパス（デフォルト: data/kabusys.duckdb）
  - PAPER_FILL_MODE: paper_trading 時の MockBroker 挙動 (instant|partial|never|reject)（デフォルト: instant）
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

セットアップ手順
----------------
1. リポジトリのクローン
   git clone <repo>
2. 仮想環境作成・有効化（推奨）
3. 依存パッケージをインストール
   pip install duckdb psutil requests openai streamlit
4. プロジェクトルートに .env を作成（.env.example を参照して必要なキーを設定）
5. 必要なら data ディレクトリを作成
   mkdir -p data

起動・使い方
------------

実行エンジン（注文実行）
- 役割: ブローカークライアントを作成し ExecutionEngine を起動。paper_trading 環境では MockBroker を使い、paper_trading 用 DB に書き込む。
- 起動コマンド例（リポジトリルートで）:
  - PYTHONPATH を通すかパッケージとしてインストール後:
    python -m kabusys.run_execution
- 注意:
  - KABUSYS_ENV=paper_trading にすると paper_trading 用 DB (PAPER_TRADING_SQLITE_PATH) を使用します。
  - 実行中は data/execution.pid に PID を出力します。停止は kill.flag 等、もしくは stop_requested.flag を用いることができます（実装内で参照）。

監視ループ（System / Trade / Risk 監視）
- 役割: SystemMonitor 等を定期ポーリングして monitoring DB に記録、アラートや KillSwitch 評価を実施。
- 起動:
  python -m kabusys.run_monitoring
- オプション:
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60）
- 実行時の DB:
  - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する点に注意

Streamlit 監視ダッシュボード
- 起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- ダッシュボードは読み取り専用で monitoring DB の dashboard / positions / trade_logs / system_status / risk_logs を可視化します。

Paper Trading 検証レポート
- スクリプト:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
- オプション:
  --from, --to, --db（PAPER_TRADING_SQLITE_PATH より優先して DB 指定可）
- 出力: 指定期間の稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を標準出力へ表示し PASS/FAIL 判定を行います。

AI 機能（ニュースNLP / レジーム判定）
- 必要: OPENAI_API_KEY を環境変数に設定
- 関数:
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
- 注意: API 失敗時はフェイルセーフとして部分的に 0.0 を用いる等の設計がされていますが、API キーは必須です。

停止・保守
----------
- 停止フラグ:
  - data/stop_requested.flag: run_monitoring / run_execution がループを抜けるために参照（存在時に終了）
  - data/kill.flag: KillSwitch が書き込むと ExecutionEngine 停止をトリガーする（Execution 側で参照）
- PID ファイル:
  - data/execution.pid に実行中の PID を書き込み / stale PID 検知ロジックあり

注意事項 / 実装上のポイント
----------------------------
- 環境設定: Settings クラスは .env/.env.local と OS 環境変数から値を読み込みます。必須キーが未設定の場合は ValueError を送出します。
- Paper Trading 分離: paper_trading モードでは実トレード DB と完全分離することを想定しています。
- DuckDB: リサーチ系（ファクター計算、AI の入力取得など）は DuckDB を使って高速に集計します。DuckDB 用ファイルパスは DUCKDB_PATH で指定。
- ロギング: 主要スクリプトは logging.basicConfig(level=logging.INFO) を使用します。LOG_LEVEL で上書き可。
- モジュール設計: 多くのロジックは純粋関数（副作用無し）として設計されており、ユニットテストが容易です（例: portfolio/*, research/*）。

ディレクトリ構成（主要ファイル）
--------------------------------
src/kabusys/
- __init__.py — パッケージメタ情報
- config.py — Settings（環境変数/.env ロード）
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ（抜粋）
- ai/
  - news_nlp.py — ニュースの LLM スコアリング（OpenAI）
  - regime_detector.py — 市場レジーム判定（MA + LLM 合成）
- monitoring/
  - monitoring_db.py — SQLite スキーマ初期化 / 永続化層
  - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor.py — 注文滞留・約定異常チェック
  - risk_monitor.py — ドローダウン / ポジション上限監視
  - kill_switch.py — 停止フラグ作成ユーティリティ
  - alert_manager.py — LINE プッシュ通知
  - monitoring_engine.py — モニタ群の統合ポーリング
  - streamlit_dashboard.py — Streamlit ダッシュボード
- execution/
  - order_manager.py — 注文作成・キャンセルなどの外向き API
  - reconciler.py — 起動時リコンシリエーション
  - ...（ブローカー抽象等）
- portfolio/
  - portfolio_builder.py — 候補選定・重み付け
  - position_sizing.py — 株数算出、総投資額スケール処理
  - risk_adjustment.py — セクター制限、レジーム乗数
- research/
  - factor_research.py — モメンタム／ボラティリティ／バリュー計算
  - feature_exploration.py — 将来リターン・IC・統計サマリ
- tools/
  - paper_verification_report.py — Paper Trading 検証レポート生成スクリプト
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity 設定ユーティリティ

よくある操作例
----------------
- Paper Trading で Execution を起動:
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- 監視ループ起動（デフォルト間隔 60s）:
  python -m kabusys.run_monitoring
  MONITOR_POLL_INTERVAL=10 python -m kabusys.run_monitoring
- Streamlit ダッシュボード起動:
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
- Paper 検証レポート作成:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

ライセンス・貢献
----------------
- 本 README ではライセンス・貢献フローの情報は含めていません。必要に応じて LICENSE ファイル・CONTRIBUTING ガイドを追加してください。

最後に
------
この README はリポジトリ内の主要スクリプトとモジュールの振る舞いを簡潔にまとめたものです。詳細な設計指針（PortfolioConstruction.md, StrategyModel.md など）やテーブル設計はリポジトリ内のドキュメントを参照してください。質問や実行中の問題があれば、該当モジュールのログ出力や .env 設定を確認してください。