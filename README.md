# KabuSys

日本株向け自動売買システムの Python パッケージ（README）。  
この README はリポジトリ内の主要なモジュール実装に基づき、プロジェクト概要、機能、セットアップ手順、使い方、ディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株の自動売買・調査・監視機能を備えた小規模なシステムです。  
主な目的は以下を含みます：

- 売買シグナルに基づくポートフォリオ構築と発注（本番・ペーパートレード対応）
- システム監視・アラート（稼働率・データ鮮度・リスク監視）
- 研究用ファクター計算・特徴量解析（DuckDB を用いたオンメモリ／SQL ベース計算）
- ニュースの NLP 処理を用いたセンチメント評価（OpenAI API 利用）
- ペーパートレード検証レポート生成

設計方針の例：
- 外部 API キー等は .env（または環境変数）で管理
- ペーパートレードは本番 DB と分離（data/paper_trading.db）
- ロギングは統一的に設定し、ファイル出力は日次ローテーション

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（MockBroker）、live を切替
  - データベース接続、エンジンのスレッド実行、停止フラグ監視
- 監視ループ起動スクリプト（run_monitoring.py）
  - SystemMonitor をポーリングし system_status 等を記録
  - MONITOR_POLL_INTERVAL によるポーリング間隔変更可能
- 設定ウィザード（config_setup.py）
  - 対話式に .env を作成 / 更新
- 設定検証ツール（validate_config.py）
  - .env と config/*.yaml の基本チェック、--strict モードあり
- ポートフォリオ構築モジュール
  - 候補選定、等配分・スコア加重、ポジションサイズ計算、セクター制約、レジーム乗数など
- 研究モジュール（research）
  - モメンタム / ボラティリティ / バリュー等のファクター計算
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI モジュール（ai）
  - raw_news を OpenAI に投げて銘柄ごとのセンチメントスコアを生成（news_nlp）
  - マクロニュース + ETF MA200 を使って市場レジーム判定（regime_detector）
- 監視（monitoring）
  - MonitoringDB（SQLite）抽象化、RiskMonitor、TradeMonitor、KillSwitch、AlertManager 統合
- ユーティリティ
  - ログ設定（logging_setup）、プロセス優先度設定（process_priority）など
- ツール
  - Paper Trading の検証レポートジェネレータ（tools/paper_verification_report.py）

---

## 前提 / 必要条件

- Python 3.10 以上（型ヒントに | None 等を使用）
- 推奨パッケージ（例）
  - duckdb
  - psutil
  - openai
  - PyYAML（config の YAML 検査を行う場合）
- OS: Windows / Linux / macOS に対応（ただし一部機能は OS 固有の挙動あり）

例（最低限のインストール例）:
```
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. Python 仮想環境を作成・有効化（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate  # macOS/Linux
   .venv\Scripts\activate     # Windows
   ```
3. 必要なパッケージをインストール
   ```
   pip install duckdb psutil openai pyyaml
   ```
4. .env の初期作成
   - 対話式ウィザードを使う：
     ```
     python -m kabusys.config_setup
     ```
   - または手動で .env を作成（`.env.example` を参照して必要な値を設定）
     - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
     - その他: KABUSYS_ENV (development|paper_trading|live), DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, OPENAI_API_KEY（AI 機能利用時）など
5. 設定検証（推奨）
   ```
   python -m kabusys.validate_config
   # 警告も失敗とする場合:
   python -m kabusys.validate_config --strict
   ```
6. データディレクトリとログディレクトリの準備（通常は自動作成されますが、明示的に作る場合）
   ```
   mkdir -p data logs
   ```
7. （ペーパートレード）データベース初期化などはエンジン起動時に必要テーブルが作成されます

---

## 使い方（主要なコマンド / 実行例）

- 実行エンジン（ExecutionEngine）を起動
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV で切替
  ```
  # 例: development
  export KABUSYS_ENV=development
  python -m kabusys.run_execution
  ```
  - ペーパートレード時は paper_sqlite_path を使い DB を分離します（デフォルト: data/paper_trading.db）
  - 起動時に data/stop_requested.flag が存在すると起動を行わず終了します

- 監視ループを起動
  ```
  # ポーリング間隔を 30 秒にしたい場合
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
  - Monitoring は実行環境の KABUSYS_ENV に関わらず、監視用の sqlite_path を使用して永続化します（デフォルト: data/monitoring.db）
  - 停止は data/stop_requested.flag の作成で検知します

- 設定ウィザード
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート（ツール）
  ```
  # 期間指定
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # DB を明示する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```
  - 簡易ルールに基づいて PASS/FAIL 判定を行う（稼働率・成立率・送信率・P95 レイテンシ等）

- ライブラリ API の利用（コード内で呼ぶ例）
  ```python
  from datetime import date
  import duckdb
  from kabusys.research import calc_momentum, calc_volatility

  conn = duckdb.connect("data/kabusys.duckdb")
  res = calc_momentum(conn, date(2026, 4, 11))
  ```

- AI 機能（OpenAI API）を使う場合
  - 環境変数 `OPENAI_API_KEY` を設定するか、関数呼び出し時に api_key 引数を渡す
  - news_nlp.score_news(conn, target_date, api_key=None)
  - regime_detector.score_regime(conn, target_date, api_key=None)

---

## 重要な環境変数と動作メモ

- KABUSYS_ENV: execution 挙動の切替（development | paper_trading | live）
  - paper_trading: MockBroker を利用し、paper_sqlite_path を使用して DB を分離
  - live: 本番挙動（外部 API による実発注など）
- JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD: 必須
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト: data/paper_trading.db）
- DUCKDB_PATH: DuckDB 用ファイルパス（デフォルト: data/kabusys.duckdb）
- OPENAI_API_KEY: AI 機能利用時に必要
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PID ファイル / Kill Switch:
  - run_execution は data/execution.pid を用いる（pid ファイルパスは Settings.pid_file_path）
  - KillSwitch は Settings.kill_flag_path（デフォルト data/kill.flag）により Execution を停止させるためのフラグを作成

注意:
- Monitoring 側は監視テーブルの初期化を行います（init_monitoring_db）
- config_setup により生成された .env は絶対に Git にコミットしないでください

---

## 開発者向けメモ

- ログ設定は kabusys.utils.logging_setup.setup_logging を通じて統一的に行われます。デフォルトでは logs/<app_name>.log に日次ローテーションで出力します。
- process_priority.set_process_priority により起動スクリプトは優先度を "high" に設定しようとします。権限不足の場合は警告を出してスキップします。
- DuckDB を用いたデータ分析コードは外部 API を呼ばず、prices_daily / raw_financials 等のテーブルを前提としています。
- OpenAI との通信はやや堅牢化（リトライ・レスポンスバリデーション）されていますが、API レートやエラーの取り扱いを導入側でも監視してください。
- テスト時は OPENAI 呼び出し等をモックする設計になっています（コード内に patch 可能な呼び出し関数あり）。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主なファイルとモジュール（抜粋）です：

- src/
  - kabusys/
    - __init__.py
    - config.py                       — 環境変数 / 設定読み込み
    - config_setup.py                 — .env 対話式ウィザード
    - validate_config.py              — 設定検証 CLI
    - run_execution.py                — ExecutionEngine 起動スクリプト
    - run_monitoring.py               — SystemMonitor ポーリング起動スクリプト
    - utils/
      - logging_setup.py              — ログ設定ユーティリティ
      - process_priority.py           — プロセス優先度 / CPU affinity
    - execution/                       — (発注関連の実装群)
      - broker_factory.py
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
    - monitoring/
      - monitoring_db.py              — SQLite 永続化層
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - monitoring_engine.py
      - alert_manager.py
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

その他:
- data/      — データベース・フラグファイル置き場（例: monitoring.db, paper_trading.db, kill.flag, stop_requested.flag）
- logs/      — ログファイル出力先（LOG_DIR で変更可）
- config/    — YAML 設定ファイル群（system_config.yaml 等。validate_config で検査）

---

## よくある操作フロー（推奨）

1. .env を作成（config_setup）
2. validate_config で設定をチェック
3. DuckDB および SQLite の初期状態を確認（必要に応じてデータ投入）
4. 監視プロセスを起動（run_monitoring）
5. Execution を起動（run_execution）
6. ペーパートレードならツールで検証レポートを生成（paper_verification_report）

---

## ライセンス・貢献

本リポジトリのライセンス情報はプロジェクトルートの LICENSE ファイルを参照してください。  
バグ報告・機能改善提案・プルリクエストは歓迎します。

---

この README はコードベースの概要説明を目的としています。詳細な実装仕様や API の引数、戻り値などは各モジュールのドキュメント文字列（docstring）やソースコードを参照してください。疑問点があれば実装ファイルの該当箇所を指示していただければ、より詳細な説明を作成します。