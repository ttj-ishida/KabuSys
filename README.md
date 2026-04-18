# KabuSys

日本株向けの自動売買システム（ライブラリ / 実行スクリプト群）

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買を目的としたモジュール群です。  
主に以下の機能を含みます:

- 注文実行エンジン（ExecutionEngine）
- 監視（System / Trade / Risk）と Kill Switch による安全停止
- ポートフォリオ構築（銘柄選定・重み付け・株数算出）
- リサーチ用ファクター計算（モメンタム、バリュー、ボラティリティ等）
- ニュースを用いた LLM（OpenAI）ベースのセンチメント評価 / レジーム判定
- ペーパートレード向けログ・検証レポート生成
- 設定ウィザード / 設定検証 CLI

設計方針の一部:
- 環境変数ベースの設定（.env）を採用
- paper_trading モードは本番 DB と完全分離
- DuckDB を分析・リサーチ用に使用、SQLite を運用ログに使用
- 外部 API 呼び出し（kabuステーション / J-Quants / OpenAI）を想定

---

## 主な機能一覧

- 実行エンジン起動スクリプト（run_execution.py）
  - KABUSYS_ENV により paper_trading（MockBroker）/ live（実際のブローカー）を切替
  - ペーパートレード時は `data/paper_trading.db` に記録（本番 DB と分離）
- 監視プロセス起動スクリプト（run_monitoring.py）
  - CPU / メモリ / ディスク / データ鮮度 / 実行プロセスの監視
  - Kill Switch の評価（ドローダウン、ポジション上限など）
- 監視 DB レイヤー（monitoring_db）
  - system_status / trade_logs / positions / risk_logs / dashboard テーブル管理
- リスク監視（RiskMonitor）
  - ドローダウン検知・ポジション数上限検知、必要ならリスクイベント記録
- ポートフォリオ構築（portfolio/*.py）
  - 候補選定、等重・スコア重み付け、株数計算（単元株丸め、資金上限調整 等）
- 研究／ファクター（research/*.py）
  - モメンタム、ボラティリティ、バリューの算出
  - 将来リターン、IC（Information Coefficient）、統計サマリー
- AI モジュール（ai/news_nlp.py, ai/regime_detector.py）
  - OpenAI (gpt-4o-mini 想定) を用いたニュースセンチメント / マクロセンチメント評価
  - ai_scores / market_regime の DuckDB 書き込み
- 設定ウィザード（config_setup.py）と検証ツール（validate_config.py）
- ペーパートレード検証レポート生成（tools/paper_verification_report.py）

---

## 要件 / 依存関係

推奨 Python バージョン: 3.9+

主な Python パッケージ（例）
- duckdb
- psutil
- openai
- PyYAML（config 検証時に使用。無くても実行は可能）
- その他: 標準ライブラリや sqlite3 は標準で利用

インストール例:
```bash
python -m pip install -r requirements.txt
# requirements.txt がない場合は個別に:
python -m pip install duckdb psutil openai pyyaml
```

---

## セットアップ手順

1. リポジトリをクローン / 配置
2. 仮想環境（任意）を作成・有効化
3. 依存パッケージをインストール（上記参照）
4. .env を作成
   - 対話式ウィザードを利用:
     ```bash
     python -m kabusys.config_setup
     ```
   - ウィザードで `.env` を生成後、必須環境変数（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD 等）を設定してください。
5. 設定検証:
   ```bash
   python -m kabusys.validate_config
   # --strict を付けると警告も失敗扱い
   python -m kabusys.validate_config --strict
   ```
6. 必要であればデータディレクトリを作成（スクリプト実行時に自動作成されることもありますが明示的に準備しておくと良い）
   - デフォルトのパス:
     - DuckDB: data/kabusys.duckdb
     - SQLite (監視): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / flag: data/execution.pid, data/stop_requested.flag, data/kill.flag
     - ログ: logs/

---

## 環境変数（主要）

- 必須
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
- 任意 / デフォルトあり
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
  - PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
  - LOG_LEVEL: DEBUG | INFO | WARNING | ERROR | CRITICAL（デフォルト: INFO）
  - LOG_DIR: logs/
  - OPENAI_API_KEY: OpenAI を使う機能で必要
  - MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、デフォルト 60）
  - KILL_FLAG_CLEAR_ON_START: 1 = 起動時に kill.flag を自動クリア（危険: 本番では 0 推奨）
  - PID_FILE_PATH, KILL_FLAG_PATH（デフォルトは data 内のパス）

例 (.env の一部)
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

- 実行エンジン（ExecutionEngine）を起動:
  - 本番 / ペーパートレードは KABUSYS_ENV に依存します。
  ```bash
  python -m kabusys.run_execution
  ```
  - 停止: 外部から `data/stop_requested.flag` を作成すると起動済みエンジンに停止指示を送れます（または monitoring の Kill Switch が `data/kill.flag` を書き込みます）。

- 監視プロセスを起動:
  ```bash
  # ポーリング間隔は MONITOR_POLL_INTERVAL で上書き可（秒）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

- .env の作成（対話式ウィザード）:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート生成:
  ```bash
  # デフォルト db: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report
  # 期間指定や db パス指定も可能:
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11 --db /path/to/paper_trading.db
  ```

- AI 機能（ニューススコア / レジーム判定）は OpenAI API キーが必要:
  - OPENAI_API_KEY を環境変数に設定するか、関数に渡して使用します（モジュール内部で参照）。

---

## 停止 / Kill Switch / フラグファイル

- run_execution.py / run_monitoring.py はプロジェクト内 `data/stop_requested.flag` を参照してループ/スレッドを終了します。
- 監視ロジックの KillSwitch は `data/kill.flag` を書き込み、ExecutionEngine に停止信号を与える運用を行います（kill.flag を既に存在する場合は再書き込みしません）。
- PID ファイル: `data/execution.pid`（実行エンジンの PID を保持する用途）

運用上の注意:
- 本番環境（KABUSYS_ENV=live）では `KILL_FLAG_CLEAR_ON_START`=1 の設定は危険（自動クリアされてしまうため推奨しません）。
- kill.flag / stop_requested.flag の作成・削除は慎重に行ってください。

---

## ロギング

- ログは stdout（コンソール）とファイル両方へ出力されます（TimedRotatingFileHandler: 日次ローテーション、30日分保持）。
- デフォルトログディレクトリ: `logs/`
- ログ設定は `kabusys.utils.logging_setup.setup_logging(app_name=...)` で統一設定されます。
- 環境変数 `LOG_LEVEL` / `LOG_DIR` で動作を変更可能。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内 `src/kabusys` 相対の想定）

- kabusys/
  - __init__.py
  - config.py                — 環境変数・設定管理
  - config_setup.py          — .env 対話ウィザード
  - validate_config.py       — 設定検証ツール
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — Monitoring 起動スクリプト
  - tools/
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py            — ニュース NLP（OpenAI）スコアリング
    - regime_detector.py     — 市場レジーム判定（MA + マクロセンチメント）
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py       (実装あり／参照)
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py       (実装あり／参照)
  - execution/
    - execution_engine.py    (実装あり／参照)
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - data/                    — 実行時に利用するファイル群（デフォルト）
    - monitoring.db
    - paper_trading.db
    - kabusys.duckdb
    - execution.pid
    - stop_requested.flag
    - kill.flag

上記は主要なモジュールを抜粋した構成です。細かいサブモジュールや実装は各ファイルを参照してください。

---

## 運用上のヒント / 注意点

- KABUSYS_ENV によって動作が大きく変わるので、開発 / テスト時は `development` または `paper_trading` を使用してください。`live` は実際の発注が行われるため慎重に。
- Paper trading は本番 DB と分離するため `PAPER_TRADING_SQLITE_PATH` を確認してください。
- OpenAI 呼び出し部分は外部 API が関与するためレート制限や API エラーに備えた設計になっています。APIキー管理とコストに注意してください。
- ストレージ/ログの容量管理、PID/flag ファイルの取扱い、Kill Switch の設定は運用ルールを事前に決めておくことを推奨します。
- DB スキーマ変更に対しては monitoring_db で簡易マイグレーション処理を行いますが、本番環境ではバックアップを取得してからマイグレーションしてください。

---

必要に応じて README の具体的なコマンドや .env のテンプレートを追加します。どの部分をより詳述したいか教えてください（例: ExecutionEngine の起動フロー、AI モジュールの使い方、またはデータベース初期化手順など）。