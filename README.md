# KabuSys

日本株自動売買システムのコンポーネント群（ライブラリ・起動スクリプト・ツール類）のリポジトリです。  
この README はリポジトリ内の主要モジュールに基づいて、導入・起動方法、機能一覧、ディレクトリ構成などをまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買基盤を想定したモジュール群です。主な機能は以下の通りです。

- データ収集／分析（DuckDB ベース）
- シグナル生成／ポートフォリオ構築（純関数モジュール）
- 発注実行エンジン（本番 / ペーパートレード切替対応）
- 実行監視（システム状態、注文・リスク監視、Kill Switch）
- AI 支援（OpenAI を使ったニュースセンチメント評価・レジーム判定）
- 開発支援ツール（対話式 .env 作成、設定検証、ペーパートレード検証レポートなど）

設計方針の要点：
- 環境変数 / .env による構成管理
- 本番とペーパートレードの DB 分離
- ルックアヘッドバイアスの排除（日時参照の扱いに注意）
- フェイルセーフ（API 失敗時は安全側にフォールバック）

---

## 機能一覧（主なモジュール）

- 起動スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動
  - run_execution.py : ExecutionEngine の起動（KABUSYS_ENV=paper_trading 時は MockBroker）
- 設定・ユーティリティ
  - config.py: 環境変数 / .env 自動読み込み・Settings クラス
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前チェック CLI（--strict あり）
  - utils/logging_setup.py: 共通のログ設定ユーティリティ
  - utils/process_priority.py: プロセス優先度 / CPU affinity 設定
- 監視（monitoring）
  - monitoring_db.py: SQLite による監視ログ永続化層
  - system_monitor.py: CPU/メモリ/ディスク・データ鮮度・プロセス監視
  - trade_monitor.py:（注文ログ監視、滞留注文検出等 — ソース参照）
  - risk_monitor.py: ドローダウン・ポジション上限の監視
  - monitoring_engine.py: 各 Monitor を束ねるポーリングエンジン
  - kill_switch.py: data/kill.flag による ExecutionEngine 停止
  - alert_manager.py:（LINE 等への通知管理 — ソース参照）
- 発注・実行（execution）: ExecutionEngine、OrderManager、RiskManager、Reconciler 等（発注ロジック）
- ポートフォリオ（portfolio）
  - portfolio_builder.py: 候補選定・ウェイト計算
  - position_sizing.py: 発注株数計算・資金制約の適用
  - risk_adjustment.py: セクターキャップ・レジーム乗数
- 研究（research）
  - factor_research.py: モメンタム／ボラティリティ／バリュー等の計算（DuckDB 経由）
  - feature_exploration.py: 将来リターン / IC 計算、統計サマリ
- AI（ai）
  - news_nlp.py: ニュースの LLM センチメント評価（OpenAI） → ai_scores へ保存
  - regime_detector.py: マクロ + ETF MA を組み合わせた市場レジーム判定
- ツール（tools）
  - paper_verification_report.py: ペーパートレード検証レポート生成

---

## セットアップ手順

前提
- Python 3.9+（実装は型ヒント・機能によっては 3.10+ を推奨）
- システムにより追加のネイティブライブラリが必要な場合あり（psutil 等）

1. リポジトリをクローンしてワークディレクトリへ移動
   - git clone (repo)
   - cd (repo)

2. 仮想環境作成（任意だが推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 依存ライブラリをインストール
   - 必須例:
     - duckdb
     - psutil
     - openai
     - （オプション）PyYAML（config 検証で YAML をパースする場合）
   - 例:
     - pip install duckdb psutil openai PyYAML

   ※ requirements.txt がある場合はそれを使用してください（このコードスニペットでは同梱されていません）。

4. .env の準備
   - 対話式ウィザード:
     - python -m kabusys.config_setup
   - 生成後、設定を検証:
     - python -m kabusys.validate_config
     - 本番チェックを厳格にする場合は --strict を付ける

5. データディレクトリ作成（必要に応じて）
   - デフォルト SQLite / DuckDB / logs ディレクトリは自動作成を試みますが、権限により失敗することがあります。
   - data/ と logs/ を事前に作成しておくと安全です:
     - mkdir -p data logs

---

## 環境変数（主要なもの）

- JQUANTS_REFRESH_TOKEN: J-Quants API（必須）
- KABU_API_PASSWORD: kabuステーション API（必須）
- KABUSYS_ENV: 実行環境（development | paper_trading | live） — デフォルト development
  - paper_trading: 発注は MockBroker、DB は data/paper_trading.db に分離
  - live: 本番モード（注意して設定）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（ai モジュール使用時）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- LOG_DIR: ログ出力先ディレクトリ（デフォルト logs/）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: MockBroker の約定モード（instant|partial|never|reject）

例（.env の一部）
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...
```

---

## 使い方（起動・コマンド）

各モジュールはパッケージとして実行できます（python -m kabusys.<module>）。

- 対話式 .env 作成
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - 厳格モード（警告も失敗扱い）:
    - python -m kabusys.validate_config --strict

- 監視プロセスを起動（SystemMonitor のポーリング）
  - 環境変数 MONITOR_POLL_INTERVAL によってポーリング間隔を変更できます（秒）。
  - 例: MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  - 停止方法:
    - data/stop_requested.flag を作成するとループを検知して終了します（または Ctrl+C）。

- 実行エンジン（ExecutionEngine）を起動
  - python -m kabusys.run_execution
  - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、ペーパートレード専用 DB に書き込まれます。
  - 起動時に data/stop_requested.flag が存在すると起動を中止します。
  - 停止は data/stop_requested.flag を作成するか、Execution 側の Kill Switch（data/kill.flag）で止める仕組みがあります。

- ペーパートレード検証レポート生成
  - python -m kabusys.tools.paper_verification_report --from YYYY-MM-DD --to YYYY-MM-DD
  - DB パスを指定する場合:
    - python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db

- AI モジュール（ニュース評価 / レジーム判定）
  - ai.news_nlp.score_news / ai.regime_detector.score_regime を呼び出すか、用途に応じた CLI を用意して利用してください。
  - 実行には OPENAI_API_KEY が必要です。

---

## Kill Switch / 停止フラグ

- data/kill.flag
  - kill_switch モジュールが条件を満たしたときに書き込まれるフラグファイルです。ExecutionEngine はこれを検知して安全に停止します。
  - KillSwitch.clear() によって起動時に自動クリア（設定 KILL_FLAG_CLEAR_ON_START=1）できますが、本番では 0 を推奨します。
- data/stop_requested.flag
  - run_monitoring / run_execution のループを止めたり、起動を中止するためのシンプルな停止フラグです（手動で作成できます）。

---

## ロギング

- 共通ロギングは utils/logging_setup.setup_logging を使って設定されます。
- デフォルトは stdout 出力と logs/<app_name>.log（日次ローテーション・30日保持）への出力です。
- 環境変数:
  - LOG_LEVEL（例: DEBUG, INFO）
  - LOG_DIR（ログ保存ディレクトリ）

---

## トラブルシューティング

- DB ファイルに対する書き込み権限がない場合、ファイル/ディレクトリ作成に失敗します。事前に data/ と logs/ の所有権/権限を確認してください。
- OpenAI 呼び出しで API エラーが発生した場合、モジュールはリトライ・フェイルセーフを行いますが、API キーが無いと明示的にエラーを投げます。
- psutil による優先度設定や CPU affinity は権限により失敗することがあります。失敗時は警告ログが出ますが動作自体は継続します。
- validate_config での警告やエラーは、起動前に必ず確認してください（特に KABUSYS_ENV=live の場合）。

---

## ディレクトリ構成

（主要ファイルのみ抜粋）

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_monitoring.py
  - run_execution.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照元に存在する想定)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/ (上記)
  - data/ (実行時生成されることが多い)
  - logs/ (ログ出力先)

---

## 開発・拡張メモ

- DuckDB を用いた分析処理は SQL と Python を組み合わせて実装されています。prices_daily / raw_financials 等のテーブルが必要です。
- portfolio や position sizing の関数は純粋関数として設計されており、ユニットテストが書きやすい構成です。
- AI 関連は OpenAI SDK に依存します。API のレスポンス形式変化に対して寛容になるよう設計されていますが、SDK のバージョンアップ時はテストを行ってください。
- 構成ファイル（config/*.yaml）や .env のテンプレートは scripts や別ドキュメントで生成/管理する想定です。validate_config は存在確認・パース検証を行います（PyYAML 非インストール時はパース検証をスキップ）。

---

もし README の特定セクション（例: デプロイ手順や systemd / Windows サービスでの常駐化、より詳細な設定例）を追加したい場合は教えてください。必要に応じてサンプル .env や systemd ユニットのテンプレートも作成します。