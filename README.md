# KabuSys

日本株自動売買プラットフォームのコアライブラリ（モジュール群）。  
データ取得（J-Quants）、DuckDB を用いたデータ基盤、ETL パイプライン、特徴量生成、リサーチ用ユーティリティ、ニュース収集、監査ログなどを提供します。

---

## プロジェクト概要

KabuSys は日本株の自動売買システムに必要なデータ基盤とユーティリティ群を提供する Python パッケージです。  
主な役割は以下です。

- J-Quants API を使った市場データ（株価・財務・カレンダー等）の取得と DuckDB への冪等保存
- DuckDB ベースのスキーマ定義・初期化
- ETL（差分取得・バックフィル・品質チェック）パイプライン
- RSS ベースのニュース収集と銘柄紐付け
- 戦略リサーチ用のファクター計算（モメンタム・ボラティリティ・バリュー等）および IC / 統計サマリ
- 発注監査ログ（order_requests / executions 等）の初期化ユーティリティ
- 簡単な統計ユーティリティ（Zスコア正規化等）

設計方針としては、外部 API 呼び出しの取り扱い（レート制限・リトライ・トークン更新）、DuckDB による冪等保存、Look-ahead バイアスへの配慮（fetched_at 記録）、およびテスト容易性を重視しています。

---

## 機能一覧

- 環境設定読み込み（.env / .env.local / OS 環境変数、自動ロード・無効化可）
- J-Quants クライアント
  - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - save_daily_quotes, save_financial_statements, save_market_calendar（冪等）
  - レートリミット制御・リトライ・トークン自動リフレッシュ実装
- DuckDB スキーマ管理
  - init_schema(db_path): 全テーブル（Raw / Processed / Feature / Execution）を作成
  - get_connection(db_path)
- ETL パイプライン
  - run_daily_etl(conn, ...): カレンダー → 株価 → 財務 → 品質チェック の一括処理
  - run_prices_etl / run_financials_etl / run_calendar_etl: 個別 ETL
  - ETLResult: ETL 結果オブジェクト
- データ品質チェック
  - 欠損・スパイク・重複・日付不整合の検出（QualityIssue を返す）
- ニュース収集
  - RSS 取得（SSRF 対策・gzip 制限・XML 安全パーサ）
  - 記事正規化・ID 生成（sha256 先頭）・raw_news への冪等保存
  - 銘柄コード抽出（known_codes フィルタ）
- リサーチ / ファクター計算
  - calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials 参照）
  - calc_forward_returns, calc_ic（Spearman ρ）, factor_summary
  - zscore_normalize（data.stats）
- 監査ログ（audit）
  - init_audit_schema / init_audit_db: 発注→約定までを追跡する監査テーブルを作成

---

## セットアップ手順

以下は最小構成の手順例です。環境に応じて適宜調整してください。

1. Python 仮想環境を作成・有効化（例: venv）
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows (PowerShell)
   ```

2. 必要なパッケージをインストール  
   主要依存（最小）:
   - duckdb
   - defusedxml

   例:
   ```bash
   pip install duckdb defusedxml
   ```

   実運用では requests 等の追加ライブラリや slack クライアント、kabu API 用の依存が必要になる可能性があります。プロダクション用 requirements.txt を用意している場合はそれを使用してください。

3. 環境変数を設定（.env をプロジェクトルートに置くことを推奨）  
   self-hosted の自動 .env ロード挙動:
   - プロジェクトルートは .git または pyproject.toml を基準に自動検出され、.env, .env.local が順に読み込まれます。
   - 無効化する場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   主な環境変数:
   - JQUANTS_REFRESH_TOKEN: J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD: kabuステーション API パスワード（必須）
   - KABU_API_BASE_URL: kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - SLACK_BOT_TOKEN: Slack ボットトークン（必須）
   - SLACK_CHANNEL_ID: Slack 通知先チャンネル ID（必須）
   - DUCKDB_PATH: DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH: 監視用 SQLite パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV: 実行環境 (development | paper_trading | live)、デフォルト development
   - LOG_LEVEL: ログレベル (DEBUG | INFO | ...)、デフォルト INFO

   例 .env（参考）:
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C12345678
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG
   ```

4. DuckDB スキーマを初期化
   ```bash
   python -c "from kabusys.data.schema import init_schema; init_schema('data/kabusys.duckdb')"
   ```

5. （監査専用 DB を分けて使う場合）監査ログ DB 初期化
   ```bash
   python -c "from kabusys.data.audit import init_audit_db; init_audit_db('data/audit.duckdb')"
   ```

---

## 使い方（主要ユースケース）

以下は主要な操作のサンプルです。

- DuckDB へ接続して日次 ETL を実行する
  ```python
  from datetime import date
  import duckdb
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  # 初期化済み DB へ接続（未初期化なら init_schema で作成）
  conn = init_schema('data/kabusys.duckdb')

  # 日次 ETL を実行（引数省略で今日）
  result = run_daily_etl(conn)
  print(result.to_dict())
  ```

- 個別 ETL（株価のみ）
  ```python
  from kabusys.data.pipeline import run_prices_etl
  from datetime import date
  import duckdb

  conn = duckdb.connect('data/kabusys.duckdb')
  fetched, saved = run_prices_etl(conn, target_date=date.today())
  print(f"fetched={fetched}, saved={saved}")
  ```

- ニュース収集ジョブ実行（既知銘柄リストと紐付け）
  ```python
  from kabusys.data.news_collector import run_news_collection
  import duckdb

  conn = duckdb.connect('data/kabusys.duckdb')
  known_codes = {'7203', '6758'}  # 例: トヨタ・ソニー等
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)
  ```

- リサーチ / ファクター計算（DuckDB 接続と target_date が必要）
  ```python
  from kabusys.research import calc_momentum, calc_forward_returns, calc_ic, zscore_normalize
  import duckdb
  from datetime import date

  conn = duckdb.connect('data/kabusys.duckdb')
  target = date(2024, 12, 31)

  momentum = calc_momentum(conn, target)
  forwards = calc_forward_returns(conn, target, horizons=[1,5,21])

  # 例: mom_1m と fwd_1d の IC を計算
  ic = calc_ic(momentum, forwards, factor_col='mom_1m', return_col='fwd_1d')
  print('IC (mom_1m vs fwd_1d) =', ic)
  ```

- Zスコア正規化
  ```python
  from kabusys.data.stats import zscore_normalize
  normalized = zscore_normalize(momentum, ['mom_1m', 'mom_3m'])
  ```

- 監査スキーマの初期化（既存接続に監査テーブルを追加）
  ```python
  from kabusys.data.audit import init_audit_schema
  import duckdb

  conn = duckdb.connect('data/kabusys.duckdb')
  init_audit_schema(conn, transactional=True)
  ```

注意:
- J-Quants API 呼び出しは rate limit（120 req/min）やリトライロジックを含みます。大量のページネーションを行う場合は負荷に注意してください。
- 本パッケージは価格・発注 API の直接実行（実際の発注）は含みません。発注連携は別モジュール（execution 等）に実装される想定です。

---

## ディレクトリ構成

主要ファイルとモジュール構成（抜粋）:

```
src/
└─ kabusys/
   ├─ __init__.py
   ├─ config.py                 # 環境変数/設定管理（.env 自動読み込み）
   ├─ data/
   │  ├─ __init__.py
   │  ├─ jquants_client.py      # J-Quants API client + 保存ユーティリティ
   │  ├─ news_collector.py      # RSS ニュース収集・保存・銘柄抽出
   │  ├─ schema.py              # DuckDB スキーマ定義・初期化
   │  ├─ stats.py               # 統計ユーティリティ（zscore_normalize）
   │  ├─ pipeline.py            # ETL パイプライン（run_daily_etl 等）
   │  ├─ quality.py             # データ品質チェック
   │  ├─ calendar_management.py # 市場カレンダー管理・営業日判定
   │  ├─ audit.py               # 監査ログ（発注→約定トレース）
   │  ├─ features.py            # 特徴量インターフェース（再エクスポート）
   │  └─ etl.py                 # ETL 公開インターフェース (ETLResult 再エクスポート)
   ├─ research/
   │  ├─ __init__.py
   │  ├─ feature_exploration.py # 将来リターン計算、IC、factor_summary、rank
   │  └─ factor_research.py     # momentum/volatility/value 等のファクター計算
   ├─ strategy/                 # 戦略モジュール（エントリポイント）
   ├─ execution/                # 発注関連（空の __init__ がある）
   └─ monitoring/               # 監視関連（空の __init__ がある）
```

---

## 注意事項 / 運用上のヒント

- 環境設定は機密情報（トークン・パスワード）を含むため、バージョン管理システムに .env を載せないでください。
- KABUSYS_ENV を "live" にすると本番向け動作フラグ（is_live 等）が有効になる想定です。テスト時は "paper_trading" / "development" を使ってください。
- DuckDB の初期化は冪等（既存テーブルは上書きしない）です。schema.init_schema() を初回のみ実行してください。
- ニュース収集は外部 URL を扱うため SSRF、XML BOM、gzip爆弾、トラッキングパラメータ等への対策を実装していますが、運用時の想定外ケースには注意してください。
- J-Quants API の ID トークンは自動リフレッシュされますが、refresh token の有効期限やレート制限は外部要因のため運用監視が必要です。

---

この README はコードベースの概要と主要な使い方を簡潔にまとめたものです。詳細な設計資料（DataPlatform.md、StrategyModel.md 等）や運用手順、CI/CD、テストガイドは別ドキュメントを参照してください。質問や追加のドキュメント化の希望があれば教えてください。