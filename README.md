# KabuSys

日本株自動売買システムのモジュール群（ライブラリ＋実行スクリプト）の抜粋リポジトリ用 README。

以下はこのコードベースに含まれる主要機能、セットアップ手順、使い方、ディレクトリ構成の簡潔な説明です。

---

## プロジェクト概要

KabuSys は日本株の自動売買・リサーチ・監視を目的としたモジュール群です。  
主な設計方針：

- 発注ロジック（Execution）と監視（Monitoring）を分離
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境で切替
- DuckDB を用いたリサーチ／ファクター計算（prices_daily 等）
- SQLite を用いた監視ログ・紙上発注ログ（monitoring.db / paper_trading.db）
- LLM（OpenAI）を用いたニュースセンチメント / レジーム判定機能（任意）
- フェイルセーフ設計（API失敗時のフォールバック、Kill Switch、冪等な DB 書き込み など）

バージョン: 0.1.0

---

## 主な機能一覧

- 実行エンジン起動スクリプト
  - run_execution.py: ExecutionEngine を起動。KABUSYS_ENV が `paper_trading` のときは MockBrokerClient を使い paper_trading.db に記録して本番 DB と分離。
  - プロセス優先度を高く設定して実行（psutil 利用）
  - 停止フラグ（data/stop_requested.flag）検出で安全停止
- 監視ループ起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループを起動（MONITOR_POLL_INTERVAL で間隔変更可）
  - 監視結果は本番用 sqlite_path を使用して永続化
- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク、Execution プロセス生存、データ鮮度をチェックし monitoring DB に記録
  - TradeMonitor: 滞留注文・約定価格異常を検出して risk_logs に記録
  - RiskMonitor: ドローダウン／ポジション上限を監視し、必要時にリスクイベント／Kill Switch をトリガー
  - KillSwitch: 条件により data/kill.flag を書き込み ExecutionEngine に停止信号を送る
  - MonitoringEngine: 以上のモニタを束ねてポーリング、アラート発行
- 監視 DB ヘルパー
  - monitoring_db.py: SQLite のテーブル作成、ログ / ダッシュボードの upsert、risk_logs の重複抑止等
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio_builder: 候補選定、等重・スコア重み算出
  - position_sizing: 発注株数計算（ロット丸め、aggregate cap、risk_based 等）
  - risk_adjustment: セクターキャップ適用、レジーム乗数
- リサーチ（DuckDB ベース）
  - factor_research: Momentum / Volatility / Value 等ファクター算出
  - feature_exploration: 将来リターン、IC（スピアマン）計算、統計サマリー
- AI（任意）
  - news_nlp: raw_news を LLM（OpenAI）でスコアリングし ai_scores に書き込み
  - regime_detector: ETF（1321）MA とマクロニュース LLM を合成して日次レジーム判定（market_regime）
- ツール
  - config_setup.py: 対話式ウィザードで .env を作成・更新
  - validate_config.py: .env と config/*.yaml の基本チェック（--strict で警告も失敗扱い）
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成
- ユーティリティ
  - process_priority: クロスプラットフォームでプロセス優先度 / CPU affinity を設定
  - config: .env 自動読み込み、Settings クラス：環境変数中心の設定管理

---

## 必須・主要環境変数

最低限設定すべき環境変数（validate_config でもチェックされます）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)

他の重要な環境変数とデフォルト:

- KABUSYS_ENV: 実行環境。`development` / `paper_trading` / `live`（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（デフォルト: INFO）
- OPENAI_API_KEY: OpenAI を使う場合に必要（news_nlp / regime_detector）
- PAPER_FILL_MODE: paper_trading のマッチングモード（instant / partial / never / reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト: 60）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1、本番では 0 推奨）

注意: .env 自動読み込みはデフォルトで有効。自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

## 必要な Python パッケージ（代表例）

このリポジトリの各機能により依存するパッケージ：

- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（validate_config の YAML 検証を有効にする場合）

（実際の requirements.txt はこの抜粋に含まれていません。環境に合わせてインストールしてください。）

例:
pip install duckdb psutil openai pyyaml

---

## セットアップ手順（ローカル開発用の最小手順）

1. リポジトリをクローン、作業ディレクトリに移動
2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)
3. 必要パッケージをインストール
   - pip install duckdb psutil openai pyyaml
4. 対話式ウィザードで .env を作成
   - python -m kabusys.config_setup
5. 設定検証（任意）
   - python -m kabusys.validate_config
   - 厳密モード: python -m kabusys.validate_config --strict
6. 必要に応じてデータディレクトリを作成
   - mkdir -p data

---

## 使い方（主要スクリプト）

- 環境設定ウィザード（.env 作成）
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - strict モード（警告を失敗扱い）: python -m kabusys.validate_config --strict

- 実行エンジン起動（ExecutionEngine）
  - python -m kabusys.run_execution
  - 注意: KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し paper_trading.db に記録されるため本番 DB と分離されます。
  - 実行中 stop をしたい場合はプロジェクトルート/data/stop_requested.flag を作成することでスレッドが安全停止します（run_execution は起動時に既に存在すれば起動を行いません）。

- 監視ループ起動（SystemMonitor）
  - python -m kabusys.run_monitoring
  - ポーリング間隔を変更するには環境変数 MONITOR_POLL_INTERVAL=n（秒）
    - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 監視は Settings.sqlite_path を使用して monitoring DB に永続化します（環境に関わらず本番 sqlite_path を使用する挙動に注意）。

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report
  - 期間指定: --from YYYY-MM-DD --to YYYY-MM-DD
  - DB 指定: --db PATH （環境変数 PAPER_TRADING_SQLITE_PATH でも可）
  - 例: python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

- AI 系（OpenAI API キーが必要）
  - ニュースのスコアリング（プログラム的に）:
    - from kabusys.ai.news_nlp import score_news
    - score_news(duckdb_conn, target_date, api_key="...")  # api_key を渡すか環境変数 OPENAI_API_KEY を設定
  - レジーム判定:
    - from kabusys.ai.regime_detector import score_regime
    - score_regime(duckdb_conn, target_date, api_key="...")

---

## 停止・Kill スイッチに関する挙動

- stop_requested.flag
  - run_execution.py / run_monitoring.py はプロジェクトの data/stop_requested.flag を参照し、存在するとループを抜けて安全に終了します。
- kill.flag
  - KillSwitch（監視側）が判定した場合、Settings.kill_flag_path（デフォルト data/kill.flag）へ理由を書き込みます。ExecutionEngine 側は kill.flag を見て適切に停止する実装（別モジュール）を期待します。
- PID ファイル
  - run_execution は起動時に data/execution.pid を PID ファイルとして使用し、system monitor は該当 PID が生存しない場合 stale PID として扱います。

---

## ディレクトリ構成（コード抜粋に基づく）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数／.env 読み込み、Settings クラス
  - config_setup.py                 — .env 対話式ウィザード
  - validate_config.py              — 起動前チェック CLI
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
  - utils/
    - __init__.py
    - process_priority.py           — プロセス優先度 / CPU affinity ユーティリティ
  - monitoring/
    - monitoring_db.py              — SQLite 監視 DB 操作クラス
    - system_monitor.py             — システム / データ鮮度監視
    - trade_monitor.py              — 注文滞留・約定異常検出
    - risk_monitor.py               — ドローダウン / ポジション上限監視
    - kill_switch.py                — kill.flag の書き込みロジック
    - monitoring_engine.py          — 各 monitor を束ねる実行エンジン
    - alert_manager.py              — （アラート送信ロジック、ここでは抜粋未表示）
  - execution/                       — 発注周り（OrderManager / ExecutionEngine 等）※抜粋の一部のみ参照
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - tools/
    - paper_verification_report.py
    - __init__.py

- data/
  - デフォルト DB / フラグ / PID ファイルの置き場（例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag, data/execution.pid）

- config/
  - system_config.yaml, data_config.yaml, strategy_config.yaml, risk_config.yaml, execution_config.yaml, monitoring_config.yaml
  - validate_config はこれらの存在と YAML パースの簡易チェックを行う（PyYAML がインストールされている場合）

---

## 追加の注意点 / ベストプラクティス

- 本番環境（KABUSYS_ENV=live）では kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START=1）を避けること（安全上の理由）。
- paper_trading モードは本番 DB と完全に分離するため、検証やデバッグ時は paper_trading を使用することを推奨。
- OpenAI を利用する機能は API 料金が発生するため、API キーの管理・利用制限に注意してください。
- monitoring_db.init_monitoring_db() は冪等にテーブルを作成・マイグレーション処理を行います。既存 DB を上書きする操作は行いませんが、バックアップは常に推奨します。
- 実稼働では systemd 等のプロセスマネージャで run_execution/run_monitoring を管理すると安全です（PID ファイルや stop フラグ検知の仕組みを補完できます）。

---

これで README の概要は終了です。必要であれば次の内容を追加できます：

- サンプル .env.example（鍵名と説明）
- 開発用テストコマンドの例（各モジュールのユニットテスト起動方法）
- alert_manager の実装例（LINE 通知設定）
- 実行エンジン / ブローカーファクトリの詳細（MockBroker の挙動や API マッピング）