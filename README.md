# KabuSys

日本株向け自動売買基盤のコアライブラリ（KabuSys）。  
データ取得（J-Quants）、ETL パイプライン、ニュース収集、データ品質チェック、DuckDB スキーマ定義、監査ログ（発注→約定トレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## プロジェクト概要

KabuSys は日本株の自動売買システム向けに設計されたライブラリ群です。主な目的は以下です。

- J-Quants API から株価・財務・市場カレンダーを安全かつ冪等に取得して DuckDB に格納する。
- RSS からニュース記事を収集し、記事と銘柄コードの紐付けを行う。
- ETL（差分取得、バックフィル、品質チェック）を行い、生データ → 整形データ → 特徴量 までのパイプラインをサポートする。
- 発注・約定の監査ログを保存して、信頼できるトレーサビリティを提供する。

設計上の要点:
- J-Quants のレート制限（120 req/min）やリトライ・トークンリフレッシュを考慮。
- RSS 収集時の SSRF / XML BOM / メモリ DoS 対策を実装。
- DuckDB への保存は基本的に冪等（ON CONFLICT）で実装。
- 品質チェックは Fail-Fast せず検出項目を集めて返却。

---

## 機能一覧

- データ取得（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務（四半期 BS/PL）、市場カレンダーをページネーション対応で取得
  - レートリミット制御、リトライ、トークン自動リフレッシュ、取得時刻（fetched_at）記録

- DuckDB スキーマ管理（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層のテーブル定義
  - インデックス、テーブル作成、接続ユーティリティ

- ETL パイプライン（kabusys.data.pipeline）
  - 日次 ETL（カレンダー、株価、財務）、差分取得、バックフィル、品質チェック統合
  - ETL 結果を ETLResult として返却

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得、XML パース（defusedxml）、前処理、記事ID生成（URL 正規化→SHA-256）
  - raw_news へ冪等保存、銘柄抽出・紐付け

- データ品質チェック（kabusys.data.quality）
  - 欠損データ、スパイク（前日比閾値）、重複、日付整合性チェック
  - QualityIssue を返却

- 監査ログ（kabusys.data.audit）
  - signal_events / order_requests / executions 等の監査テーブル、監査用インデックス
  - 発注→約定のトレーサビリティ保存（UTC タイムスタンプ）

- 環境設定読み込み（kabusys.config）
  - .env / .env.local の自動ロード（プロジェクトルート検出）
  - 設定アクセス用 settings オブジェクト（必須チェックを含む）

---

## セットアップ手順

前提:
- Python 3.10 以上（PEP 604 のユニオン記法や型ヒントを使用）
- システムに DuckDB を利用できる環境

1. リポジトリをクローン / プロジェクトディレクトリへ移動

2. 仮想環境を作成（推奨）
   - python -m venv .venv
   - source .venv/bin/activate  (Windows: .venv\Scripts\activate)

3. 必要パッケージをインストール
   - pip install duckdb defusedxml
   - （開発時）pip install -e . が使える場合はプロジェクトのパッケージ化に応じて実行してください。

4. 環境変数設定 (.env)
   - プロジェクトルートに `.env` または `.env.local` を作成すると自動読み込みされます（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可）。
   - 必要な環境変数（主なもの）:
     - JQUANTS_REFRESH_TOKEN=<your_jquants_refresh_token>  (必須)
     - KABU_API_PASSWORD=<kabu_api_password>              (必須)
     - KABU_API_BASE_URL (省略時: http://localhost:18080/kabusapi)
     - SLACK_BOT_TOKEN=<token>                            (必須)
     - SLACK_CHANNEL_ID=<channel>                         (必須)
     - DUCKDB_PATH (省略時: data/kabusys.duckdb)
     - SQLITE_PATH (省略時: data/monitoring.db)
     - KABUSYS_ENV (development | paper_trading | live)    (省略時: development)
     - LOG_LEVEL (DEBUG | INFO | WARNING | ERROR | CRITICAL) (省略時: INFO)

   例 (.env):
   ```
   JQUANTS_REFRESH_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxx
   KABU_API_PASSWORD=your_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=INFO
   ```

---

## 使い方（簡単なコード例）

以下は最小限の利用例です。Python スクリプトまたは REPL で実行します。

- DuckDB スキーマ初期化（ファイル DB）
  ```
  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")
  ```

- 日次 ETL 実行（J-Quants トークンは settings が .env から読み込み）
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema("data/kabusys.duckdb")
  result = run_daily_etl(conn)  # デフォルトは今日の ETL
  print(result.to_dict())
  ```

- ニュース収集ジョブ実行
  ```
  from kabusys.data.schema import init_schema
  from kabusys.data.news_collector import run_news_collection

  conn = init_schema("data/kabusys.duckdb")
  # known_codes を与えると記事内の4桁銘柄を抽出して news_symbols に紐付ける
  known_codes = {"7203", "6758", "9984"}  # 事前に取れる銘柄セットを用意
  results = run_news_collection(conn, sources=None, known_codes=known_codes)
  print(results)
  ```

- 監査スキーマの初期化（既存接続に追加）
  ```
  from kabusys.data.audit import init_audit_schema
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  init_audit_schema(conn)
  ```

- J-Quants から株価データを直接取得（テストや手動確認用）
  ```
  from kabusys.data import jquants_client as jq
  conn = jq  # jquants_client は settings を利用するので環境変数が必要
  daily = jq.fetch_daily_quotes(code="7203", date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

注意点:
- settings.jquants_refresh_token 等の必須環境変数が未設定だと ValueError が発生します。
- J-Quants クライアントはレート制御やリトライを行いますが、API 利用制限を尊重してください。

---

## ディレクトリ構成

主要なファイル/モジュール (src/kabusys 以下) の構成:

- src/kabusys/
  - __init__.py
  - config.py  — 環境変数/設定読み込み、settings オブジェクト
  - data/
    - __init__.py
    - jquants_client.py         — J-Quants API クライアント（fetch / save）
    - news_collector.py        — RSS 収集・記事保存・銘柄抽出
    - schema.py                — DuckDB スキーマ定義 / init_schema / get_connection
    - pipeline.py              — ETL パイプライン（run_daily_etl 等）
    - audit.py                 — 監査ログテーブル初期化
    - quality.py               — データ品質チェック
  - strategy/
    - __init__.py              — 戦略関連プレースホルダ
  - execution/
    - __init__.py              — 実行層プレースホルダ
  - monitoring/
    - __init__.py              — モニタリングプレースホルダ

参考（ツリー風）:
```
src/kabusys/
├─ __init__.py
├─ config.py
├─ data/
│  ├─ __init__.py
│  ├─ jquants_client.py
│  ├─ news_collector.py
│  ├─ schema.py
│  ├─ pipeline.py
│  ├─ audit.py
│  └─ quality.py
├─ strategy/
│  └─ __init__.py
├─ execution/
│  └─ __init__.py
└─ monitoring/
   └─ __init__.py
```

---

## 実運用向けの注記 / ベストプラクティス

- 環境分離:
  - KABUSYS_ENV を使って development / paper_trading / live を切り替え。
  - 本番実行時は is_live フラグ等を使用して実際の発注を抑制/許可するガードを実装してください。

- セキュリティ:
  - .env に機密情報を保存する場合はファイルの権限に注意。
  - news_collector は SSRF・XML 攻撃対策を行っていますが、実行環境のネットワーク制御も行ってください。

- テスト:
  - 自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して手動で環境を注入してください。
  - jquants_client のネットワーク呼び出しはモックしてユニットテストを行うことを推奨します（例: _urlopen, _get_cached_token の差し替え）。

- パフォーマンス:
  - DuckDB のファイルパスは十分な I/O 性能のあるストレージを使用してください。
  - 大規模導入時はデータ保管戦略（パーティション、バックアップ）を検討してください。

---

## 既知の依存ライブラリ

- duckdb
- defusedxml

（追加でログ連携・Slack 通知や証券会社 API クライアント等が必要であれば、別途導入してください）

---

問題や改善提案があればコードコメントや Issue でお知らせください。README の補足（例: .env.example、CI / デプロイ手順、より詳細な運用手順等）を追加できます。必要ならテンプレートを作成します。