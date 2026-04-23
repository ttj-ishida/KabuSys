# KabuSys

日本株向け自動売買システムのミニマル実装（ライブラリ + 起動スクリプト群）。

この README はリポジトリ内の主要モジュール群に基づいて作成しています。各スクリプトはパッケージモードから実行できます（例: `python -m kabusys.run_execution`）。

---

## プロジェクト概要

KabuSys は以下のような機能を持つモジュール群で構成された自動売買システムです：

- 注文実行エンジン（ExecutionEngine、ブローカー抽象化、リスク管理、再調整）
- 監視（System / Trade / Risk のポーリングとアラート、Kill Switch）
- ポートフォリオ構築（銘柄選定、重み計算、ポジションサイズ計算、セクター制限）
- 調査 / リサーチ（ファクター計算、特徴量探索）
- AI 関連（ニュース NLP による銘柄センチメント、レジーム判定）
- 各種ユーティリティ（設定読み込み、ロギング、プロセス優先度設定、.env ウィザード、設定検証）
- ペーパートレード用の分離 DB と検証レポート生成ツール

設計上、データ永続化には SQLite（監視・発注ログ等）と DuckDB（時系列・分析用）を併用します。Paper trading（模擬発注）用 DB は本番 DB と完全に分離されます。

---

## 主な機能一覧

- Execution
  - ブローカークライアント抽象化（実運用とモックの切替）
  - 注文管理、オーダーリポジトリ、リスク管理、再調整（Reconciler）
  - PID ファイル生成・停止フラグ監視（data/execution.pid, data/stop_requested.flag）
- Monitoring
  - システム（CPU/メモリ/ディスク）・データ鮮度監視
  - 注文ログ、リスクログの収集／永続化（monitoring_db）
  - Kill Switch（ドローダウン／ポジション上限で ExecutionEngine を停止）
  - アラート発行（AlertManager 経由）
- Portfolio
  - 候補選定、等重／スコア重み、リスクベースのポジションサイズ算出
  - セクター上限適用、レジームに応じた乗数
- Research
  - モメンタム、ボラティリティ、バリュー等のファクター計算（DuckDB 経由）
  - 将来リターン・IC 計算、統計サマリ
- AI
  - ニュースの LLM（OpenAI）を使ったセンチメントスコア生成（ai_scores への書込み）
  - マクロニュース + 指数（1321）の MA を使った市場レジーム判定
- 開発支援
  - .env ウィザード（config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools/paper_verification_report）

---

## 必要要件（概算）

主要依存パッケージ（実行に必要となる可能性が高いもの）:

- Python 3.9+
- duckdb
- psutil
- openai (AI 機能を使う場合)
- PyYAML（設定 YAML 検証を行う場合、なくても警告となる）
- （その他）標準ライブラリ

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
# 実際は requirements.txt があれば `pip install -r requirements.txt` を使ってください
```

---

## 環境変数（主要なもの）

必須:

- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション:

- KABUSYS_ENV: 実行環境（development | paper_trading | live）。デフォルト: development
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- OPENAI_API_KEY: OpenAI API キー（AI モジュール使用時）
- PAPER_FILL_MODE: Paper ブローカーの約定挙動（instant|partial|never|reject、デフォルト: instant）
- MONITOR_POLL_INTERVAL: 監視ループのポーリング間隔（秒、監視プロセス用。デフォルト 60）

監視／停止関連ファイル（設定経由で変更可）:

- PID_FILE_PATH（デフォルト: data/execution.pid）
- KILL_FLAG_PATH（デフォルト: data/kill.flag）
- KILL_FLAG_CLEAR_ON_START（起動時に kill.flag を自動クリアするか。1=クリア）

注意:
- run_monitoring（監視）は KABUSYS_ENV にかかわらず本番の sqlite_path（SQLITE_PATH）を使用します。
- run_execution は KABUSYS_ENV=paper_trading の場合に PAPER_TRADING_SQLITE_PATH を使用し、本番 DB と完全分離します。

---

## セットアップ手順（簡略）

1. リポジトリをチェックアウト
2. 仮想環境作成・依存パッケージをインストール
3. .env を作成（推奨: ウィザードを使用）
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成後、設定を検証:
     ```bash
     python -m kabusys.validate_config
     # 警告も FAIL として扱う strict モード:
     python -m kabusys.validate_config --strict
     ```
4. 必要なディレクトリを作成（ログ・data 等）:
   ```bash
   mkdir -p data logs
   ```
   ログディレクトリは `LOG_DIR` 環境変数またはデフォルト `logs/` が使用されます。

---

## 使い方（主要コマンド例）

すべてパッケージモードで実行できます。

- 監視ループの起動（SystemMonitor のポーリング）
  ```bash
  # ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で上書き可能
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```
  注: run_monitoring は data/stop_requested.flag を検知するとループを終了します。

- 実行エンジン（ExecutionEngine）の起動
  ```bash
  # 環境切替: paper_trading / live / development
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution
  ```
  実行中は `data/execution.pid` が作成され、`data/stop_requested.flag` によって停止されます。

- .env の作成（ウィザード）
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

  # 別 DB を指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- AI スコアリング / レジーム判定（ライブラリ呼び出し）
  - OpenAI API キーを設定して、該当関数を呼ぶことで実行できます（例: `kabusys.ai.score_news` / `kabusys.ai.regime_detector.score_regime`）。
  - 例（スクリプト内呼び出し）:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect('data/kabusys.duckdb')
    score_news(conn, date(2026, 4, 1), api_key="sk-...")
    ```

- ログ設定
  - すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging(app_name=...)` を呼び出します。ログは stdout と日次ローテートされるファイルに出力されます（`logs/<app_name>.log`）。

---

## 停止・Kill Switch の取り扱い

- ExecutionEngine を外部から停止したい場合:
  - 監視コンポーネント（KillSwitch）または手動で `data/kill.flag` を作成すると、実行側で検出して停止等の動作を行う仕組みがあります（KillSwitch は設定に応じて書き込みます）。
  - run_monitoring / run_execution は `data/stop_requested.flag` の存在をチェックして終了します。手動で停止させたい場合はこのファイルを作ると良いでしょう。

- kill.flag の自動クリア:
  - 設定 `KILL_FLAG_CLEAR_ON_START=1` をセットすると、Execution 起動時に kill.flag を自動消去します（本番では通常 0 推奨）。

---

## 開発・デバッグ向けメモ

- Logging
  - ロギングは一元化されているので、ログレベルを変えてデバッグしやすい（`LOG_LEVEL=DEBUG`）。
- プロセス優先度
  - 起動スクリプトはプロセス優先度を「high」にセットしようとします（psutil の権限に依存）。
- DB マイグレーション
  - monitoring_db.init_monitoring_db() は冪等で実行され、必要に応じて簡単なマイグレーション（カラム追加）も行います。
- テスト用 API のモックや関数の単体実行が可能（MonitoringEngine.run_once 等）。

---

## ディレクトリ構成（抜粋）

以下はこのリポジトリの主要ファイル／ディレクトリの簡易ツリー（src/kabusys 以下）です。

- src/kabusys/
  - __init__.py
  - config.py                      # 環境変数・Settings
  - config_setup.py                # .env 対話ウィザード
  - validate_config.py             # 設定検証 CLI
  - run_monitoring.py              # SystemMonitor ポーリング起動スクリプト
  - run_execution.py               # ExecutionEngine 起動スクリプト
  - utils/
    - logging_setup.py             # ログ設定ユーティリティ
    - process_priority.py          # プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py             # monitoring DB ラッパー
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
    - broker_factory.py
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

（上記は主要ファイルの抜粋です。実際のファイル一覧はリポジトリを参照してください。）

---

## 参考・注意事項

- 本 README はコードベースの現状に基づいて作成しています。実際の運用では追加のセキュリティ対策（API キー管理、アクセス権限設定）、障害時のオペレーション手順、テストスイート、CI/CD 等を整備してください。
- AI（OpenAI）連携箇所は API キー・レートリミット・費用に注意して利用してください。失敗時はフォールバック動作が実装されていますが、安全運用方針を設けることを推奨します。
- Paper Trading 用 DB は本番 DB と分離されています。Paper トレードと本番データの混在に注意してください。

---

必要なら README にサンプル .env テンプレートや、詳細な起動オプション（各モジュールのパラメータ説明）、ユースケース別の推奨設定（local/dev/paper/live）を追記できます。追加したい項目があれば教えてください。