# KabuSys

日本株向け自動売買システムのライブラリ / 実行スクリプト群です。  
このリポジトリには、戦略・ポートフォリオ構築、発注エンジン、監視、AI（ニュースセンチメント／レジーム判定）、および運用ユーティリティが含まれます。

## 目次
- プロジェクト概要
- 機能一覧
- 前提条件 / 依存パッケージ
- セットアップ手順
- 使い方（主要スクリプト・コマンド例）
- 環境変数（主なもの）
- ディレクトリ構成
- 運用上の注意 / トラブルシュート

---

## プロジェクト概要
KabuSys は、日本株の自動売買に必要なコンポーネント群を提供します。主な役割は以下です。

- データ処理・ファクター計算（DuckDB を利用）
- シグナル生成・ポートフォリオ構築（等配分・スコア加重・リスク制御）
- ExecutionEngine（発注ロジック／ブローカークライアントの抽象化）
- Monitoring（システム稼働監視、注文・リスク監視、Kill Switch）
- AI モジュール（ニュースのセンチメントスコアリング、レジーム判定） — OpenAI API を利用
- 運用ユーティリティ（.env ウィザード、設定検証、ペーパートレード検証レポート 等）

---

## 機能一覧
- portfolio
  - 候補選定、等ウェイト・スコア加重の重み計算
  - ポジションサイズ計算（リスクベース、上限・単元丸め、集約上限のスケールダウン）
  - セクターキャップ適用、レジーム乗数計算
- research
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB）
  - 将来リターン計算、IC（Information Coefficient）などの解析ユーティリティ
- execution
  - ExecutionEngine 起動スクリプト（本番 / ペーパートレード切り替え）
  - ブローカークライアント抽象化（paper_trading 時は MockBroker を使用）
- monitoring
  - SystemMonitor / TradeMonitor / RiskMonitor を統合する MonitoringEngine
  - 監視ログの永続化（SQLite）
  - KillSwitch（条件を満たすと kill.flag を書いて ExecutionEngine を停止）
- ai
  - ニュースの NLP（OpenAI）による銘柄別センチメント取得と ai_scores への保存
  - レジーム判定（ETF MA とマクロセンチメントの合成）
- tools
  - Paper Trading 検証レポート生成（SQLite データから各種指標を集計）
- utils
  - ロギング初期化（ファイルローテーション）
  - プロセス優先度 / CPU affinity 設定
- 開発支援
  - .env 対話式ウィザード（config_setup）
  - 設定検証 CLI（validate_config）

---

## 前提条件 / 依存パッケージ
推奨 Python バージョン: 3.10+（typing の構文等を利用）

主な依存（必須 / 任意）:
- duckdb
- psutil
- openai (ai モジュールを利用する場合)
- PyYAML（config/*.yaml の中身チェックを行う場合は任意でインストール推奨）

インストール例（仮想環境を作成してから）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（requirements.txt がある場合はそれを使ってください）

---

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <repo_url>
   cd <repo_root>
   ```

2. 仮想環境の作成・依存パッケージのインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt   # もし用意されていれば
   # または最低限:
   pip install duckdb psutil openai pyyaml
   ```

3. .env の作成（対話式ウィザード推奨）
   ```bash
   python -m kabusys.config_setup
   ```
   これによりプロジェクトルートの `.env` を生成・更新できます。

4. 設定の検証
   ```bash
   python -m kabusys.validate_config
   # 警告もエラー扱いにしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. data / logs ディレクトリ
   - デフォルトデータパス（環境変数で上書き可能）
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading DB: data/paper_trading.db
   - ログはデフォルトで logs/<app_name>.log に日次ローテーションで出力されます。

---

## 使い方（主要スクリプト）

- ExecutionEngine を起動（本番 / paper_trading は KABUSYS_ENV に依存）
  ```bash
  # 実行例
  python -m kabusys.run_execution
  ```
  - KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用し paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 起動時に data/stop_requested.flag が存在する場合は起動しません。
  - 実行中は data/execution.pid に PID を書きます。停止は stop flag を作成するか、プロセスにシグナルを送ってください。

- Monitoring を起動（監視ループ）
  ```bash
  # ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可、デフォルト 60
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  - 監視は常に本番の sqlite_path を参照します（KABUSYS_ENV に依らず）。
  - data/stop_requested.flag を検出するとループを終了します。

- .env 対話式ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成
  ```bash
  # デフォルトの DB path は data/paper_trading.db。--db で指定可
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

- AI 関連（ライブラリ API）
  - ニューススコアリング:
    - 関数: kabusys.ai.score_news(conn, target_date, api_key=None)
    - OpenAI API キーは api_key 引数、または環境変数 OPENAI_API_KEY を利用
  - レジームスコア:
    - 関数: kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)

---

## 環境変数（主なものとデフォルト）

- 必須（運用には設定が必要）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD

- 実行環境
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - KILL_FLAG_CLEAR_ON_START: 0 / 1（本番では 0 推奨）

- ログ / データパス
  - LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
  - LOG_DIR: ログ保存先（デフォルト: logs）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db

- Execution / Monitoring
  - PID_FILE_PATH: data/execution.pid
  - KILL_FLAG_PATH: data/kill.flag
  - MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒） — default 60
  - PAPER_FILL_MODE: ペーパートレード時の約定挙動（instant/partial/never/reject）

- OpenAI
  - OPENAI_API_KEY: OpenAI を利用する場合に設定

より詳しい説明は `kabusys.config.Settings` を参照してください（デフォルト値・妥当性チェックが実装されています）。

---

## ディレクトリ構成（抜粋）
以下は src/kabusys 以下の主要ファイル・ディレクトリ構成です。

- kabusys/
  - __init__.py
  - config.py                # 環境変数 / 設定読み込み
  - config_setup.py          # .env 対話式ウィザード
  - validate_config.py       # 設定検証 CLI
  - run_execution.py         # ExecutionEngine 起動スクリプト
  - run_monitoring.py        # Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - execution/                # ExecutionEngine 関連（ブローカー、order 管理など）
  - data/                     # (運用時生成) DB・フラグ・PID ファイル置き場
  - logs/                     # (運用時生成) ログファイル置き場

（上記は主要ファイルの抜粋です。完全な一覧はリポジトリを参照してください）

---

## 運用上の注意 / トラブルシュート

- ログディレクトリが作成できないとファイル出力ハンドラは無効化され、コンソール出力のみになります。パーミッション等を確認してください。
- プロセス優先度設定は OS に依存します。`psutil.AccessDenied` 等で設定できない場合は警告ログが出力されますが処理は続行します。
- Monitoring / Execution の停止:
  - `data/stop_requested.flag` が存在すると起動時に実行を回避したり、ループ中に停止します（両スクリプトで使用）。
  - KillSwitch は `data/kill.flag` を書き込み、ExecutionEngine の停止を誘発します。`KILL_FLAG_CLEAR_ON_START=1` に注意（本番では 0 推奨）。
- Paper trading:
  - KABUSYS_ENV=paper_trading の場合、発注は MockBroker によりペーパートレード DB（PAPER_TRADING_SQLITE_PATH）へ記録され、本番 DB と分離されます。
- OpenAI 利用:
  - API 呼び出しに失敗した場合（429/ネットワーク/5xx）はリトライやフェイルセーフ（0.0やスキップ）が入る設計ですが、APIキー未設定ではエラーになります。`OPENAI_API_KEY` を設定してください。
- DuckDB / SQLite:
  - DuckDB は分析用のテーブル（prices_daily, raw_financials 等）を参照します。テーブルが存在しないと関数は例外や空結果を返す場合があります。
- 設定検証:
  - `python -m kabusys.validate_config` で起動前に必須環境変数や config/*.yaml の存在等をチェックできます。
- テスト／開発:
  - 自動的に .env を読み込む機能は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化できます（ユニットテストなどで便利です）。

---

必要に応じてこの README をプロジェクト向けに追補してください。特に運用時のプロセス管理（systemd / Supervisor / cron などでのデーモン化）、バックアップ・DB 配置、またブローカークライアント設定（API の認証情報）については運用環境に合わせたドキュメント化を推奨します。