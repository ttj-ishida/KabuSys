# KabuSys — README (日本語)

日本株向け自動売買 / リサーチ基盤の小規模フレームワークです。  
このリポジトリは、取引実行エンジン、監視（Monitoring）、ポートフォリオ構築、ファクター計算、AI（ニュースセンチメント）などのコンポーネントを含みます。各コンポーネントはできるだけ副作用を抑え、環境変数ベースで設定可能となっています。

---

目次
- プロジェクト概要
- 主な機能一覧
- セットアップ手順
- 使い方（起動・コマンド例）
- 環境変数（主要なもの）
- ディレクトリ構成
- 追加の注意事項

---

## プロジェクト概要

KabuSys は日本株の自動売買や研究（リサーチ）処理を想定したコードベースです。  
主な設計方針は以下の通りです。

- 設定は .env（環境変数）で管理（自動ロード機能あり）。
- Execution（発注）と Monitoring（稼働監視）は独立したプロセスとして起動可能。
- Paper Trading（模擬発注）用の専用 DB を用意し、本番 DB と分離。
- DuckDB を分析用データベースとして利用し、ファクター計算・リサーチは DuckDB を直接参照。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント / レジーム判定モジュールを含む（API キー必須）。
- ログはコンソールと日次ローテートされたファイルへ出力。

---

## 主な機能一覧

- 実行関連
  - ExecutionEngine 起動スクリプト（run_execution.py）
  - BrokerClientFactory によるブローカークライアント選定（本番 / Mock）
  - OrderManager / OrderRepository / Reconciler / RiskManager

- 監視関連
  - SystemMonitor: CPU/メモリ/ディスク/データ鮮度/プロセス生存監視
  - TradeMonitor: 注文ログ監視（滞留注文・異常約定など）
  - RiskMonitor: ドローダウン・ポジション上限監視（kill flag の発行）
  - MonitoringEngine: 上のモニタを統合してポーリング（run_monitoring.py）

- ポートフォリオ構築
  - 候補抽出、等ウェイト / スコアウェイト計算
  - セクター上限適用、レジームによる乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- リサーチ / ファクター計算
  - モメンタム、ボラティリティ、バリュー等のファクター（DuckDB を用いた計算）
  - 将来リターン計算、IC（スピアマン）や統計サマリー

- AI（OpenAI）連携
  - ニュース NLP による銘柄別センチメント（ai_scores へ格納）
  - マクロニュース + ETF MA による市場レジーム判定（market_regime への書込み）
  - API 呼び出しはリトライ / バックオフ、レスポンス検証を含む

- ユーティリティ
  - 設定ウィザード（config_setup.py）で .env を対話生成
  - 設定検証 CLI（validate_config.py）
  - Paper Trading 検証レポート出力ツール（tools/paper_verification_report.py）
  - ログ設定ユーティリティ（utils/logging_setup.py）
  - プロセス優先度 / CPU affinity 設定（utils/process_priority.py）

---

## セットアップ手順

前提
- Python 3.9+（コードは型注釈・パス表記を使用）
- システムに sqlite3 は標準で同梱されていますが、以下の外部パッケージを利用します。

推奨インストール（例）
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai
# 任意（YAML 検証用）
pip install PyYAML
```

ディレクトリ準備（データ／ログ）
```bash
mkdir -p data logs
```

.env の作成（ウィザード）
```bash
python -m kabusys.config_setup
# 対話形式で .env を生成します（.env は Git に入れないでください）
```

設定検証
```bash
python -m kabusys.validate_config
# --strict を付けると警告もエラー扱いになります
```

注意:
- OpenAI を使う機能を利用する場合は OPENAI_API_KEY を .env に設定してください。
- Paper Trading（模擬発注）を使う場合は KABUSYS_ENV=paper_trading に設定し、PAPER_TRADING_SQLITE_PATH（任意）を指定できます。

---

## 使い方（起動・コマンド例）

主要なエントリポイントはモジュール実行（-m）です。

- 実行エンジン起動（ExecutionEngine）
  - 本番 / ペーパーの切替は KABUSYS_ENV により自動判定
  - 起動例:
    ```bash
    # 通常（.env で KABUSYS_ENV を設定）
    python -m kabusys.run_execution

    # 環境変数でポール間隔変更など
    KABUSYS_ENV=paper_trading python -m kabusys.run_execution
    ```

  - 実行時の動作:
    - プロセス優先度を high に設定し（可能な環境で）、SQLite / DuckDB に接続します。
    - paper_trading 環境では MockBroker を使用し data/paper_trading.db に記録します。
    - data/stop_requested.flag が作成されるとエンジンを停止します。

- 監視プロセス起動（Monitoring）
  - 起動例:
    ```bash
    # ポーリング間隔は MONITOR_POLL_INTERVAL で上書き（秒、デフォルト 60）
    MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
    ```
  - 動作:
    - SystemMonitor / TradeMonitor / RiskMonitor を用いて定期チェックを実行
    - KillSwitch が条件を満たすと data/kill.flag を書き込み ExecutionEngine の停止を指示できます
    - 監視は常に本番 sqlite_path を使用（環境に依存せず）

- 環境設定ウィザード
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証
  ```bash
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- Paper Trading 検証レポート（SQLite のパス指定可）
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を明示する:
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI 関連（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=None)
  - ai.regime_detector.score_regime(conn, target_date, api_key=None)
  - これらは DuckDB 接続オブジェクトを受け取ります。API キーは引数か環境変数 OPENAI_API_KEY で渡します。

ログ出力
- デフォルトで logs/<app_name>.log に日次ローテーションで出力されます（30日保持）。
- console は stdout に出力します。

停止 / キルフラグ
- Execution 停止用フラグ: data/kill.flag（KillSwitch により作成）
- 監視停止フラグ（run_monitoring / run_execution 用）: data/stop_requested.flag

---

## 主要な環境変数

（重要なもののみ抜粋）

- JQUANTS_REFRESH_TOKEN — 必須（J-Quants API 用）
- KABU_API_PASSWORD — 必須（kabuステーション API）
- KABUSYS_ENV — 実行環境: development | paper_trading | live（デフォルト: development）
- LOG_LEVEL — ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH — SQLite (monitoring) ファイルパス（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — Paper Trading 用 SQLite（デフォルト data/paper_trading.db）
- PAPER_FILL_MODE — paper_trading の約定モード（instant|partial|never|reject）
- OPENAI_API_KEY — OpenAI API キー（AI 機能使用時に必須）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）
- LOG_DIR — ログ保存先（デフォルト logs/）
- KILL_FLAG_CLEAR_ON_START — 起動時に kill.flag を自動クリア（0/1、本番では 0 推奨）

設定ファイルの自動読込
- プロジェクトルートにある .env / .env.local を自動で読み込みます（OS 環境変数優先）。
- 自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下）

- __init__.py
- config.py — Settings クラス（.env 読込・設定アクセス）
- config_setup.py — .env 対話ウィザード
- validate_config.py — 設定検証 CLI
- run_execution.py — ExecutionEngine 起動スクリプト
- run_monitoring.py — Monitoring 起動スクリプト

- execution/（発注関連コンポーネント）
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - reconciler.py
  - risk_manager.py

- monitoring/
  - monitoring_db.py — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - monitoring_engine.py
  - kill_switch.py
  - alert_manager.py

- portfolio/
  - portfolio_builder.py
  - risk_adjustment.py
  - position_sizing.py

- research/
  - factor_research.py
  - feature_exploration.py

- ai/
  - news_nlp.py
  - regime_detector.py

- tools/
  - paper_verification_report.py

- utils/
  - logging_setup.py
  - process_priority.py

その他:
- data/ — デフォルト DB・PID・フラグファイルを置く（自動作成可能）
  - data/monitoring.db
  - data/paper_trading.db
  - data/kabusys.duckdb
  - data/execution.pid
  - data/kill.flag
  - data/stop_requested.flag

- logs/ — ログファイル（logs/execution.log, logs/monitoring.log など）

---

## 追加の注意事項 / 運用上のポイント

- 本番（KABUSYS_ENV=live）では LINE の通知設定（LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID）を必ず確認してください。validate_config は live 時に追加チェックを行います。
- run_monitoring は監視 DB の sqlite_path（Settings.sqlite_path）を常に使います（環境に依存せず本番 DB を参照する設計）。
- run_execution は paper_trading 環境では専用 Paper DB を使い、本番 DB と分離します。
- kill.flag の自動クリア（KILL_FLAG_CLEAR_ON_START）を本番で有効にするのは危険です（安全側は 0）。
- OpenAI 呼び出しはレート制限や一時的障害に備えてリトライ／バックオフが組み込まれています。ただし API キーや料金体系には注意してください。
- DuckDB / SQLite のスキーマは monitoring_db.init_monitoring_db などで自動作成・マイグレーションを行います。

---

README はここまでです。必要であれば以下の点について README を拡張します:
- 具体的な開発フロー（ユニットテスト、CI 設定）
- requirements.txt の候補
- 各モジュール（ExecutionEngine / SystemMonitor / AI モジュール等）の詳細 API ドキュメント

どの部分を詳しく追記しますか？