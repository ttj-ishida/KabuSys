# KabuSys

日本株向け自動売買システムの Python 実装（モジュール群）。  
このリポジトリには、取引エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ / ファクター計算、ポートフォリオ構築、AI（ニュース NLP / レジーム判定）などの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は次の目的を持つモジュール化された自動売買基盤です。

- 戦略に基づく銘柄選定・配分・株数決定（portfolio モジュール）
- DuckDB を用いた時系列データ処理とファクター計算（research モジュール）
- 発注ロジック / リスク管理 / 発注ログ（execution モジュール）
- 実行監視・アラート・Kill Switch（monitoring モジュール）
- ニュースセンチメントやレジーム判定のための LLM（AI）連携（ai モジュール）
- ペーパートレード検証用レポート生成ツール（tools）

設計上の特徴：

- 環境変数 / .env による柔軟な設定（`kabusys.config.Settings`）
- 本番とペーパートレードで SQLite DB を分離（`KABUSYS_ENV=paper_trading`）
- ロギングは共通ユーティリティ（`kabusys.utils.logging_setup.setup_logging`）
- フェイルセーフ（API失敗はスキップ、部分更新で既存データ保護 など）

---

## 主な機能一覧

- ExecutionEngine（実取引／ペーパートレード両対応）
  - ブローカークライアント抽象化（Mock を含む）
  - リスク管理（最大ポジション比率、利用率、ドローダウン監視）
  - オーダー管理・約定ログ保存
- Monitoring
  - システム（CPU/メモリ/ディスク）監視
  - 注文ログ監視（滞留注文、約定異常など）
  - リスク監視（ドローダウン／ポジション数）
  - Kill Switch（条件成立で停止フラグ書き込み）
- Research / Factors
  - モメンタム、ボラティリティ、バリューファクター計算（DuckDB）
  - 特徴量探索（forward returns, IC, summary）
- AI
  - ニュースのセンチメントスコア化（OpenAI）
  - マクロニュース + ETF MA による市場レジーム判定
- ユーティリティ
  - .env 設定ウィザード（`config_setup`）
  - 設定検証 CLI（`validate_config`）
  - ペーパートレード検証レポート生成スクリプト

---

## 必要条件 / 推奨環境

- Python 3.10+
- pip
- 推奨パッケージ（最低限）:
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config YAML 検証時、任意）
- OS: Linux / macOS / Windows（process priority / affinity は OS に依存する挙動あり）

インストール例（仮想環境内）:

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil openai pyyaml
```

（必要に応じて追加パッケージをインストールしてください）

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動

   ```bash
   git clone <repo-url>
   cd <repo-root>
   ```

2. 仮想環境・依存パッケージをインストール（上記参照）

3. 環境変数（.env）を作成
   - 対話式ウィザードを利用する場合:

     ```bash
     python -m kabusys.config_setup
     ```

     ウィザードで `.env` を生成できます。

   - 必須環境変数（最低限）:
     - JQUANTS_REFRESH_TOKEN
     - KABU_API_PASSWORD

   - 重要な設定例:
     - KABUSYS_ENV: development | paper_trading | live
       - paper_trading の場合、MockBrokerClient を使用し DB は `data/paper_trading.db` に分離されます。
     - DUCKDB_PATH: 分析用 DB（デフォルト data/kabusys.duckdb）
     - SQLITE_PATH: 監視 DB（デフォルト data/monitoring.db）
     - OPENAI_API_KEY: OpenAI を使う場合に必要

4. 設定検証（任意だが推奨）

   ```bash
   python -m kabusys.validate_config
   # 警告も fail にしたい場合:
   python -m kabusys.validate_config --strict
   ```

5. ディレクトリ作成（必要に応じて）

   ログや DB を出力するために `data/` や `logs/` は自動作成されますが、権限等で失敗するケースがあるため手動で作ることも可能です。

---

## 使い方

各起動スクリプトはモジュールとして実行します。

- ExecutionEngine（エンジン起動）

  ```bash
  # 本番または .env の KABUSYS_ENV に従う
  python -m kabusys.run_execution
  ```

  挙動:
  - 起動時にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続します。
  - KABUSYS_ENV=paper_trading のときは paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離します。
  - 起動中、`data/stop_requested.flag` の存在を監視して停止します。
  - PID ファイル: data/execution.pid（デフォルト。Settings.pid_file_path で変更可）

- Monitoring（監視ループ起動）

  ```bash
  # ポーリング間隔は MONITOR_POLL_INTERVAL（秒）で変更可（デフォルト 60）
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  挙動:
  - システム状態（CPU/MEM/DISK）、データ鮮度、トレードログ、リスクチェックを定期実行。
  - 監視は常に（環境にかかわらず）本番 sqlite_path を使用して監視テーブルを初期化します。
  - `data/stop_requested.flag` を検知して終了します。

- ペーパートレード検証レポート

  ```bash
  # デフォルト DB: data/paper_trading.db
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB を直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
  ```

- .env の作成 / 更新（ウィザード）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  ```

停止・Kill スイッチ関連:

- 手動停止フラグ（run_execution / run_monitoring がチェック）
  - data/stop_requested.flag を作成すると、両スクリプトは検知して安全に停止します。
- KillSwitch（監視が条件を満たすと書き込む）
  - `data/kill.flag` が生成されると ExecutionEngine に致命的停止（Kill Switch）を促します。
  - Settings に `KILL_FLAG_CLEAR_ON_START` があり、起動時に自動クリアするか選べます（本番では 0 推奨）。

ログ:

- ログはデフォルトで logs/<app_name>.log に日次ローテートで保存されます（logs/ ディレクトリ）。
- すべての起動スクリプトは `kabusys.utils.logging_setup.setup_logging` を使って統一的に設定されます。

AI 機能 (news_nlp / regime_detector):

- OpenAI を利用するために `OPENAI_API_KEY` を設定してください。
- API エラー時はフェイルセーフでスコアを 0 にするなど保守的な挙動を取ります。

---

## 重要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV (development | paper_trading | live) — デフォルト: development
- DUCKDB_PATH — デフォルト: data/kabusys.duckdb
- SQLITE_PATH — デフォルト: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH — paper_trading 用（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY — AI モジュール使用時に必須
- LOG_LEVEL — デフォルト INFO
- MONITOR_POLL_INTERVAL — 監視ポーリング間隔（秒、run_monitoring 用）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START など

詳しくは `kabusys.config.Settings` を参照してください。

---

## ディレクトリ構成（主要ファイル）

リポジトリの主要な構成は以下の通りです（抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理（Settings）
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py  — ペーパートレード検証レポート
  - ai/
    - news_nlp.py             — ニュース NLP（OpenAI 経由）
    - regime_detector.py      — レジーム判定
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - monitoring_db.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - monitoring_engine.py
    - kill_switch.py
    - alert_manager.py
  - execution/                — (発注ロジック、OrderManager 等) ＊詳細はリポジトリ内
  - utils/
    - logging_setup.py
    - process_priority.py
  - data/ (実行時に生成される想定)
  - logs/ (ログ出力先)

（注: 上記はこのリポジトリの主要ソースファイル抜粋です。詳細は実際のツリーをご参照ください。）

---

## 開発・テスト時のヒント

- 設定検証（validate_config）は起動前チェックに便利です。
- `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットすると config.py の自動 .env ロードを抑止できます（テストで環境を制御したい場合に有用）。
- MonitoringEngine は `run_once()` を持っていて単体テスト用に 1 回だけ監視処理を実行できます（ユニットテストでの利用推奨）。
- AI 関連は API コールを含むため、ユニットテストでは `_call_openai_api` をモックしてテストしてください（モジュール内ドキュメント参照）。

---

## ライセンス / 貢献

この README はコードベースの説明を目的としたもので、実際の運用にあたっては必ず設定やリスクポリシーを確認してください。  
コントリビュートやライセンスに関する情報はリポジトリのトップレベルにある LICENSE / CONTRIBUTING を参照してください（存在する場合）。

---

以上。必要であれば、README に .env.example のサンプルや起動シーケンス図、よくあるトラブルシューティング（ログディレクトリ権限、DB マイグレーションなど）を追加します。どの情報を優先して追記しますか？