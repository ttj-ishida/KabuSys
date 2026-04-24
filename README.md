# KabuSys

日本株向け自動売買システムのライブラリ/ツール群（実行エンジン・監視・ポートフォリオ構築・研究・AI補助など）。  
このリポジトリは複数の起動スクリプトとモジュール群で構成され、ローカル開発からペーパートレード / 本番運用までを想定しています。

バージョン: 0.1.0

---

## 概要

KabuSys は次のような責務を分離して実装しています。

- ExecutionEngine（発注・注文管理・リスク管理）
- Monitoring（システム健全性・注文ログ・リスク監視・Kill Switch）
- Portfolio Construction（候補選定・重み計算・ポジションサイズ算出）
- Research（ファクター計算・特徴量解析）
- AI モジュール（ニュースセンチメント評価・レジーム判定）
- ユーティリティ（ロギング設定、プロセス優先度制御、環境設定ウィザード等）
- CLI ツール（.env 作成ウィザード、設定検証、Paper Trading レポートなど）

設計上のポイント:
- DuckDB を分析用 DB、SQLite を監視/注文ログ用に使用
- 環境変数 `.env` による設定、`.env.local` で上書き可能
- Paper trading（模擬発注）と Live（実発注）を明確に分離
- OpenAI を用いたニュース NLP / レジーム判定の統合（任意）

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用して data/paper_trading.db に記録
  - リスク管理（max position, drawdown 等）
- 監視ループ（run_monitoring.py）
  - CPU/メモリ/ディスクやプロセス存否・データ鮮度の定期チェック
  - Kill Switch の評価・通知（条件満たしたら data/kill.flag を作成）
  - ポーリング間隔は環境変数で変更可能（MONITOR_POLL_INTERVAL）
- ポートフォリオ構築ユーティリティ
  - 候補選定、等重・スコア重み、リスク調整、ポジションサイズ決定
- リサーチ/ファクター計算（DuckDB に対する純粋関数）
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン・IC（Information Coefficient）計算
- AI モジュール（OpenAI）
  - ニュースを集約して銘柄ごとにセンチメント（ai_scores）を算出
  - ETF を用いた市場レジーム判定（market_regime）
- ツール
  - 環境設定ウィザード: python -m kabusys.config_setup
  - 設定検証 CLI: python -m kabusys.validate_config
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## 必要条件 / 推奨環境

- Python 3.10 以上（型アノテーションに `X | None` 形式を使用）
- 必須 Python パッケージ（用途に応じてインストール）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML (config YAML の検証を行う場合)
- SQLite（標準ライブラリに同梱）
- ネットワークアクセス（kabuステーション API, OpenAI を使う場合）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. レポジトリをクローン
2. Python 仮想環境を作成して依存をインストール（上記参照）
3. .env の作成
   - 対話式ウィザード: python -m kabusys.config_setup
   - 手動で作る場合はプロジェクトルートに `.env` を配置（.env.example を参考に）
   - 主要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
     - DUCKDB_PATH（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH（デフォルト data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - LOG_LEVEL（例: INFO）
4. 設定検証（推奨）
```
python -m kabusys.validate_config
# 警告もエラー扱いにしたい場合:
python -m kabusys.validate_config --strict
```
5. 必要に応じて data/ ディレクトリや logs/ を作成（多くは自動作成されますがパーミッション等を確認）

---

## 使い方（実行例）

- ExecutionEngine（取引エンジン）を起動
  - 本番/開発/ペーパートレードは KABUSYS_ENV に依存
  - 起動:
    ```
    python -m kabusys.run_execution
    ```
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、data/paper_trading.db に記録されます

- Monitoring（監視ループ）を起動
  - ポーリング間隔を秒で指定（デフォルト 60 秒）
  - MONITOR_POLL_INTERVAL 環境変数で上書き:
    ```
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 監視は Settings.sqlite_path（通常 data/monitoring.db）を使用します（モニタは本番 DB を参照）

- 環境設定ウィザード（.env 作成）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI モジュール（ニューススコアリング / レジーム）をプログラムから呼ぶ
  - OpenAI API キーが必要（OPENAI_API_KEY もしくは関数引数で渡す）
  - 例（Python 内）:
    ```
    from kabusys.ai.news_nlp import score_news
    from kabusys.ai.regime_detector import score_regime

    # DuckDB 接続 conn を用意してから
    score_news(conn, target_date=date(2026,4,10), api_key="sk-...")
    score_regime(conn, target_date=date(2026,4,10), api_key="sk-...")
    ```

- ログ
  - デフォルトでコンソール出力とファイル出力を併用
  - ログファイルは logs/<app_name>.log（例: logs/execution.log）
  - ロギングは kabusys.utils.logging_setup.setup_logging より統一設定

---

## 重要なファイル/フラグ

- data/stop_requested.flag
  - run_execution / run_monitoring の起動ループで検知される停止フラグ
- data/kill.flag
  - Kill Switch（監視で致命的条件を検出したときに作成） — ExecutionEngine 停止の信号
- data/execution.pid
  - ExecutionEngine の PID ファイル（デフォルトパスは Settings.pid_file_path）
- DB デフォルトパス
  - DuckDB: data/kabusys.duckdb
  - SQLite (monitoring): data/monitoring.db
  - Paper trading SQLite: data/paper_trading.db

---

## ディレクトリ構成

ここでは主要なファイル/モジュールを示します（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py
    - 環境変数 / Settings クラス、自動 .env ロード
  - config_setup.py
    - .env 対話式ウィザード
  - validate_config.py
    - 起動前設定検証 CLI
  - run_execution.py
    - ExecutionEngine 起動スクリプト
  - run_monitoring.py
    - Monitoring 起動スクリプト
  - utils/
    - logging_setup.py
      - 共通ロギング設定（stdout + 日次ローテートファイル）
    - process_priority.py
      - プロセス優先度・CPU affinity 設定ユーティリティ
  - execution/
    - execution_engine.py, order_manager.py, risk_manager.py, broker_factory.py, ...
    - （発注ロジック・OrderRepository 等）
  - monitoring/
    - monitoring_db.py
      - SQLite スキーマ初期化 + DB 操作ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - alert_manager.py, kill_switch.py, ...
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - portfolio 関連の純粋関数群（DB に依存しない）
  - research/
    - factor_research.py
    - feature_exploration.py
    - DuckDB を使ったファクター・統計処理
  - ai/
    - news_nlp.py
      - ニュースを LLM でスコアリングし ai_scores に書き込む
    - regime_detector.py
      - ETF MA とマクロニュースの LLM を合成して市場レジーム判定
  - tools/
    - paper_verification_report.py
      - Paper Trading の検証／サマリ出力

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では .env の管理に注意し、.env は絶対に Git にコミットしないこと
- kill_flag や stop フラグの自動クリアは危険（KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨）
- AI（OpenAI）呼び出しはコストが掛かるため、API キーの管理と呼び出し頻度に注意
- ロギングは必ず確認し、ログディレクトリのパーミッション（書込み可能）を事前にチェック
- データ鮮度や監視アラートは本番前にチューニング（閾値等）を行うこと

---

## 開発 / テスト

- モジュールは可能な限り純粋関数に分離（副作用を最小化）しているため、ユニットテストが書きやすい設計
- OpenAI 呼び出し部分はパッチ可能（テストでネットワーク依存を避ける）
- validate_config.py や monitoring_engine.run_once() 等は CI / テストで利用しやすい

---

必要な情報や具体的な起動・設定例を追加で望む場合は、利用シナリオ（開発環境 / ペーパートレード / 本番）を教えてください。README に例の .env テンプレートや systemd / Supervisor の起動ユニット例を追記できます。