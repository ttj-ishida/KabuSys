# KabuSys

日本株自動売買システムのリポジトリ（抜粋）。本READMEはリポジトリ内の主要モジュールを元にした概要・セットアップ・使い方の説明です。

> 対象: src/kabusys 以下のモジュール群（実行エントリ、設定管理、監視、実行エンジン周り、ポートフォリオ構成、研究用ユーティリティ、AI ニュース解析ツール等）

---

## 概要

KabuSys は日本株の自動売買に必要なコンポーネント（戦略の研究・ファクター計算、ポートフォリオ構築、発注実行エンジン、実行時監視・アラート、ペーパートレード用の分離環境、LLM を用いたニュースセンチメントや市場レジーム判定など）を含むモジュール群です。

主要な設計方針（抜粋）:
- 実行環境（development / paper_trading / live）を .env で切り替え
- ペーパートレードは本番 DB と分離（data/paper_trading.db）
- 監視（Monitoring）コンポーネントは環境にかかわらず本番の sqlite_path を参照してログを残す
- OpenAI を利用する AI 部分は API キー必須で、失敗時はフェイルセーフでフォールバックする設計
- ログは統一的に setup_logging を用いて stdout と日次ローテートファイルへ出力

---

## 機能一覧

- 実行エンジン（ExecutionEngine）起動スクリプト（run_execution.py）
  - 本番/ペーパートレードの切替
  - ブローカークライアント抽象化（BrokerClientFactory）
  - OrderManager / RiskManager / Reconciler 等の組み立て
  - PIDファイル管理、停止フラグ監視（data/stop_requested.flag）

- 監視プロセス（Monitoring / SystemMonitor）起動スクリプト（run_monitoring.py）
  - システム負荷（CPU/Memory/Disk）、データ鮮度、Execution プロセス生存監視
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト 60 秒）
  - 監視ログは SQLite（monitoring.db）へ永続化

- 監視永続化（monitoring_db.py）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブル定義とマイグレーション

- Kill Switch（kill_switch.py）
  - ドローダウンやポジション上限などの条件で data/kill.flag を出力して ExecutionEngine を安全停止

- RiskMonitor / TradeMonitor / MonitoringEngine
  - ドローダウン監視、ポジション上限監視、滞留注文検出などの自動アラート

- ポートフォリオ構築（portfolio/*）
  - 候補選定、等重/スコア重み算出、セクターキャップ、レジーム乗数、ポジションサイズ計算（lot 単位で丸め）

- 研究用モジュール（research/*）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン・IC（Information Coefficient）算出、統計サマリ

- AI モジュール（ai/news_nlp.py, ai/regime_detector.py）
  - OpenAI を用いたニュースセンチメント（銘柄別）スコアリング
  - マクロニュース + ETF（1321）MA200乖離から市場レジーム（bull/neutral/bear）を算出
  - API レート制限・一時エラーに対するリトライ・フェイルセーフを実装

- CLI ユーティリティ
  - 設定ウィザード: python -m kabusys.config_setup（.env を対話式で生成/編集）
  - 設定検証: python -m kabusys.validate_config（.env と config/*.yaml の検証）
  - Paper Trading 検証レポート生成: python -m kabusys.tools.paper_verification_report

---

## 前提 / 必要環境

- Python 3.10 以上（型ヒントで PEP 604 の `X | None` などを使用）
- SQLite（組み込み）
- duckdb（duckdb-python）
- psutil
- openai（AI 機能を使う場合）
- PyYAML（設定 YAML を検証する場合・オプション）

例（最低限）:
pip install duckdb psutil openai

（開発用には requirements.txt を用意している場合はそちらを利用してください）

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - pip install --upgrade pip
   - pip install duckdb psutil openai pyyaml

   （プロジェクトで requirements.txt がある場合は `pip install -r requirements.txt`）

4. .env を作成
   - 推奨: 対話式ウィザードを使用
     - python -m kabusys.config_setup
   - もしくは .env.example を参考に手動作成
   - 必須環境変数（最低）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD
   - OpenAI を使う場合:
     - OPENAI_API_KEY=...

5. 設定検証（任意だが推奨）
   - python -m kabusys.validate_config
   - 問題があれば .env を修正し再検証
   - --strict を付けると警告も失敗扱い

6. データ/ログ用ディレクトリ
   - デフォルトでは `data/` と `logs/` を使用します。起動時に自動作成する機能もありますが、権限に注意してください。

---

## 使い方（主要コマンド）

- 実行エンジン起動（本番/ペーパー切替は KABUSYS_ENV）
  - python -m kabusys.run_execution
  - 動作:
    - Settings から DB/環境を読み込む
    - Paper Trading の場合は専用 SQLite（デフォルト: data/paper_trading.db）を使用し MockBrokerClient が使われる
    - 起動前に data/stop_requested.flag があると起動せず終了
    - 実行中に data/stop_requested.flag が作成されると安全停止処理を行う

- 監視プロセス起動
  - python -m kabusys.run_monitoring
  - 動作:
    - SystemMonitor 等を初期化してポーリングループを回す
    - ポーリング間隔: デフォルト 60 秒（環境変数 MONITOR_POLL_INTERVAL で上書き可能）
    - 停止: data/stop_requested.flag が作成されると監視ループが終了

- 設定ウィザード
  - python -m kabusys.config_setup
  - .env を対話式で生成/更新します

- 設定検証
  - python -m kabusys.validate_config [--strict]

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]
  - デフォルト DB: 環境変数 PAPER_TRADING_SQLITE_PATH または data/paper_trading.db

- AI 機能（プログラムからの呼び出し）
  - kabusys.ai.score_news(conn, target_date, api_key=None)
  - kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続（duckdb.connect(...).cursor() ではなく接続オブジェクト）を受け、DB 内のテーブル（raw_news / prices_daily 等）を参照します。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL

- DB パス
  - DUCKDB_PATH: data/kabusys.duckdb（デフォルト）
  - SQLITE_PATH: data/monitoring.db（監視ログ）
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（ペーパートレード時に使用）

- Paper Trading
  - PAPER_FILL_MODE: instant|partial|never|reject（デフォルト: instant）

- OpenAI
  - OPENAI_API_KEY（ai/news_nlp.py, ai/regime_detector.py で使用）

- 監視関連
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
  - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START 等は Settings で確認可能

---

## 停止・Kill の仕組み

- 停止フラグ（監視・実行の外部停止）
  - data/stop_requested.flag を作成すると run_execution や run_monitoring は次のサイクルで検知して終了します（run_execution は起動を拒否することもある）。
- Kill Switch（自動停止）
  - KillSwitch は RiskMonitor 等の判定で条件を満たすと data/kill.flag を書き込み、その存在を ExecutionEngine が検知して安全停止する仕組みです。
  - 本番環境での誤作動防止のため KILL_FLAG_CLEAR_ON_START の挙動には注意してください（validate_config でも警告します）。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py                — 環境変数 / Settings 管理（.env 自動読み込み）
- config_setup.py          — .env 対話式ウィザード
- validate_config.py       — 起動前の設定検証 CLI
- run_execution.py         — ExecutionEngine 起動スクリプト
- run_monitoring.py        — Monitoring 起動スクリプト

- utils/
  - logging_setup.py       — 統一ロギング設定
  - process_priority.py    — プロセス優先度 / CPU affinity
- monitoring/
  - monitoring_db.py       — SQLite テーブル定義と永続化 API
  - monitoring_engine.py   — 各 Monitor を束ねるエンジン
  - system_monitor.py      — システム状態・データ鮮度監視
  - risk_monitor.py        — ドローダウン / ポジション数監視
  - kill_switch.py         — Kill Switch ロジック
  - trade_monitor.py       — （参照されるが抜粋に未掲載）
  - alert_manager.py       — （参照されるが抜粋に未掲載）

- execution/               — 発注・注文管理関連（OrderManager, RiskManager, Engine 等）
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- research/
  - factor_research.py
  - feature_exploration.py

- ai/
  - news_nlp.py
  - regime_detector.py

- monitoring_db / tools / data などのサポートファイル

（実際のリポジトリではさらに多くのモジュール・サンプル・スクリプトが存在する可能性があります）

---

## 開発・運用上の注意

- データベースパスの親ディレクトリが存在しない場合は起動時に自動作成されますが、権限や配置は事前に確認してください。
- 本番運用時（KABUSYS_ENV=live）は LINE 通知等のアラート設定と KILL_FLAG_CLEAR_ON_START を特に注意して設定してください（validate_config にて警告します）。
- OpenAI を利用する処理は API コスト・レート制限に注意してください。news_nlp と regime_detector はリトライ/バックオフを実装していますが、実運用では帯域や呼び出し頻度の制御が必要です。
- logging_setup は logs/<app_name>.log に日次ローテートでログを出力します。ディスク容量管理に注意してください（デフォルトで30世代保持）。

---

必要であれば、以下を追加で作成できます:
- requirements.txt の推奨依存リスト
- 起動用 systemd / docker-compose のサンプル
- 実行フロー図（ExecutionEngine と Monitoring の相互作用）
- 各モジュールの API 仕様（関数一覧・引数詳細）

他に README に追記したい内容（例: 具体的な .env.example、systemd サービス定義、DB スキーマ図 等）があれば教えてください。