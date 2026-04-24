# KabuSys

日本株自動売買システムのコードベース。ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ／ファクター計算、AI（ニュースセンチメント・レジーム判定）、および運用支援ツール群を含みます。

バージョン: 0.1.0

---

## 概要

KabuSys は日本株自動売買のためのモジュール群を提供するプロジェクトです。主要な責務は次の通りです。

- データ読み込み・分析（DuckDB を利用）
- 売買シグナルに基づくポートフォリオ構築（候補選定、重み付け、リスク調整、株数算出）
- 発注エンジン（本番 / ペーパートレード対応、ブローカークライアント抽象化）
- 実行運用の監視（システム状態・注文ログ・リスク監視、Kill Switch）
- AI を用いたニュースセンチメント評価・市場レジーム判定（OpenAI）
- 運用サポートツール（設定ウィザード、設定検証、ペーパートレード検証レポートなど）

設計上、分析・リサーチ系は本番発注にはアクセスせず、DuckDB やローカル DB（SQLite）を用いたオフライン／検証可能な処理を重視しています。

---

## 機能一覧

- 設定管理
  - .env 自動読み込み（プロジェクトルートの .env / .env.local）
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config
- 実行（Execution）
  - ExecutionEngine（本番 / paper_trading 切替）
  - RiskManager / OrderManager / Reconciler 等
  - pid / stop フラグ管理（data/execution.pid, data/stop_requested.flag）
- 監視（Monitoring）
  - SystemMonitor / TradeMonitor / RiskMonitor を束ねる MonitoringEngine
  - SQLite 監視 DB（system_status / trade_logs / positions / risk_logs / dashboard）
  - Kill Switch（data/kill.flag）による外部停止シグナル
- ポートフォリオ構築
  - 候補選定、等金額・スコア重み、リスク調整（セクターキャップ・レジーム乗数）
  - ポジションサイジング（risk_based / equal / score）
- リサーチ
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリ
- AI
  - ニュースの NLP スコアリング（OpenAI を利用）
  - 市場レジーム判定（ETF MA + マクロニュースの LLM 評価の合成）
- ツール
  - Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）

---

## 前提（依存ライブラリ・要件）

主要な依存ライブラリ（バージョンは用途に合わせて適宜選定してください）:

- Python 3.9+
- duckdb
- psutil
- openai
- PyYAML（config YAML 検証を行う場合）
- （任意）その他：sqlite3（標準ライブラリ）、logging（標準）

インストール例:

```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

※ requirements.txt があれば `pip install -r requirements.txt` を推奨します。

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化して依存をインストール（上記参照）
3. データディレクトリの作成（ログ・DB・フラグ用）:

   ```
   mkdir -p data logs
   ```

4. .env の作成（2通り）
   - 対話式ウィザードで作成:

     ```
     python -m kabusys.config_setup
     ```

   - 手動でファイルを作成（プロジェクトルートに `.env`）  
     最低限必要な環境変数:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）

     例（.env の抜粋）:
     ```
     JQUANTS_REFRESH_TOKEN=your_token_here
     KABU_API_PASSWORD=your_password_here
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     DUCKDB_PATH=data/kabusys.duckdb
     SQLITE_PATH=data/monitoring.db
     PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
     OPENAI_API_KEY=...
     ```

5. 設定検証:

   ```
   python -m kabusys.validate_config
   ```

   --strict を付けると警告も失敗扱いになります。

---

## 実行方法（主なコマンド）

- ExecutionEngine（発注エンジン）起動:

  ```
  python -m kabusys.run_execution
  ```

  動作概要:
  - KABUSYS_ENV が `paper_trading` の場合は MockBrokerClient を使用し、data/paper_trading.db に記録されます（本番 DB と分離）。
  - 起動時に `data/stop_requested.flag` が存在する場合は起動をスキップします。
  - 停止は `data/stop_requested.flag` 作成、または ExecutionEngine が自身で stop を受け取る仕組み。

- Monitoring（監視ループ）起動:

  ```
  python -m kabusys.run_monitoring
  ```

  動作概要:
  - デフォルトで 60 秒間隔でポーリング。
  - 環境変数でポーリング間隔を上書き可能: `MONITOR_POLL_INTERVAL`（秒）
  - 監視は本番 sqlite_path（Settings.sqlite_path）を参照して DB に書き込みます（環境に依存せず本番 path を使用）。
  - 停止フラグ: プロジェクトの data/stop_requested.flag を検知するとループを終了します。

- Paper Trading 検証レポート生成:

  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```

  オプション `--db` で SQLite ファイルパスを指定できます（環境変数 PAPER_TRADING_SQLITE_PATH も使用可）。

- 設定ウィザード:

  ```
  python -m kabusys.config_setup
  ```

- 設定検証:

  ```
  python -m kabusys.validate_config
  ```

---

## 主要設定項目（抜粋）

- KABUSYS_ENV: development | paper_trading | live
  - paper_trading: MockBroker を用いる
  - live: 実際の発注を行う
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI を使う機能で必要
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 DB（デフォルト data/paper_trading.db）
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: paper_trading の約定挙動（instant|partial|never|reject）

---

## プログラム的な利用例

- AI ニューススコアの実行（プログラムから）:

  ```python
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect('data/kabusys.duckdb')
  written = score_news(conn, target_date=date(2026, 4, 11), api_key="YOUR_OPENAI_KEY")
  print("書き込み件数:", written)
  conn.close()
  ```

- レジーム判定:

  ```python
  from kabusys.ai.regime_detector import score_regime
  written = score_regime(conn, target_date=date(2026,4,11), api_key="YOUR_OPENAI_KEY")
  ```

- ポートフォリオ関数利用:

  ```python
  from kabusys.portfolio import select_candidates, calc_score_weights, calc_position_sizes
  ```

---

## 運用上の注意点

- .env は絶対にリポジトリ（Git）にコミットしないでください（秘密情報を含む）。
- KABUSYS_ENV=live の設定では十分な確認のうえで起動してください。validate_config は live 時に警告を出します。
- Kill Switch（data/kill.flag）は ExecutionEngine を停止させるための重要な機構です。KILL_FLAG_CLEAR_ON_START は本番で 0（クリアしない）を推奨します。
- ログはデフォルトで logs/ に出力され、日次ローテーション（30日保持）で管理されます。ログディレクトリ作成に失敗した場合、コンソール出力のみになります。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
  - __init__.py
  - config.py               — 環境変数・設定管理
  - config_setup.py         — .env 対話式ウィザード
  - validate_config.py      — 設定検証 CLI
  - run_execution.py        — ExecutionEngine 起動スクリプト
  - run_monitoring.py       — Monitoring ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py
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
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - ...（trade_monitor, alert_manager 等）
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
  - utils/
    - logging_setup.py
    - process_priority.py

その他、data/（DB・フラグ）、logs/（ログ）が運用時に使用されます。

---

## 開発・デバッグのヒント

- ログ出力は `kabusys.utils.logging_setup.setup_logging(app_name=...)` で統一して設定しています。各起動スクリプトはこれを呼び出しているため、ログ周りの挙動は一元管理されています。
- 実行プロセスは起動時にプロセス優先度を上げようとします（psutil を使用）。権限がない場合は警告が出ますが処理は継続します。
- DuckDB のクエリは SQL を多用しています。大型データや速度改善は DuckDB 側のインデックス／クエリ最適化も検討してください。
- テスト時は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定すると自動で .env をロードしないためテストを独立して実行できます。
- OpenAI API 呼び出し周りはリトライ・バックオフを組み込んでいますが、APIキー・コスト管理は注意してください。

---

## ライセンス・注意

この README はコードベースからの抜粋説明です。実運用にあたっては各自で十分なテストとレビューを行い、実際の発注を行う環境では特に設定・ガード（Kill Switch、通知設定、リスク閾値）を慎重に検討してください。

--- 

必要であれば README に記載する具体的な .env のテンプレート、Docker / systemd ユニット例、あるいは各モジュールの API 使用例（より詳細）を追加で作成します。どの情報を拡張しますか？