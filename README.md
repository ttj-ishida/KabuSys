# KabuSys

日本株向け自動売買システムのサンプル実装（ライブラリ・運用スクリプト群）。  
本リポジトリは、戦略研究・ポートフォリオ構築・発注エンジン・監視・AI によるニュース分析までを含むモジュール群で構成されています。

---

## プロジェクト概要

KabuSys は以下の機能ブロックを提供します。

- 戦略研究（ファクター計算・特徴量解析）
- ポートフォリオ構築（候補選定、重み算出、ポジションサイズ計算）
- 発注系（ExecutionEngine／OrderManager／RiskManager 等）
- 監視（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch / MonitoringEngine）
- AI モジュール（ニュースの NLP スコアリング、レジーム判定：OpenAI を利用）
- 運用ユーティリティ（.env ウィザード・設定検証・レポート生成）

設計方針の一例：
- DB（DuckDB / SQLite）を使った分析・ログ保存
- Paper Trading と Live の分離（paper_trading 環境では専用 DB を使用）
- ルックアヘッドバイアス対策（日時参照の扱いに注意）
- フェイルセーフ（APIエラー時は安全なデフォルトで継続）

---

## 主な機能一覧

- config_setup: 対話式に `.env` を生成/更新
- validate_config: .env および config/*.yaml の事前検証
- run_execution: 発注/実行エンジン起動スクリプト（KABUSYS_ENV による paper/live 切替）
- run_monitoring: 監視ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔変更可）
- monitoring: システム/注文/リスク監視、kill.flag による停止
- ai.news_nlp: OpenAI を用いたニュースのセンチメントスコア計算（ai_scores へ書込）
- ai.regime_detector: マーケットレジーム判定（ma200 + マクロニュース）
- research: ファクター計算（momentum, volatility, value）・IC 計算・統計サマリ
- portfolio: 候補選定、等重/スコア重み、ポジションサイズ計算、セクター上限適用
- tools.paper_verification_report: Paper Trading の検証レポートを生成

---

## 前提 / 依存ライブラリ

推奨 Python バージョン: 3.9+（ソースの typing 構文などを使用）

主な外部依存（抜粋）:
- duckdb
- psutil
- openai
- PyYAML（config.yaml のパース検証に任意）
- SQLite（標準ライブラリで提供）
- （テスト時）unittest.mock 等

インストール例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

（実際の requirements.txt がある場合はそちらを使用してください）

---

## 環境変数（主要なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション（デフォルト値は実装参照）:
- KABUSYS_ENV: development | paper_trading | live（default: development）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- LOG_LEVEL: INFO 等
- OPENAI_API_KEY: OpenAI を利用する機能で必要
- PAPER_FILL_MODE: instant | partial | never | reject
- KILL_FLAG_CLEAR_ON_START: 0/1（本番で 1 は危険）

注意:
- 自動で .env をロードする仕組みがあり、プロジェクトルートに `.env` / `.env.local` があれば読み込まれます。自動ロードを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## セットアップ手順（開発/運用）

1. リポジトリをクローンしてワークスペースに入る
2. 仮想環境を作成して依存をインストール
   - 例:
     ```bash
     python -m venv .venv
     source .venv/bin/activate
     pip install duckdb psutil openai PyYAML
     ```
3. 環境変数設定
   - 推奨: 対話式ウィザードで `.env` を作成
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザード完了後、設定を検証:
     ```bash
     python -m kabusys.validate_config
     # 警告も FAIL にしたい場合:
     python -m kabusys.validate_config --strict
     ```
4. 必要なディレクトリ（例: data/, logs/）が自動作成されますが、権限やパスを確認してください。

---

## 使い方（起動・実行）

- 発注エンジン（ExecutionEngine）起動:
  - 本番/ペーパーは KABUSYS_ENV に依存
  - コマンド:
    ```bash
    python -m kabusys.run_execution
    ```
  - 補足:
    - KABUSYS_ENV=paper_trading の場合、MockBrokerClient が使用され、データは PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）へ分離して記録されます。
    - 起動時に data/stop_requested.flag が存在すると起動をスキップします。
    - 実行中は pid ファイル（data/execution.pid など）を作成します。

- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は Settings.sqlite_path（monitoring 用 DB）を参照します。run_monitoring は KABUSYS_ENV に関係なく本番 sqlite_path を使用します。
  - 停止: data/stop_requested.flag を作成すると監視ループは終了します。

- Paper Trading 検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB を指定:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから利用）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)
  - どちらも OPENAI_API_KEY（引数または環境変数）を必要とします。

---

## 停止 / Kill Switch の挙動

- data/kill.flag: Kill Switch が書き込むファイル。ExecutionEngine に対する停止シグナルとして使用します。
- data/stop_requested.flag: スクリプト（run_monitoring, run_execution）が監視している "停止リクエスト" フラグ。存在すると起動やループを終了します。
- KillSwitch（監視モジュール）はリスク異常（ドローダウン超過・ポジション上限など）を検知すると kill.flag を生成します。KILL_FLAG_CLEAR_ON_START=1 を本番で設定するのは危険です（自動クリアされるため）。

---

## ディレクトリ構成（主要ファイルと役割）

以下はパッケージ内の主要ファイル・モジュールとその説明です（src/kabusys/ 以下）:

- __init__.py
  - バージョンと公開モジュール定義

- config.py
  - Settings クラス: 環境変数の取得・検証、自動 .env 読み込みロジック

- config_setup.py
  - .env 対話式ウィザード（python -m kabusys.config_setup）

- validate_config.py
  - 起動前の設定検証 CLI（python -m kabusys.validate_config）

- run_execution.py
  - ExecutionEngine 起動スクリプト（発注エンジン）

- run_monitoring.py
  - Monitoring のポーリングループ起動スクリプト

- monitoring/
  - monitoring_db.py: SQLite の監視テーブル初期化と読み書きユーティリティ
  - monitoring_engine.py: 各 Monitor を束ねる監視エンジン
  - system_monitor.py: システム資源・データ鮮度・プロセス生存監視
  - trade_monitor.py: 発注/約定ログの監視（stale order 等）
  - risk_monitor.py: ドローダウン / ポジション上限監視
  - kill_switch.py: kill.flag 生成/管理
  - alert_manager.py: （アラート通知機能。LINE 等に送信する実装が入る想定）

- execution/
  - broker_factory.py, execution_engine.py, order_manager.py, risk_manager.py, reconciler.py, order_repository.py
  - 発注の実装・抽象化（MockBrokerClient を含む）

- portfolio/
  - portfolio_builder.py: 候補選定・重み計算
  - position_sizing.py: 発注株数計算・集約制限
  - risk_adjustment.py: セクターキャップ・レジーム乗数

- research/
  - factor_research.py: momentum / volatility / value 等のファクター計算（DuckDB を想定）
  - feature_exploration.py: 将来リターン計算、IC、統計サマリ

- ai/
  - news_nlp.py: ニュースの LLM によるセンチメントスコア化（ai_scores への書込み）
  - regime_detector.py: MA200 と LLM を組み合わせた市場レジーム判定

- data/
  - （運用で生成されるファイル配下: monitoring.db, paper_trading.db, kill.flag, execution.pid, stop_requested.flag など）

- logs/
  - ログ出力先（setup_logging を通じて日次ローテーションで出力）

---

## DB・ログの既定パス

- DuckDB: data/kabusys.duckdb（DUCKDB_PATH）
- SQLite (monitoring): data/monitoring.db（SQLITE_PATH）
- Paper Trading SQLite: data/paper_trading.db（PAPER_TRADING_SQLITE_PATH）
- ログディレクトリ: logs/（LOG_DIR 環境変数で上書き可）

---

## 開発者向けメモ / 注意事項

- 設定の自動ロード: config.py はプロジェクトルート（.git または pyproject.toml）から `.env` を自動ロードします。テストで自動ロードを無効にする場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB マイグレーション: monitoring_db.init_monitoring_db() は既存 DB に対して冪等にスキーマ作成・簡易マイグレーション（カラム追加）を行います。
- OpenAI 呼び出し: news_nlp / regime_detector は API エラーやレート制限に対して指数バックオフのリトライ処理を持ちます。API キーと呼び出し制限に注意してください。
- ロギング: setup_logging(app_name=...) を各起動スクリプトで呼ぶことで統一したログ出力（コンソール + 日次ファイルローテーション）が使えます。
- Paper Trading と Live の分離: paper_trading 環境は発注をシミュレートし、専用 DB に記録するため本番 DB と分離されます。環境切替には必ず KABUSYS_ENV を確認してください。

---

## よく使うコマンドまとめ

- .env 作成:
  ```bash
  python -m kabusys.config_setup
  ```
- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```
- 発注エンジン起動:
  ```bash
  python -m kabusys.run_execution
  ```
- 監視起動:
  ```bash
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば README にチュートリアル（サンプル .env、cron/systemd の例、テスト用のモック設定等）を追加できます。どの内容を追記しますか？