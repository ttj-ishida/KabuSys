KabuSys
=======

日本株向けの自動売買 / データ基盤ライブラリです。  
DuckDB をデータレイヤに用い、J‑Quants からのデータ取り込み、ニュースの収集・LLM によるニュースセンチメント、マーケットレジーム判定、ファクター計算、ETL パイプライン、監査ログ（発注／約定トレース）などを提供します。

特徴
----
- J‑Quants API 経由で株価・財務・カレンダーを差分取得・保存（ページネーション・リトライ・レート制御込み）
- RSS ベースのニュース収集と前処理（SSRF 対策・トラッキング除去・サイズ制限）
- OpenAI（gpt-4o-mini）を使ったニュース NLP（銘柄別センチメント）と市場レジーム判定
- DuckDB ベースの ETL パイプライン（差分取得・保存・品質チェック）
- データ品質チェック（欠損、スパイク、重複、日付不整合）
- 監査ログスキーマ（signal → order_request → execution のトレース用テーブル群）と初期化ユーティリティ
- 研究用ユーティリティ（ファクター計算、将来リターン、IC、Zスコア正規化 等）

必要条件
------
- Python 3.10+
- パッケージ（主な依存）
  - duckdb
  - openai
  - defusedxml
  - （その他標準ライブラリのみで多くの処理を実装）

セットアップ
---------

1. リポジトリをクローンし、仮想環境を作成します（例: venv）。

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. 必要パッケージをインストールします（setup.cfg / pyproject.toml がある場合はそれに従ってください）。最低限:

   ```bash
   pip install duckdb openai defusedxml
   ```

   開発用にはその他 linters / test ライブラリなどを追加してください。

3. パッケージを開発モードでインストール（任意）:

   ```bash
   pip install -e .
   ```

環境変数 / 設定
----------------
このパッケージは環境変数またはプロジェクトルートの .env / .env.local を自動読み込みします（自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定）。

主要な環境変数（.env 例）
- JQUANTS_REFRESH_TOKEN : J‑Quants のリフレッシュトークン（必須）
- KABU_API_PASSWORD     : kabu ステーション API パスワード（必須）
- KABU_API_BASE_URL     : kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN       : Slack Bot Token（必須）
- SLACK_CHANNEL_ID      : Slack Channel ID（必須）
- OPENAI_API_KEY        : OpenAI API キー（score_news / regime 判定に使用）
- DUCKDB_PATH           : DuckDB ファイルパス（既定: data/kabusys.duckdb）
- SQLITE_PATH           : SQLite（監視用）パス（既定: data/monitoring.db）
- KABUSYS_ENV           : 環境 (development | paper_trading | live)
- LOG_LEVEL             : ログレベル (DEBUG, INFO, WARNING, ...)

使い方（主要 API / ユーティリティ例）
------------------------------

以下はライブラリとしての呼び出し例です。実行はアプリケーション側で適宜ラップしてください。

- DuckDB 接続を作って ETL を日次で実行する

  ```python
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を作成して ai_scores テーブルへ書き込む

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  count = score_news(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  print(f"書き込んだ銘柄数: {count}")
  ```

- マーケットレジームを判定して market_regime テーブルへ保存する

  ```python
  from datetime import date
  import duckdb
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key="sk-...")
  ```

- 監査ログ用 DuckDB を初期化する（order/signals/executions 用スキーマ作成）

  ```python
  from kabusys.data.audit import init_audit_db
  conn = init_audit_db("data/audit.duckdb")
  ```

- RSS を取得する（ニュースコレクタのユーティリティ）

  ```python
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  articles = fetch_rss(DEFAULT_RSS_SOURCES["yahoo_finance"], source="yahoo_finance")
  for a in articles:
      print(a["id"], a["datetime"], a["title"])
  ```

補足 / 動作設計のポイント
-----------------------
- Look-ahead バイアス対策: 多くの関数は datetime.today() を内部で参照しないよう設計されています。バックテスト等では target_date を明示的に与えてください。
- API リトライ / フェイルセーフ: OpenAI / J‑Quants の呼び出しはリトライとフォールバック（失敗時に安全なデフォルト値を使用）を備えています。
- ETL の品質チェックは Fail-Fast ではなく、問題を全件収集して呼び出し元で対応を決められるようにしています。
- news_collector は SSRF / XML BOM 等のセキュリティ考慮（スキーム検証、プライベート IP 拒否、defusedxml 利用、最大レスポンスサイズ制限）を含みます。

ディレクトリ構成（主要ファイル）
------------------------------
src/kabusys/
- __init__.py — パッケージ定義・バージョン
- config.py — 環境変数 / 設定管理（.env の自動読み込み、settings オブジェクト）
- ai/
  - __init__.py
  - news_nlp.py — ニュース NLP（銘柄別センチメント算出）
  - regime_detector.py — マーケットレジーム判定（ETF 1321 MA200 + マクロセンチメント）
- data/
  - __init__.py
  - calendar_management.py — 市場カレンダー管理（営業日判定等）
  - etl.py — ETL インターフェースエクスポート
  - pipeline.py — 日次 ETL パイプライン（prices/financials/calendar + 品質チェック）
  - stats.py — 汎用統計（Zスコア等）
  - quality.py — データ品質チェック（欠損・スパイク・重複・日付不整合）
  - audit.py — 監査ログスキーマと初期化ユーティリティ
  - jquants_client.py — J‑Quants API クライアント（取得 / 保存関数）
  - news_collector.py — RSS ニュース収集・前処理
- research/
  - __init__.py
  - factor_research.py — Momentum/Value/Volatility 等のファクター計算
  - feature_exploration.py — 将来リターン / IC / 統計サマリー 等

利用上の注意
------------
- OpenAI API を利用する箇所は API 利用料が発生します。バッチサイズやモデル選択を運用ポリシーに合わせて調整してください。
- J‑Quants API はレート制限があります（このクライアントは固定間隔スロットリングで保護していますが、キーの権限・使用料はご自身で管理してください）。
- 本パッケージ自体は発注ロジック（実際の send/receive）とブローカー固有実装を含みません。発注実装は execution 層（execution モジュール等）や運用アダプタ側で実装してください。
- 本 README に記載のコード例はライブラリを直接呼び出す最小例です。実運用ではログ設定、エラーハンドリング、ジョブスケジューラや監視を整備してください。

貢献
----
バグ報告・改善提案は Issue を開いてください。Pull Request 前に Issue を立てて設計方針を相談いただけるとスムーズです。

ライセンス
--------
リポジトリ内の LICENSE を参照してください。

---

README の補足や、特定の使い方（例えば ETL の Cron 設定例、運用時の Slack 通知の組み込み方、kabu API 発注のサンプル実装など）が必要であれば、目的に合わせた例を追加で作成します。どの部分の詳細を優先してほしいか教えてください。