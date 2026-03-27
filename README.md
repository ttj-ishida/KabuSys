# KabuSys

日本株向けのデータ基盤・リサーチ・AI支援・監査ログを備えた自動売買補助ライブラリです。  
本リポジトリは ETL（J-Quants）→ データ品質チェック → 研究用ファクター計算 → AI ニュースセンチメント → 市場レジーム判定 → 監査ログの一連機能を提供します。

---

## 主な特徴（機能一覧）

- データ取得・ETL
  - J-Quants API から株価（日足）、財務データ、JPXカレンダーを差分取得し DuckDB に冪等保存
  - 差分更新・バックフィル・ページネーション・トークン自動リフレッシュ・レート制御・リトライ対応

- データ品質チェック
  - 欠損（OHLC）・主キー重複・前日比スパイク・日付不整合（未来日・非営業日）検出
  - QualityIssue オブジェクトとして詳細を収集

- ニュース収集 / NLP（AI）
  - RSS 取得（SSRF対策、トラッキングパラメータ除去、gzipサイズ制限）
  - OpenAI（gpt-4o-mini）を用いた銘柄別ニュースセンチメント（ai_scores テーブルへ）生成
  - マクロニュースと ETF（1321）の MA200 乖離を合成した市場レジーム判定（bull/neutral/bear）

- リサーチ支援
  - Momentum / Volatility / Value 等のファクター計算
  - 将来リターン計算、IC（Spearman）や統計サマリー、Zスコア正規化

- 監査ログ（トレーサビリティ）
  - signal_events / order_requests / executions などの監査テーブル定義と初期化ユーティリティ
  - UUID を用いた冪等・トレース可能な設計

- ユーティリティ
  - カレンダー管理（営業日判定、next/prev trading day）
  - DuckDB 用スキーマ初期化 / audit DB 作成

---

## 要求環境 / 依存

- Python 3.10 以上（型ヒントに新しい構文を使用）
- 依存パッケージ（少なくとも以下をインストールしてください）
  - duckdb
  - openai
  - defusedxml

（プロジェクトの packaging/requirements.txt がある場合はそちらを優先してください）

---

## 環境変数（主なもの）

設定は環境変数またはプロジェクトルートの `.env` / `.env.local` から自動ロードされます（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。優先順位は OS 環境 > .env.local > .env です。

主要な環境変数（使用する機能に応じて設定してください）:

- JQUANTS_REFRESH_TOKEN: J-Quants リフレッシュトークン（ETL / jquants_client 用）
- OPENAI_API_KEY: OpenAI API キー（AI スコアリング用）
- KABU_API_PASSWORD: kabuステーション API パスワード（発注連携等）
- KABU_API_BASE_URL: kabu API のベース URL（省略時: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用（本コードベース内で参照）
- DUCKDB_PATH: デフォルト DuckDB パス（例: data/kabusys.duckdb）
- SQLITE_PATH: 監視用 SQLite（例: data/monitoring.db）
- KABUSYS_ENV: 開発モード（development / paper_trading / live）
- LOG_LEVEL: ログレベル（DEBUG/INFO/WARNING/ERROR/CRITICAL）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env ロードを無効化する場合は `1`

.env ファイルのパースはシェル風（export 付き行やクォート、行内コメント等）をサポートします。

---

## セットアップ手順

1. リポジトリをクローン
   ```
   git clone <repo-url>
   cd <repo>
   ```

2. Python 仮想環境の作成（任意）
   ```
   python -m venv .venv
   source .venv/bin/activate
   ```

3. 依存インストール
   - 最小:
     ```
     pip install duckdb openai defusedxml
     ```
   - 開発 / パッケージ化されている場合:
     ```
     pip install -e .
     ```

4. 環境変数設定
   - プロジェクトルートに `.env` を作成（.env.example を参照、存在しない場合は手動で設定）
   - 例:
     ```
     JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
     OPENAI_API_KEY=sk-...
     DUCKDB_PATH=data/kabusys.duckdb
     KABUSYS_ENV=development
     LOG_LEVEL=INFO
     ```
   - テスト中に自動ロードを無効にする場合:
     ```
     export KABUSYS_DISABLE_AUTO_ENV_LOAD=1
     ```

5. DuckDB の初期化（監査ログ用 DB を用意する場合）
   ```py
   from kabusys.data.audit import init_audit_db
   conn = init_audit_db("data/audit.duckdb")  # または ":memory:"
   conn.close()
   ```

---

## 使い方（代表的な API と実行例）

以下は主要ユースケースの最小例です。実行前に必要な環境変数（API キー等）を設定してください。

- DuckDB に接続して日次 ETL を実行する
  ```py
  import duckdb
  from datetime import date
  from kabusys.data.pipeline import run_daily_etl

  conn = duckdb.connect("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date(2026, 3, 20))
  print(result.to_dict())
  ```

- ニュースセンチメント（銘柄別）を生成する（OpenAI API が必要）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.news_nlp import score_news

  conn = duckdb.connect("data/kabusys.duckdb")
  written = score_news(conn, target_date=date(2026, 3, 20), api_key=None)  # None の場合は OPENAI_API_KEY を参照
  print("書き込み銘柄数:", written)
  ```

- 市場レジーム判定（ETF 1321 の MA200 とマクロニュースを合成）
  ```py
  import duckdb
  from datetime import date
  from kabusys.ai.regime_detector import score_regime

  conn = duckdb.connect("data/kabusys.duckdb")
  score_regime(conn, target_date=date(2026, 3, 20), api_key=None)
  ```

- RSS を取得して記事一覧を得る（news_collector）
  ```py
  from kabusys.data.news_collector import fetch_rss, DEFAULT_RSS_SOURCES

  url = DEFAULT_RSS_SOURCES["yahoo_finance"]
  articles = fetch_rss(url, source="yahoo_finance")
  for a in articles[:5]:
      print(a["id"], a["datetime"], a["title"])
  ```

- 監査ログスキーマを初期化する
  ```py
  import duckdb
  from kabusys.data.audit import init_audit_schema

  conn = duckdb.connect("data/kabusys.duckdb")
  init_audit_schema(conn, transactional=True)
  ```

注意:
- score_news / score_regime など OpenAI を呼ぶ関数は API キーが必須です。api_key 引数を渡すか環境変数 OPENAI_API_KEY を設定してください。
- jquants_client の ETL は J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）が必要です。

---

## 主要モジュール（概要）

- kabusys.config
  - 環境変数・設定管理、自動 .env ロード、Settings クラス

- kabusys.data
  - jquants_client.py: J-Quants API クライアント（取得・保存機能）
  - pipeline.py / etl.py: 日次 ETL 実行、個別 ETL（prices/financials/calendar）
  - quality.py: データ品質チェック（欠損・スパイク・重複・日付不整合）
  - news_collector.py: RSS 取得・前処理・記事 ID 正規化（SSRF 対策等）
  - calendar_management.py: 市場カレンダー管理・営業日判定
  - audit.py: 監査ログテーブル定義・初期化ユーティリティ
  - stats.py: 汎用統計ユーティリティ（Zスコア正規化）
  - pipeline.ETLResult: ETL 実行結果データ構造

- kabusys.ai
  - news_nlp.py: 銘柄別ニュースセンチメント（OpenAI 呼び出し、バッチ処理、検証）
  - regime_detector.py: ETF(1321) MA200 とマクロセンチメントを合成して市場レジーム判定

- kabusys.research
  - factor_research.py: Momentum / Volatility / Value 等のファクター計算
  - feature_exploration.py: 将来リターン計算、IC（Spearman）計算、統計サマリー、ランク関数

- その他
  - パッケージ初期化やエクスポート用の __init__.py が各サブパッケージに存在します。

ディレクトリ（主なファイル）
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ ai/
│  ├─ __init__.py
│  ├─ news_nlp.py
│  └─ regime_detector.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ pipeline.py
│  ├─ etl.py
│  ├─ quality.py
│  ├─ news_collector.py
│  ├─ calendar_management.py
│  ├─ audit.py
│  └─ stats.py
├─ research/
│  ├─ __init__.py
│  ├─ factor_research.py
│  └─ feature_exploration.py
└─ research/
```

---

## 実運用における注意点 / 設計方針のポイント

- Look-ahead バイアス回避: バックテストに使う場合、関数群は内部で datetime.today() を参照しないか、明示的な target_date を用いる設計です。ETL / スコアリングの呼び出し時は必ず target_date を意識してください。
- 冪等性: J-Quants → DuckDB の保存は ON CONFLICT で上書きすることで冪等に設計されています。
- フェイルセーフ: AI/API 失敗時は多くの処理でスコアを 0 にフォールバックする、あるいは処理をスキップして他部分は継続する設計です。
- セキュリティ: RSS 取得は SSRF 回避のためホスト/IP 検査、リダイレクト検査、レスポンスサイズ制限、defusedxml の使用などを行っています。
- ログと監視: ログ出力（LOG_LEVEL）を設定し、ETL 結果は ETLResult として外部に渡せます。Slack 連携等は別モジュールで実装を推奨します。

---

## 開発 / テスト

- ユニットテスト作成時は環境変数自動ロードを無効化して（KABUSYS_DISABLE_AUTO_ENV_LOAD=1）、必要な設定をテスト側で注入してください。
- OpenAI 呼び出しや外部 HTTP はモック化（unittest.mock.patch）可能です。news_nlp、regime_detector の _call_openai_api を差し替えてテストを行ってください。
- DuckDB はインメモリ（":memory:"）で簡単にテストできます。

---

必要に応じて README をプロジェクトの実際のパッケージング情報（requirements, setup, .env.example）に合わせて調整してください。追加で「操作フロー図」や「DB スキーマ定義の詳細」を記載することも可能です。必要であれば教えてください。