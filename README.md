# KabuSys

日本株自動売買システムの参照実装ライブラリ / 実行スクリプト群です。  
このリポジトリはトレード実行エンジン（ExecutionEngine）、監視（Monitoring）、リサーチ／ファクター計算、AI を用いたニュース解析などの主要コンポーネントで構成されています。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は以下の責務を持つモジュール群で構成されています：

- Execution: 発注ロジック・リスク管理・注文リポジトリ・ブローカーインターフェース（ペーパートレード時はモック）  
- Monitoring: システム状態監視、注文監視、リスク（ドローダウン・保有数）監視、Kill Switch（フラグ書き込み）  
- Research: DuckDB を用いたファクター計算 / 特徴量探索（モメンタム、バリュー、ボラティリティ 等）  
- AI: OpenAI を利用したニュースのセンチメント評価・市場レジーム判定（gpt-4o-mini を想定）  
- Portfolio: 候補選定・重み計算・ポジション決定ロジック  
- Tools: ペーパートレード検証レポート生成などの CLI ユーティリティ  
- Utils: ロギング設定、プロセス優先度設定、設定読み込みユーティリティなど

設計上のポイント：
- 環境変数・`.env` による設定管理（自動ロードあり）。プロジェクトルートを基準に `.env` / `.env.local` を読み込みます（無効化可）。
- DuckDB（分析用）、SQLite（監視・発注ログ）を使用（パスは環境変数で変更可能）。
- Paper trading（KABUSYS_ENV=paper_trading）は本番 DB と分離された専用 SQLite を使用。
- OpenAI を使う機能は API キー必須。API 呼び出しはリトライやフェイルセーフを備えています。

---

## 主な機能一覧

- 実行
  - ExecutionEngine による発注セッション（本番 / ペーパートレード切替）
  - RiskManager に基づく注文ブロック
  - OrderRepository / OrderManager / Reconciler

- 監視
  - SystemMonitor: CPU/MEM/DISK、データ鮮度、Execution プロセス生死チェック
  - TradeMonitor: 注文の滞留・異常約定検出（trade_logs 参照）
  - RiskMonitor: ドローダウン計算・ポジション数チェック、dashboard 更新
  - KillSwitch: 条件を満たしたら `data/kill.flag` を書き込み Execution を止める
  - MonitoringEngine: 各モニターの定期実行、アラート発行連携

- リサーチ / ポートフォリオ構築
  - ファクター計算（momentum / volatility / value）
  - 将来リターン・IC 計算、特徴量サマリ
  - 候補選定 / 等金額・スコア重み / リスクベースのポジションサイズ決定
  - セクター上限・レジーム乗数の適用

- AI
  - ニュース記事を LLM でスコアリングして ai_scores に書き込む（score_news）
  - マクロ記事＋ETF MA から市場レジームを判定して market_regime に保存（score_regime）

- ツール
  - 環境設定ウィザード（.env の対話式生成: config_setup）
  - 設定検証 CLI（validate_config）
  - Paper Trading 検証レポート生成（tools.paper_verification_report）

---

## 必要条件 / 推奨環境

- Python 3.10+
- ライブラリ（主なもの）
  - duckdb
  - psutil
  - openai
  - （任意）PyYAML — config/*.yaml の検証に利用
- OS: Linux / macOS / Windows（多くはクロスプラットフォーム対応）

インストール例（仮の requirements を想定）:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil openai PyYAML
# 開発時はパッケージを編集可能インストール
pip install -e .
```

---

## 環境変数（主なもの）

`.env` に設定する主要なキー（一部）:

- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- OPENAI_API_KEY (AI 機能を使う場合必須)
- KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
- DUCKDB_PATH: 分析用 DB（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視 DB（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: ペーパートレード用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: instant | partial | never | reject（ペーパートレード時の約定挙動）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL
- KILL_FLAG_CLEAR_ON_START: 0|1（Execution 起動時の kill.flag 自動クリア）
- MONITOR_POLL_INTERVAL: 監視ループの秒間隔（デフォルト 60） — run_monitoring で参照
- PID_FILE_PATH / KILL_FLAG_PATH: ファイルパス（デフォルト data/execution.pid / data/kill.flag）

注意:
- Settings モジュールは自動でプロジェクトルートの `.env` / `.env.local` を読み込みます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
- Monitoring（run_monitoring）は KABUSYS_ENV に関わらず本来の（production）`SQLITE_PATH` を使うよう設計されています。

---

## セットアップ手順

1. リポジトリをクローン
2. 仮想環境作成・有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数を作成
   - 対話式ウィザード:
     ```bash
     python -m kabusys.config_setup
     ```
   - 生成後、設定検証:
     ```bash
     python -m kabusys.validate_config
     # 警告も fail 扱いにする:
     python -m kabusys.validate_config --strict
     ```
5. DuckDB / SQLite の初期化は各スクリプト実行時に必要テーブルを作成します（monitoring の init_monitoring_db 等）。

ログディレクトリ:
- デフォルトで `logs/` に日次ローテートのログファイルが作られます（logs/<app_name>.log）。

---

## 使い方（実行例）

- ExecutionEngine（発注エンジン）を起動:
  - 本番 / 開発 / ペーパートレードは KABUSYS_ENV による切替
  - ペーパートレードでは専用 DB を使用し MockBrokerClient を使います
  ```bash
  python -m kabusys.run_execution
  ```

- Monitoring（監視ループ）を起動:
  - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL（秒）で上書き可能（デフォルト 60）
  ```bash
  export MONITOR_POLL_INTERVAL=30
  python -m kabusys.run_monitoring
  ```

- Paper Trading 検証レポート生成:
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  # DB パスを直接指定する場合
  python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
  ```

- AI スコアリング / レジーム判定（Python REPL から):
  ```python
  import duckdb
  from datetime import date
  from kabusys.ai import score_news  # top-level エクスポート

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, date(2026, 4, 10), api_key="sk-...")
  print("書き込み銘柄数:", written)
  ```

- Kill / Stop の扱い:
  - 実行プロセスの停止要求はフラグファイルで行います:
    - ExecutionEngine を外部から停止したい場合は `data/stop_requested.flag` を作成すると run_execution/run_monitoring がこれを検知して終了します。
    - Kill Switch（監視側）がリスク閾値超過を検出した場合は `data/kill.flag` を書き込み、ExecutionEngine 側でこれを検出して停止します。
  - `KILL_FLAG_CLEAR_ON_START=1` を設定すると Execution 起動時に kill.flag を自動でクリアします（本番では 0 を推奨）。

---

## 注意点 / 運用メモ

- OpenAI 利用:
  - OPENAI_API_KEY を必ず設定してください。AI モジュールは失敗時にフォールバック（例: macro_sentiment=0.0）する設計ですが、API キー未設定時は例外になります。
- プロセス優先度設定:
  - 起動時にプロセス優先度を "high" に設定しようとしますが、権限により失敗することがあります（警告ログに出力されます）。
- DB マイグレーション:
  - monitoring_db.init_monitoring_db は冪等でテーブル/インデックス作成・簡単なマイグレーション（カラム追加）を行います。
- テスト / CI:
  - Settings の自動 .env 読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化できます（テスト時に便利）。

---

## ディレクトリ構成（抜粋）

src/kabusys/
- __init__.py
- config.py                  — 環境変数/.env ロードと Settings
- config_setup.py            — .env 対話式ウィザード
- validate_config.py         — 設定検証 CLI
- run_execution.py           — ExecutionEngine 起動スクリプト
- run_monitoring.py          — SystemMonitor ポーリング起動スクリプト

パッケージ群:
- ai/
  - news_nlp.py               — ニュース NLP スコアリング
  - regime_detector.py       — 市場レジーム判定
- monitoring/
  - monitoring_db.py         — SQLite 永続化層（system_status, trade_logs, positions, risk_logs, dashboard）
  - system_monitor.py
  - trade_monitor.py         — （注: trade_monitor の実装は省略されているが存在）
  - risk_monitor.py
  - kill_switch.py
  - monitoring_engine.py
  - alert_manager.py         — （アラート送信管理、実装参照）
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
- tools/
  - paper_verification_report.py
- utils/
  - logging_setup.py         — 一貫したログ設定（console + TimedRotatingFileHandler）
  - process_priority.py      — プロセス優先度 / CPU affinity

データ・ログ:
- data/                      — デフォルトの DB/フラグ/ pid 保存先（例: data/monitoring.db, data/paper_trading.db, data/kill.flag, data/execution.pid）
- logs/                      — デフォルトのログ出力先

---

## 開発・拡張案

- ブローカー実装の追加（kabuステーション以外）
- Strategy モジュールのプラグイン化（ユーザー戦略の差し替え）
- ロギング／メトリクスの外部集約（Prometheus / Grafana）
- AI 呼び出しの非同期化・キュー化（レート制御・コスト最適化）
- 単体テストの充実（AI 呼び出しはモック化してテスト可能）

---

以上。README の補足や特定モジュールの詳細ドキュメント（使い方サンプル、API の引数例など）が必要であれば教えてください。