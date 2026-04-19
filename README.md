# KabuSys

日本株向けの自動売買／リサーチ基盤のコアライブラリ群です。  
このリポジトリには発注エンジン、監視／アラート、ポートフォリオ構築、ファクター計算、AI を使ったニュース解析ツールなどが含まれます。

---

## プロジェクト概要

KabuSys は次のような責務を持つモジュール群で構成されたシステムです。

- ExecutionEngine：発注・注文管理・リスク管理を行う実行エンジン（paper_trading モード対応）
- Monitoring：システム稼働状態、注文ログ、リスク指標の監視と Kill Switch（停止フラグ）生成
- Portfolio：銘柄選定・重み付け・株数決定の純粋関数群
- Research：DuckDB を用いたファクター計算・特徴量探索
- AI：OpenAI を利用したニュースのセンチメント評価や市場レジーム判定
- CLI ユーティリティ：.env 作成ウィザード、設定検証、ペーパートレード検証レポート など

本 README は開発者向けセットアップ・起動方法、主要コマンドとディレクトリ構成をまとめたものです。

---

## 主な機能一覧

- 発注実行エンジン（本番 / ペーパートレード切替）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、data/paper_trading.db に記録
- 監視ループ（SystemMonitor / TradeMonitor / RiskMonitor）
  - CPU / メモリ / ディスク使用率、プロセスの生存確認、データ鮮度チェック
  - Kill Switch（条件により data/kill.flag を書き込み ExecutionEngine を停止）
- モニタリング DB（SQLite）によるログ永続化（system_status / trade_logs / risk_logs / positions / dashboard）
- ポートフォリオ構築ユーティリティ（候補選定、等配分 / スコア加重、リスク調整、ポジションサイズ計算）
- 研究用モジュール（DuckDB を使ったファクター計算、将来リターン、IC 計算など）
- AI ベースニューススコアリング（OpenAI を用いた銘柄別センチメント算出）
- 設定ウィザード（.env の対話的生成）と設定検証 CLI
- ペーパートレード検証レポート生成スクリプト

---

## 要件（主な依存）

実行には以下パッケージが必要です（プロジェクトに合わせて適宜 requirements.txt を用意してください）:

- python >= 3.9
- duckdb
- psutil
- openai (または openai SDK のバージョンに合わせたパッケージ)
- sqlite3（標準ライブラリ）
- その他：ローカル環境で HTTP を使うクライアント（kabu API 関連）等

開発環境では仮想環境を作成して依存をインストールしてください。例:

- python -m venv .venv
- source .venv/bin/activate
- pip install duckdb psutil openai

（実際の requirements.txt がある場合は `pip install -r requirements.txt` を使用）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成して有効化
3. 必要パッケージをインストール
4. .env を作成
   - 対話式ウィザードを利用:
     - python -m kabusys.config_setup
   - 手動で作成する場合は .env.example を参考に `JQUANTS_REFRESH_TOKEN`・`KABU_API_PASSWORD` 等の必須項目を設定
5. 設定検証:
   - python -m kabusys.validate_config
   - --strict を付けると警告も失敗扱い
6. データディレクトリとログディレクトリを作成（通常自動作成されますが確認）
   - data/
   - logs/

注意:
- 自動で monitoring DB 等は初回起動時に作成・マイグレーションされます（init_monitoring_db）。
- OpenAI を使う機能を動かす場合は `OPENAI_API_KEY` を .env に設定してください。

---

## 環境変数（主要）

以下は本システムで使用する主要環境変数（.env に設定）:

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

任意 / デフォルトを持つ:
- KABUSYS_ENV — 実行環境 (development | paper_trading | live) （デフォルト: development）
  - paper_trading: Mock broker を使用し paper_trading DB に記録
  - live: 実際に発注
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR — ログ保存先（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI を使う機能で利用
- MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔秒（run_monitoring では環境変数で上書き可、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — ExecutionEngine 起動時に kill.flag を自動クリアするか（0/1）

---

## 起動・使用方法

モジュールは Python のモジュール実行形式で起動します。プロジェクトルートで以下コマンドを実行してください。

- 設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳密モード: python -m kabusys.validate_config --strict

- ExecutionEngine の起動（発注エンジン）
  - python -m kabusys.run_execution
  - 挙動:
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い paper_trading DB に記録
    - 起動時に data/stop_requested.flag が存在すると起動せず終了
    - 実行中、data/stop_requested.flag を検知するとエンジンを停止する
    - 実行中は PID ファイル（data/execution.pid）を作成

- Monitoring の起動（監視ループ）
  - python -m kabusys.run_monitoring
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を秒で上書き可能（デフォルト 60）
  - 監視は常に本番 sqlite_path を使用（環境にかかわらず監視 DB は本番パス）
  - 停止は data/stop_requested.flag を作成することで行える

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH または環境変数 PAPER_TRADING_SQLITE_PATH

- AI 関連（プログラム呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続と OPENAI_API_KEY（または api_key 引数）を必要とします

停止フローのポイント:
- Execution を止めたい場合は Monitoring によって data/kill.flag が書き込まれるか、管理者が手動で data/stop_requested.flag を作成します。run_execution はこのフラグを監視して安全に終了します。

ログ:
- ログは stdout に出力され、さらに logs/<app_name>.log に日次ローテートで保存されます（デフォルト 30 日保持）。setup_logging が統一的に設定します。

---

## よく使うコマンド例

- .env を対話式で作る:
  - python -m kabusys.config_setup
- 設定チェック:
  - python -m kabusys.validate_config --strict
- 監視ループ起動（ポーリング 30 秒に設定）:
  - MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
- 実行エンジン起動（ペーパートレード）:
  - KABUSYS_ENV=paper_trading python -m kabusys.run_execution
- ペーパートレードレポート（2026-04-01 〜 2026-04-11）:
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## ディレクトリ構成（主要ファイル・モジュール説明）

- src/kabusys/
  - __init__.py — パッケージ化
  - config.py — 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py — .env 対話ウィザード
  - validate_config.py — 起動前チェック CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成 CLI
  - ai/
    - news_nlp.py — ニュースを LLM で評価して ai_scores に書込む処理
    - regime_detector.py — マクロ＋MA を使って市場レジーム判定し DB に書込む
  - monitoring/
    - monitoring_db.py — SQLite のスキーマ初期化 & 永続化ユーティリティ
    - system_monitor.py — CPU/メモリ/ディスク/データ鮮度/プロセス監視
    - trade_monitor.py — （注文ログ監視。実装参照）
    - risk_monitor.py — ドローダウン・ポジション上限監視
    - kill_switch.py — kill.flag の読み書きロジック
    - monitoring_engine.py — 各モニタを束ねるループ
    - alert_manager.py — （アラート通知ロジック）
  - execution/ — ExecutionEngine 関連（BrokerFactory / Engine / OrderManager / RiskManager 等）
  - portfolio/
    - portfolio_builder.py — 候補選定・重み計算
    - position_sizing.py — 株数計算・スケーリング
    - risk_adjustment.py — セクターキャップ・レジーム乗数
  - research/
    - factor_research.py — モメンタム・ボラティリティ・バリュー計算（DuckDB）
    - feature_exploration.py — 将来リターン・IC・統計サマリー
  - utils/
    - logging_setup.py — 共通ログ設定
    - process_priority.py — プロセス優先度 / CPU affinity 設定
  - data/ — 既定の保存先（実行時に作成）
    - monitoring.db（デフォルト SQLITE_PATH）
    - kabusys.duckdb（デフォルト DUCKDB_PATH）
    - paper_trading.db（ペーパートレード用）
    - execution.pid, stop_requested.flag, kill.flag などのフラグ／PID ファイル

---

## 注意事項 / 運用上のヒント

- 本番（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 に設定することを強く推奨します（自動クリアは危険）。
- OpenAI の呼び出しは API 料金が発生するため、API キーと呼び出し回数に注意してください。
- monitoring は本番 DB（SQLITE_PATH）を参照します。監視 DB は本番パスを使う設計ですので運用時はパスと権限を確認してください。
- ペーパートレード用 DB は production DB と完全に分離されます（settings.paper_sqlite_path）。
- ログディレクトリ作成に失敗した場合はファイルログを無効化し stdout のみで動作します。

---

必要に応じて README にサンプル .env、systemd ユニット、docker-compose の例を追加できます。どの形式を追加したいか教えてください。