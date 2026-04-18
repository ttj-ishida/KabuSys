# KabuSys

日本株向け自動売買システム（ライブラリ＋起動スクリプト群）。  
シグナル生成・ポートフォリオ構築・発注エンジン・監視・AI（ニュース NLP / レジーム判定）・検証ツールを含むモジュール群で構成されています。

バージョン: 0.1.0

---

## 概要

KabuSys は、データ取得／ファクター計算／ポートフォリオ構築／実際の発注（またはペーパートレード）／運用監視までを一貫して扱う自動売買基盤のプロトタイプ実装です。  
主な設計方針は次の通りです。

- モジュール分離（execution / monitoring / research / portfolio / ai / utils）
- 本番（live）とペーパートレード（paper_trading）を明確に分離
- DuckDB／SQLite によるデータ保管（分析用 / 監視用）
- OpenAI を用いたニュース NLP / レジーム判定（フェイルセーフ設計）
- 簡易な Kill Switch / flag ファイルによる外部停止

---

## 機能一覧

- 環境設定ウィザード（.env を対話式に生成）: `kabusys.config_setup`
- 設定検証 CLI（env / config/*.yaml のチェック）: `kabusys.validate_config`
- 実行エンジン起動スクリプト（ExecutionEngine）: `kabusys.run_execution`
  - KABUSYS_ENV に応じて本番 or ペーパートレードを選択
  - paper_trading 時は MockBroker を用い、専用 DB に記録
- 監視プロセス起動スクリプト（SystemMonitor ポーリング）: `kabusys.run_monitoring`
  - システム資源（CPU/メモリ/ディスク）、データ鮮度、Executionプロセスの健全性を監視
- 監視エンジン（MonitoringEngine）: 各 Monitor の束ね処理、アラート連携、Kill Switch 評価
- 監視 DB 永続化層（SQLite）: `monitoring_db`
- リスク監視（ドローダウン/ポジション上限）: `monitoring.risk_monitor`
- Trade / Order 関連のログ・管理（trade_logs / positions / risk_logs / dashboard）
- ポートフォリオ構築モジュール（候補選定・配分・リスク制御・ポジションサイジング）
- リサーチ（ファクター計算 / 特徴量探索 / IC 計算）
- AI モジュール
  - news_nlp: ニュースから銘柄ごとのセンチメントを生成（OpenAI）
  - regime_detector: マクロ + ETF MA を使った市場レジーム判定（OpenAI）
- 検証ツール
  - Paper Trading 検証レポート生成: `kabusys.tools.paper_verification_report`

---

## 前提 / 推奨環境

- Python 3.10+
- 必要な Python パッケージ（一例）:
  - duckdb
  - psutil
  - openai
  - pyyaml (config YAML の検証に使用、必須ではない)
- SQLite（標準ライブラリに含まれる）
- ネットワーク接続（OpenAI を利用する場合）

インストール例:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（プロジェクトに requirements.txt がある場合はそちらを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 展開
2. 仮想環境を作成して依存パッケージをインストール
3. 環境変数設定
   - 対話式で .env を作る（推奨）:
     ```
     python -m kabusys.config_setup
     ```
   - あるいは `.env` を直接作成して以下の主要キーを設定:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - KABUSYS_ENV（development / paper_trading / live）
     - OPENAI_API_KEY（AI 機能を使う場合）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用: data/paper_trading.db）
     - LOG_LEVEL（例: INFO）
     - その他 README 内の説明参照
4. 設定検証（起動前に推奨）
   ```
   python -m kabusys.validate_config
   # 警告を fail としたい場合:
   python -m kabusys.validate_config --strict
   ```
5. 必要に応じてデータディレクトリ作成:
   ```
   mkdir -p data logs
   ```

---

## 使い方（主要スクリプト）

- Execution（売買エンジン）起動:
  - 本番:
    ```
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - ペーパートレード:
    ```
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 実行中停止:
    - `data/stop_requested.flag` を作成すると起動中スレッドが検出して停止します（または ExecutionEngine により kill.flag を検知して停止）。
    - KillSwitch がトリガーした停止は `data/kill.flag` に理由が書き込まれます。

- Monitoring（監視プロセス）起動:
  ```
  export MONITOR_POLL_INTERVAL=60   # 省略時は 60 秒
  python -m kabusys.run_monitoring
  ```
  - 監視ループは定期的に SystemMonitor / TradeMonitor / RiskMonitor を実行し、必要に応じて Kill Switch を書き込みます。
  - 監視は常に production（SQLITE_PATH）を参照します（KABUSYS_ENV に依存せず本番監視 DB を使う）。

- 設定ウィザード:
  ```
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成:
  ```
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを明示する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能をプログラムから呼び出す例（Python API）:
  ```python
  from datetime import date
  from kabusys.ai.news_nlp import score_news
  import duckdb, os

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 4, 10), api_key=os.environ.get("OPENAI_API_KEY"))
  ```

---

## 主要環境変数（抜粋）

- KABUSYS_ENV: execution 動作モード（development / paper_trading / live）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必須）
- KABU_API_PASSWORD: kabuステーション API パスワード（必須）
- OPENAI_API_KEY: OpenAI API キー（AI 機能使用時）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL: ログレベル（DEBUG/INFO/…）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- PAPER_FILL_MODE: ペーパートレードの約定振る舞い（instant / partial / never / reject）
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（1=有効、デフォルト 0）

注意: .env の自動読み込み機能はプロジェクトルート（.git または pyproject.toml を含む）を基準に行われます。自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

## ログ / DB / フラグファイル

- ログ: デフォルト `logs/` 下にアプリ毎（execution.log, monitoring.log 等）で日次ローテーション保存
- 監視 DB: デフォルト `data/monitoring.db`
- DuckDB: デフォルト `data/kabusys.duckdb`
- ペーパートレード DB: `data/paper_trading.db`（paper_trading 時に使用）
- PID / Stop / Kill フラグ:
  - Execution PID: `data/execution.pid`
  - Stop リクエスト（プロセスを優しく止める）: `data/stop_requested.flag`
  - Kill Switch（自動的に書き込まれる）: `data/kill.flag`

---

## ディレクトリ構成（抜粋）

プロジェクトの主要ファイル配置（src/kabusys）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数/Settings 管理
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor ポーリング起動スクリプト
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py (参照)
  - execution/
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - broker_factory.py
    - reconciler.py
    - risk_manager.py
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
  - utils/
    - logging_setup.py
    - process_priority.py
  - tools/
    - paper_verification_report.py

（上記はリストの一部抜粋です。詳細はソースツリーを参照してください）

---

## 開発者向けメモ / 注意点

- Paper Trading と Live の DB は分離されています。paper_trading モードは `PAPER_TRADING_SQLITE_PATH` を使用します（実運用 DB と混ぜないこと）。
- AI（OpenAI）呼び出しはリトライやフェイルセーフを組み込んでいますが、APIキーと利用上限には注意してください。API 呼び出し失敗時は基本的に処理を継続します（ゼロやスキップでフォールバック）。
- process priority（高優先度設定）や CPU affinity 設定はプラットフォームに依存するので権限不足等で失敗することがあります（警告ログのみ）。
- DuckDB を用いた研究モジュールは SQL を使った大規模集計向けに設計されています。テーブル名（prices_daily 等）を前提とした実装です。
- `monitoring_db.init_monitoring_db` は冪等でスキーマ作成／簡易マイグレーション（カラム追加）を行います。

---

## トラブルシューティング

- .env を作成したが設定が反映されない:
  - プロジェクトルートが検出できない（.git / pyproject.toml がない）と自動ロードをスキップします。`KABUSYS_DISABLE_AUTO_ENV_LOAD` の設定も確認してください。
- OpenAI 関連で認証エラー:
  - `OPENAI_API_KEY` が正しく設定されているか確認してください。
- ログファイルが作成されない:
  - `logs/` ディレクトリへ書き込み権限があるか確認。`setup_logging` はディレクトリ作成失敗時にコンソール出力へフォールバックします。
- データベース（DuckDB / SQLite）への接続エラー:
  - ファイルパスや権限、ディスク容量を確認してください。

---

## ライセンス / コントリビューション

この README はコードベースに基づくドキュメント生成例です。実際のライセンスやコントリビューションガイドはプロジェクトのルートに追加してください。

---

必要に応じて README に追記したい項目（例: API 詳細、構成ファイルの例、テスト手順、CI 設定など）があれば教えてください。