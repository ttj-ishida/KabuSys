# KabuSys

日本株自動売買システムのコードベース（ライブラリ＋起動スクリプト群）。  
本リポジトリは、シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI を組み合わせた運用/検証用ツール群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株の自動売買ワークフローを構成するモジュール群です。主な機能は次の通りです。

- データ分析／研究（DuckDB ベース）
- ファクター計算・特徴量探索（research）
- ポートフォリオ構築・ポジションサイズ決定（portfolio）
- 発注ロジック（ExecutionEngine、MockBroker を含む）
- 監視・アラート（MonitoringEngine、Kill Switch、監視 DB）
- ニュース NLP（OpenAI を用いたニュースセンチメント）
- 環境設定ウィザード・設定検証ツール
- ペーパートレード用検証レポート生成ツール

設計上、分析・研究用モジュールは本番の発注 API とは依存分離されており、ペーパートレード機能を利用して安全に検証できます。

---

## 主な機能一覧

- kabusys.config: 環境変数 / .env 読み込みと Settings クラス（既定値・バリデーション）
- config_setup: 対話式で .env を生成・更新するウィザード
- validate_config: .env や config/*.yaml の事前チェック CLI
- run_execution: ExecutionEngine の起動スクリプト（KABUSYS_ENV=paper_trading 時は MockBroker を使用）
- run_monitoring: SystemMonitor ポーリングループ起動スクリプト（MONITOR_POLL_INTERVAL で間隔を調整可能）
- monitoring: SystemMonitor、TradeMonitor、RiskMonitor、KillSwitch、MonitoringEngine、SQLite ベースの監視永続化
- portfolio: 候補選定・重み計算・ポジションサイズ決定・セクターキャップ・レジーム乗数
- research: ファクター計算（モメンタム/ボラティリティ/バリュー）・将来リターン・IC・統計サマリ
- ai: ニュース NLP（OpenAI を利用）・市場レジーム判定ロジック
- tools.paper_verification_report: ペーパートレード結果の検証レポート生成スクリプト

---

## 前提・依存

必須（環境により異なる）：

- Python 3.9+（コード内の型ヒント等を前提）
- パッケージ（一例）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検証を行う場合）
- SQLite（標準ライブラリに含まれます）
- ネットワークアクセス（OpenAI / 各 API を利用する場合）

依存のインストールは仮想環境（venv/virtualenv/conda 等）を推奨します。

例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

主要な任意/デフォルト:
- KABUSYS_ENV — 実行環境（development / paper_trading / live）。デフォルト: development
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（デフォルト: INFO）
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
- OPENAI_API_KEY — OpenAI API キー（ai.news_nlp / ai.regime_detector で使用）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant / partial / never / reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START — Execution 起動時に kill.flag を自動クリアするか（"1" で有効）

詳しい一覧とデフォルトは kabusys.config.Settings を参照してください。

---

## セットアップ手順（基本）

1. リポジトリをクローンし、仮想環境を作成して有効化する。
2. 必要な Python パッケージをインストールする（duckdb, psutil, openai, pyyaml 等）。
3. .env を準備する
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
     これによりプロジェクトルートに `.env`（既定）を生成できます。
   - あるいは、手動で環境変数を設定する。
4. 設定検証（任意、起動前に推奨）:
   ```
   python -m kabusys.validate_config
   python -m kabusys.validate_config --strict
   ```
5. データベースとログディレクトリの権限やディレクトリ構成を確認する（デフォルトの data/ logs/ 等）。
6. 実行（下記参照）。

---

## 使い方（コマンド例）

- ExecutionEngine（実際の発注／ペーパートレード）を起動:
  ```
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading を指定すると paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）と MockBrokerClient を使います。
  - 起動時、data/execution.pid に PID を書き込みます。
  - 停止は data/stop_requested.flag を作成するか、プロセスを SIGINT（Ctrl+C）で終了します。
  - Kill Switch（data/kill.flag）が立っている場合は起動を中止するオプションがあります。

- Monitoring（監視ループ）を起動:
  ```
  python -m kabusys.run_monitoring
  ```
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
  - 監視は本番用 sqlite_path（Settings.sqlite_path）を使って永続化します。
  - 停止は data/stop_requested.flag を作成するか Ctrl+C。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポートを生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  または DB を直接指定:
  ```
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- ライブラリ API（プログラムから使用）:
  - ファクター計算:
    ```
    from kabusys.research import calc_momentum, calc_volatility, calc_value
    ```
  - ポートフォリオ・ポジション計算:
    ```
    from kabusys.portfolio import select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes
    ```
  - AI ニューススコアリング（プログラム呼び出し）:
    ```
    from kabusys.ai import score_news
    # score_news(conn, target_date, api_key=None)
    ```

---

## 注意事項 / 運用上のポイント

- Kill Switch:
  - data/kill.flag を作成すると ExecutionEngine に対して停止シグナルを送れます（KillSwitch が評価してフラグを書きます）。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に自動で kill.flag を削除しますが、本番環境では無効 (0) を推奨します。
- ログ:
  - ログはデフォルトで logs/ に日次ローテーションで保存されます。LOG_DIR で変更可能。
- ペーパートレード:
  - KABUSYS_ENV=paper_trading 時は本番 DB とは分離された PAPER_TRADING_SQLITE_PATH を使用します。
- OpenAI:
  - AI モジュールを利用するには OPENAI_API_KEY が必要です。API 呼び出しはリトライやフェイルセーフを組み込んでいますが、API 使用量に注意してください。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は既存 DB に対して冪等にテーブル作成と必要なカラム追加（マイグレーション）を行います。

---

## ディレクトリ構成（抜粋）

（パッケージルート: src/kabusys）

- run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py — ExecutionEngine 起動スクリプト
- config.py — .env 自動読み込み、Settings クラス
- config_setup.py — .env 対話型ウィザード
- validate_config.py — 起動前チェック CLI

- ai/
  - news_nlp.py — ニュースの LLM スコアリング（ai_scores 書き込み）
  - regime_detector.py — 市場レジーム判定（ETF + マクロ NLP 合成）
  - __init__.py

- research/
  - factor_research.py — モメンタム/ボラティリティ/バリュー計算（DuckDB）
  - feature_exploration.py — 将来リターン・IC・統計
  - __init__.py

- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 発注株数計算・スケールダウン・lot 単位処理
  - risk_adjustment.py — セクターキャップ・レジーム乗数
  - __init__.py

- monitoring/
  - monitoring_db.py — SQLite 永続化レイヤ（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム状態 & データ鮮度監視
  - trade_monitor.py —（取引監視。コードベースに定義あり）
  - risk_monitor.py — ドローダウン & ポジション上限監視
  - kill_switch.py — kill.flag 書き込みユーティリティ
  - monitoring_engine.py — 各 Monitor を束ねるポーリングエンジン
  - alert_manager.py —（アラート送信管理。コードベースに定義あり）

- execution/
  - execution_engine.py — 発注セッションのコントローラ（Engine）
  - order_manager.py, order_repository.py, reconciler.py, risk_manager.py, broker_factory.py — 発注関連ユーティリティ

- data/ (ランタイムで生成される想定)
  - monitoring.db（SQLITE_PATH）
  - paper_trading.db（PAPER_TRADING_SQLITE_PATH）
  - kill.flag, stop_requested.flag, execution.pid

- utils/
  - logging_setup.py — 統一的なログ設定（console + TimedRotatingFile）
  - process_priority.py — プロセス優先度 / CPU affinity 設定

- tools/
  - paper_verification_report.py — ペーパートレード検証レポート生成スクリプト

---

## よく使うファイル / フラグの説明

- data/stop_requested.flag — run_monitoring / run_execution の停止チェックに使用する外部フラグ
- data/kill.flag — KillSwitch により書き込まれるフラグ（Execution の即時停止トリガー）
- data/execution.pid — run_execution が書き込む PID ファイル
- logs/<app_name>.log — ログファイル（app_name: execution / monitoring など）

---

## 開発者向けメモ

- DuckDB 接続を渡して pure functions を呼ぶ設計が多く、テストしやすくなっています（外部副作用を最小化）。
- AI 関連のネットワーク呼び出し部分は内部でリトライ/バックオフやレスポンス検証を行い、失敗時はフォールバックする設計です。
- 設定の自動ロードはプロジェクトルートの検出（.git または pyproject.toml）に基づき行われます。不要な自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます。
- CLI での設定検証やウィザードを活用してから起動してください。

---

この README はコードベースの主要点をまとめたものです。実行や運用の詳細は各モジュール（特に run_execution.py、run_monitoring.py、config_setup.py、validate_config.py、ai/*.py、monitoring/*.py）内の docstring やログ出力を参照してください。質問や追加したい内容があれば教えてください。