# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ向け README（日本語）。

本ドキュメントはこのコードベースの概要・機能・セットアップ手順・使い方・ディレクトリ構成を示します。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコンポーネント群です。  
主な目的は以下：

- 戦略に基づく銘柄選定・ポジション決定（Portfolio construction）
- 発注実行（ExecutionEngine。paper_trading モードはモックブローカーを使用）
- システム監視・リスク監視・アラート（Monitoring）
- 研究用ファクター計算（DuckDB を利用）
- ニュース NLP を用いた AI スコアリング（OpenAI を使用。オプション）
- 運用支援ツール（.env ウィザード・設定検証・ペーパートレード検証レポート等）

起動スクリプトは主に以下：
- run_execution.py — ExecutionEngine を起動する（発注・リスク管理）
- run_monitoring.py — Monitoring のポーリングループを起動する

設計上の特徴：
- 環境設定は .env（または環境変数）で管理（自動ロード機構あり）
- paper_trading モードでは本番 DB と分離して paper_trading 用 SQLite を使用
- DuckDB を分析・研究処理に利用
- ロギングは統一された setup_logging を通じて stdout + 日次ローテーションファイルに出力
- Kill Switch はファイルベース（data/kill.flag）で ExecutionEngine を安全に停止可能

---

## 主な機能一覧

- Execution
  - ExecutionEngine による注文作成・発注（実ブローカー or MockBroker）
  - リスク管理（最大ポジション比率・利用率・回路ブレーカー等）
  - OrderRepository / OrderManager / Reconciler 等の発注周辺ユーティリティ

- Monitoring
  - SystemMonitor：CPU/メモリ/Disk、データ鮮度、Execution プロセスの健全性チェック
  - TradeMonitor：注文の滞留検出・約定異常検出（trade_logs / positions）
  - RiskMonitor：ドローダウン、ポジション上限監視
  - MonitoringEngine：各 Monitor を束ねて定期実行、KillSwitch 評価・アラート通知

- Portfolio（純粋関数）
  - 銘柄選定、等金額・スコア加重の重み算出
  - セクターキャップ適用・レジーム乗数
  - ポジションサイズ計算（単元株・利用可能現金・リスクベース等）

- Research
  - ファクター計算（Momentum, Volatility, Value など）
  - 将来リターン、IC（Information Coefficient）評価、統計サマリ

- AI（任意）
  - news_nlp：OpenAI を使ったニュースセンチメント集約 → ai_scores へ書き込み
  - regime_detector：ETF の MA とマクロニュースを組み合わせ市場レジーム判定

- ツール
  - config_setup.py：対話式 .env 作成ウィザード
  - validate_config.py：環境変数・config/*.yaml の事前検証 CLI
  - tools.paper_verification_report：Paper Trading の検証レポート生成

- DB / 永続化
  - monitoring_db.py：SQLite による監視ログ永続化（system_status / trade_logs / positions / risk_logs / dashboard）

---

## セットアップ手順（開発環境向け）

以下は一般的なローカルセットアップ例です。環境によって適宜調整してください。

1. リポジトリをクローン
   - git clone <repo-url>
   - cd <repo-root>

2. Python 環境（仮想環境）作成
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必要パッケージをインストール
   - 本リポジトリに requirements.txt がない場合は少なくとも以下を入れてください：
     - duckdb
     - psutil
     - openai
     - PyYAML（設定ファイルの検証時に利用）
   - 例：
     - pip install duckdb psutil openai pyyaml

4. .env を作成（対話式ウィザード推奨）
   - python -m kabusys.config_setup
   - ウィザードはデフォルト値や秘密情報（トークン）入力を案内します。
   - 主要な必須環境変数：
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
   - よく使う任意変数（デフォルト値は .env ウィザード参照）
     - KABUSYS_ENV (development | paper_trading | live)
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）
     - LOG_LEVEL / LOG_DIR
     - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート用）

5. 設定検証
   - python -m kabusys.validate_config
   - --strict をつけると警告も FAIL 扱いになります（exit code 1）。

6. データディレクトリ作成（必要に応じて）
   - mkdir -p data logs

注意: 自動で .env を読み込む仕組みがありますが、テストで無効化したい場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます。

---

## 使い方（起動・操作）

動作モードに応じて実行スクリプトを使います。実行は仮想環境内で行ってください。

### 実行エンジン（ExecutionEngine）

- 起動（通常）
  - python -m kabusys.run_execution
  - 起動時にプロセス優先度が "high" に設定されます。
  - KABUSYS_ENV が `paper_trading` の場合、MockBrokerClient を使用し paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）に記録され、本番 DB と完全分離されます。
  - 起動時に data/stop_requested.flag が存在する場合は起動をせず終了します。
  - PID ファイル: data/execution.pid（Settings.pid_file_path で変更可）

- 停止
  - data/stop_requested.flag を作成すると実行中ループが検出して停止します（run_execution.py と run_monitoring.py の両方が参照）。
  - Kill Switch による停止: monitoring が条件を満たすと data/kill.flag に理由を書き込み、ExecutionEngine がそれを検出して停止します。
  - 起動時に KILL_FLAG_CLEAR_ON_START=1 を設定していると起動時に kill.flag を自動クリアします（本番では 0 推奨）。

### 監視ループ（Monitoring）

- 起動
  - python -m kabusys.run_monitoring
  - デフォルトのポーリング間隔は 60 秒。環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（例: MONITOR_POLL_INTERVAL=30）。
  - Monitoring は KABUSYS_ENV に関わらず本番 sqlite_path（Settings.sqlite_path）を使用します（監視データは本番 DB に残す意図）。
  - ログは stdout と logs/monitoring.log に出力されます（LOG_DIR/LOG_LEVEL を参照）。

### ツール

- 設定ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- Paper Trading 検証レポート
  - python -m kabusys.tools.paper_verification_report
  - 期間指定:
    - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  - DB パス指定:
    - --db オプション、または環境変数 PAPER_TRADING_SQLITE_PATH を使用

### AI 機能

- OpenAI を利用する処理（news_nlp / regime_detector）を使う場合は `OPENAI_API_KEY` を .env または環境変数で設定してください。
- AI 呼び出しにはリトライ・バックオフ・レスポンス検証等のフェイルセーフが組み込まれていますが、API 利用量・料金に注意してください。

---

## 主要な環境変数（抜粋）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV (development | paper_trading | live) — デフォルト: development

- DB / ファイルパス
  - DUCKDB_PATH — デフォルト: data/kabusys.duckdb
  - SQLITE_PATH — 監視 DB。デフォルト: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH — paper_trading 用 DB。デフォルト: data/paper_trading.db
  - PID_FILE_PATH — PID ファイルパス。デフォルト: data/execution.pid
  - KILL_FLAG_PATH — kill.flag のパス。デフォルト: data/kill.flag

- ログ
  - LOG_LEVEL — デフォルト: INFO
  - LOG_DIR — デフォルト: logs/

- Monitoring
  - MONITOR_POLL_INTERVAL — 監視ループのポーリング間隔（秒）。デフォルト: 60

- AI
  - OPENAI_API_KEY — OpenAI API キー
  - PAPER_FILL_MODE — paper_trading の約定挙動: instant|partial|never|reject（デフォルト: instant）

- Kill Switch / 制御
  - KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリアするか（0/1）。本番は 0 推奨。

---

## 運用上の注意

- monitoring は監視用途の DB に書き込みます。監視 DB のパス（SQLITE_PATH）に注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL を用いてループします。テスト時は小さく設定して動作確認してください。
- run_execution は paper_trading モード時に paper_trading 用 DB を使用します。本番 DB と混同しないように注意してください。
- kill.flag / stop_requested.flag によるファイル制御を使用します。自動化スクリプト・監視ツールがこれらを誤って作成しないよう注意してください。
- ログディレクトリ作成に失敗した場合はコンソール出力のみになります。権限・ディスク容量を監視してください。
- psutil によるプロセス優先度設定や affinity 設定は環境や権限に依存します。失敗時は警告ログを出して続行します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 配下の主要ファイル・モジュール一覧（本 README 作成時点のソースに基づく）

- kabusys/                             — パッケージルート
  - __init__.py                        — パッケージ定義（__version__ 等）
  - config.py                          — 環境変数 / 設定読み込みロジック（.env 自動読み込み含む）
  - config_setup.py                    — 対話式 .env ウィザード
  - validate_config.py                 — 設定検証 CLI
  - run_execution.py                   — ExecutionEngine 起動スクリプト
  - run_monitoring.py                  — Monitoring ポーリングループ起動スクリプト

  - utils/
    - logging_setup.py                 — ログ設定ユーティリティ（stdout + 日次ローテーション）
    - process_priority.py              — プロセス優先度・CPU affinity 設定ユーティリティ
    - __init__.py

  - monitoring/
    - monitoring_db.py                 — SQLite 監視 DB 層（テーブル初期化 + 永続化メソッド）
    - system_monitor.py                — システム状態・データ鮮度監視
    - trade_monitor.py                 — 注文・約定監視（ファイルからのログ参照）
    - risk_monitor.py                  — ドローダウン・ポジション上限監視
    - kill_switch.py                    — kill.flag 書き込みロジック
    - alert_manager.py                 — （アラート送信ラッパー。コードベースに依存）
    - monitoring_engine.py             — 各 Monitor を束ねるエンジン

  - execution/
    - (ExecutionEngine, OrderManager, BrokerFactory, RiskManager, etc.)
    - order_repository.py
    - order_manager.py
    - reconciler.py
    - execution_engine.py
    - broker_factory.py
    - risk_manager.py
    - (詳細は該当ファイル参照)

  - portfolio/
    - portfolio_builder.py              — 候補選定・重み計算
    - position_sizing.py                — 株数決定（単元考慮・aggregate cap）
    - risk_adjustment.py                 — セクター上限・レジーム乗数
    - __init__.py

  - research/
    - factor_research.py                — momentum / volatility / value 等
    - feature_exploration.py            — 将来リターン・IC・統計解析
    - __init__.py

  - ai/
    - news_nlp.py                       — ニュース NLP（OpenAI）による銘柄別スコア化
    - regime_detector.py                — マクロニュース + ETF MA による市場レジーム判定
    - __init__.py

  - monitoring/monitoring_db.py         — 監視 DB スキーマ・API（上記）

  - tools/
    - paper_verification_report.py      — Paper Trading 検証レポート生成
    - __init__.py

- data/                                — 実行時に使用される DB / フラグファイル 等（デフォルト）
  - monitoring.db (SQLITE_PATH のデフォルト)
  - paper_trading.db (PAPER_TRADING_SQLITE_PATH のデフォルト)
  - kabusys.duckdb (DUCKDB_PATH のデフォルト)
  - kill.flag
  - stop_requested.flag
  - execution.pid

- logs/                                — ログファイル（LOG_DIR のデフォルト）

---

## 参考コマンドまとめ

- 仮想環境作成・依存インストール
  - python -m venv .venv
  - source .venv/bin/activate
  - pip install duckdb psutil openai pyyaml

- .env ウィザード
  - python -m kabusys.config_setup

- 設定検証
  - python -m kabusys.validate_config
  - python -m kabusys.validate_config --strict

- 起動
  - 実行エンジン: python -m kabusys.run_execution
  - 監視:        python -m kabusys.run_monitoring

- ツール
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

---

## 最後に / 注意事項

- 本リポジトリには実際の証券取引に関するコードを含む可能性があります。`KABUSYS_ENV=live` を設定して実行する際は、すべての設定（API キー、口座、Kill Switch、リスクパラメータ）を十分に確認してください。
- .env や秘密情報は決して Git にコミットしないでください（config_setup にも注意書きがあります）。
- OpenAI API を使用する機能は外部 API 呼び出しと費用が発生します。利用ポリシーに従ってください。

必要であれば README にサンプル .env（テンプレート）や更に詳細な運用手順（systemd ユニット、Docker 化、監視ダッシュボード連携など）を追記します。どの情報をさらに追加したいか教えてください。