# KabuSys

KabuSys は日本株の自動売買 / リサーチ / 監視を目的とした Python パッケージです。本リポジトリには発注実行（ExecutionEngine）、モニタリング、ポートフォリオ構築、ファクター計算、ニュース NLP（LLM を用いたセンチメント推定）などの主要コンポーネントが含まれます。

以下はこのコードベースの概要、機能、セットアップ・使い方、ディレクトリ構成のサンプル README (日本語) です。

---

## プロジェクト概要

- 自動売買エンジン（発注管理、リスク管理、再同期）
- 監視基盤（システム状態、注文の滞留・約定異常、ドローダウン監視、kill-switch）
- ポートフォリオ構築（候補選定、重み付け、ポジションサイズ計算、セクター制限）
- リサーチ（ファクター計算、将来リターン・IC 評価、統計サマリー）
- ニュース NLP（OpenAI を用いた銘柄別センチメント評価）
- 運用補助ツール（Paper Trading 検証レポート生成、Streamlit モニタリングダッシュボード）

設計のポイント：
- DuckDB をファクトデータ（prices_daily 等）集計に使用
- SQLite を監視ログ / 発注履歴に使用
- 環境変数および .env（.env.local）で設定を管理
- Paper Trading（KABUSYS_ENV=paper_trading）時は本番 DB と分離して動作

---

## 主な機能一覧

- 実行関連
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
  - Broker クライアントの抽象化および mock 対応（paper_trading）
  - 発注マネージャ（OrderManager）、再同期・リコンシリエーション（Reconciler）

- 監視関連
  - SystemMonitor: CPU / メモリ / ディスク / プロセス生存・データ鮮度チェック
  - TradeMonitor: 注文滞留・約定異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視
  - KillSwitch: フラグファイルによる ExecutionEngine 停止指示
  - AlertManager: LINE Push による通知
  - モニタリング用 DB 層（MonitoringDB）と Streamlit ダッシュボード

- ポートフォリオ構築
  - 候補選定、等金額/スコア加重の重み付け
  - セクター集中制限、レジーム乗数
  - ポジションサイズ計算（単元株丸め・リスクベース割当）

- リサーチ & AI
  - ファクター計算（Momentum / Volatility / Value 等）
  - 特徴量探索（forward returns / IC / summary）
  - ニュース NLP（OpenAI で銘柄ごとのセンチメントを算出）
  - レジーム判定（ETF の MA とマクロニュースで合成）

- ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
  - Streamlit ベース監視ダッシュボード

---

## 必要条件（推奨）

- Python 3.10+
- パッケージ（例）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（標準ライブラリで利用）
- ネットワーク / API キー（OpenAI など）を使う機能を有効にする場合は適宜

インストール例（簡易）:
```bash
python -m pip install duckdb psutil requests openai streamlit
```
プロジェクト側で requirements.txt があればそれを利用してください。

---

## 設定（環境変数）

Settings モジュール（src/kabusys/config.py）は環境変数を参照します。自動的にプロジェクトルートの `.env` と `.env.local` を読み込みます（OS 環境変数が優先）。自動読み込みを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` をセットします。

重要な環境変数（抜粋）:

- KABUSYS_ENV: 実行環境。valid: `development`, `paper_trading`, `live`（デフォルト: development）
  - `paper_trading` の場合は MockBroker を使用し、Paper 用 SQLite を使用して本番 DB と分離します。
- JQUANTS_REFRESH_TOKEN: J-Quants API 用（必須）
- KABU_API_PASSWORD: kabu ステーション API 用（必須）
- OPENAI_API_KEY: OpenAI 呼び出しに使用（news_nlp, regime_detector）
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db） — Monitoring は環境にかかわらず本番 sqlite_path を使用
- PAPER_TRADING_SQLITE_PATH: Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）
- PAPER_FILL_MODE: paper_trading の MockBroker の fill 動作。`instant`|`partial`|`never`|`reject`（デフォルト: instant）
- PID_FILE_PATH: ExecutionEngine の PID ファイル（デフォルト: data/execution.pid）
- KILL_FLAG_PATH: KillSwitch のフラグファイル（デフォルト: data/kill.flag）
- MONITOR_POLL_INTERVAL: run_monitoring のポーリング間隔（秒。デフォルト 60）
- LOG_LEVEL, CPU_THRESHOLD_PCT, MEMORY_THRESHOLD_PCT, DISK_THRESHOLD_PCT など

例: .env に書く
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

.env のパース挙動は POSIX シェル互換（export のサポート、クォートの扱い、コメント処理）です。詳細は src/kabusys/config.py を参照してください。

---

## セットアップ手順（簡易）

1. Python の仮想環境を作成・有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Windows: .venv\Scripts\activate
   ```

2. 必要パッケージをインストール
   ```bash
   python -m pip install -U pip
   python -m pip install duckdb psutil requests openai streamlit
   ```

3. プロジェクトルートに `.env` を作成して必要な環境変数を設定（.env.example を参考にする想定）

4. データディレクトリ作成（必要に応じて）
   ```bash
   mkdir -p data
   ```

5. DuckDB / SQLite ファイルは実行時に自動で生成されます（初回 run でテーブル作成処理が走ります）。

---

## 使い方（主要コマンド）

- 監視ループの起動（SystemMonitor をポーリング）
  ```bash
  python -m kabusys.run_monitoring
  ```
  - 環境変数 `MONITOR_POLL_INTERVAL`（秒）でポーリング間隔を変更できます（デフォルト 60 秒）。
  - run_monitoring は Monitoring 用の sqlite_path（Settings.sqlite_path）を使用します（環境にかかわらず本番 path を使う設計）。

- 実行エンジン（ExecutionEngine）起動
  ```bash
  python -m kabusys.run_execution
  ```
  - `KABUSYS_ENV=paper_trading` の場合、MockBroker を使用し Paper 用 DB（PAPER_TRADING_SQLITE_PATH）へ書き込みます。
  - 起動時にプロセス優先度を "high" に試みます（権限がないと警告でスキップされます）。

- Streamlit ダッシュボード（監視）
  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

- Paper Trading 検証レポート生成
  ```bash
  python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
  ```
  - `--db` オプションで DB パスを明示できます。環境変数 `PAPER_TRADING_SQLITE_PATH` でも指定可能。

- AI / レジーム判定（Python API）
  - ニューススコアリング:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news

    conn = duckdb.connect("data/kabusys.duckdb")
    count = score_news(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```
  - レジーム判定:
    ```python
    from datetime import date
    import duckdb
    from kabusys.ai.regime_detector import score_regime

    conn = duckdb.connect("data/kabusys.duckdb")
    score_regime(conn, target_date=date(2026, 4, 10), api_key="sk-...")
    ```

---

## 重要な挙動・運用メモ

- Monitoring DB 初期化: run_monitoring / run_execution 起動時に monitoring DB のスキーマ作成（冪等）を行います（init_monitoring_db）。
- kill.flag: KillSwitch が条件を満たすと `KILL_FLAG_PATH`（デフォルト data/kill.flag）を書き、ExecutionEngine 停止を促します。既存ファイルがある場合は上書きしません（冪等）。
- PID ファイル: ExecutionEngine は `PID_FILE_PATH` に PID を書きます。SystemMonitor はこの PID ファイルを見てプロセス生存を確認します。不正な PID ファイルは削除され、ログに記録されます。
- Paper Trading: `KABUSYS_ENV=paper_trading` のときは実稼働 DB に書き込まないよう設計されています（PAPER_TRADING_SQLITE_PATH を使用）。
- Process priority / CPU affinity: プロセス優先度や CPU affinity の設定を試みますが、権限不足や未サポート OS の場合は警告を出してスキップします。

---

## ディレクトリ構成（抜粋）

（実際のパッケージは src/kabusys 以下に格納）

- src/kabusys/
  - __init__.py
  - config.py                       — 環境変数 / .env ロード・Settings
  - run_monitoring.py               — SystemMonitor のポーリング起動スクリプト
  - run_execution.py                — ExecutionEngine 起動スクリプト
  - data/ (参照モジュールあり: data.pipeline 等)
  - ai/
    - news_nlp.py                    — ニュース NLP / OpenAI 呼び出し
    - regime_detector.py             — 市場レジーム判定
  - monitoring/
    - monitoring_db.py               — SQLite スキーマ・永続化層（MonitoringDB）
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - monitoring_engine.py
    - streamlit_dashboard.py
  - execution/
    - reconciler.py
    - order_manager.py
    - order_repository.py (参照)
    - execution_engine.py (参照)
    - broker_factory.py (参照)
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
    - process_priority.py

上記は主なファイル構成で、細かなモジュールや補助ユーティリティはパッケージ内にさらにあります。

---

## トラブルシューティング / 注意点

- OpenAI への API 呼び出しはレート制限や 5xx を考慮したリトライロジックがありますが、API キー未設定時は例外が発生します（用途に応じて環境変数 OPENAI_API_KEY を設定してください）。
- DuckDB / SQLite ファイルがない場合、初回実行でテーブル作成が走ります。read-only で開く Streamlit 実行時はファイルパスの指定に注意してください。
- process priority / cpu affinity は OS に依存します。権限がないと設定に失敗してログに警告が出ますが、処理は継続します。
- .env の読み込みはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

---

この README はコードベースから抽出した要点をまとめたものです。細かい挙動や拡張・詳細は各モジュールの docstring およびソースコード（src/kabusys 以下）を参照してください。必要であれば、導入用の requirements.txt や起動用の systemd / supervisor サンプルユニットのテンプレートも作成できます。希望があれば教えてください。