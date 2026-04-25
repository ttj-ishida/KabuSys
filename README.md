# KabuSys

日本株自動売買システムのライブラリ／実行スクリプト群です。  
このリポジトリには、発注エンジン（ExecutionEngine）、監視（Monitoring）、ポートフォリオ構築、リサーチ、AI（ニュースのセンチメント等）など、自動売買システムの主要コンポーネントが含まれます。

バージョン: 0.1.0

---

## 概要

- 発注ロジックと監視ロジックを分離し、モジュール化した設計。
- 本番（live）・ペーパートレード（paper_trading）・開発（development）を環境変数で切替可能。
- DuckDB を使ったリサーチ／ファクター計算、SQLite を使った監視ログ・ペーパートレード履歴保存。
- OpenAI を利用したニュースセンチメント評価・市場レジーム判定（API キー必要）。
- ログやプロセス優先度のユーティリティ、設定ウィザード、設定検証ツールを備える。

---

## 主な機能一覧

- Execution（発注）
  - ExecutionEngine（発注セッションの実行）
  - Broker クライアントの抽象化（本番/モック切替）
  - OrderManager / OrderRepository / RiskManager / Reconciler 等による注文管理・リスク制御
  - Paper trading モード（KABUSYS_ENV=paper_trading）では MockBrokerClient を使用し DB を分離

- Monitoring（監視）
  - SystemMonitor: CPU / メモリ / ディスク / プロセス・PIDファイル・データ鮮度監視
  - TradeMonitor: 発注ログの監視（滞留・約定異常など）
  - RiskMonitor: ドローダウン・ポジション上限チェックとアラート記録
  - KillSwitch: 条件に応じて停止フラグ（data/kill.flag）を書き込む
  - MonitoringEngine: 上記を統合して定周期ポーリング

- ポートフォリオ構築
  - 候補選定、等重/スコア加重、リスクベースの株数算出、セクター制限、レジーム乗数等の純粋関数集

- Research（リサーチ）
  - ファクター計算（モメンタム、バリュー、ボラティリティ等）
  - 将来リターン計算、IC（Information Coefficient）、統計サマリー

- AI
  - news_nlp: ニュース記事を OpenAI で評価し銘柄ごとのスコアを ai_scores テーブルに格納
  - regime_detector: ETF 200日MA乖離とマクロニュースを合成して市場レジーム判定

- ユーティリティ
  - logging_setup: 統一的なログ設定（標準出力 + 日次ローテートファイル）
  - process_priority: プロセス優先度 / CPU affinity 設定
  - 設定ウィザード（config_setup）・設定検証（validate_config）
  - ツール: paper_verification_report によるペーパートレード検証レポート生成

---

## 必要要件（概略）

以下は主な Python パッケージ例です。環境によって追加が必要になることがあります。

- Python 3.9+
- duckdb
- psutil
- openai
- pyyaml（config ファイル検証時）
- その他標準ライブラリ（sqlite3 等）

インストール例:

```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai pyyaml
```

（requirements.txt はリポジトリに含まれていないため、必要に応じて環境に合わせて追加してください）

---

## セットアップ手順（推奨ワークフロー）

1. リポジトリをクローンし、仮想環境を作成して依存ライブラリをインストールする。

2. .env の作成（対話式ウィザード）:
   - 次のコマンドで .env を生成／更新できます。

     ```bash
     python -m kabusys.config_setup
     ```

   - 主要な必須環境変数（例）:
     - JQUANTS_REFRESH_TOKEN（必須）
     - KABU_API_PASSWORD（必須）
     - OPENAI_API_KEY（AI 機能を使用する場合）
     - KABUSYS_ENV（development / paper_trading / live）
     - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
     - SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
     - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB、デフォルト: data/paper_trading.db）

   - .env の自動ロード: プロジェクトルート（.git または pyproject.toml がある場所）から `.env` / `.env.local` を自動読み込みします。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

3. 設定検証（起動前チェック）:

```bash
python -m kabusys.validate_config
# 警告も厳密に扱いたい場合
python -m kabusys.validate_config --strict
```

4. DB 初期化は実行スクリプトが自動的に行います（monitoring 用テーブルや列のマイグレーションを含む）。

---

## 使い方（実行例）

- ExecutionEngine を起動（発注エンジン）

  ```bash
  python -m kabusys.run_execution
  ```

  - ペーパートレードを実行する場合は環境変数 `KABUSYS_ENV=paper_trading` をセットします。Paper trading 時は `PAPER_TRADING_SQLITE_PATH`（または既定の data/paper_trading.db）に記録され、本番 DB と分離されます。

- Monitoring（監視ループ）を起動

  ```bash
  python -m kabusys.run_monitoring
  ```

  - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL`（秒）で上書き可能（デフォルト 60 秒）。
  - 監視は常に本番の sqlite_path（Settings.sqlite_path）を使用します。

- 設定ウィザード（.env の作成）

  ```bash
  python -m kabusys.config_setup
  ```

- 設定検証

  ```bash
  python -m kabusys.validate_config
  ```

- Paper Trading 検証レポート生成

  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを直接指定する場合:
  python -m kabusys.tools.paper_verification_report --db path/to/paper_trading.db
  ```

- AI 機能（プログラムから呼び出す例）

  OpenAI API キーが必要です（環境変数 `OPENAI_API_KEY` または明示的に渡す）。

  例（スクリプト内）:

  ```python
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  # target_date は datetime.date 型
  count = score_news(conn, target_date, api_key="sk-...")
  ```

---

## 停止・Kill フラグについて

- stop_requested.flag
  - `run_execution.py` や `run_monitoring.py` はプロジェクトの `data/stop_requested.flag` を監視しており、存在するとループを止めます（外部からの安全な停止シグナル）。

- kill.flag（KILL SWITCH）
  - `KillSwitch` はリスク条件（ドローダウン超過など）を満たした場合に `data/kill.flag` を書き込み、ExecutionEngine 側で検知して停止させます。
  - `Settings.kill_flag_clear_on_start` が `1` に設定されていると起動時に自動でクリアされます（本番では `0` 推奨）。

---

## 主要な環境変数（抜粋）

- JQUANTS_REFRESH_TOKEN（必須）
- KABU_API_PASSWORD（必須）
- OPENAI_API_KEY（AI を使用する場合）
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH（監視 DB、デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
- LOG_LEVEL（INFO / DEBUG / ...）
- MONITOR_POLL_INTERVAL（監視ポーリング間隔, 秒, デフォルト 60）
- KILL_FLAG_CLEAR_ON_START（0/1）

---

## ディレクトリ構成（抜粋）

リポジトリの主要ファイル／ディレクトリは以下の通りです（`src/kabusys` がパッケージルート）:

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数／設定読み込みロジック
  - config_setup.py          — .env 対話式ウィザード
  - validate_config.py       — 設定検証 CLI
  - run_execution.py         — ExecutionEngine 起動スクリプト
  - run_monitoring.py        — SystemMonitor 起動スクリプト
  - tools/
    - paper_verification_report.py — ペーパートレード検証レポート生成
  - utils/
    - logging_setup.py       — ログ初期化ユーティリティ
    - process_priority.py    — プロセス優先度 / CPU affinity
  - monitoring/
    - monitoring_db.py       — SQLite テーブル作成・永続化 API
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - monitoring_engine.py
    - alert_manager.py
  - execution/                — 発注関連（Engine, OrderManager, BrokerFactory 等）
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

- data/                      — 実行時に使用する DB / フラグ（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/stop_requested.flag）
- logs/                      — ログ出力先（デフォルト）

---

## 注意事項 / 実運用に関するメモ

- Paper trading の DB は本番 DB と分離されています。`KABUSYS_ENV=paper_trading` を設定して起動してください。
- OpenAI 利用機能を動かすには `OPENAI_API_KEY` を必ず設定してください。API 呼び出しはリトライやフェイルセーフが組まれていますが、API コストに注意してください。
- ログディレクトリが作成できない場合はファイルロギングをスキップしてコンソール出力のみで継続します。
- monitor 系は常に本番の sqlite_path を参照する設計（監視は本番対象を監視するため）。paper_trading のみを監視対象にしたい場合は設定を調整してください。
- 設定検証ツール（validate_config）は起動前の必須項目漏れや設定ファイルのパースエラーを検出するのに便利です。
- DB マイグレーションは簡易的にソース内で行われます（例: monitoring_db は欠損カラムがあれば追加する）。

---

## 問い合わせ / 貢献

バグ報告・改善提案は Issue を立ててください。プルリクエストは歓迎します。

---

README は以上です。必要であれば、セットアップ手順の詳細（requirements.txt、Dockerfile、systemd ユニットのサンプルなど）や API ドキュメントを追加で作成します。どの情報を優先して追加しますか？