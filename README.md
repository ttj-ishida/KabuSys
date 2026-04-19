# KabuSys

バージョン: 0.1.0

日本株向け自動売買システムのコアライブラリ群です。シグナル生成、ポートフォリオ構築、ポジションサイズ決定、注文実行（本番/ペーパートレード切替）、監視・アラート、研究用ユーティリティ、AI を使ったニュース評価などを含みます。

---

主な特徴、セットアップ、使い方、ディレクトリ構成をまとめた README です。

目次
- プロジェクト概要
- 機能一覧
- セットアップ手順
- 使い方
  - 環境設定ウィザード（.env）
  - 設定検証
  - 実行エンジン起動（Execution）
  - 監視ループ起動（Monitoring）
  - Paper Trading 検証レポート生成
  - AI モジュール（ニュース NLP / レジーム判定）
- 環境変数（主なもの）
- 実行時ファイル / フラグ
- ディレクトリ構成

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計された Python パッケージです。以下の役割を持つコンポーネントで構成されています。

- ExecutionEngine：ブローカーと連携して注文を出す（実取引 / ペーパートレードを切替可能）
- Monitoring：システム稼働状況・注文状況・リスク監視、必要時に Kill Switch（停止フラグ）を作成
- Portfolio：候補選定・重み付け・ポジションサイズ決定、リスク調整
- Research：DuckDB 上の時系列データからファクター等を算出する研究用ユーティリティ
- AI：OpenAI を利用したニュースセンチメント / 市場レジーム判定
- Tools：ユーティリティスクリプト（例: Paper Trading 検証レポート生成）

---

## 機能一覧

- 環境（.env）ウィザードによる対話的設定生成
- 設定検証 CLI（必須環境変数・YAML のパースチェックなど）
- ExecutionEngine（本番 / ペーパートレードの分離）
- リスク管理（ドローダウン監視、ポジション上限、レート制限等）
- MonitoringEngine（System, Trade, Risk モニタの統合ポーリング）
- Kill Switch（条件に応じて data/kill.flag を書込みエンジン停止）
- DuckDB を用いた研究用ファクター計算（Momentum/Value/Volatility 等）
- OpenAI を使ったニュースセンチメント評価（クロール済み raw_news → ai_scores）
- Paper Trading の検証レポート生成（稼働率・成功率・レイテンシ等）
- ログ設定ユーティリティ（コンソール + 日次ローテーション）

---

## セットアップ手順（開発/ローカル）

1. リポジトリをチェックアウトし、仮想環境を作成する
   ```
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

   - 本リポジトリは DuckDB、psutil、openai 等を使用します。requirements.txt に必要パッケージを含めてください。

2. .env の初期作成（対話式ウィザード）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env を生成します。生成後に `python -m kabusys.validate_config` で検証してください。

3. データディレクトリを作成（必要に応じて）
   ```
   mkdir -p data logs
   ```

4. （任意）Paper Trading 用 DB を初期化する場合は `PAPER_TRADING_SQLITE_PATH` を確認しておく。

---

## 使い方

### 環境設定ウィザード（.env の作成）

対話式で .env を作成・更新します。
```
python -m kabusys.config_setup
```
ウィザードは J-Quants トークン、kabu API パスワード、DB パス、LOG_LEVEL、KABUSYS_ENV などを対話的に設定します。

### 設定検証

作成した .env（および環境変数）を検証します。
```
python -m kabusys.validate_config
# 警告を FAIL 扱いにする strict モード
python -m kabusys.validate_config --strict
```

### 実行エンジン起動（ExecutionEngine）

ExecutionEngine を起動します。パッケージモジュールとして実行可能です。
```
python -m kabusys.run_execution
```

動作のポイント:
- 環境変数 KABUSYS_ENV により動作モードを切り替えます。
  - paper_trading: MockBrokerClient を使用し、データは data/paper_trading.db に保存（本番 DB と完全に分離）
  - live: 本番（実際に発注を行います）
  - development: 発注なしの開発用設定
- 起動時に `data/execution.pid` を PID ファイルとして扱います（path は Settings.pid_file_path で変更可能）
- 起動前に `data/stop_requested.flag`（停止フラグ）が既に存在する場合は起動せず終了します
- ExecutionEngine の停止は Kill Switch（data/kill.flag）や stop flag により行われます

### 監視ループ起動（Monitoring）

監視用ポーリングループを起動します。
```
python -m kabusys.run_monitoring
```

主な挙動:
- 既定のポーリング間隔は 60 秒（環境変数 `MONITOR_POLL_INTERVAL` で上書き可）
- Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path（Settings.sqlite_path、デフォルト data/monitoring.db）を使用して監視ログを永続化します
- SystemMonitor / TradeMonitor / RiskMonitor を呼び出し、必要に応じて Kill Switch を生成・アラート送信

監視ループ起動時の例:
```
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

### Paper Trading 検証レポート生成ツール

Paper Trading の SQLite（デフォルト data/paper_trading.db）から検証レポートを作成します。
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを直接指定する場合
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

出力内容: 稼働率、注文成功率、送信率、P95 レイテンシ等の指標と PASS/FAIL 判定。

### AI モジュール（ニュース NLP / レジーム判定）

OpenAI API を使う機能はプログラム的に利用します。環境変数 `OPENAI_API_KEY` を設定するか、関数に明示的にキーを渡してください。

- ニュースセンチメント（ai_scores への書き込み）
  - 関数: `kabusys.ai.news_nlp.score_news(conn, target_date, api_key=None)`
  - 引数: DuckDB 接続、判定対象日、（任意）APIキー
  - 返り値: 書き込んだ銘柄数

- レジーム判定（market_regime テーブルへの書き込み）
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`
  - 引数: DuckDB 接続、判定対象日、（任意）APIキー

注意:
- OpenAI 呼び出しはリトライ等の堅牢な実装を含みますが、API キー未設定時は ValueError を送出します。
- これらは CLI ではなく Python API として利用する設計です。必要ならラッパースクリプトを作成してください。

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

重要（よく使う / デフォルトあり）:
- KABUSYS_ENV (development | paper_trading | live) — デフォルト "development"
- DUCKDB_PATH — デフォルト data/kabusys.duckdb
- SQLITE_PATH — デフォルト data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 DB（デフォルト data/paper_trading.db）
- LOG_LEVEL — (DEBUG/INFO/WARNING/ERROR/CRITICAL) デフォルト INFO
- OPENAI_API_KEY — OpenAI を利用する際に必要
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒）デフォルト 60
- PAPER_FILL_MODE — ペーパートレード時の約定モード (instant | partial | never | reject)

ログディレクトリ:
- LOG_DIR（未指定時は logs/）: logs/<app_name>.log（日次ローテーション）

Kill / Stop フラグ:
- PID_FILE_PATH（デフォルト data/execution.pid）
- KILL_FLAG_PATH（デフォルト data/kill.flag）
- 停止フラグファイル: data/stop_requested.flag を存在させると監視・実行スレッドが停止します

---

## 実行時ファイル / フラグ

- data/execution.pid — ExecutionEngine が PID を書くファイル（Settings.pid_file_path）
- data/kill.flag — Kill Switch が発動した理由を書き込むファイル（Settings.kill_flag_path）
- data/stop_requested.flag — 外部プロセスが作成すると run_execution/run_monitoring が停止するフラグ
- デフォルト DB:
  - DuckDB: data/kabusys.duckdb
  - Monitoring SQLite: data/monitoring.db
  - Paper Trading SQLite: data/paper_trading.db

ログ:
- logs/<app_name>.log（例: logs/execution.log, logs/monitoring.log）

---

## 主要モジュールと責務（抜粋）

- kabusys.config: .env 自動読み込み、Settings クラス（環境変数アクセス）
- kabusys.config_setup: .env 対話式ウィザード
- kabusys.validate_config: 起動前チェック CLI
- kabusys.run_execution: ExecutionEngine 起動スクリプト（スレッドで実行）
- kabusys.run_monitoring: SystemMonitor ポーリングループ起動スクリプト
- kabusys.monitoring.*: MonitoringDB, SystemMonitor, TradeMonitor, RiskMonitor, KillSwitch, MonitoringEngine
- kabusys.portfolio.*: 候補選定・重み付け・ポジションサイズ決定・リスク補正
- kabusys.research.*: ファクター計算・特徴量探索（DuckDB ベース）
- kabusys.ai.*: news_nlp（ニュースセンチメント）, regime_detector（市場レジーム）
- kabusys.tools.paper_verification_report: Paper Trading 検証レポート生成

---

## ディレクトリ構成

（プロジェクトルートは .git または pyproject.toml によって検出されます）

例（主要ファイルのみ抜粋）:
```
.
├─ .env                      # (生成/管理) 環境変数ファイル（.git 管理しないこと）
├─ config/                   # yaml 設定テンプレート等（system_config.yaml 等）
├─ data/                     # デフォルト DB / PID / flag を置く場所
│   ├─ monitoring.db         # SQLite (監視用)    (SQLITE_PATH)
│   ├─ paper_trading.db      # SQLite (ペーパー) (PAPER_TRADING_SQLITE_PATH)
│   ├─ kabusys.duckdb        # DuckDB             (DUCKDB_PATH)
│   ├─ execution.pid
│   ├─ kill.flag
│   └─ stop_requested.flag
├─ logs/                     # ログ出力（LOG_DIR）
├─ src/
│   └─ kabusys/
│       ├─ __init__.py
│       ├─ config.py
│       ├─ config_setup.py
│       ├─ validate_config.py
│       ├─ run_execution.py
│       ├─ run_monitoring.py
│       ├─ utils/
│       │   ├─ logging_setup.py
│       │   └─ process_priority.py
│       ├─ monitoring/
│       │   ├─ monitoring_db.py
│       │   ├─ system_monitor.py
│       │   ├─ trade_monitor.py
│       │   ├─ risk_monitor.py
│       │   ├─ kill_switch.py
│       │   └─ monitoring_engine.py
│       ├─ execution/          # broker, engine, order_manager 等（注文実行ロジック）
│       ├─ portfolio/          # portfolio_builder, position_sizing, risk_adjustment
│       ├─ research/           # factor_research, feature_exploration
│       ├─ ai/
│       │   ├─ news_nlp.py
│       │   └─ regime_detector.py
│       └─ tools/
│           └─ paper_verification_report.py
└─ pyproject.toml / setup.cfg / requirements.txt
```

---

## 運用上の注意・推奨設定

- 本番環境（KABUSYS_ENV=live）の場合は .env の設定を慎重に確認してください（validate_config は live 特有の警告を出します）。
- kill flag（KILL_FLAG）を安易に自動クリアする設定（KILL_FLAG_CLEAR_ON_START=1）は本番で危険です。デフォルトは 0 を推奨します。
- ログと DB ファイルのバックアップ・ローテーション方針を検討してください（特に DuckDB / SQLite のサイズ管理）。
- OpenAI を使用する機能は API コストが発生します。production ではレート・コストを考慮した運用を行ってください。
- ペーパートレード（paper_trading）は本番 DB と完全に分離されるように設計されています。テスト時は KABUSYS_ENV=paper_trading を使用してください。

---

必要に応じて README を拡張します（詳細な設定項目、実装のドキュメントへのリンク、ユニットテストの実行方法、デプロイ手順など）。追加で記載したい項目があれば教えてください。