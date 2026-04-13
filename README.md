# KabuSys

バージョン: 0.1.0

KabuSys は日本株向けの自動売買 / リサーチ / 監視基盤のミニマルな実装です。  
主に以下の機能を含みます。

- 注文発行・注文状態管理（ExecutionEngine / OrderManager）
- 取引ログ・監視ログの永続化（SQLite）
- システム・注文・リスク監視（MonitoringEngine、SystemMonitor、TradeMonitor、RiskMonitor）
- 監視ダッシュボード（Streamlit）
- ポートフォリオ構築（候補選定・重み付け・ポジションサイズ算出）
- リサーチ用ファクター計算（Momentum / Volatility / Value 等、DuckDB ベース）
- AI を使ったニュースセンチメント（OpenAI を利用したニューススコアリング、レジーム判定）
- Paper Trading モード（Mock broker を使用し本番 DB と分離）
- 各種ユーティリティ（設定読み込み・プロセス優先度設定等）

以下はこのリポジトリを使い始めるための README です。

---

## 主な機能一覧（抜粋）

- execution
  - 起動: src/kabusys/run_execution.py
  - Broker クライアント抽象化（本番 / Paper 用の切替）
  - Reconciler による再起動時の同期処理
- monitoring
  - 起動: src/kabusys/run_monitoring.py
  - SystemMonitor: CPU / メモリ / ディスク / プロセス監視・データ鮮度検査
  - TradeMonitor: 滞留注文・約定異常の検出
  - RiskMonitor: ドローダウン・ポジション上限監視、ダッシュボード更新
  - KillSwitch: フラグファイルで ExecutionEngine 停止指示
  - AlertManager: LINE Push によるアラート通知
  - Streamlit ダッシュボード: src/kabusys/monitoring/streamlit_dashboard.py
- portfolio
  - 候補選定・等配分・スコア配分（portfolio_builder）
  - セクターキャップ適用・レジーム乗数（risk_adjustment）
  - 株数決定・単元丸め・aggregate cap（position_sizing）
- research
  - ファクター計算（momentum / volatility / value）
  - 将来リターン計算 / IC（feature_exploration）
- ai
  - news_nlp.score_news(): ニュースセンチメントを OpenAI で解析して ai_scores に保存
  - regime_detector.score_regime(): ma200 とマクロニュースで市場レジーム判定

---

## セットアップ手順

前提
- Python 3.9+（コードは型注釈等を使用）
- sqlite3（標準ライブラリ）
- DuckDB、psutil、requests、openai、streamlit などのパッケージ

例: 仮想環境を作成して必要パッケージをインストールする手順（プロジェクトに requirements.txt がない場合）:

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install --upgrade pip
pip install duckdb psutil requests openai streamlit
```

環境変数 / .env
- プロジェクトルートに `.env` / `.env.local` を置くと自動読み込みされます（OS 環境変数が優先）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。
- 主要な必須変数:
  - JQUANTS_REFRESH_TOKEN （J-Quants API 用）
  - KABU_API_PASSWORD （kabuステーション API 用）
- 任意 / 設定例:
  - OPENAI_API_KEY（AI モジュールを使う場合）
  - KABUSYS_ENV: development | paper_trading | live（デフォルト: development）
  - PAPER_FILL_MODE: instant | partial | never | reject（Paper Trading の約定モード）
  - PAPER_TRADING_SQLITE_PATH（paper_trading 用 DB）
  - DUCKDB_PATH（DuckDB ファイル、デフォルト: data/kabusys.duckdb）
  - SQLITE_PATH（監視 DB（production）のパス、デフォルト: data/monitoring.db）
  - LOG_LEVEL（INFO 等）
  - PID_FILE_PATH, KILL_FLAG_PATH 等（監視 / kill フラグ）

簡易 .env の例:
```
KABUSYS_ENV=development
JQUANTS_REFRESH_TOKEN=your_token
KABU_API_PASSWORD=your_password
OPENAI_API_KEY=sk-...
DUCKDB_PATH=data/kabusys.duckdb
SQLITE_PATH=data/monitoring.db
```

データディレクトリの準備:
- data ディレクトリを作成しておくと良いです（SQLite / DuckDB のデフォルトパスが data/ 配下のため）。
```bash
mkdir -p data
```

---

## 使い方

1) 監視ループを起動（常駐監視）
- デフォルトのポーリング間隔は 60 秒（環境変数 `MONITOR_POLL_INTERVAL` で上書き可）。
- 実行:
```bash
python -m kabusys.run_monitoring
# もしくは
python src/kabusys/run_monitoring.py
```
- MONITOR_POLL_INTERVAL の例:
```bash
export MONITOR_POLL_INTERVAL=30
python -m kabusys.run_monitoring
```
- 監視は MonitoringDB（SQLite）に system_status / trade_logs / risk_logs / positions / dashboard を書き込みます。起動時に DB スキーマは自動作成・マイグレーションされます。

2) 実行エンジン（ExecutionEngine）を起動
- Paper Trading モード: `KABUSYS_ENV=paper_trading` を設定すると MockBrokerClient を使用し、Paper 用の SQLite（`PAPER_TRADING_SQLITE_PATH` または data/paper_trading.db）に記録します（本番 DB と分離）。
- 実行:
```bash
python -m kabusys.run_execution
# または
KABUSYS_ENV=paper_trading python -m kabusys.run_execution
```
- 起動時にプロセス優先度を「high」に設定し、Reconciler による同期処理を実行してからセッション実行を開始します。kill フラグ（data/kill.flag）で停止を指示できます。

3) Streamlit ダッシュボード
- 監視用の SQLite DB を読み取ってダッシュボードを表示します（読み取り専用）。
```bash
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```
- デフォルト DB は `data/monitoring.db`。起動中の MonitoringEngine がデータを書き込んでいる必要があります。

4) Paper Trading 検証レポート生成ツール
- 過去期間の paper_trading DB を集計して簡易レポートを出力します。
```bash
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# DB を指定する場合:
python -m kabusys.tools.paper_verification_report --db data/paper_trading.db
```

5) AI モジュール（ニューススコア / レジーム判定）
- OpenAI API キーが必要です（環境変数 `OPENAI_API_KEY` または関数呼び出し時に引数で渡す）。
- ニューススコアリング:
  - 関数: `kabusys.ai.score_news(conn, target_date, api_key=None)`
  - DuckDB 接続（prices_daily, raw_news, news_symbols, ai_scores テーブル）を渡して利用します。
- レジーム判定:
  - 関数: `kabusys.ai.regime_detector.score_regime(conn, target_date, api_key=None)`

注意:
- AI 呼び出しは外部 API への依存があり、失敗時は安全にフォールバック（多くのケースで 0.0 / neutral）する実装方針です。
- 実際のブローカー統合部分は Broker API の実装・設定が必要です（本リポジトリでは抽象化レイヤを提供）。

---

## 重要な設計上のポイント / 注意事項

- 環境切替:
  - KABUSYS_ENV により以下が切り替わります: development / paper_trading / live
  - paper_trading は本番 DB と完全に分離されます（PAPER_TRADING_SQLITE_PATH）。
- プロセス優先度:
  - 起動スクリプトは最初に set_process_priority("high") を呼びます。psutil の権限等で設定できない場合はログに警告が出ます。
- Kill Switch:
  - RiskMonitor 等の結果により KillSwitch が reason を書いた場合、ExecutionEngine はフラグファイルを検出して安全に停止できます。
- DB マイグレーション:
  - init_monitoring_db は冪等にスキーマを作成し、必要に応じてカラムを追加する簡易マイグレーション処理を含みます。
- DuckDB:
  - 研究（research）モジュールは DuckDB 接続を受け取り、prices_daily / raw_financials 等のテーブルを参照して計算を行います。DuckDB を事前に用意しておいてください。
- テスト / 自動読み込み:
  - config.Settings はプロジェクトルート（.git または pyproject.toml を基準）から .env を自動ロードします。自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

---

## ディレクトリ構成（抜粋）

- src/kabusys/
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
  - portfolio/
    - __init__.py
    - portfolio_builder.py
    - risk_adjustment.py
    - position_sizing.py
  - research/
    - __init__.py
    - factor_research.py
    - feature_exploration.py
  - monitoring/
    - __init__.py
    - monitoring_db.py
    - monitoring_engine.py
    - system_monitor.py
    - trade_monitor.py
    - risk_monitor.py
    - kill_switch.py
    - alert_manager.py
    - streamlit_dashboard.py
  - execution/
    - (OrderManager, OrderRepository, Reconciler 等の実装ファイル)
    - reconciler.py
    - order_manager.py
  - utils/
    - __init__.py
    - process_priority.py
  - research, data など他モジュール（prices_daily, raw_financials を使用）

主要ファイルの説明（短め）
- run_execution.py: ExecutionEngine の起動スクリプト。環境に応じてブローカー切替・専用 DB を使用。
- run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL で間隔変更可。
- monitoring_db.py: SQLite のテーブル作成 / MonitoringDB の読み書きラッパー。
- streamlit_dashboard.py: 監視データの可視化用ダッシュボード（Streamlit）。
- news_nlp.py / regime_detector.py: OpenAI を用いたニュース NLP / 市場レジーム判定。

---

## トラブルシューティング（よくある質問）

- DB が見つからない / 読み込みできない
  - run_monitoring や run_execution は起動時に DB ファイルを作成しますが、Streamlit ダッシュボードは読み取り専用で開くため、MonitoringEngine を先に起動して DB が存在・更新されていることを確認してください。
- OpenAI API 呼び出しで失敗が多い
  - 短時間に大量呼び出しを行うと RateLimitError が発生します。AI モジュールはリトライを組み込んでいますが、API キーやレート制限、ネットワーク状態を確認してください。
- プロセス優先度や CPU affinity の設定に失敗する
  - その場合は psutil の権限不足やプラットフォーム非対応が原因です。ログに警告が出ますが、実行自体は継続されます。
- Paper Trading でログが本番 DB に混入してしまった
  - PAPER_TRADING_SQLITE_PATH と KABUSYS_ENV=paper_trading の設定を確認してください。paper_trading は明示的に paper_sqlite_path を使う実装です。

---

必要に応じて README を拡張します。特にブローカー実装、DuckDB のテーブルスキーマ（prices_daily / raw_financials / raw_news など）、および実運用での監視・デプロイ手順（systemd / supervisor 等）を追記できます。どの情報を優先して追加しますか？