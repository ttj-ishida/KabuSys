KabuSys — 日本株自動売買システム
=================

このリポジトリは日本株向けの自動売買フレームワーク「KabuSys」の一部実装です。
モジュールは売買ロジック・ポートフォリオ構築・リサーチ・監視・AI ニューススコアリングなどに分かれ、
本番（live）・ペーパートレーディング（paper_trading）・開発（development）を想定した設計になっています。

本 README はソースコード（src/kabusys 配下）を元に、プロジェクト概要、機能一覧、
セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

プロジェクト概要
----------------
KabuSys は以下を目的としたモジュール群を提供します。

- 注文発行・状態管理（ExecutionEngine / OrderManager / Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ計算・セクター制約・レジーム乗数）
- リサーチ（ファクター計算、将来リターン、IC 計算、統計サマリー）
- AI を用いたニュースセンチメント（OpenAI を用いた銘柄別スコアリング / レジーム判定）
- 監視（SystemMonitor / TradeMonitor / MonitoringEngine）とアラート（LINE push）
- 運用支援ツール（ペーパートレード検証レポート、Streamlit ダッシュボード）

主要な挙動の設計指針：
- 本番 DB / ペーパートレード DB を分離（KABUSYS_ENV により動作切替）
- ルックアヘッドバイアス防止（date.today()/datetime.today() を直接参照しない箇所が多い）
- フェイルセーフ：API 失敗やデータ不足時は例外を極力吸収して継続する設計
- 冪等性（DB 初期化や書き込みが再実行可能）

機能一覧
--------
主な機能の要約：

- 実行（Execution）
  - 注文作成・送信・同期（OrderManager、OrderRepository、Reconciler）
  - 起動時の自動リコンシリエーション（再起動後の整合性回復）
  - RiskManager による発注制限

- 監視（Monitoring）
  - SystemMonitor：CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor：滞留注文・約定異常価格検出
  - RiskMonitor：ドローダウン・ポジション上限監視と kill.flag 制御
  - MonitoringEngine：モニタをまとめてポーリング、LINE アラート送信
  - Streamlit ダッシュボード（監視データの可視化）

- ポートフォリオ（Portfolio）
  - 候補選定（select_candidates）
  - 重み計算（等金額 / スコア加重）
  - セクター制約適用（apply_sector_cap）
  - レジーム乗数（calc_regime_multiplier）
  - 発注株数計算（calc_position_sizes: risk_based / equal / score）

- リサーチ（Research）
  - ファクター計算：モメンタム、ボラティリティ、バリュー（DuckDB を利用）
  - 将来リターン・IC・統計サマリー・ランク変換

- AI（OpenAI 経由）
  - ニュース NLP（news_nlp.score_news）：銘柄ごとのセンチメントを取得して ai_scores に保存
  - レジーム判定（regime_detector.score_regime）：MA200 とマクロニュースを合成して日次判定
  - レート制限・再試行・バリデーション実装あり

- ツール
  - paper_verification_report：ペーパートレード DB を解析して検証レポートを標準出力
  - streamlit_dashboard：監視 DB を可視化する Streamlit アプリ

セットアップ手順
----------------
以下は一般的なローカル開発/実行環境の構築手順です。環境に合わせて適宜読み替えてください。

1. リポジトリをチェックアウト
   - 例: git clone … && cd <repo>

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - 主要な依存例（requirements.txt がない場合の参考）:
     - duckdb
     - psutil
     - requests
     - openai
     - streamlit
   - 例:
     - pip install duckdb psutil requests openai streamlit

   （実際のプロジェクトでは requirements.txt または poetry/poetry.lock を使って依存管理してください）

4. 環境変数の設定
   - .env（プロジェクトルート）または OS 環境変数で設定します。
   - 自動ロードはデフォルトで有効（config.py が .env/.env.local を読み込み）。
   - 自動ロードを無効化する場合:
     - export KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主要な環境変数（代表例）:
   - KABUSYS_ENV: development | paper_trading | live  （デフォルト: development）
   - SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
   - DUCKDB_PATH: DuckDB（デフォルト: data/kabusys.duckdb）
   - PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
   - PID_FILE_PATH: Execution pid ファイル（デフォルト: data/execution.pid）
   - KILL_FLAG_PATH: kill.flag ファイルパス（デフォルト: data/kill.flag）
   - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 外部 API 用の必須トークン
   - OPENAI_API_KEY: OpenAI を使う機能に必要
   - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE アラート送信用
   - PAPER_FILL_MODE: paper_trading のモック挙動（instant|partial|never|reject）

5. データディレクトリ作成
   - data/ 配下（デフォルト DB や PID ファイルの格納先）を準備します。
   - 例: mkdir -p data

基本的な使い方
--------------

実行系（ExecutionEngine）
- 本番/ペーパートレードの起動スクリプト:
  - 実行方法（パッケージ内モジュールとして起動可能）:
    - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    - python -m kabusys.run_execution  （KABUSYS_ENV が live の場合は本番 DB を使用）
  - 説明:
    - paper_trading モードでは MockBrokerClient を使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録します。
    - 起動時にプロセス優先度を上げ、監視テーブルが存在するか init_monitoring_db を呼びます。
    - ExecutionEngine 実体は src/kabusys/execution 以下に実装されています。

監視（Monitoring）
- 監視ポーリングループ起動:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き（デフォルト 60 秒）。
  - 監視は設定に関わらず本番用 sqlite_path（SQLITE_PATH）を参照して記録を行います。
  - run_monitoring は PID ファイル監視・duckdb 接続・SystemMonitor を初期化してループ実行します。

Streamlit ダッシュボード
- 起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  - 読み取り専用で監視 DB を開き、Overview / Positions / Orders / System タブを表示します。

ペーパートレード検証レポート
- 使い方:
  - python -m kabusys.tools.paper_verification_report
  - オプション:
    - --from YYYY-MM-DD
    - --to   YYYY-MM-DD
    - --db PATH  （PAPER_TRADING_SQLITE_PATH 環境変数の代替）
  - 出力内容:
    - 稼働率、注文成功率、送信率、P95 レイテンシ、リスク却下数、最終判定（PASS/FAIL）

AI（OpenAI）機能
- news_nlp.score_news / regime_detector.score_regime などの関数は OpenAI API キー（OPENAI_API_KEY）を必要とします。
- モデルは gpt-4o-mini 相当を想定しており、API コールでのレート制限・5xx エラーに対して再試行（指数バックオフ）を行います。
- 実行例（ライブラリ関数の呼び出し）:
  - Python REPL やスクリプト内で duckdb 接続を作成し、kabusys.ai.news_nlp.score_news(conn, target_date) を呼ぶことで ai_scores を更新できます。

設定 / 動作に関する注意
- KABUSYS_ENV による分岐:
  - paper_trading: ブローカークライアントはモック、DB を分離
  - live: 本番 DB / 本番ブローカーを使用
  - development: 開発用
- PID ファイルと kill.flag:
  - ExecutionEngine は PID ファイル（Settings.pid_file_path）を書き、SystemMonitor はその存在を監視します。
  - KillSwitch は RiskMonitor の検出結果等に応じて kill.flag を書き、ExecutionEngine に停止シグナルを送ります（ファイル存在で検出）。
  - KILL_FLAG_CLEAR_ON_START を 1 にすると起動時に kill.flag を自動クリアできます。
- DB 初期化:
  - init_monitoring_db(conn) は監視用テーブルを冪等に作成し、既存 DB への軽微なマイグレーション（カラム追加）も行います。

ディレクトリ構成（主要ファイル）
--------------------------------
以下は src/kabusys 配下の主要ファイルと簡単な説明です（抜粋）。

- src/kabusys/
  - __init__.py                — パッケージ定義（__version__ 等）
  - config.py                  — 環境変数 / .env ロード / Settings クラス
  - run_monitoring.py          — SystemMonitor ポーリングループの起動スクリプト
  - run_execution.py           — ExecutionEngine 起動スクリプト

- src/kabusys/monitoring/
  - monitoring_db.py           — SQLite ベースの監視ログ永続化（init / MonitoringDB）
  - system_monitor.py          — CPU/メモリ/ディスク/プロセス/データ鮮度監視
  - trade_monitor.py           — 注文滞留・約定異常検出
  - risk_monitor.py            — ドローダウン・ポジション上限監視
  - kill_switch.py             — kill.flag の作成 / 管理
  - alert_manager.py           — LINE Messaging API による通知送信
  - monitoring_engine.py       — 各 Monitor を束ねるポーリングエンジン
  - streamlit_dashboard.py     — Streamlit ベースの監視ダッシュボード

- src/kabusys/execution/
  - order_manager.py           — 注文ワークフロー（作成・送信・同期）
  - reconciler.py              — 起動時リコンシリエーション
  - order_repository.py        — （DB 操作部分：該当ファイルはコード抜粋外） 
  - execution_engine.py        — （実行エンジン本体：該当ファイルはコード抜粋外）
  - broker_factory.py          — Broker クライアント生成（Mock / 実ブローカー）

- src/kabusys/portfolio/
  - portfolio_builder.py       — 候補選定・重み計算
  - position_sizing.py         — 発注株数計算（単元丸め・リスク制限）
  - risk_adjustment.py         — セクターキャップ・レジーム乗数

- src/kabusys/research/
  - factor_research.py         — Momentum/Volatility/Value ファクター計算（DuckDB）
  - feature_exploration.py     — 将来リターン・IC・統計サマリー

- src/kabusys/ai/
  - news_nlp.py                — ニュース記事を OpenAI でスコアリングして ai_scores に保存
  - regime_detector.py         — マクロニュース + ETF MA200 で日次レジーム判定

- src/kabusys/tools/
  - paper_verification_report.py — ペーパートレード DB 解析ツール（レポート生成）
  - __init__.py

- src/kabusys/utils/
  - process_priority.py        — プロセス優先度（Windows / POSIX を吸収）
  - __init__.py

付録：よく使うコマンド例
------------------------
- 監視ループを起動（デフォルト 60 秒間隔）:
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring

- 実行エンジン（ペーパートレード）を起動:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution

- Streamlit ダッシュボードを起動:
  - streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db

- ペーパートレード検証レポート生成:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db

最後に / 注意点
----------------
- 実際の商用運用では broker API の実装や資金管理は十分に検証してください。
- OpenAI や外部 API を利用する機能は API キーやコスト、レート制限に注意が必要です。
- この README はソースコードの抜粋に基づく概要です。さらに詳細な運用手順・設計資料（例：PortfolioConstruction.md / StrategyModel.md）がプロジェクト内にある想定ですので、合わせて参照してください。

必要であれば、README の英語版や導入スクリプト（requirements.txt、docker-compose、systemd ユニット など）も作成します。どの情報を追加したいか教えてください。