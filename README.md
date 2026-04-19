# KabuSys

日本株向け自動売買システムの軽量ライブラリ / 実行スクリプト群です。  
本リポジトリは戦略・ポートフォリオ構築、発注エンジン（ExecutionEngine）、監視（Monitoring）、研究用ユーティリティ、AI を用いたニュース評価などの機能を提供します。

バージョン: 0.1.0

---

## 目次
- プロジェクト概要
- 主な機能一覧
- 必要要件
- セットアップ手順（クイックスタート）
- 環境変数 / .env の管理
- 実行方法（監視 / 実行エンジン / ツール）
- 使い方のポイント
- ディレクトリ構成

---

## プロジェクト概要
KabuSys は以下の観点を重視した設計になっています。
- 発注ロジックと監視ロジックを分離（ExecutionEngine / Monitoring）
- ペーパートレードと本番（live）を環境で切替可能
- DuckDB を用いた分析向け DB、SQLite を用いた監視ログ・発注ログ
- OpenAI を用いたニュース NLP / レジーム判定機能（任意）
- ログ・警告・Kill Switch を備えた運用重視の実装

---

## 主な機能一覧
- ExecutionEngine（run_execution.py）
  - 本番 / ペーパートレード切替（KABUSYS_ENV）
  - BrokerClientFactory によるブローカークライアントの生成
  - OrderRepository / OrderManager / RiskManager / Reconciler 組み立て
- Monitoring（run_monitoring.py, monitoring パッケージ）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス状態・データ鮮度監視
  - TradeMonitor: 発注ログや滞留注文検出（実装参照）
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: 条件発動で data/kill.flag を書いて ExecutionEngine を停止
  - MonitoringEngine: 各モニタをまとめポーリング
- Portfolio（portfolio パッケージ）
  - 候補選定、重み計算、リスク調整、株数決定（単元丸め・利用率制御）
- Research（research パッケージ）
  - ファクター計算（momentum/value/volatility）
  - 将来リターン計算、IC（Information Coefficient）等
- AI（ai パッケージ）
  - news_nlp: OpenAI を用いたニュースセンチメント取得と ai_scores への書込
  - regime_detector: ma200 とマクロニュースを合成した市場レジーム判定
- ツール
  - config_setup.py: 対話式 .env 作成ウィザード
  - validate_config.py: 起動前に設定チェック（--strict オプションあり）
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成

---

## 必要要件（概略）
以下をインストールしておくことを推奨します。
- Python 3.9+
- パッケージ（代表例）
  - duckdb
  - psutil
  - openai (AI 機能を使う場合)
  - PyYAML（config.yml 検証を行う場合は必須）
標準ライブラリの sqlite3 は利用されています。

実際の依存関係はプロジェクトに requirements.txt や pyproject.toml を用意している場合はそちらを参照してください。

---

## セットアップ手順（クイックスタート）
1. リポジトリをクローンし、仮想環境を作成
   ```
   git clone <repo-url>
   cd <repo-root>
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   pip install -U pip
   pip install duckdb psutil openai PyYAML
   ```

2. 環境変数ファイルの作成（対話式）
   ```
   python -m kabusys.config_setup
   ```
   ウィザードは .env（デフォルト）を作成します。作成後は必ず `python -m kabusys.validate_config` で検証してください。

3. （任意）.env の自動ロードを無効化したい場合
   - テスト等で自動ロードを無効にするには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## 環境変数（主なもの）
以下は本プロジェクトで使用・参照される代表的な環境変数です。`.env.example` を参考に .env を作成してください。

必須（最低限）
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

運用 / データベース / ログ
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード専用 SQLite（paper_trading モード時）
- LOG_LEVEL: DEBUG/INFO/WARNING/ERROR/CRITICAL
- LOG_DIR: ログディレクトリ（デフォルト: logs/）
- PID_FILE_PATH / KILL_FLAG_PATH etc.（Settings 参照）

Monitoring 固有
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）

Paper trading 固有
- PAPER_FILL_MODE: instant | partial | never | reject

OpenAI 関連
- OPENAI_API_KEY: news_nlp / regime_detector で利用

その他
- KILL_FLAG_CLEAR_ON_START: 起動時に kill.flag を自動クリアするか（0/1）

自動ロードのルール
- OS 環境変数 > .env.local > .env の順で読み込まれます。ただし OS 環境変数は保護されて上書きされません。

---

## 実行方法

### 1) 監視ループを起動（監視デーモン）
監視は monitoring 用の SQLite（`SQLITE_PATH`）を参照します。注意: run_monitoring は環境に関わらず本番の sqlite_path を使用します。

- デフォルト（環境変数で調整可能）
  ```
  python -m kabusys.run_monitoring
  ```
- ポーリング間隔を指定したい場合（秒）
  ```
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```
- 停止方法
  - 実行中に Ctrl+C、またはプロジェクトルートの `data/stop_requested.flag` を作成するとループが終了します。

### 2) ExecutionEngine（発注エンジン）を起動
- デフォルト起動
  ```
  python -m kabusys.run_execution
  ```
- KABUSYS_ENV による挙動
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、`PAPER_TRADING_SQLITE_PATH`（デフォルト `data/paper_trading.db`）へ記録します。本番 DB と分離されます。
  - KABUSYS_ENV=live の場合は実口座向けのブローカークライアントが使われます（設定を要確認）。

- 停止方法
  - プロジェクトルートの `data/stop_requested.flag` を作成するか、実行中に kill.flag を監視している Monitoring が書き込んだ `data/kill.flag` を検出すると停止処理を行います。
  - 実行時、PID ファイルは `data/execution.pid`（デフォルト）に書き込まれます。

### 3) 設定検証
- 設定の静的検証（警告も出力）
  ```
  python -m kabusys.validate_config
  ```
- 警告も FAIL 扱いにする（CI などで）
  ```
  python -m kabusys.validate_config --strict
  ```

### 4) .env の対話式生成
```
python -m kabusys.config_setup
```

### 5) ペーパートレード検証レポート
ペーパートレード DB（デフォルト data/paper_trading.db）から期間を指定してレポートを生成します。
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を明示する場合
python -m kabusys.tools.paper_verification_report --db ./data/paper_trading.db
```

---

## 使い方のポイント / 運用上の注意
- ログ
  - setup_logging によりコンソール（stdout）と日別ローテートファイル（logs/<app_name>.log）が設定されます。ログディレクトリが作成できない場合はファイル出力はスキップされ、コンソール出力のみになります。
- プロセス優先度
  - 起動スクリプトは起動時に `set_process_priority("high")` を呼び出します（可能な場合）。管理者権限がないと設定できないことがあります。
- Monitoring と Execution の DB 分離
  - Monitoring は常に Settings.sqlite_path（監視 DB）を使用します。Execution は KABUSYS_ENV に応じて paper_trading 用の DB と本番 DB を切り替えます。ペーパートレード時は DB を分離することで誤発注リスクを下げます。
- Kill Switch
  - RiskMonitor が一定の条件（ドローダウン、ポジション上限超過など）を満たすと `data/kill.flag` を書き込みます。ExecutionEngine 起動時の `KILL_FLAG_CLEAR_ON_START` により自動クリアの挙動を制御できます（本番では自動クリアを無効化推奨）。
- OpenAI 関連
  - news_nlp / regime_detector は OpenAI API を利用します。`OPENAI_API_KEY` を .env に設定してください。API 呼び出しはリトライ/フォールバックロジックを持つため部分的な失敗時でも安全に動作するよう設計されています。

---

## ライブラリとしての利用例
- research.calc_momentum を呼んで DuckDB 上の prices_daily に対するファクターを計算する:
  ```python
  import duckdb
  from kabusys.research import calc_momentum
  from datetime import date

  conn = duckdb.connect("data/kabusys.duckdb")
  factors = calc_momentum(conn, date(2026, 4, 1))
  ```
- ai.score_news:
  - DuckDB 接続と target_date を与えると ai_scores に書き込みます（OpenAI API key 必須）。
  ```python
  from kabusys.ai.news_nlp import score_news
  # conn: duckdb connection
  score_news(conn, date(2026,4,1), api_key="sk-...")
  ```

---

## ディレクトリ構成（抜粋）
（src/kabusys 以下の主なファイル・モジュール）
- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数/.env の読み込みと Settings
  - config_setup.py               — .env 対話式ウィザード
  - validate_config.py            — 設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリング起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート
  - utils/
    - logging_setup.py            — ログ設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py
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

---

## 最後に / 推奨ワークフロー
1. .env を作成（python -m kabusys.config_setup）
2. 設定検証（python -m kabusys.validate_config）
3. DuckDB / data ディレクトリを準備
4. 監視 (monitoring) を起動してシステムの安定性を監視
5. ExecutionEngine を paper_trading で動かし挙動を検証 → live に移行

---

README に書かれている操作はライブラリ内の実装詳細に依存します。実運用前に必ず設定ファイルやブローカークライアント実装、DB パス、ログ設定等を十分に確認してください。必要であれば README を実際の運用手順に合わせてカスタマイズします。