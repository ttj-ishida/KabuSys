# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買に必要なコンポーネント（シグナル生成、ポートフォリオ構築、発注実行、監視、リスク管理、研究用ユーティリティ、AI を使ったニュース解析）を含むモジュール群です。  
設計方針としては「本番/ペーパーを明確に分離」「DB はファイルベース（SQLite / DuckDB）」「外部 API 呼び出しは明示的に制御」「ログ・監視・Kill Switch による安全停止」を重視しています。

主な実装要素（抜粋）:
- ExecutionEngine（発注エンジン）と Broker クライアント（本番／Mock 切替）
- Monitoring（System / Trade / Risk モニタ）と Kill Switch（リスク時に自動停止）
- Portfolio 構築・ポジションサイズ計算モジュール
- Research（ファクター計算、IC 計算、特徴量探索）
- AI モジュール（ニュースセンチメント、レジーム判定） — OpenAI API を利用
- ユーティリティ（ログ設定、プロセス優先度設定、.env ウィザード、設定検証）
- ツール（Paper Trading の検証レポート生成）

---

## 主な機能一覧

- 発注・注文管理（ExecutionEngine, OrderManager, OrderRepository）
- リスク管理（RiskManager, RiskMonitor）
- システム監視（SystemMonitor）: CPU/メモリ/ディスク/プロセス・データ鮮度監視
- モニタリングエンジン（MonitoringEngine）: 各種モニタの定期実行、アラート通知連携
- Kill Switch: ドローダウンやポジション上限超過で data/kill.flag を書き出し自動停止
- Paper Trading: 本番 DB と分離した paper_trading 用 SQLite に記録して検証
- Paper Trading 検証レポート出力（tools.paper_verification_report）
- AI ベースのニュースセンチメント（ai.news_nlp）および市場レジーム判定（ai.regime_detector）
- Research 用ファクター計算（momentum, volatility, value）および forward returns / IC / summary
- .env 対話式セットアップ（config_setup）と設定検証 CLI（validate_config）
- ログはコンソール（stdout）＋日次ローテートファイル（logs/*.log）

---

## 要件（開発者向け）

- Python 3.9+
- 依存ライブラリ例（プロジェクトの requirements.txt を参照してください）:
  - duckdb
  - psutil
  - openai
  - PyYAML （config YAML の検証に必要だが必須ではない）
  - その他（プロジェクトが必要とするパッケージ群）

---

## セットアップ手順

1. リポジトリをクローン・チェックアウト
   - 任意の方法でソースを取得してください。

2. 仮想環境を作成・有効化（例）
   - python -m venv .venv
   - source .venv/bin/activate  # (macOS/Linux)
   - .venv\Scripts\activate     # (Windows)

3. 依存パッケージをインストール
   - pip install -r requirements.txt
   （requirements.txt が無い場合はプロジェクトで使用しているパッケージを個別にインストールしてください）

4. .env の作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
     - 対話に従って J-Quants、kabuAPI パスワード、DB パス、KABUSYS_ENV などを設定します。
   - あるいは手動で .env を作成（.env.example を参照）

5. 設定の検証
   - python -m kabusys.validate_config
   - 本番環境では --strict を付けると警告もエラー扱いになります:
     - python -m kabusys.validate_config --strict

6. データ／ログディレクトリ作成（必要に応じて）
   - デフォルトでは data/ と logs/ を使用します。ウォーニングが出る場合は手動で作成してください。
   - mkdir -p data logs

---

## 主要な環境変数（代表）

- 必須
  - JQUANTS_REFRESH_TOKEN — J-Quants API 用のリフレッシュトークン
  - KABU_API_PASSWORD — kabuステーション API のパスワード

- 実行環境
  - KABUSYS_ENV — one of: development, paper_trading, live（デフォルト: development）

- データベース
  - DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH — 監視 DB（デフォルト: data/monitoring.db）
  - PAPER_TRADING_SQLITE_PATH — ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）

- ログ・監視
  - LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - LOG_DIR — ログ保存ディレクトリ（デフォルト: logs/）
  - MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、デフォルト: 60）
  - PID_FILE_PATH — ExecutionEngine の pid ファイルパス（デフォルト: data/execution.pid）
  - KILL_FLAG_PATH — Kill Switch が書き込むフラグ（デフォルト: data/kill.flag）
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（1=クリア, デフォルト: 0）

- Paper Trading / Mock Broker
  - PAPER_FILL_MODE — instant|partial|never|reject（ペーパートレード時の約定挙動）

- OpenAI
  - OPENAI_API_KEY — OpenAI API を使う機能（ニュース NLP / regime_detector）で使用

- その他
  - MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD — 自動 .env ロードを無効化（テスト等で使用）

---

## 使い方（起動例）

- 設定検証（必ず実行して問題を確認）
  - python -m kabusys.validate_config

- 対話式 .env 作成
  - python -m kabusys.config_setup

- 発注エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - 注意:
    - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使い、data/paper_trading.db に記録されます（本番 DB と分離）。
    - 起動時に data/stop_requested.flag が既にある場合は起動せず終了します。
    - 停止は stop_requested.flag を作成する（data/stop_requested.flag を touch）か、プロセスに SIGINT を送る。

- 監視ループ（SystemMonitor を定期実行）
  - python -m kabusys.run_monitoring
  - 環境変数 MONITOR_POLL_INTERVAL で秒数を上書き可能（例: export MONITOR_POLL_INTERVAL=30）
  - 監視は常に本番の sqlite_path を使う（環境に依らず）

- Paper Trading 検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - --db で DB ファイルを指定可能（優先順位: --db > PAPER_TRADING_SQLITE_PATH > デフォルト）

- AI ニューススコア（プログラム API）
  - ai.score_news は DuckDB 接続と target_date, api_key を渡して呼び出す（スクリプト CLI は提供していません）。
  - 例（ライブラリ呼び出し）:
    - from kabusys.ai import score_news
    - score_news(duckdb_conn, date(2026, 4, 12), api_key="...")

---

## 停止・Kill 動作について

- stop_requested.flag
  - data/stop_requested.flag が存在すると run_execution / run_monitoring はループを抜けて終了します（外部からの正常な停止リクエスト向け）。

- kill.flag（Kill Switch）
  - RiskMonitor / KillSwitch によってドローダウンやポジション上限超過が検出されると data/kill.flag が書き込まれます。これは ExecutionEngine に対する安全停止トリガです。
  - KILL_FLAG_CLEAR_ON_START=1 を設定すると起動時に kill.flag を自動クリアしますが、本番では危険なためデフォルトは 0（クリアしない）を推奨します。

---

## ログについて

- ログは stdout（コンソール）とファイル（logs/<app_name>.log、日次ローテート、30 日保持）に出力されます。
- ログ設定は kabusys.utils.logging_setup.setup_logging で統一的に設定されます。
- LOG_LEVEL / LOG_DIR 環境変数で挙動を変更できます。

---

## 主要な CLI / スクリプト一覧

- python -m kabusys.config_setup
  - .env を対話式に作成・更新
- python -m kabusys.validate_config [--strict]
  - 環境・config の検証
- python -m kabusys.run_execution
  - ExecutionEngine の起動（実行）
- python -m kabusys.run_monitoring
  - Monitoring のポーリング起動
- python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - Paper トレード検証レポート

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイルとディレクトリの抜粋です。

- src/
  - kabusys/
    - __init__.py
    - config.py                      # 環境変数・.env 自動ロード
    - config_setup.py                # .env ウィザード
    - validate_config.py             # 設定検証 CLI
    - run_execution.py               # ExecutionEngine 起動スクリプト
    - run_monitoring.py              # SystemMonitor 起動スクリプト
    - utils/
      - logging_setup.py             # ログ設定ユーティリティ
      - process_priority.py          # プロセス優先度 / CPU affinity
    - execution/                      # 発注関連（Engine / OrderManager 等）
      - execution_engine.py
      - order_manager.py
      - order_repository.py
      - reconciler.py
      - risk_manager.py
      - broker_factory.py
    - monitoring/
      - monitoring_db.py             # monitoring 用 SQLite 抽象化層
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
    - research/
      - factor_research.py
      - feature_exploration.py
    - ai/
      - news_nlp.py                   # OpenAI を用いたニュース NLP スコアリング
      - regime_detector.py            # 市場レジーム判定
    - tools/
      - paper_verification_report.py
    - data/                           # (実行時に使用される data/ 以下のファイル)
      - monitoring.db (デフォルト)
      - kabusys.duckdb (デフォルト)
      - paper_trading.db (ペーパートレード用)

（実際のリポジトリにはさらに多くの実装ファイルが含まれます）

---

## 注意事項 / 運用上のヒント

- 本番運用前に validate_config を使って必須環境変数や DB パス、設定ファイルの妥当性を確認してください。
- KABUSYS_ENV は本番（live）にすると重大な危険があるため、LINE 通知設定や kill flag の扱いなどを慎重に確認してください。
- OpenAI API を使用する機能は API キーやコスト、レスポンス品質に依存します。テスト環境で十分な検証を行ってください。
- ログディレクトリ（LOG_DIR）や data ディレクトリは適切なパーミッションで管理してください。
- stop_requested.flag / kill.flag の運用ルールをチームで定めてください（誰がいつ作成・削除するか）。

---

## 貢献 / 開発

- コードスタイルやユニットテスト、CI の整備を歓迎します。
- 新しい戦略や Broker クライアントは抽象化されたインターフェースに従って実装してください。
- 外部 API 呼び出し（特に実売買に関する部分）は必ずテストを行い、ペーパートレードでの検証から移行してください。

---

README に書かれている以外の詳細や特定モジュールのドキュメント（関数の引数や返り値の仕様など）が必要でしたら、どのモジュールについてどのような内容を追加するかを教えてください。