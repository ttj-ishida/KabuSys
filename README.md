# KabuSys

日本株自動売買システムのリポジトリ（README、日本語）

---

目次
- プロジェクト概要
- 主な機能
- セットアップ手順
- 使い方（主要コマンド）
- 環境変数（主要な設定）
- 実行時フラグ / ファイル
- ディレクトリ構成（主要ファイル一覧）
- 開発・デバッグのヒント

---

## プロジェクト概要

KabuSys は日本株の自動売買を念頭に設計されたシステムです。  
以下のコンポーネントを含み、取引実行・監視・ポートフォリオ構築・リサーチ・AI ベースのニュース評価などを提供します。

- ExecutionEngine：発注・オーダー管理・リスク管理を担う実行エンジン
- Monitoring：システム状態、データ鮮度、取引状況、リスク指標の定期監視とアラート（Kill Switch を含む）
- Portfolio：銘柄選定・重み計算・ポジションサイズ決定ロジック
- Research：DuckDB を利用したファクター計算・将来リターン解析
- AI：OpenAI を使ったニュースセンチメント / レジーム判定（gpt-4o-mini 想定）
- Tools：ペーパートレード検証レポートなど

設計方針として、データ解析（DuckDB）と監視／発注（SQLite / Execution）を分離し、ペーパートレード用に本番 DB と分離可能な動作をサポートします。

---

## 主な機能

- 実行エンジン（本番 / ペーパートレード切替）
  - KABUSYS_ENV により `paper_trading` の場合は MockBrokerClient が使用され、紙上トレードは別 DB に記録
- 監視（Monitoring）
  - CPU / メモリ / ディスク / プロセス生存チェック、データ鮮度チェック
  - 滞留注文・約定異常・ドローダウン・ポジション上限の検出
  - Kill Switch（リスクトリガで data/kill.flag を作成してエンジンを停止）
- ポートフォリオ構築
  - 候補選定 / 等金額・スコア加重配分 / リスクベースサイズ計算
  - セクター集中抑制・レジーム乗数
- リサーチ
  - Momentum / Volatility / Value 等のファクターを DuckDB で計算
  - 将来リターン・IC（Information Coefficient）や統計サマリー
- AI（OpenAI 統合）
  - ニュースの銘柄別センチメントスコアリング（ai_scores テーブルへ書込）
  - マクロニュース＋ETF MA200 乖離からレジーム判定（market_regime テーブルへ書込）
- ツール
  - ペーパートレードの検証レポート出力（paper_verification_report）

---

## セットアップ手順

前提：
- Python 3.9+（ソースの typing と構文を参照）
- 仮想環境の利用を推奨

1. リポジトリをチェックアウト、仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate（Windows は .venv\Scripts\activate）

2. 依存パッケージをインストール
   - 必須（例）:
     - duckdb
     - psutil
     - openai
     - PyYAML（config 検証用）
   - 例:
     - pip install duckdb psutil openai PyYAML

   （プロジェクトに requirements.txt がある場合はそちらを使用してください）

3. .env の作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 生成された .env は Git にコミットしないこと（シークレット含む）

4. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱いで exit(1)

5. DB ディレクトリなど初期化
   - .env で指定したパス（デフォルト data/）がなければ作成されます
   - 実行スクリプトが起動時に必要なテーブルを作成します（init_monitoring_db）

---

## 使い方（主要コマンド）

- 実行エンジン起動
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は Mock ブローカーを使用し、PAPER_TRADING_SQLITE_PATH（デフォルト data/paper_trading.db）へ記録されます
    - 実行中に data/stop_requested.flag が置かれると安全に停止します

- 監視ループ起動
  - python -m kabusys.run_monitoring
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を変更可能（デフォルト: 60）
    - 監視は常に本番 sqlite_path を参照して監視情報を永続化します
    - data/stop_requested.flag による停止を検知します

- 環境設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - オプション: --from YYYY-MM-DD --to YYYY-MM-DD --db PATH

- AI モジュール（プログラムから使用）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - OpenAI API キーは OPENAI_API_KEY 環境変数、または api_key 引数で指定

---

## 環境変数（主要）

（.env で設定。右側はデフォルト / 説明）

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants API トークン
- KABU_API_PASSWORD (必須) — kabuステーション API パスワード
- KABU_API_BASE_URL — デフォルト: http://localhost:18080/kabusapi
- KABUSYS_ENV — {development, paper_trading, live}（デフォルト: development）
  - paper_trading: 発注はモック、paper_trading 用 DB を使用
  - live: 実際に発注する本番モード
- DUCKDB_PATH — 分析用 DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- LOG_DIR — ログ出力先ディレクトリ（デフォルト: logs）
- OPENAI_API_KEY — OpenAI API キー（AI 機能で使用）
- PAPER_FILL_MODE — ペーパートレード Fill モード（instant|partial|never|reject、デフォルト: instant）
- PID_FILE_PATH — ExecutionEngine が使う pid ファイルパス（デフォルト: data/execution.pid）
- KILL_FLAG_PATH — Kill Switch フラグ（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1、デフォルト 0）
- CPU/MEM/DISK 閾値など:
  - CPU_THRESHOLD_PCT（例 90.0）
  - MEMORY_THRESHOLD_PCT（例 85.0）
  - DISK_THRESHOLD_PCT（例 90.0）
- MONITOR_POLL_INTERVAL — run_monitoring で上書き可能（秒、デフォルト 60）

---

## 実行時フラグ / ファイル（運用時の注意）

- data/stop_requested.flag
  - run_execution/run_monitoring で存在を検知するとループを終了します（安全停止）
- data/kill.flag
  - Monitoring の KillSwitch が条件を満たすと書き込まれ、ExecutionEngine に停止指示を出します
- data/execution.pid
  - ExecutionEngine 用の PID ファイル（利用中 / 管理のため）
- ログ
  - logs/<app_name>.log に日次ローテーションで出力（TimedRotatingFileHandler）
  - コンソールは stdout に出力するので cron 等の stdout リダイレクトと併用可

---

## ディレクトリ構成（主要ファイル）

src/kabusys/
- __init__.py
- config.py — 環境変数読み込み / Settings
- config_setup.py — .env の対話式ウィザード
- validate_config.py — 起動前設定チェック CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースセンチメント（OpenAI 統合）
  - regime_detector.py — 市場レジーム判定（MA200 + マクロセンチメント）
- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — CPU/メモリ/ディスク、データ鮮度、プロセス生存チェック
  - trade_monitor.py — （滞留注文等の監視）※ファイル中に実装あり
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - kill_switch.py — Kill Switch 実装（flag ファイル書込）
  - monitoring_engine.py — モニタを束ねる実行ループ
  - alert_manager.py — アラート送信（LINE など）
- execution/
  - execution_engine.py — 実行エンジン本体
  - broker_factory.py — ブローカークライアント生成（実・Mock 切替）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py など
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算
  - risk_adjustment.py — セクター制限・レジーム乗数
- research/
  - factor_research.py — Momentum/Vol/Value ファクター計算（DuckDB）
  - feature_exploration.py — forward returns / IC / summary
- tools/
  - paper_verification_report.py — ペーパートレード検証レポート
- utils/
  - logging_setup.py — ログ初期化ユーティリティ
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ
- data/ (ランタイムで生成 / .gitignore 推奨)
  - monitoring.db, paper_trading.db, kabusys.duckdb, stop_requested.flag, kill.flag, execution.pid など

---

## 開発・デバッグのヒント

- ログを詳しく見たい場合は LOG_LEVEL=DEBUG を設定して起動します。
- ペーパートレード検証は paper_trading 環境（KABUSYS_ENV=paper_trading）で行い、PAPER_TRADING_SQLITE_PATH にデータが記録されます。検証レポートは tools/paper_verification_report.py を使用。
- OpenAI を使う機能（news_nlp, regime_detector）は API キーが必要です。環境変数 OPENAI_API_KEY を設定するか、関数呼び出し時に api_key 引数を与えてください。
- .env 自動読み込みは Settings モジュール内で行われますが、テストや CI で無効にしたい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB スキーマのマイグレーションは monitoring_db.init_monitoring_db() である程度自動化されています（カラム追加対応あり）。ただし重大な変更では手動マイグレーションを検討してください。

---

以上が README の概要です。追加で、
- インストール可能な requirements.txt の内容、
- CI / デプロイ手順、
- 各モジュールの API ドキュメント（関数シグネチャと戻り値）、
などを含めたより詳細なドキュメントを作成することもできます。必要であればどの部分を優先して展開するか教えてください。