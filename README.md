# KabuSys

KabuSys は日本株向けの自動売買／リサーチ基盤のミニマム実装です。  
このリポジトリはトレーディングの実行エンジン、監視（Monitoring）機能、ファクター計算・リサーチ、LLM を使ったニュース NLP / レジーム判定などのコンポーネントを含みます。

主な設計方針は以下の通りです。
- DuckDB を用いた時系列データ処理（prices_daily / raw_financials 等）
- SQLite を用いた監視ログ・発注履歴の永続化
- 本番 / ペーパートレードを環境変数で切替可能（DB は分離）
- OpenAI（gpt-4o-mini 等）を用いたニュースセンチメント・レジーム判定（任意）
- 監視は LINE Push で通知可能（オプション）

以下はこのコードベースの README（日本語）です。

---

## 機能一覧

- ExecutionEngine（発注エンジン）
  - シグナル読み込み → Gate（リスクチェック） → 発注（Broker API 経由）
  - 再起動時の Reconciler による注文・ポジションの同期
  - Rate limiting / circuit-breaker / risk gate の実装
  - Paper trading 環境での MockBroker サポート（DB を分離）

- Monitoring（監視）
  - SystemMonitor: CPU/メモリ/ディスク/プロセス稼働・データ鮮度監視
  - TradeMonitor: 滞留注文、約定価格異常検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: 条件到達時にフラグファイルを作成して ExecutionEngine を停止
  - AlertManager: LINE によるプッシュ通知（クールダウン管理）
  - Streamlit ダッシュボード（読み取り専用）

- Portfolio（ポートフォリオ構築）
  - 候補選定、等金額・スコア加重の重み計算
  - セクター上限適用、レジーム乗数
  - ポジションサイズ計算（単元株丸め、aggregate cap）

- Research（リサーチ）
  - モメンタム / ボラティリティ / バリュー等のファクター計算（DuckDB SQL）
  - 将来リターン計算、IC（Information Coefficient）・統計サマリ

- AI（LLM）連携
  - news_nlp: raw_news から銘柄ごとにセンチメントスコアを生成し ai_scores に保存
  - regime_detector: マクロニュース + ETF ma200 の組合せで市場レジーム判定
  - OpenAI API の利用（API キー必須）

---

## 前提 / 要件

- Python 3.10+
- 必要な外部ライブラリ（例）
  - duckdb
  - psutil
  - requests
  - streamlit (ダッシュボード用)
  - openai (AI 機能使用時)
- SQLite（組み込み） / DuckDB（Python パッケージとして使用）
- ネットワーク接続（OpenAI を使う場合）

簡単なインストール例（仮想環境推奨）:

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install duckdb psutil requests streamlit openai
```

プロジェクトで requirements ファイルがある場合はそちらを使ってください（このリポジトリにはサンプル requirements は含まれていません）。

---

## セットアップ手順

1. リポジトリをクローン／配置
2. 仮想環境を作成して依存パッケージをインストール（上記参照）
3. データ用ディレクトリを作成（デフォルトは `data/`）

```bash
mkdir -p data
```

4. 環境変数を設定する（`.env` をプロジェクトルートに置くと自動で読み込まれます。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定）

例: `.env`（最低限の例）

```
KABUSYS_ENV=development
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
JQUANTS_REFRESH_TOKEN=your_jquants_token
KABU_API_PASSWORD=your_kabu_password
OPENAI_API_KEY=sk-...
LINE_CHANNEL_ACCESS_TOKEN=...
LINE_USER_ID=...
```

主な環境変数（主要なもの）

- KABUSYS_ENV: development | paper_trading | live
  - paper_trading 時は発注は MockBroker を使い、PAPER_TRADING_SQLITE_PATH（デフォルト: data/paper_trading.db）に記録
- DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（デフォルト: data/monitoring.db）
- PAPER_TRADING_SQLITE_PATH: paper_trading 用 SQLite（デフォルト: data/paper_trading.db）
- OPENAI_API_KEY: OpenAI API キー（AI 機能を使う場合必須）
- JQUANTS_REFRESH_TOKEN: J-Quants API トークン（必要に応じて）
- KABU_API_PASSWORD: kabuステーション API パスワード（本番接続）
- LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID: LINE 通知設定
- PAPER_FILL_MODE: instant | partial | never | reject（PaperTrading の約定挙動）
- PID_FILE_PATH / KILL_FLAG_PATH: 実行プロセスの PID 保存・kill フラグのパス
- MONITOR_POLL_INTERVAL: Monitoring のポーリング間隔（秒、デフォルト 60）

---

## 使い方

以下は代表的な起動方法です。パッケージ化・インストール方法によりパスは適宜調整してください。

注意: スクリプトはパッケージ内に置かれているため、プロジェクトルートで `python -m kabusys.run_execution` 等で起動できます。

- ExecutionEngine（発注エンジン）起動

  本番 / ペーパートレードは `KABUSYS_ENV` に依存します（paper_trading では MockBroker を使用し DB を分離）。

  ```bash
  # ペーパートレードで起動（.env で KABUSYS_ENV=paper_trading を指定しても可）
  KABUSYS_ENV=paper_trading python -m kabusys.run_execution

  # 本番想定
  KABUSYS_ENV=live python -m kabusys.run_execution
  ```

  実行開始時にプロセス優先度を "high" に設定します。プロセスは PID を `Settings.pid_file_path`（デフォルト: data/execution.pid）に書きます。

  kill.flag による停止:
  - KillSwitch が条件達成時に `Settings.kill_flag_path`（デフォルト: data/kill.flag）を書き込みます。
  - 手動で停止させたい場合は同ファイルを作成することで Engine に停止シグナルを送れます。
  - 起動時に kill.flag を消去するオプション（Settings.kill_flag_clear_on_start）を環境変数で制御できます。

- MonitoringEngine（監視ループ）起動

  ポーリング間隔は `MONITOR_POLL_INTERVAL` 環境変数で上書き可能（秒、デフォルト 60）。

  ```bash
  # デフォルト間隔で起動
  python -m kabusys.run_monitoring

  # 30秒間隔で起動
  MONITOR_POLL_INTERVAL=30 python -m kabusys.run_monitoring
  ```

  監視は本番 sqlite_path を常に使用します（KABUSYS_ENV に依存せず）。

- Streamlit ダッシュボード（読み取り専用）

  Monitoring DB を読み取り専用で可視化できます。実行例:

  ```bash
  streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
  ```

  DB が存在しない / 開けない場合はエラーメッセージが表示されます。

- AI タスク（ニューススコア/レジーム判定）

  DuckDB 接続を渡して関数を直接呼ぶ設計です。例（Python REPL）:

  ```py
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news
  conn = duckdb.connect("data/kabusys.duckdb")
  # OPENAI_API_KEY 環境変数がセット済みであれば api_key=None で動作
  score_news(conn, date(2026, 3, 20))
  ```

  同様に regime_detector の `score_regime` を使って market_regime テーブルへ書き込めます。

- その他ユーティリティ
  - ポートフォリオ構築用関数群は `kabusys.portfolio` にまとめられています
  - リサーチ用関数群は `kabusys.research` にまとめられています

---

## 注意点 / 運用メモ

- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml を基準）を探索して `.env` / `.env.local` を自動で読み込みます。自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
  - `.env.local` は OS 環境変数を保護しつつ上書きします。

- Paper trading
  - `KABUSYS_ENV=paper_trading` の場合、発注は MockBroker になり、専用 SQLite（`PAPER_TRADING_SQLITE_PATH`）に記録されます。本番 DB と完全分離されます。

- プロセス優先度 / CPU affinity
  - 起動時にプロセス優先度を "high" に設定する処理があります（失敗した場合は警告）。
  - `kabusys.utils.process_priority` により Windows / POSIX の差分を吸収します。

- DB マイグレーション
  - `init_monitoring_db()` は冪等でテーブルを作成します。既存の dashboard に `peak_value` カラムがない場合は自動で追加します。

- フェイルセーフ設計
  - OpenAI API の失敗時は多くのケースでフォールバック（例: 0.0）して処理を継続します。監視系はログを残しつつシステムを停止させるための KillSwitch を提供します。

---

## ディレクトリ構成（主要ファイル）

（src/kabusys 以下を抜粋）

- src/kabusys/
  - __init__.py
  - config.py                 — 環境変数 / Settings
  - run_execution.py          — ExecutionEngine 起動スクリプト
  - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト

- src/kabusys/execution/
  - execution_engine.py
  - order_manager.py
  - order_repository.py
  - order_record.py
  - reconciler.py
  - risk_manager.py
  - broker_api.py
  - broker_factory.py
  - ...（Broker クライアント実装など）

- src/kabusys/monitoring/
  - monitoring_db.py
  - system_monitor.py
  - trade_monitor.py
  - risk_monitor.py
  - kill_switch.py
  - alert_manager.py
  - monitoring_engine.py
  - streamlit_dashboard.py

- src/kabusys/portfolio/
  - portfolio_builder.py
  - position_sizing.py
  - risk_adjustment.py

- src/kabusys/research/
  - factor_research.py
  - feature_exploration.py

- src/kabusys/ai/
  - news_nlp.py
  - regime_detector.py

- src/kabusys/utils/
  - process_priority.py

- data/
  - (デフォルトの DB ファイルや pid/flag ファイルを配置。例: data/kabusys.duckdb, data/monitoring.db, data/paper_trading.db, data/execution.pid, data/kill.flag)

---

## 開発 / テストに関するヒント

- テスト実行時は自動 .env 読み込みを無効化すると安全です：
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1 pytest ...`

- DuckDB / SQLite に対する読み取り専用アクセスは URI 経由で行えます（Streamlit ダッシュボードが使用）。

- OpenAI 呼び出し部分はテスト容易性を考慮して `_call_openai_api` を内部で分離しているので、unit test では patch して置き換え可能です。

---

この README はコードベースの主要な使い方・設定・構成をまとめたものです。より詳しい設計文書（PortfolioConstruction.md、StrategyModel.md 等）が併存する想定のため、戦略やパラメータ設計はそちらを参照してください。質問や補足が必要であれば教えてください。