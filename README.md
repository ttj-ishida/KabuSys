# KabuSys

日本株向け自動売買システムのコードベース（README）。  
本ドキュメントはリポジトリ内の主要スクリプト・モジュールに基づき、導入・実行手順およびディレクトリ構成をまとめたものです。

注意: 実際の運用・本番稼働の前に必ず設定検証（validate_config）と小規模な検証（paper_trading）を行ってください。

---

## プロジェクト概要

KabuSys は日本株の自動売買に関する以下の機能を持つモジュール群を提供します。

- データ収集・保存（DuckDB / SQLite）
- ファクター計算・リサーチ（momentum / value / volatility 等）
- ポートフォリオ構築（候補選定・重み計算・ポジションサイズ算出）
- 実行エンジン（ExecutionEngine）とブローカークライアント（本番 / ペーパートレード切替）
- 監視・アラート（SystemMonitor / TradeMonitor / RiskMonitor / KillSwitch）
- AI 周りの辅助（ニュース NLP によるセンチメント、レジーム判定）
- 運用ツール（.env ウィザード / 設定検証 / ペーパートレード検証レポート等）

設計上の方針として、本番発注 API へのアクセスは Execution 実行時にのみ行い、研究・解析モジュールは DB のみ参照します。

---

## 主な機能一覧

- 設定管理
  - .env の自動読み込み / 対話式ウィザード（kabusys.config_setup）
  - 起動前チェック（kabusys.validate_config）
- 実行基盤
  - ExecutionEngine（run_execution.py）: ブローカー切替（paper_trading / live）
  - MockBroker によるペーパートレード（paper_trading 用 SQLite に記録して完全分離）
- 監視
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine（run_monitoring.py）
  - kill.flag による ExecutionEngine 停止（KillSwitch）
  - LINE 通知用 AlertManager（トークン未設定時はログ出力）
- ポートフォリオ構築
  - 候補選定、等金額 / スコア加重、リスク調整（セクターキャップ・レジーム乗数）、ポジションサイズ算出
- リサーチ / AI
  - DuckDB ベースのファクター計算（momentum / value / volatility）
  - ニュース NLP（OpenAI）を使った銘柄別センチメント（ai.news_nlp.score_news）
  - レジーム判定（ai.regime_detector.score_regime）
- 運用ツール
  - Paper Trading 検証レポート（kabusys.tools.paper_verification_report）

---

## 必要な依存パッケージ

主な依存（抜粋）:

- Python 3.9+
- duckdb
- psutil
- openai (ニュース NLP / レジーム判定を使う場合)
- requests (LINE 通知)
- PyYAML（設定ファイル検証を行う場合に推奨）

インストール例（venv 推奨）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai requests PyYAML
```

PyYAML は validate_config で YAML のパース検証を行うために使用します。未インストールでも検証はスキップされます（警告が出ます）。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動。
2. 仮想環境を作成し、必要なパッケージをインストール（上記参照）。
3. 環境変数（.env）を作成
   - 対話式ウィザードを使う:
     ```bash
     python -m kabusys.config_setup
     ```
   - もしくは手動で `.env` を作成（例）:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_token
     KABU_API_PASSWORD=your_kabu_password
     KABU_API_BASE_URL=http://localhost:18080/kabusapi
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     KILL_FLAG_CLEAR_ON_START=0
     ```
   - .env の自動読み込みはプロジェクトルートを基準に行われます。CWD に依存しません。
4. 設定検証
   ```bash
   python -m kabusys.validate_config
   # 厳密モード（警告もエラー扱い）
   python -m kabusys.validate_config --strict
   ```
5. DB ディレクトリの作成
   - デフォルトの DB は `data/` に置かれます。存在しない場合は起動時に自動作成されることがありますが、念のため `data/` を作成しておくと安心です。
     ```bash
     mkdir -p data
     ```

---

## 使い方

以下は主要なスクリプトと実行例です。

- 監視ループを起動（SystemMonitor をポーリング）
  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能。デフォルト 60 秒。
  ```bash
  python -m kabusys.run_monitoring
  # 例: 30 秒間隔でポーリング
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は常に本番用の sqlite_path を使用（KABUSYS_ENV に関係なく monitoring は本番 DB を参照）。

- 実行エンジンを起動（ExecutionEngine）
  - `KABUSYS_ENV=paper_trading` の場合、MockBrokerClient が使われ、履歴は `data/paper_trading.db`（または `PAPER_TRADING_SQLITE_PATH`）に記録され、本番 DB と完全に分離されます。
  ```bash
  python -m kabusys.run_execution
  # ペーパートレードで起動
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  - 起動時、`data/stop_requested.flag` が存在すると起動を中止します。停止は `data/stop_requested.flag` の作成で行います（監視側もこのフラグを検知してループを終了する実装があります）。

- 環境設定ウィザード（.env 作成 / 更新）
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

  # 別 DB を指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI / リサーチ機能の実行例（スクリプトはモジュール関数を直接呼び出す）
  - ニュース NLP（ai.news_nlp.score_news）やレジーム判定（ai.regime_detector.score_regime）は Python から呼び出します。例:
  ```bash
  python - <<'PY'
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect('data/kabusys.duckdb')
  # OPENAI_API_KEY を環境変数に設定しておくか、api_key 引数で渡す
  score_news(conn, date(2026,4,1))
  PY
  ```

- kill.flag / stop 制御
  - 実行系の停止は `data/kill.flag`（KillSwitch 用）および `data/stop_requested.flag`（プロセス終了用フラグ）で実現します。KillSwitch はリスク条件を満たすと `kill.flag` を書き込み、ExecutionEngine がこれを検知して停止する流れです。
  - Execution 起動時に `KILL_FLAG_CLEAR_ON_START=1` を設定すると起動時に自動で kill.flag をクリアしますが、本番では `0` を推奨します。

---

## 主要モジュールの説明（抜粋）

- kabusys.config
  - 環境変数・.env の読み込みロジック、Settings クラスを提供。
  - 自動ロード順: OS 環境変数 > .env.local > .env（プロジェクトルートが検出できる場合のみ）
- kabusys.run_monitoring
  - SystemMonitor を定期実行して monitoring DB に記録。プロセス優先度を high に設定。
- kabusys.run_execution
  - ExecutionEngine の起動スクリプト。paper_trading を切替。各種マネージャ（OrderManager, RiskManager, Reconciler 等）を組み立てて実行。
- kabusys.monitoring
  - monitoring_db: SQLite のテーブル初期化と永続化 API
  - system_monitor / trade_monitor / risk_monitor / monitoring_engine / kill_switch / alert_manager
- kabusys.portfolio
  - portfolio_builder, position_sizing, risk_adjustment: 銘柄選定・重み付け・株数計算・セクター制限・レジーム乗数
- kabusys.research
  - factor_research: momentum, volatility, value の計算（DuckDB）
  - feature_exploration: 将来リターン、IC、統計サマリ等
- kabusys.ai
  - news_nlp: ニュース → LLM（OpenAI）で銘柄別スコアリング
  - regime_detector: ma200 と LLM マクロセンチメントを合成して日次レジーム判定

---

## ディレクトリ構成

リポジトリの主要構成（src 直下）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / Settings
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                — ExecutionEngine / OrderManager 等（詳細省略）
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
  - tools/
    - paper_verification_report.py
  - utils/
    - process_priority.py

その他:
- data/                      — データファイル（DB / pid / flag 等を置く想定）
  - monitoring.db (default)
  - kabusys.duckdb (default)
  - paper_trading.db (paper_trading 用)
  - execution.pid
  - kill.flag
  - stop_requested.flag

---

## 環境変数（主要）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: development | paper_trading | live （デフォルト: development）
- DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
- SQLITE_PATH (監視 DB, デフォルト: data/monitoring.db)
- PAPER_TRADING_SQLITE_PATH (paper_trading 用 DB, デフォルト: data/paper_trading.db)
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- OPENAI_API_KEY (ai.news_nlp / ai.regime_detector を利用する場合必須)
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID（アラート送信）
- MONITOR_POLL_INTERVAL（run_monitoring 用、秒。デフォルト 60）

---

## トラブルシューティング / 注意点

- 必須環境変数が未設定だと Settings プロパティで ValueError が送出されます。`.env.example` を参考に `.env` を用意してください。
- validate_config は PyYAML がない場合 YAML 検証をスキップします（警告）。PyYAML を入れると config/*.yaml のパース検証が行われます。
- run_execution は起動時に `data/stop_requested.flag` をチェックします。フラグが立っていると起動せず終了します。
- monitoring は本番 monitoring DB（Settings.sqlite_path）を参照します。環境により参照先を混同しないよう注意してください。
- OpenAI の呼び出しは外部 API 依存のため、API レート制限やタイムアウトに注意。モジュール内でリトライ処理を実装していますが、API キーは適切に管理してください。
- Process priority / CPU affinity の設定は OS によって動作が異なります。パーミッション不足で設定失敗することがありますが、失敗時は警告が出てスキップされます。

---

## 参考コマンドまとめ

- 仮想環境作成 / 依存インストール:
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt  # requirements.txt があれば
  pip install duckdb psutil openai requests PyYAML
  ```

- .env 作成（ウィザード）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- 監視ループ起動:
  ```bash
  python -m kabusys.run_monitoring
  ```

- 実行エンジン起動:
  ```bash
  python -m kabusys.run_execution
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```

- Paper Trading レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

---

必要であれば、この README をベースにさらに詳細な運用手順（デプロイ、サービス化、ログ管理、バックアップ方針、各種設定例）を追加できます。どのセクションを拡張したいか教えてください。