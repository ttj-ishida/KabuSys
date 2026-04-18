# KabuSys — 日本株自動売買システム

このリポジトリは日本株向けの自動売買・監視・リサーチ用ツール群です。  
README は日本語で、セットアップや主要スクリプトの使い方、ディレクトリ構成をまとめています。

---

## プロジェクト概要

KabuSys は以下の要素を含む小規模な自動売買フレームワークです。

- マーケットデータを用いたファクター計算・特徴量探索（research）
- ポートフォリオ構築・ポジションサイズ決定ロジック（portfolio）
- 発注エンジン（ExecutionEngine）と注文管理（execution）
- 監視（Monitoring）：システム状態・注文状況・リスクを定期チェックしアラート／Kill Switch を発動
- AI モジュール（news_nlp / regime_detector）：ニュースを LLM でスコアリングしてレジーム判定に利用
- 運用支援ツール（config_setup, validate_config, paper_verification_report）

設計方針の要点：
- 環境変数 / .env による設定
- DuckDB / SQLite を用いたデータ永続化（分析用: DuckDB、監視/発注ログ: SQLite）
- 本番（live） / ペーパートレード（paper_trading） / 開発（development）モードを切替可能
- LLM 呼び出しは冗長性とフォールバックを考慮して実装（リトライ・部分失敗保護等）

---

## 機能一覧

主な機能（抜粋）：

- 環境設定ウィザード（python -m kabusys.config_setup）
- 設定検証 CLI（python -m kabusys.validate_config）
- ExecutionEngine 起動スクリプト（python -m kabusys.run_execution）
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用して paper_trading DB に記録
- Monitoring 起動スクリプト（python -m kabusys.run_monitoring）
  - 定期的に System / Trade / Risk をチェック、kill.flag を書くなどの制御
  - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（秒、デフォルト 60）
- Paper Trading 検証レポート生成（python -m kabusys.tools.paper_verification_report）
- AI ニューススコアリング（kabusys.ai.score_news）
- 市場レジーム判定（kabusys.ai.regime_detector.score_regime）
- ファクター計算（momentum / volatility / value）
- ポートフォリオ構築ユーティリティ（候補選定、重み付け、ポジションサイズ計算、セクター制限）

---

## 前提・依存関係

推奨 Python バージョン: 3.10+（typing の | 記法を使用）

主な外部依存パッケージ（例）:
- duckdb
- psutil
- openai
- PyYAML（config 検証時に config/*.yaml を読みたい場合）
SQLite は標準ライブラリで使用します。

（requirements.txt がない場合は上のパッケージを適宜インストールしてください）
例:
```
pip install duckdb psutil openai PyYAML
```

---

## セットアップ手順

1. リポジトリをクローンし、作業ディレクトリをルートに移動します。
2. Python 仮想環境を作成・有効化し依存をインストールします。
3. .env を作成（推奨: ウィザードを利用）

.env 作成（ウィザード）
```
python -m kabusys.config_setup
```
ウィザードは .env を対話式で生成・更新します。`.env` を絶対にコミットしないでください。

4. 設定検証（オプション）
```
python -m kabusys.validate_config
# 警告も失敗扱いにする場合
python -m kabusys.validate_config --strict
```

5. データディレクトリ作成（必要に応じて）
デフォルトでは `data/`、ログは `logs/` に保存されます。`logs/` は `kabusys.utils.logging_setup.setup_logging` により作成されますが、必要であれば手動でディレクトリを作成してください。

---

## 主要環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- KABUSYS_ENV: 実行環境。`development` | `paper_trading` | `live`（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: SQLite 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI を使う機能（news_nlp / regime_detector）
- LOG_LEVEL: ログレベル（DEBUG/INFO/...）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: ExecutionEngine 起動時に kill.flag を自動クリアするか（"1" でクリア）

Kill / Stop フラグ等のファイル:
- Kill Switch (Kill Switch が書き込む): data/kill.flag （既定、Settings.kill_flag_path で変更可能）
- 停止要求フラグ（run_* スクリプトが監視する）: data/stop_requested.flag
- ExecutionEngine PID ファイル: data/execution.pid

---

## 使い方（例）

起動スクリプトはパッケージモジュールとして実行します。

- 環境設定ウィザード
```
python -m kabusys.config_setup
```

- 設定検証
```
python -m kabusys.validate_config
```

- Monitoring を起動
※ MONITOR_POLL_INTERVAL でポーリング間隔（秒）を変更可能。Monitoring は環境に関わらず本番 sqlite_path（SQLITE_PATH）を使用します。
```
MONITOR_POLL_INTERVAL=60 python -m kabusys.run_monitoring
```

- ExecutionEngine を起動
KABUSYS_ENV=paper_trading の場合は paper_trading 用 DB に記録され、MockBrokerClient を使用します。
```
python -m kabusys.run_execution
# ペーパートレードで起動する例
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

- Paper Trading 検証レポートを出力
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# db を明示する場合
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

- AI モジュールをスクリプトや REPL から使う
（DuckDB 接続を渡して呼び出します）

例: ニューススコアリング
```python
import duckdb
from datetime import date
from kabusys.ai.news_nlp import score_news

conn = duckdb.connect("data/kabusys.duckdb")
# target_date を指定、api_key は引数か環境変数 OPENAI_API_KEY
score_news(conn, date(2026, 4, 10), api_key="sk-...")
```

例: レジーム判定
```python
from kabusys.ai.regime_detector import score_regime
score_regime(conn, date(2026, 4, 10), api_key="sk-...")
```

- 停止・強制停止
  - 監視ループ・エンジンはプロセス内で `data/stop_requested.flag` の存在をチェックして自タスクの終了を行います。停止を要求する場合はプロジェクトルートの `data/stop_requested.flag` ファイルを作成してください（中身は任意）。
  - KillSwitch が条件を満たした場合は `data/kill.flag` を書き込んで ExecutionEngine に停止シグナルを送ります。手動で解除する場合はファイルを削除してください。

---

## ログ・トラブルシューティング

- ログはデフォルト `logs/` に日次ローテート（30 日保持）で保存されます。設定は `kabusys.utils.logging_setup.setup_logging` を参照。
- ログレベルは環境変数 `LOG_LEVEL`（例: DEBUG, INFO）で指定できます。
- config/ 以下の YAML ファイルは `python -m kabusys.validate_config` で存在確認・パース確認が可能（PyYAML が必要）。
- データベース接続でエラーが発生した場合はパス（DUCKDB_PATH / SQLITE_PATH 等）や権限を確認してください。

---

## ディレクトリ構成

リポジトリの主要構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py               — 環境変数 / 設定解決ロジック、Settings クラス
    - config_setup.py         — .env 対話式ウィザード
    - validate_config.py      — 設定検証 CLI
    - run_monitoring.py       — Monitoring の起動スクリプト
    - run_execution.py        — ExecutionEngine の起動スクリプト
    - tools/
      - paper_verification_report.py
    - ai/
      - news_nlp.py           — ニュースを LLM でスコアリング
      - regime_detector.py    — マーケットレジーム判定
    - monitoring/
      - monitoring_db.py      — SQLite テーブル作成・永続化用 API
      - monitoring_engine.py
      - system_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - trade_monitor.py      — （注文滞留等の監視：参照されるがここに存在）
      - alert_manager.py      — （通知管理、LINE 等：参照される）
    - execution/
      - execution_engine.py
      - broker_factory.py
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
    - utils/
      - logging_setup.py
      - process_priority.py

実運用時のファイル（プロジェクトルート）:
- data/monitoring.db (デフォルト)
- data/paper_trading.db (ペーパートレード用)
- data/kabusys.duckdb (DuckDB データベース)
- data/execution.pid
- data/kill.flag
- data/stop_requested.flag
- logs/* (ログファイル)

---

## 開発者向けメモ

- モジュール設計は副作用を抑え、外部 API 呼び出し（発注・LLM 等）をモジュール単位で切り離す方針です。ユニットテストでは OpenAI 呼び出しや Broker クライアントなどをモックしてテストする想定です。
- Settings は自動でプロジェクトルートの `.env` と `.env.local` を読み込みます（必要なら自動読み込みを無効化するために `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定できます）。
- Monitoring は監視ログ（system_status / trade_logs / risk_logs / dashboard / positions）用の SQLite スキーマを `monitoring_db.init_monitoring_db` で冪等に作成します。既存 DB に対する軽微なマイグレーション（カラム追加）も行います。

---

以上がプロジェクトの概要と基本的な使い方です。その他、個別のモジュール（ExecutionEngine の詳細設定や Broker クライアント実装、AlertManager の LINE 実装等）は該当ファイルの docstring とコードコメントを参照してください。必要なら README に追記・改善しますので、どの部分を詳しく書いてほしいか教えてください。