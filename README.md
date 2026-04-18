# KabuSys

日本株自動売買システム（ライブラリ／実行スクリプト群）

このリポジトリは、価格データの研究・ファクター計算、ポートフォリオ構築、発注エンジン、監視（Monitoring）や Paper Trading 検証などを含む自動売買システムのコア部分を提供します。

## 概要

- DuckDB を用いた研究（ファクター計算、特徴量解析）
- SQLite（monitoring / paper_trading）を用いた監視・ログ永続化
- ExecutionEngine（発注エンジン）と監視用 MonitoringEngine
- AI を使ったニュースセンチメント評価（OpenAI）
- 設定ウィザード (`config_setup`) と起動前チェック (`validate_config`)
- Paper Trading 検証レポート生成ツール

設計方針の一部：
- 研究モジュールは DB 参照に限定（発注 API 等にはアクセスしない）
- 本番・ペーパートレード DB を分離して安全性を確保
- OpenAI 呼び出しは故障時にフェイルセーフ（ゼロフォールバック）を行う

---

## 主な機能一覧

- 設定関連
  - .env 対話生成ウィザード: python -m kabusys.config_setup
  - 起動前設定検証: python -m kabusys.validate_config

- 実行 / 監視
  - ExecutionEngine 起動スクリプト: python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBroker を使用し、`data/paper_trading.db` に記録
    - 停止フラグ（data/stop_requested.flag や data/kill.flag）に対応
  - Monitoring 起動スクリプト: python -m kabusys.run_monitoring
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を変更可能（デフォルト 60 秒）
    - 監視用 DB は環境にかかわらず production の sqlite_path を使用

- 監視コンポーネント
  - SystemMonitor: CPU/メモリ/ディスク、プロセス／データ鮮度監視
  - TradeMonitor: 発注ログの滞留チェック・約定異常検出（実装ファイル参照）
  - RiskMonitor: ドローダウン・ポジション上限監視とリスクログ記録
  - KillSwitch: 条件を満たした時に data/kill.flag を書いて ExecutionEngine を停止

- ポートフォリオ
  - 候補選定 / 重み算出（等金額、スコア加重）
  - セクターキャップ適用
  - ポジションサイズ計算（単元反映、資金制約適用）

- 研究 / 分析
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC 計算、ファクター統計要約

- AI（OpenAI）
  - news_nlp: ニュース記事を LLM で評価して ai_scores を更新
  - regime_detector: ETF + マクロニュースで市場レジーム判定

- ツール
  - Paper Trading 検証レポート: python -m kabusys.tools.paper_verification_report

---

## 必要な依存パッケージ（例）

必須（最低限）:
- Python 3.9+
- duckdb
- psutil
- openai（AI 機能を使う場合）
- PyYAML（config ファイルの検証を行う場合）

インストール例（venv 推奨）:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して依存をインストール
3. .env を作成
   - 対話式ウィザード:
     ```
     python -m kabusys.config_setup
     ```
   - もしくは `.env.example` を参考に手動作成
4. 設定検証:
   ```
   python -m kabusys.validate_config
   ```
   - `--strict` を付けると警告も失敗扱い（exit(1)）
5. データディレクトリの確認:
   - デフォルトの DB / ログ / フラグパス
     - DuckDB: data/kabusys.duckdb
     - SQLite (monitoring): data/monitoring.db
     - Paper trading SQLite: data/paper_trading.db
     - PID / kill flag: data/execution.pid, data/kill.flag, data/stop_requested.flag
     - ログ: logs/

環境変数自動ロード:
- プロジェクトルートに `.env` / `.env.local` があれば自動で読み込みます（OS 環境変数は優先）。
- 自動ロードを無効にする場合:
  ```
  export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  ```

重要な環境変数（抜粋）:
- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- KABUSYS_ENV: development | paper_trading | live
- OPENAI_API_KEY（AI 機能使用時）
- DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH
- LOG_LEVEL, LOG_DIR
- MONITOR_POLL_INTERVAL（監視ポーリング間隔、秒, run_monitoring 用）
- PAPER_FILL_MODE（paper_trading の fill 動作）

---

## 使い方（主要コマンド）

- .env の作成（対話式）
  ```
  python -m kabusys.config_setup
  ```

- 設定検証
  ```
  python -m kabusys.validate_config
  python -m kabusys.validate_config --strict
  ```

- ExecutionEngine 起動
  - 本番 / 開発 / ペーパーは KABUSYS_ENV で制御
  - ペーパートレード（MockBroker）例:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行中停止:
    - `data/stop_requested.flag` を作成するとループが検知して停止します（起動スクリプトが参照）
    - KillSwitch が条件を満たすと `data/kill.flag` を作成します（明示的に削除・確認可能）

- Monitoring 起動
  ```
  export MONITOR_POLL_INTERVAL=60  # 秒（任意）
  python -m kabusys.run_monitoring
  ```
  - Monitoring は設定にかかわらず監視用 sqlite_path（デフォルト data/monitoring.db）を使用します

- Paper Trading 検証レポート
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # または DB パスを直接指定
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI 機能（例: レジーム判定 / ニューススコア）
  - OpenAI API キーを設定:
    ```
    export OPENAI_API_KEY="sk-..."
    ```
  - モジュール関数を呼ぶ（ライブラリ利用）:
    - kabusys.ai.score_news
    - kabusys.ai.regime_detector.score_regime
  - コード内で API キーを引数で渡すことも可能

ログ設定:
- 共通のログ初期化関数 `kabusys.utils.logging_setup.setup_logging(app_name="...")` を各起動スクリプトで呼んでいます
- ログ出力先はデフォルト `logs/<app_name>.log`、日次ローテーション（30日保持）

---

## 停止 / フラグファイル

- run_execution と run_monitoring はプロジェクト内の `data/stop_requested.flag` を監視しており、存在すれば安全にループを終了します。
- KillSwitch は条件に応じて `data/kill.flag` を作成し ExecutionEngine 停止を促します。
- 手動で停止させる場合はフラグファイルを作成するか、プロセスに SIGINT（Ctrl+C）を送ります。
- KillFlag を自動クリアする設定（危険）:
  - KILL_FLAG_CLEAR_ON_START=1 にすると起動時に kill.flag をクリアします（本番では 0 推奨）。

---

## ディレクトリ構成（主要ファイル）

（リポジトリ内 src/kabusys 以下の主なファイル／モジュール）

- kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 起動前設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリングループ起動
  - execution/               — 発注エンジン関連（Engine, broker_factory, order_manager 等）
  - monitoring/
    - monitoring_db.py       — SQLite 永続化レイヤ
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
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - ai/
    - news_nlp.py
    - regime_detector.py
    - __init__.py
  - utils/
    - logging_setup.py
    - process_priority.py
    - __init__.py
  - tools/
    - paper_verification_report.py

data/ および logs/ は実行時に作成されることが多いディレクトリです。

---

## 動作上の注意 / Q&A

- 監視 DB（SQLite）は run_monitoring が使用します。Monitoring は環境にかかわらず `Settings.sqlite_path` を使います。
- ExecutionEngine は KABUSYS_ENV によって本番あるいは Paper Trading（完全分離された DB）を使い分けます。ペーパートレード時は `paper_sqlite_path`（デフォルト data/paper_trading.db）へ書き込みます。
- OpenAI を利用する機能は API キー（OPENAI_API_KEY）が必須です。API 呼び出しはリトライ／フォールバック設計になっていますが、キー未設定では該当関数は ValueError を投げます。
- ローカルでテストするときは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットして自動 .env ロードを無効化できます。

---

## 参考（サンプル .env の主要項目）

JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-...

---

この README はリポジトリ内のソースコード（設定・実行スクリプト・ユーティリティ）に基づき作成しています。プロジェクト固有の運用手順やデプロイ方法（サービス化、systemd / コンテナ化等）は個別に追加してください。必要があれば起動フロー図やユースケース別の手順ドキュメントも作成します。