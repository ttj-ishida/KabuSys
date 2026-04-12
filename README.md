# KabuSys

日本株の自動売買プラットフォーム（モジュール群）の簡易 README。  
このリポジトリは、取引エンジン（ExecutionEngine）、監視（MonitoringEngine）、ポートフォリオ構築、リサーチ、AI（ニュースセンチメント・レジーム判定）などのコンポーネントを含みます。

---

## 概要

KabuSys は日本株自動売買システムのコンポーネント群です。個別モジュールは独立性を保ちつつ、実運用に必要な以下の機能を提供します。

- 注文生成・送信・状態管理（OrderManager / ExecutionEngine）
- 発注リコンシリエーション（Reconciler）
- リスク管理（RiskManager / RiskMonitor）
- 監視・アラート（MonitoringEngine / AlertManager）
- Paper Trading（実運用と分離された SQLite DB を使用）
- ポートフォリオ構築（候補選定、重み計算、ポジションサイズ計算）
- リサーチ（ファクター計算、前方リターン、IC計算 等）
- ニュース NLP（OpenAI を用いた銘柄センチメント算出）
- レジーム検出（ETF の MA とマクロセンチメントの合成）
- Streamlit による簡易監視ダッシュボード
- 各種ツール（Paper Trading 検証レポート生成 等）

---

## 主な機能一覧

- execution:
  - 注文作成 / 送信 / 同期（OrderManager, OrderRepository, Reconciler）
  - Broker クライアントを切り替え（実口座 / モック）
- monitoring:
  - システム状態監視（CPU, メモリ, ディスク, プロセス生存）
  - 注文滞留・約定異常チェック
  - ドローダウン・ポジション上限の監視と kill.flag 発動
  - LINE へのアラート送信（AlertManager）
  - Streamlit ダッシュボード
- portfolio:
  - 候補選定（score / rank ベース）
  - 重み計算（等分配・スコア加重）
  - ポジションサイズ計算（単元丸め・利用可能資金に対するスケール）
  - セクター制限・レジーム乗数
- research:
  - Momentum / Volatility / Value ファクター計算（DuckDB を利用）
  - 将来リターン計算、IC（Spearman）計算、統計サマリ
- ai:
  - ニュース記事を LLM に渡して銘柄別センチメントを算出・書込
  - マクロニュース + ETF MA による市場レジーム判定
- tools:
  - Paper Trading の検証レポート生成スクリプト

---

## 要件

- Python 3.10 以上（PEP 604 の型記法などを使用）
- 必須パッケージ（代表例、実際は requirements.txt を用意してください）:
  - duckdb
  - psutil
  - requests
  - openai
  - streamlit
- SQLite（組み込み）
- ネットワーク接続（LINE / OpenAI を利用する場合）

例（pip インストール）:
```
python -m venv .venv
source .venv/bin/activate
pip install duckdb psutil requests openai streamlit
```

---

## セットアップ手順

1. リポジトリをクローンして作業ディレクトリへ移動
2. 仮想環境を作成・有効化
3. 必要パッケージをインストール（上記参照）
4. 環境変数を設定（.env ファイル推奨）

Settings（環境変数）について:
- 自動でプロジェクトルートの `.env` と `.env.local` をロードします（OS 環境変数が優先）。
- 自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

主要な環境変数（デフォルト値はコード参照）:
- KABUSYS_ENV: "development" | "paper_trading" | "live"（デフォルト: development）
- JQUANTS_REFRESH_TOKEN: （必須）
- KABU_API_PASSWORD: （必須）
- KABU_API_BASE_URL: デフォルト "http://localhost:18080/kabusapi"
- OPENAI_API_KEY: OpenAI を使う場合に必要
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: AlertManager（LINE）を使う場合
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- PID_FILE_PATH: data/execution.pid
- KILL_FLAG_PATH: data/kill.flag
- MONITOR_POLL_INTERVAL: 監視ポーリング間隔（秒、デフォルト 60）

例 .env:
```
KABUSYS_ENV=paper_trading
OPENAI_API_KEY=sk-...
JQUANTS_REFRESH_TOKEN=...
KABU_API_PASSWORD=secret
PAPER_TRADING_SQLITE_PATH=data/paper_trading.db
```

---

## 使い方（主要スクリプト）

各スクリプトはモジュールとして直接起動できます（例: python -m kabusys.run_execution）。

- ExecutionEngine の起動（本番/ペーパーを Settings.env で切替）
```
python -m kabusys.run_execution
```
挙動:
- KABUSYS_ENV=paper_trading のときは MockBrokerClient を使用し、paper_trading 専用 DB（PAPER_TRADING_SQLITE_PATH）に記録され本番 DB とは分離されます。
- プロセス優先度を "high" に設定し、DuckDB / SQLite に接続します。
- 起動時に監視テーブル（monitoring DB）の初期化を実行します（冪等）。

- MonitoringEngine の起動
```
python -m kabusys.run_monitoring
```
オプション:
- MONITOR_POLL_INTERVAL 環境変数でポーリング間隔（秒）を上書き可能（デフォルト 60 秒）。
挙動:
- 常に本番の sqlite_path（Settings.sqlite_path）を使って監視ログを永続化します（KABUSYS_ENV に依らず）。

- Streamlit ダッシュボード（監視 DB を読み取り専用で開く）
```
streamlit run src/kabusys/monitoring/streamlit_dashboard.py -- --db data/monitoring.db
```

- Paper Trading 検証レポート生成ツール
```
python -m kabusys.tools.paper_verification_report --from 2026-04-01 --to 2026-04-11
# または DB を直接指定
python -m kabusys.tools.paper_verification_report --db /path/to/data/paper_trading.db
```

- AI（ニューススコア / レジーム判定）
  - ライブラリ API を直接呼び出すことを想定しています（例: Python REPL 或いはジョブから）。
  - 例:
    ```
    from datetime import date
    import duckdb
    from kabusys.ai.news_nlp import score_news
    conn = duckdb.connect("data/kabusys.duckdb")
    score_news(conn, date(2026, 4, 10), api_key="sk-...")
    ```
  - OpenAI API キーが未設定の場合は例外が発生します。API 呼び出しはリトライ・フォールバックの仕組みがあります。

---

## 注意点 / 実運用メモ

- Paper Trading モードは本番 DB と完全分離される設計です（PAPER_TRADING_SQLITE_PATH を使用）。
- Settings は自動的に .env / .env.local をプロジェクトルートからロードします（OS 環境変数が優先）。
- Monitoring は常に本番 sqlite_path を使用します（監視ログは運用 DB と共有する想定）。
- Process priority／CPU affinity の設定はプラットフォーム依存であり、権限不足時は警告でスキップされます。
- kill.flag による停止シグナル: KillSwitch は kill.flag を生成し ExecutionEngine に停止指示を行います。ExecutionEngine 側は起動時に kill flag のクリア設定等を行うオプションがあります（Settings.kill_flag_clear_on_start を参照）。
- DuckDB を用いたリサーチ・AI コンポーネントはデータテーブル（prices_daily / raw_financials / raw_news 等）を参照します。データの投入は別プロセス（ETL）を想定しています。
- OpenAI 呼び出しは JSON mode を使用し、レスポンスのバリデーションを厳格に行います。レート制限やネットワークエラーはエクスポネンシャルバックオフでリトライします。

---

## ディレクトリ構成

（プロジェクトルートに `src/kabusys` を想定）

- src/
  - kabusys/
    - __init__.py
    - config.py                 — 環境変数/設定管理
    - run_execution.py          — ExecutionEngine 起動スクリプト
    - run_monitoring.py         — SystemMonitor ポーリング起動スクリプト
    - tools/
      - __init__.py
      - paper_verification_report.py  — Paper Trading レポート生成ツール
    - portfolio/
      - __init__.py
      - portfolio_builder.py
      - position_sizing.py
      - risk_adjustment.py
    - research/
      - __init__.py
      - factor_research.py
      - feature_exploration.py
    - ai/
      - __init__.py
      - news_nlp.py             — ニュース NLP（OpenAI）処理
      - regime_detector.py      — レジーム判定（MA + マクロセンチメント）
    - monitoring/
      - __init__.py
      - monitoring_db.py        — SQLite スキーマ / ラッパー
      - system_monitor.py
      - trade_monitor.py
      - risk_monitor.py
      - monitoring_engine.py
      - alert_manager.py
      - kill_switch.py
      - streamlit_dashboard.py
    - execution/
      - (多くのファイルが存在; OrderManager, Reconciler, etc.)
      - order_manager.py
      - reconciler.py
      - order_repository.py (参照)
      - execution_engine.py (参照)
    - utils/
      - __init__.py
      - process_priority.py
    - data/
      - (DuckDB / ETL 関連モジュールがここから参照される)

---

## 開発者向け補足

- DB 初期化: monitoring のテーブルは init_monitoring_db() により自動作成され、マイグレーション（列追加）も含みます。
- DuckDB クエリは接続オブジェクトを受け取り純粋関数で計算結果を返します（テストがしやすい設計）。
- LLM（OpenAI）呼び出しはモジュール内でラップされており、テスト時は該当関数をモックしてください（_call_openai_api を patch 可能）。
- 型ヒントと pure function を重視しており、ユニットテストが書きやすい構造になっています。

---

必要があれば、以下について追記できます:
- 具体的な requirements.txt (推奨バージョン)
- 実際の BrokerClient の切り替え・設定方法
- テーブルスキーマ（DuckDB の prices_daily / raw_financials / raw_news など）
- よくある運用手順（デプロイ / systemd / コンテナ化）

ご希望があれば上記のいずれかを詳細化します。