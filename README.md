KabuSys — README
=================

概要
----
KabuSys は日本株向けの自動売買／リサーチ／監視を目的とした小規模なシステム群です。本リポジトリには以下の主要機能が含まれます。

- 実際の発注を行う ExecutionEngine（本番 / ペーパートレード対応）
- システム稼働状態・注文・リスクの継続監視（Monitoring）
- ポートフォリオ構築ユーティリティ（候補選定・重み付け・株数計算）
- リサーチ用ファクター計算・特徴量解析（DuckDB を利用）
- ニュースを LLM（OpenAI）でスコアリングする AI モジュール
- 運用時の補助ツール（レポート生成、Streamlit ダッシュボード等）

主な特徴
-------
- 環境切替（development / paper_trading / live）を環境変数 KABUSYS_ENV で切り替え可能
  - paper_trading: ブローカーはモックを使用し、ペーパートレード用 DB に記録（本番 DB と分離）
- 監視コンポーネント（SystemMonitor / TradeMonitor / RiskMonitor）をまとめる MonitoringEngine
- kill.flag による ExecutionEngine 停止シグナル、LINE へのアラート送信機能
- DuckDB を使ったリサーチ（prices_daily / raw_financials などのテーブル参照）
- OpenAI API を用いたニュースセンチメント（ai.news_nlp）および市場レジーム判定（ai.regime_detector）
- ペーパートレード向け検証レポート生成ツール

前提 / 必要環境
-------------
- Python 3.10+
- SQLite（組み込み）
- DuckDB（Python パッケージ）
- 推奨パッケージ（例）:
  - duckdb, psutil, requests, openai, streamlit
- （任意）.env ファイルによる環境変数管理（自動読み込み機構あり）

セットアップ手順
----------------
1. ソースを取得して仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

2. 依存パッケージをインストール
   - requirements.txt がある場合:
     - pip install -r requirements.txt
   - 例（主要パッケージのみ）:
     - pip install duckdb psutil requests openai streamlit

3. 環境変数を設定
   - .env をプロジェクトルートに置くと自動で読み込まれます（OS 環境変数優先）
   - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定
   - 重要な環境変数（代表例）
     - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
     - JQUANTS_REFRESH_TOKEN: J-Quants API 用トークン（必須な処理がある場合）
     - KABU_API_PASSWORD: kabuステーション API パスワード
     - OPENAI_API_KEY: OpenAI を使う機能に必要
     - SQLITE_PATH: monitoring 用 SQLite（デフォルト data/monitoring.db）
     - DUCKDB_PATH: DuckDB ファイル（デフォルト data/kabusys.duckdb）
     - PAPER_TRADING_SQLITE_PATH: ペーパートレード DB（デフォルト data/paper_trading.db）
     - PAPER_FILL_MODE: ペーパートレードでの約定モード（instant | partial | never | reject）
     - PID_FILE_PATH / KILL_FLAG_PATH: PID / kill flag のファイルパス
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知用
     - LOG_LEVEL: ログレベル（DEBUG/INFO/...）
     - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）

使い方（実行例）
----------------

- ExecutionEngine を起動する
  - 本番モード例:
    - export KABUSYS_ENV=live
    - python -m kabusys.run_execution
  - ペーパートレード例（mock broker を使用、専用 DB に記録）:
    - export KABUSYS_ENV=paper_trading
    - python -m kabusys.run_execution
  - ペーパートレードは PAPER_TRADING_SQLITE_PATH を参照（デフォルト data/paper_trading.db）

- Monitoring を起動する（ポーリング監視）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番用 sqlite_path（Settings.sqlite_path）を使用します（環境に関係なく同じ monitoring DB に記録）

- Streamlit ダッシュボードを起動する
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ペーパートレード検証レポートを生成する
  - python -m kabusys.tools.paper_verification_report
  - 期間指定例:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB を明示する例:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI（ニューススコア / レジーム判定）
  - OpenAI API キーが必要です（OPENAI_API_KEY）
  - ai.score_news / ai.regime_detector.score_regime は DuckDB 接続と target_date を受け取る関数 API です（ライブラリとして呼び出して利用）

設定と動作の注意点
-----------------
- .env の自動ロード:
  - プロジェクトルート（.git または pyproject.toml を基準）から .env/.env.local を自動読み込みします。
  - OS 環境変数は優先されます。テスト等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ペーパートレード分離:
  - KABUSYS_ENV=paper_trading のときは BrokerClientFactory が MockBrokerClient を返し、発注ログ等は paper_trading 用 SQLite に記録されます（本番 DB と完全分離）。
- PID / kill.flag:
  - ExecutionEngine は pid ファイルを生成し、監視側はこの PID を見てプロセス生存を判定します。KillSwitch は flag ファイルを置くことで ExecutionEngine 停止を促します。
- MONITOR_POLL_INTERVAL の取り扱い:
  - run_monitoring が参照する環境変数。正の整数以外はデフォルト（60秒）にフォールバックします。
- PAPER_FILL_MODE:
  - ペーパートレード時の約定挙動を設定できます。有効値: "instant" / "partial" / "never" / "reject"

ディレクトリ構成（抜粋）
----------------------
以下は本コードベースに含まれる主要ファイル群の概要です（src/kabusys 以下）:

- __init__.py
- config.py                      — 環境変数 / 設定管理 (Settings)
- run_execution.py               — ExecutionEngine 起動スクリプト
- run_monitoring.py              — SystemMonitor ポーリングループ起動スクリプト
- tools/
  - paper_verification_report.py  — ペーパー検証レポート生成 CLI
- monitoring/
  - monitoring_db.py              — monitoring 用 SQLite 永続化層
  - system_monitor.py             — CPU/メモリ/ディスク/データ鮮度の監視
  - trade_monitor.py              — 注文滞留・約定価格異常の監視
  - risk_monitor.py               — ドローダウン・ポジション上限監視
  - kill_switch.py                — kill.flag の作成 / 管理
  - alert_manager.py              — LINE 通知クライアント（クールダウン管理）
  - monitoring_engine.py          — 上記 Monitor を束ねる実行ループ
  - streamlit_dashboard.py        — Streamlit ベースの監視ダッシュボード
- execution/
  - order_manager.py              — 注文作成 / 送信の外向き API
  - reconciler.py                 — 起動時の注文・ポジションのリコンシリエーション
  - （その他：broker_factory, order_repository, execution_engine 等）
- portfolio/
  - portfolio_builder.py          — 候補選定・重み算出
  - position_sizing.py            — 株数決定・資金配分・丸め処理
  - risk_adjustment.py            — セクターキャップ、レジーム乗数
- research/
  - factor_research.py            — momentum/value/volatility ファクター計算（DuckDB）
  - feature_exploration.py        — 将来リターン / IC / 統計サマリー
- ai/
  - news_nlp.py                   — ニュースを LLM で評価して ai_scores に書き込み
  - regime_detector.py            — ETF MA + マクロニュースでレジーム判定
- utils/
  - process_priority.py           — プロセス優先度・CPU affinity 設定ユーティリティ

開発者向けメモ
--------------
- DuckDB 接続を受け取る関数群は外部 API に依存せず、prices_daily / raw_financials 等のテーブルのみを参照する設計になっています。リサーチ系はローカルデータベースで再現可能です。
- AI 呼び出し周りは失敗時にフェイルセーフ（スコア0.0 やスキップ）で継続する実装方針です。ただし API レートやコストに注意してください。
- monitoring_db.init_monitoring_db は冪等でマイグレーション処理を含みます。初回起動時に必要なテーブルとカラムが作成されます。

ライセンス / 貢献
-----------------
本リポジトリのライセンスやコントリビュートルールはプロジェクトルートの LICENSE / CONTRIBUTING を参照してください（存在する場合）。

問い合わせ
---------
使い方やトラブルシュートの質問は Issue を立てるか、リポジトリ管理者に問い合わせてください。

以上。必要があれば README に含めるコマンド例や環境変数のテンプレート（.env.example）を追加で作成します。どの情報を追記したいか教えてください。