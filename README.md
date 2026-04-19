# KabuSys

日本株自動売買システムのコアライブラリおよび起動スクリプト群

---

## プロジェクト概要

KabuSys は日本株向けの自動売買システムのコア実装です。  
主な役割は次の通りです：

- 戦略用のファクター計算（DuckDB を用いたリサーチ用モジュール）
- ポートフォリオ構築とポジションサイズ計算（純粋関数群）
- ExecutionEngine（発注ロジック）およびペーパートレード用の分離DB
- 監視コンポーネント（System / Trade / Risk Monitor）と Kill Switch
- OpenAI を用いたニュース NLP / 市場レジーム判定
- 設定ウィザード・設定検証ツール・レポート生成ツール

設計方針として、DBアクセスは明示的に渡す（DuckDB / SQLite）、外部API呼び出し（kabuAPI, J-Quants, OpenAI）は設定で有効化、テストしやすい純粋関数やフェイルセーフを重視しています。

---

## 機能一覧

- 設定管理（.env ファイルの自動読み込み、Settings クラス）
- 対話式 .env ウィザード（kabusys.config_setup）
- 設定検証 CLI（kabusys.validate_config）
- ExecutionEngine 起動スクリプト（kabusys.run_execution）
  - KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し paper_trading.db に記録
- Monitoring（kabusys.run_monitoring / MonitoringEngine）
  - System / Trade / Risk の監視、kill.flag による停止指示、アラート送信フック
- 監視 DB（SQLite）読み書きレイヤ（monitoring_db）
- ポートフォリオ構築ユーティリティ（select_candidates / weight 計算 / position sizing）
- リサーチ：ファクター計算（momentum/volatility/value）・特徴量解析（IC, forward returns）
- AI モジュール：ニュースセンチメント（news_nlp）、市場レジーム判定（regime_detector）
- ツール：Paper Trading 検証レポート生成（kabusys.tools.paper_verification_report）

---

## 前提条件

- Python 3.9+
- pip（仮想環境の利用を推奨）
- SQLite（標準ライブラリで利用可能）
- 依存パッケージ（少なくとも以下をインストールしてください）:
  - duckdb
  - psutil
  - openai
  - PyYAML（config.yaml のパース検証を行う場合）
- OS: Linux / macOS / Windows（プロセス優先度 API は一部制限される場合あり）

（requirements.txt はリポジトリに含まれていないため、必要なパッケージを手動でインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
```

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN — J-Quants API 用リフレッシュトークン
- KABU_API_PASSWORD — kabuステーション API パスワード

推奨 / デフォルトあり:
- KABUSYS_ENV — 実行モード: development / paper_trading / live（デフォルト: development）
- DUCKDB_PATH — DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH — ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- LOG_LEVEL — ログレベル（DEBUG/INFO/...、デフォルト: INFO）
- OPENAI_API_KEY — OpenAI を使う機能（news_nlp / regime_detector）で必要
- PAPER_FILL_MODE — ペーパートレードの約定モード（instant/partial/never/reject）
- MONITOR_POLL_INTERVAL — run_monitoring のポーリング間隔（秒、デフォルト 60）

その他:
- LOG_DIR — ログ保存先ディレクトリ（デフォルト: logs/）
- KILL_FLAG_CLEAR_ON_START — 本番で Kill Flag を自動クリアするか（注意: 本番では 0 推奨）

詳細は kabusys.config.Settings と kabusys/validate_config.py のコメントを参照してください。

---

## セットアップ手順（基本）

1. リポジトリをクローンして作業ディレクトリへ移動
2. Python 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. .env を作成（対話式ウィザード推奨）

対話式 .env 作成:
```bash
python -m kabusys.config_setup
```

作成後、設定の検証:
```bash
python -m kabusys.validate_config
# --strict をつけると警告もエラー扱い
python -m kabusys.validate_config --strict
```

データディレクトリ、ログディレクトリが自動作成されますが、ファイルパーミッションやディレクトリの親がない場合は警告が出ます。必要に応じて手動で作成してください（例: data/ logs/）。

---

## 使い方

### 実行コンポーネント

- ExecutionEngine を起動（本番 / ペーパートレードの起動スクリプト）:
```bash
python -m kabusys.run_execution
```
- Monitoring を起動（ポーリング監視）:
```bash
# ポーリング間隔は MONITOR_POLL_INTERVAL 環境変数で上書き可能
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```

run_execution の挙動:
- KABUSYS_ENV=paper_trading の場合、MockBrokerClient を使用して data/paper_trading.db に取引ログを記録（本番 DB と分離）
- 起動時に data/stop_requested.flag（または stop フラグ）があると起動しない
- 起動中に data/stop_requested.flag が作成されると実行を停止

run_monitoring の挙動:
- Monitoring は環境にかかわらず本番 sqlite_path を使用して監視データを永続化
- ポーリングごとに SystemMonitor.check_once() を呼び出し、Monitoring DB と Risk Monitor などを更新する
- MONITOR_POLL_INTERVAL で間隔指定（デフォルト 60 秒）

### ツール

- Paper Trading 検証レポート生成:
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB パスを指定する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

### プログラム的に呼び出す（ライブラリ利用例）

リサーチ:
```python
from datetime import date
import duckdb
from kabusys.research import calc_momentum

conn = duckdb.connect("data/kabusys.duckdb")
records = calc_momentum(conn, target_date=date(2026,4,11))
```

ポートフォリオ:
```python
from kabusys.portfolio import select_candidates, calc_equal_weights, calc_position_sizes
```

AI スコアリング:
```python
from kabusys.ai.news_nlp import score_news
# OpenAI API キーは OPENAI_API_KEY 環境変数または api_key 引数で指定
```

---

## ログ・監視・停止

- ログはデフォルトで logs/ に日次ローテーションで出力されます（kabusys.utils.logging_setup.setup_logging）。
- プロセス優先度は起動スクリプト内で "high" に設定されています（psutil を使用）。
- ExecutionEngine を停止させるには kill.switch を使って data/kill.flag を書く（KillSwitch）か、監視コンポーネントが条件を満たすと自動で kill.flag を書きます。
- 停止フラグ / PID ファイル:
  - data/kill.flag — ExecutionEngine 停止トリガ
  - data/execution.pid — ExecutionEngine の PID（run_execution が利用）
  - data/stop_requested.flag — run_monitoring/run_execution が監視する停止フラグ

---

## ディレクトリ構成

（リポジトリの src/kabusys 配下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py — 環境変数 / Settings
  - config_setup.py — .env 対話式ウィザード
  - validate_config.py — 設定検証 CLI
  - run_execution.py — ExecutionEngine 起動スクリプト
  - run_monitoring.py — Monitoring 起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — Paper Trading 検証レポート
  - ai/
    - __init__.py
    - news_nlp.py — ニュース NLP スコアリング（OpenAI）
    - regime_detector.py — 市場レジーム判定（OpenAI + MA）
  - monitoring/
    - monitoring_db.py — SQLite 永続層
    - monitoring_engine.py — 各 Monitor を束ねる
    - system_monitor.py — システム / データ鮮度監視
    - trade_monitor.py — （trade 監視: 実装参照）
    - risk_monitor.py — ドローダウン・ポジション制限監視
    - kill_switch.py — kill.flag 書込みユーティリティ
    - alert_manager.py —（アラート送信ロジック: 実装参照）
  - execution/  — ExecutionEngine や OrderManager 等（起動時に組み立て）
    - execution_engine.py
    - order_manager.py
    - order_repository.py
    - ...（broker_factory 等）
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
  - monitoring/（上に同じ）
  - data/ （実行時に生成される想定）
    - *.db, kill.flag, execution.pid, stop_requested.flag など

---

## 注意事項・運用メモ

- KABUSYS_ENV が `live` の場合は本番動作になります。validate_config は `live` のときに注意喚起を出します。実運用時は .env の取り扱いに十分注意してください（.env は Git 管理しない）。
- OpenAI を利用する機能は API 使用量が発生します。OPENAI_API_KEY を適切に管理してください。
- ペーパートレード（KABUSYS_ENV=paper_trading）は本番 DB と分離されます。ペーパートレード DB は PAPER_TRADING_SQLITE_PATH を利用します。
- DuckDB/SQLite のファイルパスやログディレクトリの親ディレクトリがない場合、validate_config で警告が出ます。起動スクリプトは可能な限り自動でディレクトリを作成しますが、権限等に注意してください。
- run_monitoring は MONITOR_POLL_INTERVAL に 1未満の値を与えるとデフォルト（60秒）にフォールバックします。

---

この README はコードベースの主要機能と運用に必要な情報をまとめた簡易マニュアルです。詳細な実装や追加の設定は各モジュール（特に config.py、monitoring/*、execution/*、ai/*）のドキュメンテーションコメントを参照してください。必要であれば README にインストール用の requirements.txt、運用フロー（systemd / Supervisor 用の unit ファイル例）や、より詳細な開発ガイドを追記できます。