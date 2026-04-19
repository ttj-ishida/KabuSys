# KabuSys

日本株向け自動売買システムのモジュール群（ライブラリ + 起動スクリプト）。  
本リポジトリは取引実行エンジン、監視（Monitoring）、ポートフォリオ構築・リスク管理、研究用ファクター計算、AI（ニュース NLP / レジーム判定）などを含みます。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の主要コンポーネントで構成されます。

- Execution Engine: ブローカークライアント経由で発注を行う実行エンジン（本番 / ペーパートレード対応）。
- Monitoring: システム/取引/リスク監視、Kill Switch（フラグファイルを介した安全停止）およびアラート管理。
- Portfolio Construction: 候補選定、重み付け、ポジションサイズ計算、セクター制約などの純粋関数群。
- Research: DuckDB 上で動くファクター計算・特徴量探索（モメンタム、バリュー、ボラティリティ等）。
- AI: ニュースのセンチメントスコアリング（OpenAI）および市場レジーム判定。
- Tools: ペーパートレード検証レポート生成などのユーティリティスクリプト。
- 設定管理ツール: 対話式 `.env` ウィザード（config_setup.py）と起動前検証（validate_config.py）。

設計方針の一部:
- 本番 DB とペーパートレード DB は分離（KABUSYS_ENV により切替）。
- ルックアヘッドバイアス回避のため、日付参照は引数ベースで実装。
- フェイルセーフ設計（API失敗時はフォールバックして継続）。

---

## 主な機能一覧

- 発注ワークフロー（ExecutionEngine、OrderManager、RiskManager）
- 監視機能
  - SystemMonitor（CPU/Mem/Disk、データ鮮度、プロセス生存確認）
  - TradeMonitor（滞留注文、約定異常検出 等）
  - RiskMonitor（ドローダウン、ポジション上限監視）
  - KillSwitch（条件に応じた stop flag 書込み）
  - MonitoringEngine（各 Monitor をまとめて定期実行）
- ポートフォリオ構築
  - 候補選定（スコア順）
  - 重み付け（等分・スコア加重）
  - ポジションサイズ計算（リスクベース / 重みベース、単元丸め、集約キャップ）
  - セクターキャップ、レジーム乗数
- 研究（research）
  - ファクター計算（momentum / volatility / value）
  - 将来リターン、IC（スピアマン）等の分析ユーティリティ
- AI モジュール
  - ニュース NLP（OpenAI を用いた銘柄別センチメント集計、ai_scores 書込み）
  - レジーム判定（ETF MA とマクロニュースの LLM スコア合成）
- ツール群
  - config_setup.py（.env 対話式生成）
  - validate_config.py（環境・設定検証）
  - paper_verification_report（ペーパートレード検証レポート生成）

---

## 動作要件（推奨）

- Python 3.10+
- SQLite（標準ライブラリ sqlite3 を使用）
- DuckDB (`duckdb` Python パッケージ)
- psutil
- openai （AI 機能を利用する場合）
- PyYAML （config の内容検証を行う場合）
- 追加: 標準ライブラリと OS 標準ツール

インストール（仮想環境の例）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil openai PyYAML
```
（requirements.txt がある場合はそれを利用してください。）

---

## 環境変数（主なもの）

必須:
- JQUANTS_REFRESH_TOKEN
- KABU_API_PASSWORD

主要オプション（デフォルト値があるものは併記）:
- KABUSYS_ENV: execution モード（development | paper_trading | live）, デフォルト: development
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db（paper_trading 用 DB）
- LOG_LEVEL: INFO（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- OPENAI_API_KEY: OpenAI を使う場合に必要
- PAPER_FILL_MODE: instant | partial | never | reject（paper_trading の挙動）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（run_monitoring で上書き可能、デフォルト 60）
- KILL_FLAG_CLEAR_ON_START: (0/1) 起動時に kill.flag を自動クリアするか（本番は 0 推奨）

注意: 自動環境変数ローディングが有効（プロジェクトルートに .env / .env.local があれば自動で読み込まれます）。無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

---

## セットアップ手順

1. リポジトリをクローンし、仮想環境を作成・有効化する。
2. 依存パッケージをインストールする（上記参照）。
3. 対話式ウィザードで .env を生成:
   ```bash
   python -m kabusys.config_setup
   ```
   これによりプロジェクトルートに `.env` が作成されます（必要に応じて .env.local を使用）。

4. 設定検証:
   ```bash
   python -m kabusys.validate_config
   ```
   --strict を付けると警告も失敗扱いになります。

5. データディレクトリとログディレクトリが自動で作成されますが、必要であれば手動で作成してください:
   - data/
   - logs/

---

## 使い方（主要スクリプト）

- 実行エンジン（Execution Engine）を起動:
  - 本番 / 開発 / ペーパートレードは環境変数 KABUSYS_ENV に依存します。
  - 例（ペーパートレード）:
    ```bash
    export KABUSYS_ENV=paper_trading
    python -m kabusys.run_execution
    ```
  - 例（本番）:
    ```bash
    export KABUSYS_ENV=live
    python -m kabusys.run_execution
    ```
  - ペーパートレード時は MockBrokerClient を使用し、データは `PAPER_TRADING_SQLITE_PATH`（デフォルト: data/paper_trading.db）に記録されます。

- 監視ループを起動:
  ```bash
  export MONITOR_POLL_INTERVAL=60  # オプション
  python -m kabusys.run_monitoring
  ```
  - 監視ループは system / trade / risk のチェックを定期実行します。監視は production 用の sqlite_path を常に参照します（KABUSYS_ENV に関係なく本番監視 DB を使用）。

- Kill / Stop:
  - ExecutionEngine の停止シグナルは data/kill.flag（KillSwitch）または data/stop_requested.flag（run scripts の stop フラグ）で制御します。
  - kill.flag は KillSwitch によって書き込まれます。手動で停止したい場合はフラグファイルを作成できます（dangerous: 実行エンジンを停止します）。

- 設定ウィザード:
  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証:
  ```bash
  python -m kabusys.validate_config
  ```

- ペーパートレード検証レポート:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - デフォルト DB は環境変数 `PAPER_TRADING_SQLITE_PATH`（または `data/paper_trading.db`）。

---

## よく使うファイル / 環境（例）

例 .env（抜粋）:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token_here
KABU_API_PASSWORD=your_password_here
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
LOG_LEVEL=INFO
OPENAI_API_KEY=sk-xxxxxxxx
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
PAPER_FILL_MODE=instant
KILL_FLAG_CLEAR_ON_START=0
```

ログ:
- デフォルトログディレクトリ: logs/
- ログファイル: logs/<app_name>.log （例: logs/execution.log, logs/monitoring.log）
- ログは Stream（stdout） と 日次ローテートファイルに出力されます。

---

## ディレクトリ構成（主要ファイル）

以下はコードベースの主要モジュール一覧（src/kabusys 以下の抜粋）:

- src/kabusys/
  - __init__.py
  - config.py                     — 環境変数 / Settings 管理（.env 自動ロード含む）
  - config_setup.py               — 対話式 .env ウィザード
  - validate_config.py            — 起動前設定検証 CLI
  - run_execution.py              — ExecutionEngine 起動スクリプト
  - run_monitoring.py             — SystemMonitor ポーリングループ起動スクリプト
  - tools/
    - __init__.py
    - paper_verification_report.py — ペーパートレード検証レポート
  - ai/
    - __init__.py
    - news_nlp.py                  — ニュース NLP（OpenAI 経由のセンチメント）
    - regime_detector.py           — 市場レジーム判定（MA + マクロセンチメント）
  - monitoring/
    - monitoring_db.py            — SQLite 永続化レイヤ（監視テーブル）
    - monitoring_engine.py        — 監視エンジン（各 Monitor を束ねる）
    - system_monitor.py           — システム・データ鮮度監視
    - trade_monitor.py            — （取引監視: 該当コード参照）
    - risk_monitor.py             — ドローダウン / ポジション上限監視
    - kill_switch.py              — kill.flag 操作ユーティリティ
    - alert_manager.py            — アラート送信管理（実装参照）
  - execution/
    - execution_engine.py         — ExecutionEngine 実装（EngineConfig など）
    - broker_factory.py           — ブローカークライアント生成（Mock含む）
    - order_manager.py
    - order_repository.py
    - reconciler.py
    - risk_manager.py
  - portfolio/
    - portfolio_builder.py
    - position_sizing.py
    - risk_adjustment.py
    - __init__.py
  - research/
    - factor_research.py
    - feature_exploration.py
    - __init__.py
  - utils/
    - logging_setup.py            — ロギング設定ユーティリティ
    - process_priority.py         — プロセス優先度 / CPU affinity
    - __init__.py

（注）一部ファイルは本 README にすべて網羅されていないため、詳細はソースツリーを参照してください。

---

## 開発・運用上の注意点

- 本番運用時は KABUSYS_ENV=live を設定してください。validate_config.py は live 環境に対する追加警告を出します。
- kill.flag / stop_requested.flag の扱いに注意してください（誤って本番エンジンを停止しないように）。
- OpenAI を使う機能は API レートやコストに注意。API キーは `.env` に設定し、決してリポジトリにコミットしないでください。
- DuckDB と SQLite のファイルパスは環境変数で上書き可能です。バックアップ・永続化方針を決めておくことを推奨します。
- ログはデフォルトで logs/ に日次ローテーションで残ります（30日分）。必要に応じて LOG_DIR を設定してください。

---

## サポート / 貢献

- バグ報告・機能要求は Issue にてお願いします。
- コードスタイル、テスト、CI ルールなどは別途 CONTRIBUTING を参照してください（未含）。

---

README は以上です。詳細な使い方（各モジュールのパラメータ、BrokerClient 実装、AlertManager 設定など）は該当ソースファイルおよびドキュメント（例: PortfolioConstruction.md, StrategyModel.md）を参照してください。必要であれば、そのドキュメントの抜粋や追加の運用手順も作成します。どの情報がさらに必要か教えてください。