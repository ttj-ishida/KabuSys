# KabuSys

日本株向け自動売買システムのリポジトリ（KabuSys）。  
戦略・ポートフォリオ構築、発注エンジン、監視・アラート、研究ツール、AI（ニュース NLP / レジーム判定）を含むモジュール群で構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下のような機能を持つ、プロダクション志向の日本株自動売買フレームワークです。

- シグナル → ポートフォリオ構築 → 注文発行までの一連ワークフロー
- ExecutionEngine（発注エンジン）と BrokerClient の抽象化（本番 / ペーパートレード切替）
- 監視サブシステム（System / Trade / Risk）と Kill Switch による自動停止
- LINE による一方向通知（AlertManager）
- DuckDB を用いた研究用データ処理（ファクター算出など）
- OpenAI を用いたニュースセンチメント（news_nlp）およびマーケットレジーム判定（regime_detector）
- ペーパートレード用の分離 DB、検証レポート生成ツール

設計方針として「本番 DB とペーパートレード DB の分離」「ルックアヘッドバイアス回避（日時参照の取り扱い）」「フェイルセーフ（API 失敗は無害化）」等が採用されています。

---

## 主な機能一覧

- 環境設定管理
  - .env 自動ロード / 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
- 実行系
  - ExecutionEngine（run_execution.py）: 実取引 / ペーパートレード切替
  - BrokerClientFactory によるブローカー抽象化
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor
  - MonitoringEngine（ポーリングループ）
  - MonitoringDB（SQLite ベースの永続化）
  - KillSwitch（閾値超過で実行エンジン停止フラグを書き込み）
  - AlertManager（LINE Push）
- ポートフォリオ構築
  - 候補選定、等重・スコア加重、ポジションサイジング、セクター制限、レジーム乗数
- 研究（Research）
  - ファクター計算（Momentum / Volatility / Value）
  - 将来リターン計算、IC（Information Coefficient）などの統計関数
- AI
  - news_nlp: raw_news を LLM でスコアリングして ai_scores へ書込
  - regime_detector: ma200 とマクロニュースの LLM センチメントを合成して日次レジーム判定
- ツール
  - Paper Trading 検証レポート（tools/paper_verification_report.py）

---

## 必要要件

- Python 3.10+
- 主な Python ライブラリ（例）
  - duckdb
  - psutil
  - openai
  - requests
  - PyYAML（config YAML の検証に必要、任意）
- SQLite（標準ライブラリ sqlite3 を利用）
- ネットワークアクセス（kabuステーション API、OpenAI、LINE API を利用する場合）

（requirements.txt は本リポジトリに含まれていない場合があるため、上記パッケージを pip でインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成して依存をインストールする。
2. data ディレクトリを作成（PID / flag / DB ファイルがここに作られます）。
   ```bash
   mkdir -p data
   ```
3. 対話式ウィザードで .env を作成（推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD
   - オプション: LINE 関連トークン、DUCKDB_PATH, SQLITE_PATH 等
4. 設定を検証
   ```bash
   python -m kabusys.validate_config        # 警告は注意表示
   python -m kabusys.validate_config --strict  # 警告を FAIL とする
   ```
5. 必要なら DuckDB / SQLite の初期化は各起動スクリプトで行われます（init_monitoring_db を通してテーブル作成されます）。
6. （OpenAI を利用する機能を使う場合）OPENAI_API_KEY を .env に設定するか環境変数にセットしてください。

重要ファイル・フラグ:
- data/execution.pid — ExecutionEngine の PID を書き込む
- data/stop_requested.flag — run_* スクリプトの外部停止フラグ（存在するとループを終了）
- data/kill.flag — KillSwitch が書き込む停止要求（ExecutionEngine 側が検知して停止）
- data/monitoring.db — 監視用 SQLite（Settings のデフォルト）
- data/paper_trading.db — ペーパートレード用 SQLite（KABUSYS_ENV=paper_trading 時に使用）

---

## 環境変数（主なもの）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — 監視 DB。デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — ペーパー用 DB（KABUSYS_ENV=paper_trading）
- PAPER_FILL_MODE — ペーパートレードの約定挙動（instant|partial|never|reject） デフォルト: instant
- OPENAI_API_KEY — OpenAI 利用時に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID — AlertManager（任意）
- LOG_LEVEL — ログレベル（DEBUG|INFO|...）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

簡単な .env 例（config_setup によって生成される形式と類似）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_token_here
KABU_API_PASSWORD=your_kabu_password_here
KABU_API_BASE_URL=http://localhost:18080/kabusapi
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
KABUSYS_ENV=development
LOG_LEVEL=INFO
KILL_FLAG_CLEAR_ON_START=0
```

---

## 使い方

- 設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 実行エンジン（ExecutionEngine）起動
  - 本番（設定に応じて実ブローカー使用）
    ```bash
    python -m kabusys.run_execution
    ```
  - ペーパートレードに切り替える:
    ```bash
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```
    ペーパートレード時は専用の SQLite（PAPER_TRADING_SQLITE_PATH、デフォルト data/paper_trading.db）に記録され、本番 DB と分離されます。

- 監視プロセス起動
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を秒単位で上書き可能（例: 30）。
    ```bash
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```

- 外部停止・停止フラグ
  - run_execution / run_monitoring はプロジェクトルートの data/stop_requested.flag を監視しています。ファイルを作成すると安全に停止します。
  - KillSwitch（監視側）は data/kill.flag を書き込み ExecutionEngine に停止要求を出します。

- Paper Trading 検証レポート
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB 指定:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 機能（ニュース NLP / レジーム判定）
  - OPENAI_API_KEY を設定した上で、対応する関数をスクリプトやジョブから呼び出します（例: kabusys.ai.score_news / kabusys.ai.regime_detector.score_regime）。
  - OpenAI 呼び出しはリトライ・バックオフ・レスポンス検証などの堅牢化が施されています。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py — 環境変数 & Settings クラス、自動 .env ロード
- config_setup.py — .env 対話式ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — SystemMonitor ポーリング起動スクリプト

サブパッケージ:
- ai/
  - news_nlp.py — ニュースを LLM でスコアリングして ai_scores に書込
  - regime_detector.py — マーケットレジーム判定
- monitoring/
  - monitoring_db.py — SQLite テーブル作成・CRUD（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py — システム・データ鮮度監視
  - trade_monitor.py — 注文滞留 / 約定異常監視
  - risk_monitor.py — ドローダウン・ポジション上限監視
  - monitoring_engine.py — 複数 Monitor を束ねるエンジン
  - kill_switch.py — kill.flag の書込みロジック
  - alert_manager.py — LINE による通知（クールダウン管理）
- execution/
  - （ExecutionEngine, OrderManager, OrderRepository, Reconciler, RiskManager 等の実装がここに存在）
- portfolio/
  - portfolio_builder.py — 候補選定・重み計算
  - position_sizing.py — 株数計算・単元丸め・スケールダウンロジック
  - risk_adjustment.py — セクター上限・レジーム乗数
- research/
  - factor_research.py — Momentum / Volatility / Value ファクター計算（DuckDB 使用）
  - feature_exploration.py — 将来リターン / IC / 統計要約
- tools/
  - paper_verification_report.py — ペーパー検証レポート生成
- utils/
  - process_priority.py — プロセス優先度 / CPU affinity ユーティリティ

プロジェクトルート:
- .env, .env.local（推奨で管理外）
- config/*.yaml（設定テンプレート。validate_config で検査対象）
- data/ (DB・PID・flag を格納するディレクトリ)

---

## 運用上の注意点

- KABUSYS_ENV を `live` に設定する場合は特に注意してください（validate_config は警告を出します）。本番では KILL_FLAG_CLEAR_ON_START は 0 を推奨します。
- PID / flag / DB ファイルのパーミッションに注意してください（サービスユーザーが読み書き可能であること）。
- OpenAI や LINE、kabu API のキーは決してリポジトリにコミットしないでください（.env は .gitignore に入れて管理してください）。
- ペーパートレードは本番 DB と完全に分離されますが、運用前に validate_config / config_setup を実行して設定を確実に確認してください。
- 監視・実行プロセスは stop_requested.flag の存在で安全に停止できます。Kill Switch は監視ルールに従って自動で kill.flag を作成します。

---

## 開発・拡張ポイント（参考）

- strategy / execution の実装を差し替えて独自戦略を組み込むことが容易になるように設計されています（純粋関数群と DB 分離）。
- DuckDB を利用したファクター計算・研究用クエリは、データ量が増えても効率的に集計できます。
- OpenAI 呼び出しはレスポンス検証・クリッピング・リトライを実装済みですが、使用モデルやプロンプトの調整はプロジェクトの要件に応じて行ってください。

---

この README はコードベース（src/kabusys）から主要な挙動をまとめたものです。実際の運用前に config/*.yaml や .env を環境に合わせて適切に設定し、validate_config で検証してください。必要があれば、追加の運用手順（systemd ユニット、コンテナ定義、ログローテーション等）を整備してください。