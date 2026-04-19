# KabuSys

日本株向けの自動売買／リサーチ基盤（ライブラリ＆起動スクリプト群）

このリポジトリは以下の主要機能を持つモジュール群で構成されています。
- 注文実行エンジン（ExecutionEngine）と発注・リスク管理周辺ロジック
- 監視（Monitoring）および Kill Switch（停止フラグ）機構
- ポートフォリオ構築・ポジションサイジング・リスク調整の純関数群
- リサーチ（ファクター計算・特徴量探索）
- ニュース NLP / 市場レジーム判定（OpenAI を利用したスコアリング）
- 開発補助スクリプト（.env ウィザード / 設定検証 / レポート生成）

README ではプロジェクト概要、機能一覧、セットアップ手順、使い方、ディレクトリ構成を日本語で説明します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムを構成するモジュール群です。実行エンジンは実口座（live）とペーパートレード（paper_trading）を切り替え可能で、監視コンポーネントが動作状況やデータ鮮度、リスク（ドローダウン・ポジション上限など）を常時監視します。AI ベースのニュースセンチメント（OpenAI）を取り込み、市場レジーム判定や銘柄ごとの sentiment スコアを生成できます。データ処理・計算は DuckDB / SQLite を利用します。

設計方針の特徴：
- リサーチ／ファクター計算は DuckDB 上で完結（本番口座にアクセスしない）
- ペーパートレードは本番 DB と完全分離（`data/paper_trading.db`）
- ログ・監視の永続化は SQLite（monitoring.db）
- 構成は環境変数 / .env で管理。`.env` の自動ロード機能あり（プロジェクトルートを検出）

---

## 主な機能一覧

- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動（KABUSYS_ENV に応じて実口座 / モック）
  - run_monitoring.py: SystemMonitor のポーリングループ起動（MONITOR_POLL_INTERVAL で間隔設定可）
- 設定管理・補助
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: .env と config/*.yaml の存在・妥当性検証 CLI
  - config.py: Settings クラス（環境変数読み取り・検証、自動 .env 読み込みロジック）
- 監視
  - monitoring_engine.py: 各 Monitor を束ねて定期実行
  - system_monitor.py: システム資源 / データ鮮度 / 実行プロセス監視
  - trade_monitor.py / risk_monitor.py: 注文・リスク関連の監視（risk_monitor はドローダウン／ポジション数）
  - kill_switch.py: 条件に応じて data/kill.flag を書き込み ExecutionEngine に停止シグナルを送る
  - monitoring_db.py: SQLite に対する読み書き抽象（テーブル作成・マイグレーション含む）
- 実行（Execution）
  - ExecutionEngine, BrokerClientFactory, OrderManager, Reconciler, RiskManager（実装ファイル群は execution パッケージ内）
  - paper_trading モードは MockBrokerClient を使用し DB を分離
- ポートフォリオ構築
  - portfolio/ : 候補選定、重み算出、セクター制限、ポジションサイズ計算
- リサーチ
  - research/ : ファクター計算（momentum, volatility, value）・将来リターン・IC 計算
- AI（OpenAI）
  - ai/news_nlp.py: ニュースを LLM でセンチメント評価して ai_scores に書き込み
  - ai/regime_detector.py: マクロニュース + ETF MA を組み合わせてレジーム判定
- ツール
  - tools/paper_verification_report.py: ペーパートレードログから検証レポートを生成
- ユーティリティ
  - utils/logging_setup.py: 統一ログ設定（コンソール + 日次ローテーションファイル）
  - utils/process_priority.py: プラットフォーム差分を吸収したプロセス優先度/CPU affinity 設定

---

## 必要な依存ライブラリ

（代表的なもの）
- Python 3.10+（型アノテーションに | を使用）
- duckdb
- psutil
- openai
- PyYAML（config ファイルの検証時に利用。無くても動作はするが YAML 検証がスキップされる）
- その他標準ライブラリ（sqlite3, threading, logging, pathlib, etc.）

例: requirements.txt がない場合のインストール例
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

psutil は platform によって追加のビルド要件がある場合があります。必要に応じて OS のパッケージマネージャで準備してください。

---

## セットアップ手順

1. リポジトリをクローン
   - git clone <repo-url>

2. Python 仮想環境を作成・有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 依存パッケージをインストール
   - pip install duckdb psutil openai pyyaml

4. ディレクトリを作成（初回）
   - mkdir -p data logs

   主要デフォルトパス:
   - DuckDB: data/kabusys.duckdb （DUCKDB_PATH）
   - SQLite (monitoring): data/monitoring.db （SQLITE_PATH）
   - Paper trading SQLite: data/paper_trading.db （PAPER_TRADING_SQLITE_PATH）
   - PID / フラグ: data/execution.pid, data/kill.flag, data/stop_requested.flag
   - ログ: logs/

5. .env の作成（推奨）
   - 対話式ウィザード: python -m kabusys.config_setup
   - もしくは .env を手動で作成（以下に必須 env を例示）

必須環境変数（最低限）
- JQUANTS_REFRESH_TOKEN=...
- KABU_API_PASSWORD=...

重要な環境変数（例）
- KABUSYS_ENV=development|paper_trading|live
- DUCKDB_PATH=data/kabusys.duckdb
- SQLITE_PATH=data/monitoring.db
- PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
- PAPER_FILL_MODE=instant|partial|never|reject
- OPENAI_API_KEY=（AI 機能利用時に必要）
- LOG_LEVEL=INFO
- LOG_DIR=logs
- KILL_FLAG_CLEAR_ON_START=0 または 1
- LINE_CHANNEL_ACCESS_TOKEN=（通知利用）
- LINE_USER_ID=（通知利用）

6. 設定検証（任意）
   - python -m kabusys.validate_config
   - --strict をつけると警告も失敗扱いになります: python -m kabusys.validate_config --strict

---

## 使い方（主なコマンド）

- 実行エンジンを起動
  - production/live / development / paper_trading に応じて .env の KABUSYS_ENV を設定
  - python -m kabusys.run_execution
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、paper_trading 用 DB（PAPER_TRADING_SQLITE_PATH）に記録
    - run_execution は data/stop_requested.flag を確認し、フラグがあれば起動しない／停止する

- 監視ループを起動
  - python -m kabusys.run_monitoring
    - デフォルトのポーリング間隔は 60 秒。環境変数で上書き可:
      - MONITOR_POLL_INTERVAL=30（秒）
    - 監視は monitoring DB（SQLITE_PATH）を使用（KABUSYS_ENV に依存せず本番 sqlite_path を使用）

- ペーパートレード検証レポート
  - python -m kabusys.tools.paper_verification_report --db data/paper_trading.db --from 2026-04-01 --to 2026-04-11

- AI によるニューススコア / レジーム判定（スクリプトやリサーチから呼ぶ）
  - OpenAI API キーを環境変数 OPENAI_API_KEY にセット
  - ai.score_news / ai.regime_detector.score_regime を呼び出す（DuckDB 接続と target_date を渡す）

- ログ設定
  - すべての起動スクリプトは kabusys.utils.logging_setup.setup_logging を呼び出します
  - ログはデフォルト logs/<app_name>.log に日次ローテーションで保存されます（LOG_DIR で変更可）

- Kill Switch / Stop フラグ
  - KillSwitch は条件に応じて data/kill.flag を書き込みます（ExecutionEngine はこのファイルを監視して停止）
  - 手動停止用のフラグ: data/stop_requested.flag（run_execution/run_monitoring はこれを見て終了）

---

## 注意事項 / 運用メモ

- .env の自動読み込み
  - プロジェクトルートが検出される場合、自動で `.env` を読み込みます（`.env.local` は上書き可）。
  - 自動読み込みを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

- DB の分離
  - ペーパートレード（paper_trading）は本番監視 DB と分離するよう設計されています。PAPER_TRADING_SQLITE_PATH を確認してください。

- OpenAI 関連
  - AI 機能を使うには OPENAI_API_KEY が必要です。
  - 使用モデルはコード上で gpt-4o-mini を指定しています（変更する場合は該当モジュールを編集）。

- ログディレクトリ作成に失敗した場合はコンソール出力のみで継続します（ファイルへの書き込みはスキップされます）。

- システム優先度設定
  - 起動スクリプトは最初に set_process_priority("high") を実行します。権限不足で設定に失敗した場合は警告が出ますが処理は継続します。

---

## ディレクトリ構成（抜粋）

以下は src/kabusys 以下の主要ファイル・ディレクトリ構成の抜粋です。

- src/kabusys/
  - __init__.py
  - config.py
  - config_setup.py
  - validate_config.py
  - run_execution.py
  - run_monitoring.py
  - tools/
    - __init__.py
    - paper_verification_report.py
  - ai/
    - __init__.py
    - news_nlp.py
    - regime_detector.py
  - monitoring/
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - trade_monitor.py (実装あり)
    - alert_manager.py (実装あり)
  - execution/
    - execution_engine.py
    - broker_factory.py
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - utils/
    - __init__.py
    - logging_setup.py
    - process_priority.py
  - monitoring/
    - （上記の監視関連ファイル群）

また、プロジェクトルートには次のような運用用パスが想定されます（デフォルト）:
- data/monitoring.db
- data/paper_trading.db
- data/kabusys.duckdb
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag
- logs/<app_name>.log

---

## よくある操作例

- .env を対話式で生成
  - python -m kabusys.config_setup

- 設定の事前検証
  - python -m kabusys.validate_config
  - 本番前に --strict を使うことを推奨

- 監視をデーモンで実行（例）
  - MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring &

- 実行エンジンをデバッグ実行
  - python -m kabusys.run_execution

- ペーパートレードレポート作成
  - python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-30

---

## 開発・拡張のヒント

- DuckDB を使ったリサーチ関数は副作用なしで純関数化されています。テストが書きやすく、データソースを差し替え可能です。
- AI まわり（news_nlp / regime_detector）は OpenAI の呼び出しを内部でラップしています。ユニットテスト時は `_call_openai_api` をモックしてください（コード内でもその想定でコメントがあります）。
- monitoring_db.init_monitoring_db は冪等でマイグレーション処理を行います。既存 DB に対する列追加処理（例: latency_ms, peak_value）を含みます。

---

もし README に追加してほしい内容（例: 詳細な設定例、config/*.yaml の説明、CI 手順、実際の起動例の systemd サービス定義 など）があれば教えてください。必要に応じて追記します。