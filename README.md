# KabuSys

日本株向けの自動売買システム（ライブラリ＋起動スクリプト群）

このリポジトリは、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI によるニュース分析などを含む自動売買基盤のコア部品を提供します。設計方針としては「本番用の安全ガード」「ペーパートレードとの分離」「DuckDB を用いたリサーチ」「OpenAI を使ったニューススコアリング」などが組み込まれています。

---

## 主な機能

- ExecutionEngine
  - 実際の発注またはペーパートレードを行うエンジン
  - リスク管理（最大ポジション比率や利用率など）
  - 発注／注文管理／照合（reconciler）等
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、paper_trading 用 DB に記録

- Monitoring
  - システムのCPU/メモリ/ディスク監視
  - プロセス生存チェック（execution の PID ファイル参照）
  - 注文の滞留／約定異常検知
  - ドローダウンやポジション数上限の監視
  - Kill Switch（flag ファイルを書き込んで ExecutionEngine 停止を指示）
  - 監視ログの永続化（SQLite）

- Portfolio（銘柄選定・配分・ポジションサイズ）
  - 候補選定、等配分／スコア配分、リスクベースの単元丸め、セクター上限などの純粋関数群

- Research
  - DuckDB を用いたファクター計算（モメンタム／ボラティリティ／バリュー等）
  - 将来リターン計算、IC（Information Coefficient）計算、特徴量サマリー

- AI
  - ニュース NLP（OpenAI）を用いた銘柄ごとのセンチメントスコア生成（ai_scores 書き込み）
  - 市場レジーム判定（ETF の MA とマクロニュースを合成）

- ツール
  - 設定ウィザード（.env 作成支援）
  - 設定検証 CLI（.env / config/*.yaml の事前チェック）
  - Paper Trading 検証レポート出力スクリプト

---

## 前提（Prerequisites）

- Python 3.9+
- 必要なライブラリ（例、インストール例）
  - duckdb
  - psutil
  - openai
  - PyYAML（設定ファイル検証に必要）
- SQLite は標準で利用（Python 標準モジュール）
- （任意）OpenAI API を使う場合は API キーが必要

依存関係は requirements.txt があればそれを使ってください。なければ上記パッケージを pip で入れてください。

例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローン／配置

2. 仮想環境の作成（推奨）
```
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
```

3. 依存パッケージのインストール
```
pip install -r requirements.txt   # もし用意されていれば
# または最低限:
pip install duckdb psutil openai PyYAML
```

4. .env の作成（対話ウィザード推奨）
```
python -m kabusys.config_setup
```
このウィザードは J-Quants トークン、kabuAPI パスワード、DB パス、KABUSYS_ENV など主要な環境変数を対話式で作成します。

5. 設定検証（起動前チェック）
```
python -m kabusys.validate_config
# 警告も失敗扱いにする場合:
python -m kabusys.validate_config --strict
```

---

## 主要な環境変数（抜粋）

- KABUSYS_ENV
  - 実行環境: `development` | `paper_trading` | `live`
  - `paper_trading` の場合、発注はモック（data/paper_trading.db を使用）になります。

- JQUANTS_REFRESH_TOKEN
  - J-Quants API 用リフレッシュトークン（必須）

- KABU_API_PASSWORD
  - kabuステーション API のパスワード（必須）

- DUCKDB_PATH
  - DuckDB ファイルのパス（デフォルト: data/kabusys.duckdb）

- SQLITE_PATH
  - 監視用 SQLite（monitoring.db）のパス（デフォルト: data/monitoring.db）
  - Monitoring は環境にかかわらず本番 sqlite_path を使用します。

- PAPER_TRADING_SQLITE_PATH
  - paper_trading 時の専用 SQLite（デフォルト: data/paper_trading.db）

- LOG_LEVEL
  - ログレベル（例: INFO, DEBUG）

- OPENAI_API_KEY
  - OpenAI を使う機能（news_nlp / regime_detector）の API キー

- MONITOR_POLL_INTERVAL
  - 監視ポーリング間隔（秒）。run_monitoring のデフォルトは 60 秒。0 以下／不正値は 60 秒にフォールバック。

- KILL_FLAG_CLEAR_ON_START
  - 起動時に kill.flag を自動でクリアするか（0/1）。本番では 0 推奨。

その他は config_setup の項目参照。

---

## 実行方法（使い方）

- 監視ループを起動
```
python -m kabusys.run_monitoring
```
- 説明:
  - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 監視は停止フラグ (data/stop_requested.flag) を検出するとループを終了します。
  - 監視開始前にプロセス優先度を "high" に設定し、SQLite / DuckDB に接続します。

- 発注エンジン（ExecutionEngine）を起動
```
python -m kabusys.run_execution
```
- 説明:
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使い、ペーパートレード専用 DB（PAPER_TRADING_SQLITE_PATH）へ記録します。
  - 起動時に data/stop_requested.flag が存在すると起動せず終了します。
  - 実行中は data/execution.pid が使用されます（Settings.pid_file_path）。

- 設定ウィザード
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
```

- Paper Trading 検証レポート（ツール）
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI / Research 関数
  - AI の機能はライブラリ関数として提供されています（CLI は基本的に無い）。
  - 例: news_nlp.score_news(conn, target_date, api_key) や ai.regime_detector.score_regime(conn, target_date, api_key)
  - DuckDB 接続を渡して呼び出す形です。

---

## ログ / データファイル

- ログ
  - ログはデフォルトで logs/ ディレクトリに出力されます。ファイル名はアプリケーション名をプレフィックスにした日次ローテーション（例: logs/monitoring.log）。
  - LOG_DIR 環境変数で変更可能。

- データベース
  - DuckDB: data/kabusys.duckdb（デフォルト）
  - 監視 SQLite: data/monitoring.db（デフォルト）
  - Paper Trading SQLite: data/paper_trading.db（paper_trading 環境時）

- Kill / Stop フラグ
  - data/kill.flag: Kill Switch（監視がこのファイルを書き込むことで ExecutionEngine 停止を指示）
  - data/stop_requested.flag: ローカル停止要求（run_monitoring/run_execution がチェック）

---

## 停止・Kill の仕組み

- KillSwitch（監視側）がリスク条件（ドローダウン上限やポジション数上限）を満たすと data/kill.flag を書き込みます。ExecutionEngine はこのフラグを検出して安全に停止します。
- 管理者が手動で停止したい場合は data/stop_requested.flag を作成すると run_* スクリプトが検出して終了します。
- 実運用では KILL_FLAG_CLEAR_ON_START を 0（デフォルト）にしておくことを推奨します。

---

## 主なモジュール概要（抜粋）

- kabusys.config
  - .env 自動読み込み、Settings クラス。KABUSYS_ENV / DB パス / 各種閾値等をプロパティとして提供。

- kabusys.utils.logging_setup
  - ルートロガーの統一設定（コンソール + 日次ローテートファイル）。

- kabusys.utils.process_priority
  - Windows / POSIX を吸収したプロセス優先度設定・CPU affinity ユーティリティ。

- kabusys.monitoring.*
  - monitoring_db: SQLite テーブル初期化と永続化層
  - system_monitor: CPU/メモリ/ディスク/データ鮮度/プロセス監視
  - trade_monitor, risk_monitor, kill_switch, alert_manager, monitoring_engine: 監視の各責務

- kabusys.execution.*
  - BrokerFactory / ExecutionEngine / OrderManager / RiskManager / Reconciler 等（発注ロジック）

- kabusys.portfolio.*
  - portfolio_builder, position_sizing, risk_adjustment（候補選定・重み付け・サイズ計算）

- kabusys.research.*
  - factor_research, feature_exploration（DuckDB を用いたファクター計算・IC 等）

- kabusys.ai.*
  - news_nlp: OpenAI を用いたニュースセンチメント集計／ai_scores への書き込み
  - regime_detector: マクロセンチメント + ETF MA によるレジーム判定

---

## ディレクトリ構成（主なファイル）

src/kabusys/
- __init__.py
- config.py                  — 環境設定読み込み / Settings
- config_setup.py            — .env 対話ウィザード
- validate_config.py         — 設定検証 CLI
- run_monitoring.py          — SystemMonitor ポーリングループ起動スクリプト
- run_execution.py           — ExecutionEngine 起動スクリプト
- utils/
  - logging_setup.py
  - process_priority.py
- monitoring/
  - monitoring_db.py
  - monitoring_engine.py
  - system_monitor.py
  - risk_monitor.py
  - trade_monitor.py
  - kill_switch.py
  - alert_manager.py
- execution/
  - broker_factory.py
  - execution_engine.py
  - order_manager.py
  - order_repository.py
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
- monitoring/ (既出)
- tools/
  - paper_verification_report.py

（注）上記は本リポジトリに含まれる主要ソースファイルです。実装の詳細は各ファイルの docstring を参照してください。

---

## 開発 / テストのヒント

- .env の自動ロードは default で有効。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DuckDB によるリサーチ関数は外部 API に依存しないためユニットテストが容易です。
- OpenAI 呼び出し部分は _call_openai_api などで抽象化されており、テスト時には patch してモック化できます。
- validate_config を先に実行して設定ミスを検出してください。

---

## ライセンス / バージョン

パッケージバージョンは kabusys.__version__ = "0.1.0"（初期状態）。ライセンス情報はリポジトリの LICENSE ファイルを参照してください（存在しない場合はプロジェクトのポリシーに従って追加してください）。

---

必要であれば、README に以下の追加情報を入れます:
- requirements.txt の具体的な推奨バージョン
- systemd / Supervisor 用のサービスユニット例（運用向け）
- 実行時のログ例・エラーメッセージの説明

どれを追加しますか？