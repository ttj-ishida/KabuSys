# KabuSys

日本株自動売買システムのサブセット実装。  
戦略のリサーチ、ポートフォリオ構築、発注管理、監視、Paper Trading 検証、そしてニュース NLP / レジーム判定などのユーティリティ群を含みます。

---

## プロジェクト概要

- Python で実装された自動売買ユーティリティ群。
- DuckDB を用いた時系列・財務データ処理、SQLite を用いた監視・発注ログの永続化。
- 本番/ペーパー（paper_trading）環境の切替機構を持ち、ペーパー環境は DB を完全分離可能。
- 監視（Monitoring）コンポーネントはプロセス死活監視・データ鮮度チェック・注文滞留検出・リスクイベントのログ化・LINE 通知をサポート。
- OpenAI（gpt-4o-mini）を用いたニュースセンチメント（ai_scores）やマクロセンチメントによるレジーム判定機能を提供。

---

## 主な機能一覧

- 実行系
  - ExecutionEngine 起動スクリプト（kabusys.run_execution）  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、Paper 用 SQLite（data/paper_trading.db など）に記録。
    - 発注管理、リスク管理、リコンシリエーション機能を統合。
- 監視系
  - SystemMonitor / TradeMonitor / RiskMonitor の定期ポーリング（kabusys.run_monitoring）
  - MonitoringDB（SQLite）へのログ永続化（system_status, trade_logs, positions, risk_logs, dashboard）
  - KillSwitch（data/kill.flag）による外部停止シグナル
  - LINE へのプッシュ通知（AlertManager）
  - Streamlit ダッシュボード（監視用）
- リサーチ / 特徴量
  - factor_research: Momentum / Volatility / Value 等のファクター計算（DuckDB）
  - feature_exploration: 将来リターン計算、IC（Spearman）など統計解析ユーティリティ
- ポートフォリオ構築
  - 候補選定、重み計算（等金額・スコア加重）
  - セクター集中制限、レジーム乗数の適用
  - ポジションサイズ計算（単元丸め・リスクベース配分・集約キャップ）
- AI
  - news_nlp: OpenAI を使ったニュース記事の銘柄別センチメント評価・ai_scores への書込
  - regime_detector: ETF（1321）MA200 とマクロニュースの LLM スコアを合成して日次レジーム判定
- ツール
  - paper_verification_report: Paper Trading DB から検証レポートを生成（稼働率、注文成功率、レイテンシ、判定 PASS/FAIL）

---

## 必要パッケージ（例）

主要な外部依存（抜粋）:
- Python 3.9+
- duckdb
- psutil
- requests
- openai（OpenAI SDK）
- streamlit

インストール例:
```bash
pip install duckdb psutil requests openai streamlit
```
（プロジェクトの requirements.txt がある場合はそれを使用してください）

---

## セットアップ手順

1. リポジトリをクローン / 配布コードを取得
2. Python 仮想環境を作成して依存パッケージをインストール
3. 環境変数（または .env / .env.local）を用意

重要な環境変数（代表例）
- JQUANTS_REFRESH_TOKEN — J-Quants API トークン（必須）
- KABU_API_PASSWORD — kabuステーション API パスワード（必須）
- OPENAI_API_KEY — OpenAI API キー（AI 機能を使う場合）
- KABUSYS_ENV — 起動環境（development | paper_trading | live）デフォルト: development
- PAPER_FILL_MODE — paper_trading 時の約定挙動: instant | partial | never | reject（デフォルト: instant）
- PAPER_TRADING_SQLITE_PATH — Paper DB（デフォルト: data/paper_trading.db）
- SQLITE_PATH — 監視用 SQLite（デフォルト: data/monitoring.db）
- DUCKDB_PATH — DuckDB ファイル（デフォルト: data/kabusys.duckdb）
- PID_FILE_PATH, KILL_FLAG_PATH など（デフォルト有り）

.env 自動読み込み:
- 実行時、プロジェクトルート（.git または pyproject.toml があるディレクトリ）にある `.env` と `.env.local` が自動で読み込まれます（OS 環境変数が優先されます）。
- 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

注意:
- PAPER_TRADING 環境では sqlite が分離され、実際の（本番）monitoring DB を汚さない構成です。
- PAPER_FILL_MODE は "instant" / "partial" / "never" / "reject" のいずれかを指定してください（無効値は例外）。

---

## 使い方（実行例）

- ExecutionEngine を起動（本番 / 開発 / paper_trading に応じて KABUSYS_ENV を設定）
```bash
# 本番・デフォルト (development)
python -m kabusys.run_execution

# Paper Trading モード（Mock Broker を使用）
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```

- Monitoring（監視ループ）を起動
```bash
# ポーリング間隔は MONITOR_POLL_INTERVAL で指定（秒、デフォルト 60）
MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
```
- Streamlit ダッシュボード（監視 DB を読み取り専用で表示）
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート生成ツール
```bash
# デフォルト DB: data/paper_trading.db
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11

# 別 DB を指定
python -m kabusys.tools.paper_verification_report --db /path/to/paper_trading.db
```

- AI スコア / レジーム判定（プログラムから呼び出す）
  - news_nlp.score_news(conn, target_date, api_key=...)
  - regime_detector.score_regime(conn, target_date, api_key=...)
  - どちらも OPENAI_API_KEY が必要（api_key 引数で上書き可）。API 呼び出し失敗時はフェイルセーフで処理継続する設計です。

---

## 実装上の注意点 / 動作仕様

- Settings（kabusys.config）
  - OS 環境変数 > .env.local > .env の順に読み込み（既定の保護機構あり）。
  - 必須環境変数未設定時は ValueError を送出するプロパティがある（例: JQUANTS_REFRESH_TOKEN）。
  - KABUSYS_ENV は "development", "paper_trading", "live" のいずれかである必要があります。

- DB 初期化
  - run_monitoring/run_execution は起動時に init_monitoring_db() を呼び、必要な監視テーブルを作成します（冪等）。
  - monitoring_db.init_monitoring_db は既存 DB に対してカラム追加マイグレーション（例: peak_value, latency_ms）も行います。

- プロセス優先度/CPU affinity
  - 起動スクリプトは最初に set_process_priority("high") を呼びます（psutil を使用）。権限不足や未対応 OS の場合はログを出してスキップします。
  - set_cpu_affinity も util として提供。

- KillSwitch
  - リスク条件（ドローダウン超過、ポジション上限超過）で data/kill.flag を書き込んで ExecutionEngine に停止を促します（冪等・既存ファイルは上書きしない）。
  - ExecutionEngine 側で起動時に kill.flag をクリアするオプションが Settings.kill_flag_clear_on_start で設定可能。

- Paper Trading
  - KABUSYS_ENV=paper_trading の場合、BrokerClientFactory は MockBrokerClient を返し、紙上の挙動（PAPER_FILL_MODE 等）を制御します。DB は paper_sqlite_path（デフォルト data/paper_trading.db）へ分離されます。

- AI モジュール
  - news_nlp: 銘柄単位で記事を集約し OpenAI にバッチ送信。レスポンスは厳密な JSON を期待（JSON mode を利用）。
  - regime_detector: ETF 1321 の MA200 とマクロニュース LLM スコアを合成して regime_label を生成、DuckDB の market_regime テーブルへ書き込み。
  - API エラーはリトライやフェイルセーフ（代替値使用）で対処します。

---

## ディレクトリ構成（該当コードベース）

以下は本リポジトリ内の主要ファイル／パッケージのツリー（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py
    - run_monitoring.py
    - run_execution.py
    - tools/
      - __init__.py
      - paper_verification_report.py
    - ai/
      - __init__.py
      - news_nlp.py
      - regime_detector.py
    - monitoring/
      - __init__.py
      - monitoring_db.py
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - kill_switch.py
      - alert_manager.py
      - monitoring_engine.py
      - streamlit_dashboard.py
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - risk_adjustment.py
      - position_sizing.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - execution/
      - (order_manager.py, reconciler.py, order_repository.py, execution_engine.py, broker_factory.py, ...)
      - order_manager.py
      - reconciler.py
      - (その他発注関連モジュール)
    - utils/
      - __init__.py
      - process_priority.py
    - (その他: data/, strategy/ 等想定のパッケージが参照される)

---

## 例: 簡易 .env の雛形

```
# .env
KABUSYS_ENV=development
LOG_LEVEL=INFO

JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password

OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db

PAPER_FILL_MODE=instant
```

---

## トラブルシューティング / よくある質問

- DB が見つからない / 読み込めない
  - DuckDB, SQLite のパス (DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH) を確認してください。streamlit は読み取り専用 URI を使うためパス解決に失敗するとエラーになります。
- OpenAI が動かない
  - OPENAI_API_KEY が設定されているか確認してください。API レート制限やネットワーク障害はログに出力されリトライ・フェイルセーフされますが、キーが無いと ValueError が発生します。
- MONITOR_POLL_INTERVAL の設定
  - run_monitoring でポーリング間隔を上書きするには環境変数 MONITOR_POLL_INTERVAL（秒）を設定してください。不正な値や 0 以下はデフォルト 60 秒にフォールバックします。

---

必要であれば、README に実行例（起動時の log 出力抜粋や環境変数のより詳細な説明）、または各モジュール（ExecutionEngine, OrderManager, MonitoringEngine 等）の内部フロー図を追加できます。どの情報を優先して追加しますか？