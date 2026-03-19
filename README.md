# KabuSys

日本株向けの自動売買プラットフォームのライブラリ群（部分実装）。  
データ収集（J-Quants）、DuckDB ベースのデータレイク、特徴量生成、ETL パイプライン、ニュース収集、監査ログなどを含むモジュール群を提供します。

> 注意: このリポジトリはフルプロダクトではなく、ライブラリ／モジュール群の抜粋実装です。実行には外部 API キーや環境設定、DuckDB 等が必要です。

## 主な機能（機能一覧）

- 環境設定管理
  - .env / .env.local を自動読み込み（プロジェクトルート基準）、必須値チェック
  - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能

- データ取得・保存（J-Quants）
  - 株価日足（OHLCV）・決算（四半期）・JPX カレンダーの取得（ページネーション対応）
  - レート制御（120 req/min）、リトライ・トークン自動リフレッシュ実装
  - DuckDB へ冪等保存（ON CONFLICT / DO UPDATE）

- ETL（データパイプライン）
  - 差分更新（最終取得日ベース）とバックフィル（後出し修正を吸収）
  - 市場カレンダー先読み、株価・財務データの差分取得保存
  - 品質チェック連携（欠損、スパイク、重複、日付不整合検出）

- データ品質チェック
  - 欠損（OHLC）検出、前日比スパイク検出、主キー重複、将来日付・非営業日データ検出
  - 問題は QualityIssue オブジェクトとしてまとめ取得可能

- ニュース収集
  - RSS フィード取得、XML パース（defusedxml）で安全に処理
  - URL 正規化・トラッキング除去・記事ID生成（SHA-256）
  - SSRF 対策（スキーム検証、プライベートホスト検出）、サイズ上限、gzip 対応
  - DuckDB へ冪等保存（raw_news / news_symbols）

- 研究用ユーティリティ（Research）
  - Momentum / Volatility / Value 等のファクター計算（prices_daily / raw_financials を参照）
  - 将来リターン計算、IC（Spearman）算出、ファクター統計サマリ
  - Zスコア正規化ユーティリティ（data.stats）

- スキーマ・監査ログ
  - DuckDB 用スキーマ定義（Raw / Processed / Feature / Execution / Audit）
  - 監査ログ（signal_events / order_requests / executions）用の初期化関数

## 必要条件

- Python 3.10+
  - typing の `X | Y` 構文を利用しているため 3.10 以上が必要です
- 必須パッケージ（例）
  - duckdb
  - defusedxml

（プロジェクトに requirements.txt がない場合は上記をインストールしてください）

例:
```bash
python -m venv .venv
source .venv/bin/activate
pip install duckdb defusedxml
# そのほかプロジェクトに応じて必要なパッケージを追加
```

## 環境変数（主要な設定項目）

Settings クラス（kabusys.config.settings）で参照される主要な環境変数:

- JQUANTS_REFRESH_TOKEN (必須) — J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) — kabuステーション API のパスワード
- KABU_API_BASE_URL — kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN (必須) — Slack 通知用 Bot トークン
- SLACK_CHANNEL_ID (必須) — Slack チャンネル ID
- DUCKDB_PATH — デフォルト DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH — 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV — "development" / "paper_trading" / "live"（デフォルト: development）
- LOG_LEVEL — "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL"（デフォルト: INFO）

自動 .env 読み込みはプロジェクトルートの `.env` と `.env.local` を対象に行われます。テストなどで無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

## セットアップ手順

1. リポジトリをクローン
   ```bash
   git clone <このリポジトリのURL>
   cd <repo>
   ```

2. Python 仮想環境を作成して有効化
   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   ```

3. 依存パッケージをインストール
   ```bash
   pip install duckdb defusedxml
   # プロジェクトで他に必要なパッケージがあれば追加
   ```

4. 環境変数を設定（.env をプロジェクトルートに作成）
   例: .env
   ```
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. DuckDB スキーマ初期化
   Python REPL かスクリプトで:
   ```python
   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")   # ディレクトリがなければ自動で作成
   ```

6. 監査DB（任意）
   ```python
   from kabusys.data.audit import init_audit_db
   conn_audit = init_audit_db("data/audit.duckdb")
   ```

## 使い方（簡単な例）

- 日次 ETL を実行する（パイプライン）
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

- ニュース収集ジョブを実行する
  ```python
  from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")

  # known_codes を渡すと記事と銘柄の紐付けを行う（例: 上場銘柄コードセット）
  known_codes = {"7203", "6758", "9984"}
  stats = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
  print(stats)
  ```

- J-Quants データを直接フェッチして保存する
  ```python
  import duckdb
  from kabusys.data.jquants_client import fetch_daily_quotes, save_daily_quotes
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  records = fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = save_daily_quotes(conn, records)
  print("saved", saved)
  ```

- 研究用ファクター計算
  ```python
  from kabusys.research import calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, zscore_normalize
  from kabusys.data.schema import init_schema
  from datetime import date

  conn = init_schema("data/kabusys.duckdb")
  target = date(2024, 1, 31)

  mom = calc_momentum(conn, target)
  vol = calc_volatility(conn, target)
  val = calc_value(conn, target)
  fwd = calc_forward_returns(conn, target)
  # 例: calc_ic を呼ぶには factor_records と forward_records を code でマッチさせて渡す
  ```

- Zスコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(mom, ["mom_1m", "mom_3m", "ma200_dev"])
  ```

## 主要モジュール・ディレクトリ構成（概要）

以下はソース配下の主要ファイル／モジュールです（抜粋）。

- src/kabusys/
  - __init__.py
  - config.py                — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py      — J-Quants API クライアント（取得＋DuckDB 保存）
    - news_collector.py      — RSS ニュース収集・正規化・保存
    - schema.py              — DuckDB スキーマ定義・初期化
    - stats.py               — 統計ユーティリティ（zscore_normalize 等）
    - pipeline.py            — ETL パイプライン（run_daily_etl 等）
    - quality.py             — データ品質チェック
    - calendar_management.py — 市場カレンダー管理（営業日判定等）
    - audit.py               — 監査ログスキーマ初期化
    - features.py            — 特徴量関連の公開インターフェース
    - etl.py                 — ETL 結果クラスの再公開
  - research/
    - __init__.py
    - factor_research.py     — Momentum/Volatility/Value 等の計算
    - feature_exploration.py — 将来リターン計算・IC・統計サマリ
  - strategy/                 — (空のパッケージ: 戦略実装を置く)
  - execution/                — (空のパッケージ: 発注/約定ロジックを置く)
  - monitoring/               — (空のパッケージ: 監視用機能を置く)

（上記はリポジトリ内ファイルを抜粋した構成説明です）

## 設計上の注意点 / 実行時の注意

- DuckDB の INSERT 文は多くの箇所で ON CONFLICT を利用し冪等性を担保していますが、外部の直接書き込み等によりデータ不整合が生じる可能性があります。品質チェックを定期的に実行してください（data.quality.run_all_checks）。
- J-Quants API 呼び出しはモジュール単位でレート制御を行います。複数プロセスで API を叩く場合は全体レートに注意してください。
- ニュース収集においては RSS の構造差異やエンコーディング差異によりパースに失敗することがあります。fetch_rss は失敗時に空リストを返すなどの保護を行います。
- 本リポジトリ内の戦略・発注モジュールはサンプル実装が中心であり、実運用前の十分なテストとリスク管理ルール（マネージャ層・資金管理・監査）を必ず追加してください。

## 開発 / 貢献について

- コードの拡張（戦略、発注連携、モニタリング等）歓迎します。Pull Request の際は単体テストと簡単な説明を添えてください。
- 大きな設計変更や外部インタフェース変更は事前に Issue で議論してください。

## ライセンス

リポジトリにライセンス情報がない場合は、利用前にライセンスを明確にしてください。商用利用や再配布の際は権利関係に注意してください。

---

質問や README に追記してほしい点があれば教えてください。使用例の追加や設定の雛形（.env.example）も作成できます。