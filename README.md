# KabuSys

日本株向けの自動売買 / データ基盤ライブラリです。  
ETL（J-Quants からのデータ取得 → DuckDB 保存）、ニュース収集、品質チェック、特徴量計算、監査ログ用スキーマなどを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム開発を支援する内部ライブラリ群です。主な目的は次のとおりです。

- J-Quants API からの株価・財務・カレンダーの差分取得と DuckDB への冪等保存
- RSS ベースのニュース収集と記事→銘柄紐付け
- データ品質チェック（欠損・重複・スパイク・日付不整合など）
- 研究用の特徴量（モメンタム、ボラティリティ、バリュー等）計算と IC 検証ユーティリティ
- 監査ログ（シグナル → 発注 → 約定 のトレース）用スキーマ
- ETL パイプラインの単体呼び出し API

設計上の注意点:
- DuckDB を主要なデータストアとして利用（軽量・高速）
- 外部依存は最小限（標準ライブラリ中心、ただし duckdb, defusedxml は必須）
- ETL / データ収集は冪等（ON CONFLICT / DO UPDATE）で安全に反復可能
- J-Quants API のレート制限とリトライ、トークン自動リフレッシュを考慮

---

## 機能一覧

- 環境設定管理
  - .env/.env.local 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）
  - 必須設定の検査（settings オブジェクト）

- データ取得・保存（kabusys.data.jquants_client）
  - 株価日足（fetch_daily_quotes / save_daily_quotes）
  - 財務データ（fetch_financial_statements / save_financial_statements）
  - マーケットカレンダー（fetch_market_calendar / save_market_calendar）
  - レート制御、リトライ、トークン自動更新

- ETL パイプライン（kabusys.data.pipeline）
  - run_daily_etl：カレンダー → 株価 → 財務 → 品質チェック（一連実行）
  - 差分取得・バックフィルの自動算出

- データスキーマ管理（kabusys.data.schema）
  - DuckDB 用のテーブル定義と初期化（init_schema / get_connection）
  - 監査ログ用スキーマ初期化（init_audit_schema / init_audit_db）

- 品質チェック（kabusys.data.quality）
  - 欠損、重複、スパイク、日付不整合の検出・一覧化

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得（SSRF 対策、gzip 制限、トラッキングパラメータ除去）
  - raw_news 保存、news_symbols（銘柄紐付け）
  - 記事IDは正規化URLの SHA-256（先頭32文字）

- 研究モジュール（kabusys.research）
  - calc_momentum / calc_volatility / calc_value 等のファクター計算
  - calc_forward_returns / calc_ic / factor_summary / rank
  - zscore 正規化ユーティリティ（kabusys.data.stats）

- その他
  - 監査ログ（signal/events/order_requests/executions）スキーマと初期化
  - カレンダー管理ユーティリティ（営業日計算）

---

## セットアップ手順

前提
- Python 3.9+（typing の機能を利用）
- DuckDB を使用するため、ローカルにファイルを書き出せること

1. リポジトリをクローン（パッケージ化されていれば pip install での利用も可）
   - 例: git clone ...

2. Python 仮想環境を作成し有効化
   - python -m venv .venv
   - source .venv/bin/activate  （Windows: .venv\Scripts\activate）

3. 必須パッケージをインストール
   - pip install duckdb defusedxml

   （本プロジェクトは urllib 等の標準ライブラリを使うため、requests 等は不要）

4. 環境変数（.env）を準備

   プロジェクトルートに .env（または .env.local）を置くと自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
   KABU_API_PASSWORD=your_kabu_api_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C0123456
   DUCKDB_PATH=data/kabusys.duckdb
   SQLITE_PATH=data/monitoring.db
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

5. データベース初期化（DuckDB スキーマ作成）
   - Python REPL またはスクリプトで:
     from kabusys.data.schema import init_schema
     conn = init_schema("data/kabusys.duckdb")

   - 監査ログ専用 DB を別途作る場合:
     from kabusys.data.audit import init_audit_db
     audit_conn = init_audit_db("data/kabusys_audit.duckdb")

---

## 使い方（基本例）

ここでは代表的なユースケースの呼び出し例を示します。

1) DuckDB スキーマ初期化
```
from kabusys.data.schema import init_schema
conn = init_schema("data/kabusys.duckdb")
```

2) 日次 ETL 実行（J-Quants からの差分取得・保存・品質チェック）
```
from kabusys.data.pipeline import run_daily_etl
result = run_daily_etl(conn)
print(result.to_dict())
```

3) ニュース収集ジョブの実行
```
from kabusys.data.news_collector import run_news_collection, DEFAULT_RSS_SOURCES, extract_stock_codes
# known_codes は銘柄コードの set（例: {"7203","6758",...}）
res = run_news_collection(conn, sources=DEFAULT_RSS_SOURCES, known_codes=known_codes)
print(res)
```

4) 研究用ファクター計算（例: モメンタム）
```
from datetime import date
from kabusys.research import calc_momentum
rows = calc_momentum(conn, date(2024, 1, 31))
# rows は {date, code, mom_1m, mom_3m, mom_6m, ma200_dev} の dict のリスト
```

5) forward returns と IC 計算
```
from kabusys.research import calc_forward_returns, calc_ic
fwd = calc_forward_returns(conn, date(2024,1,31), horizons=[1,5])
# factor_records は例えば calc_momentum の結果
ic = calc_ic(factor_records, fwd, factor_col="mom_1m", return_col="fwd_1d")
```

6) z-score 正規化
```
from kabusys.data.stats import zscore_normalize
normed = zscore_normalize(factor_records, ["mom_1m", "ma200_dev"])
```

---

## よく使う設定・環境変数

- JQUANTS_REFRESH_TOKEN (必須) - J-Quants のリフレッシュトークン
- KABU_API_PASSWORD (必須) - kabuステーション API パスワード
- KABU_API_BASE_URL (任意) - kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
- SLACK_BOT_TOKEN, SLACK_CHANNEL_ID (必須) - 通知用 Slack 設定
- DUCKDB_PATH (任意) - DuckDB のファイルパス（デフォルト: data/kabusys.duckdb）
- SQLITE_PATH (任意) - 監視用 SQLite パス（デフォルト: data/monitoring.db）
- KABUSYS_ENV (任意) - development / paper_trading / live（デフォルト: development）
- LOG_LEVEL (任意) - DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）
- KABUSYS_DISABLE_AUTO_ENV_LOAD=1 - 自動 .env ロードを無効にする（テストなどで使用）

注意: config.Settings は必須 env が未設定だと例外を投げます。

---

## ディレクトリ構成

以下は主要ファイル/モジュールの一覧（抜粋）です。src 配下にパッケージが配置されています。

- src/kabusys/
  - __init__.py
  - config.py               -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py     -- J-Quants API クライアント + 保存ロジック
    - news_collector.py     -- RSS 収集・前処理・保存
    - schema.py             -- DuckDB スキーマと init_schema / get_connection
    - stats.py              -- zscore_normalize 等の統計ユーティリティ
    - pipeline.py           -- ETL パイプライン（run_daily_etl 等）
    - features.py           -- data.stats の再エクスポート
    - calendar_management.py-- マーケットカレンダー管理（営業日判定等）
    - audit.py              -- 監査ログ（signal/order/execution）スキーマ初期化
    - etl.py                -- ETLResult の公開インターフェース
    - quality.py            -- データ品質チェック
  - research/
    - __init__.py           -- 研究用 API の公開
    - feature_exploration.py-- forward returns / IC / summary / rank
    - factor_research.py    -- momentum/value/volatility の計算
  - strategy/                -- 戦略層（空のパッケージ: 実装を追加）
  - execution/               -- 発注実装（空のパッケージ: 実装を追加）
  - monitoring/              -- 監視・メトリクス（空のパッケージ: 実装を追加）

この README に掲載している機能は上記のモジュールに対応しています。strategy / execution / monitoring は外部実装や上位層からの利用を想定したプレースホルダです。

---

## 開発・運用上の注意

- J-Quants API にはレート制限（120 req/min）があります。jquants_client は内部で RateLimiter とリトライを実装していますが、大量バッチの際は注意してください。
- news_collector は SSRF や XML Bomb に対する防御を実装していますが、未知のフィードに対してはログ監視を推奨します。
- DuckDB のトランザクション挙動やバージョン差異に注意してください（DDL の一部は DuckDB のバージョンに依存する可能性あり）。
- 本システムは本番発注を直接行うモジュールを含みません（execution パッケージは空のプレースホルダ）。本番発注ロジックを実装する場合、十分な監査・安全性チェックと手動テストを行ってください。

---

もし README に追加したい事項（例: CI 設定、ユニットテスト実行手順、ライセンス情報、より詳細な API ドキュメント）があれば教えてください。必要に応じて追記します。