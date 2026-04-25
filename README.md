# KabuSys

日本株自動売買システム（KabuSys）のリポジトリ説明書。  
この README はプロジェクト概要、主な機能、セットアップ手順、使い方（起動コマンド例）、および主要なディレクトリ構成を日本語でまとめたものです。

---

## プロジェクト概要

KabuSys は日本株向けの自動売買プラットフォーム向けライブラリ群です。以下の主要機能を提供します。

- 注文実行エンジン（ExecutionEngine）とブローカークライアント抽象化
- 監視・アラート機能（System / Trade / Risk モニタ）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ決定）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ニュースの NLP を用いたセンチメント評価（OpenAI 経由）
- 市場レジーム判定（MA + マクロセンチメントの合成）
- 開発支援ツール（.env 作成ウィザード、設定検証、ペーパートレード検証レポート）

設計上のポイント：
- DuckDB / SQLite をデータ基盤として使用（分析用 DuckDB、監視・注文履歴は SQLite）
- Paper Trading（模擬発注）は本番 DB と完全分離（`data/paper_trading.db`）
- LLM 呼び出しはフェイルセーフ設計（リトライやフォールバックを備える）
- 時刻参照はルックアヘッドバイアス対策が施されている（テスト性重視）

---

## 主な機能一覧

- Execution
  - ExecutionEngine を起動して注文処理を行う（実ブローカー or モック）
  - RiskManager, OrderManager, Reconciler 等のコンポーネント
- Monitoring
  - SystemMonitor: CPU/メモリ/ディスク/プロセスの監視、データ鮮度チェック
  - TradeMonitor: 発注ログの監視・異常検出（滞留注文、約定異常等）
  - RiskMonitor: ドローダウン・ポジション上限の監視、Kill Switch 連携
  - MonitoringEngine によるポーリングループと AlertManager 経由の通知
- Portfolio construction
  - 候補選定（スコア順）、等配分/スコア加重、リスクベースの株数算出
  - セクター・キャップ適用、レジーム乗数
- Research
  - ファクター計算（momentum, volatility, value）
  - 将来リターン計算、IC（Information Coefficient）等の統計解析
- AI（OpenAI）
  - news_nlp: ニュース記事をまとめて LLM に送り銘柄ごとのセンチメントを算出・保存
  - regime_detector: ETF MA とマクロセンチメントを合成して market_regime を判定・保存
- ツール
  - config_setup.py: .env を対話式に作成・更新するウィザード
  - validate_config.py: 環境変数と config/*.yaml の事前チェック
  - tools.paper_verification_report: ペーパートレードの検証レポート生成

---

## 必要な依存ライブラリ（概略）

リポジトリに requirements.txt が無い場合は、少なくとも以下をインストールしてください（バージョンは用途に合わせて調整してください）。

- Python 3.8+
- duckdb
- psutil
- openai
- PyYAML（設定ファイル検証を行う場合）
- その他：標準ライブラリ以外でコード内に import されているパッケージ

インストール例（pip）:
```
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（重要）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

よく使う/重要:
- KABUSYS_ENV: 実行環境（development / paper_trading / live）  
  - paper_trading の場合は MockBrokerClient が使用され、paper_trading 用 DB に書き込まれます
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（monitoring）パス（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: ペーパートレード時の約定モード（instant / partial / never / reject）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: 本番通知（任意）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリア（0/1）

.config_setup ウィザードで主要項目を対話的に作成できます。

---

## セットアップ手順（開発者向け）

1. リポジトリをクローン
   - git clone <repo>

2. Python 仮想環境を作成・有効化（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install -r requirements.txt  （もし用意されていれば）
   - または必要なパッケージを個別にインストール（上記参照）

4. 環境変数ファイルを作成
   - 対話式ウィザードを使う（推奨）
     - python -m kabusys.config_setup
   - もしくはリポジトリルートの `.env` を手動で作成
   - 作成後に設定検証を行う:
     - python -m kabusys.validate_config
     - 問題があれば出力を確認して修正してください

5. データディレクトリの準備
   - デフォルトで使用されるディレクトリ例: data/, logs/
   - 必要に応じてパスを環境変数で変更してください

---

## 使い方（起動・実行例）

- ExecutionEngine を起動（本番/ペーパーに応じて .env の KABUSYS_ENV を設定）
```
python -m kabusys.run_execution
```
- 監視ループ（SystemMonitor）を起動
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）
```
python -m kabusys.run_monitoring
# 例: 30秒間隔で実行
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

- .env を対話式で作成/更新
```
python -m kabusys.config_setup
```

- 設定検証（起動前に実行）
```
python -m kabusys.validate_config
# --strict を付けると警告も失敗扱い（exit 1）
python -m kabusys.validate_config --strict
```

- Paper Trading 検証レポート生成（SQLite DB を指定可能）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パス指定
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI / 研究系関数（ライブラリ使用例）
  - ニュース NLP スコア算出: kabusys.ai.score_news(conn, target_date, api_key=...)
  - レジーム判定: kabusys.ai.regime_detector.score_regime(duckdb_conn, target_date, api_key=...)

注意点:
- Paper Trading 環境（KABUSYS_ENV=paper_trading）は本番 DB と分離され、モックブローカーを使用します。
- ExecutionEngine 停止は kill.flag（デフォルト: data/kill.flag）を介して行われます。KillSwitch による自動書き込みも実装されています。
- ログは `kabusys.utils.logging_setup.setup_logging` を通して `logs/<app_name>.log` に日次ローテーションで保存されます。ログディレクトリは `LOG_DIR` 環境変数で変更可能です。

---

## 便利なファイル・フラグ（運用）

- data/stop_requested.flag — 起動スクリプトはこのファイルが存在するとループを停止します
- data/execution.pid — 実行エンジン用の PID ファイル（起動時に設定される想定）
- data/kill.flag — Kill Switch が書き込む停止フラグ（ExecutionEngine 停止シグナル）

---

## ディレクトリ構成

主要なファイル・ディレクトリ（src/kabusys 以下）：

- kabusys/
  - __init__.py
  - config.py                 -- 環境変数/設定管理（.env 自動ロード含む）
  - config_setup.py           -- .env 対話式ウィザード
  - validate_config.py        -- 設定検証 CLI
  - run_execution.py          -- ExecutionEngine 起動スクリプト
  - run_monitoring.py         -- SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - paper_verification_report.py  -- ペーパートレード検証レポート生成
  - execution/                -- ExecutionEngine まわりの実装（BrokerFactory 等）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
  - monitoring/
    - monitoring_db.py        -- SQLite 永続化層（system_status, trade_logs, positions, ...）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - ai/
    - news_nlp.py              -- ニュースセンチメント算出（OpenAI）
    - regime_detector.py       -- 市場レジーム判定（MA + マクロセンチメント）
  - data/                     -- （運用時に生成される想定）DB・フラグ・PID 等
  - utils/
    - logging_setup.py        -- ロギング設定
    - process_priority.py     -- プロセス優先度・CPU affinity 設定

（上記は現状の主要モジュール一覧です。実装ファイルはリポジトリ内に複数存在します。）

---

## 運用上の注意 / ベストプラクティス

- 本番（KABUSYS_ENV=live）では .env の値を慎重に管理し、LINE 通知等の連携を確保してください。
- KILL_FLAG_CLEAR_ON_START は本番で `1` に設定すると危険（Kill Switch を自動でクリアしてしまう）。本番は `0` 推奨。
- OpenAI キーや API トークン等のシークレットは `.env` を経由して管理し、リポジトリへは絶対にコミットしないでください。
- 監視ループ（monitoring）はデフォルト 60 秒間隔。運用要件に応じて `MONITOR_POLL_INTERVAL` を設定してください。
- Paper Trading を利用して作業フローや戦略ロジックを十分に検証してから本番運用へ移行してください。

---

必要があれば、この README をベースに「デプロイ手順」「Docker 化」「CI 設定」「詳細な API ドキュメント」などの追加ドキュメントも作成できます。どの部分を拡張しますか？