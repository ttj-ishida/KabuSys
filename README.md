# KabuSys

日本株自動売買に向けたデータ基盤＋ETL＋監査レイヤのライブラリ群です。  
J-Quants API や RSS を使ったデータ収集、DuckDB を用いたスキーマ/永続化、データ品質チェック、監査ログ（発注〜約定までのトレーサビリティ）などを提供します。

バージョン: 0.1.0

---

## 主要機能

- J-Quants API クライアント（jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーを取得
  - レート制限（120 req/min）対応の固定間隔レートリミッタ
  - リトライ（指数バックオフ、最大 3 回）・401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止
  - DuckDB へ冪等保存（ON CONFLICT DO UPDATE）

- ニュース収集（news_collector）
  - RSS フィードから記事を取得して raw_news に保存
  - URL 正規化（utm 等のトラッキングパラメータ除去）→ SHA-256（先頭32文字）で記事ID生成（冪等）
  - SSRF 対策（スキーム制限、プライベートIPチェック、リダイレクト検査）
  - レスポンスサイズ上限（デフォルト 10MB）、gzip 解凍後のチェック
  - 銘柄コード抽出・news_symbols への紐付け（既知銘柄セットを利用）

- ETL パイプライン（pipeline）
  - 差分取得（最終取得日ベース）、バックフィルのサポート（デフォルト backfill_days=3）
  - カレンダー先読み（デフォルト 90 日）
  - 保存 → 品質チェック（quality）で欠損・スパイク・重複・日付不整合を検出
  - 日次 ETL 実行用エントリポイント run_daily_etl

- DuckDB スキーマ定義（schema）
  - Raw / Processed / Feature / Execution 層を定義
  - 多数のテーブル（raw_prices, raw_financials, raw_news, market_calendar, features, signals, orders, trades, positions, …）
  - インデックス定義と冪等な初期化 api（init_schema / get_connection）

- 監査ログ（audit）
  - シグナル → 発注要求 → 約定のトレーサビリティを保持する audit テーブル群
  - order_request_id を冪等キーとして二重発注を防止
  - init_audit_schema / init_audit_db による初期化（UTC タイムゾーン固定）

- データ品質チェック（quality）
  - 欠損、スパイク（前日比閾値）、重複、日付不整合検出
  - QualityIssue オブジェクトで問題を集約し、呼び出し元で対処可能

---

## 必要条件 / 推奨環境

- Python 3.10 以上（PEP 604 の union 型記法などを使用）
- 推奨パッケージ（最低限）:
  - duckdb
  - defusedxml

レビュー済みコード中で標準ライブラリの urllib、json、datetime、logging、hashlib、ipaddress などを使用しています。

のちほど requirements.txt を用意する場合は上記を追加してください。

---

## 環境変数（必須 / 重要）

設定は .env ファイルまたは環境変数から自動読み込みされます（パッケージルートを .git または pyproject.toml から自動検出）。自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。

主要な環境変数（Settings クラス）:

- JQUANTS_REFRESH_TOKEN (必須)  
  J-Quants のリフレッシュトークン（get_id_token のため）。

- KABU_API_PASSWORD (必須)  
  kabuステーションAPI 用パスワード。

- KABU_API_BASE_URL (任意)  
  kabu API ベース URL（デフォルト: http://localhost:18080/kabusapi）。

- SLACK_BOT_TOKEN (必須)  
  通知用 Slack Bot トークン。

- SLACK_CHANNEL_ID (必須)  
  Slack チャンネル ID。

- DUCKDB_PATH (任意)  
  DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）。

- SQLITE_PATH (任意)  
  監視用途の SQLite パス（デフォルト: data/monitoring.db）。

- KABUSYS_ENV (任意)  
  環境: development / paper_trading / live（デフォルト: development）。

- LOG_LEVEL (任意)  
  ログレベル: DEBUG/INFO/WARNING/ERROR/CRITICAL（デフォルト: INFO）。

.env の例（README 用サンプル）:
```
JQUANTS_REFRESH_TOKEN=your_jquants_refresh_token
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
DUCKDB_PATH=data/kabusys.duckdb
KABUSYS_ENV=development
LOG_LEVEL=INFO
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン / チェックアウト

2. 仮想環境作成（推奨）
   ```
   python -m venv .venv
   source .venv/bin/activate   # macOS / Linux
   .venv\Scripts\activate      # Windows
   ```

3. 必要パッケージをインストール
   - 最低限:
     ```
     pip install duckdb defusedxml
     ```
   - 開発用に依存リストがあれば requirements.txt を利用してください。

4. 環境変数を設定
   - プロジェクトルートに `.env` を作成するか、環境変数をエクスポートしてください。
   - 自動ロードを無効にする場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。

5. DuckDB スキーマ初期化（例）
   ```python
   from kabusys.config import settings
   from kabusys.data.schema import init_schema

   conn = init_schema(settings.duckdb_path)
   ```

6. 監査ログ用スキーマ初期化（必要時）
   ```python
   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（代表的なコード例）

- 日次 ETL を実行する（簡易例）:
  ```python
  from kabusys.config import settings
  from kabusys.data.schema import init_schema
  from kabusys.data.pipeline import run_daily_etl

  conn = init_schema(settings.duckdb_path)
  result = run_daily_etl(conn)  # 戻り値は ETLResult オブジェクト
  print(result.to_dict())
  ```

  オプションを渡す例:
  ```python
  run_daily_etl(conn, backfill_days=5, spike_threshold=0.6, run_quality_checks=True)
  ```

- RSS ニュース収集ジョブ:
  ```python
  from kabusys.data.news_collector import run_news_collection
  from kabusys.data.schema import init_schema

  conn = init_schema("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 既知銘柄のセット
  results = run_news_collection(conn, known_codes=known_codes)
  print(results)  # ソースごとの新規保存数
  ```

- J-Quants から直接データを取得（テスト用）:
  ```python
  from kabusys.data.jquants_client import fetch_daily_quotes, get_id_token
  token = get_id_token()  # settings から自動取得
  rows = fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  ```

- 品質チェックを個別実行:
  ```python
  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i)
  ```

---

## 主なパラメータ・設定の説明

- backfill_days: ETL が前回取得日より遡って再フェッチする日数（デフォルト 3）。API の後出し修正に対応します。
- calendar_lookahead_days: market_calendar をどれだけ先まで先読みするか（デフォルト 90）。
- spike_threshold: データ品質チェックのスパイク検出閾値（デフォルト 0.5 = 50%）。

---

## ディレクトリ構成（抜粋）

リポジトリ内の主要ファイル/モジュール構成:

- src/kabusys/
  - __init__.py
  - config.py                      -- 環境変数 / 設定管理
  - data/
    - __init__.py
    - schema.py                    -- DuckDB スキーマ定義・初期化
    - jquants_client.py            -- J-Quants API クライアント（取得・保存）
    - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
    - news_collector.py            -- RSS 収集・記事保存・銘柄抽出
    - calendar_management.py       -- カレンダー更新・営業日判定
    - audit.py                     -- 監査ログ（シグナル→発注→約定）
    - quality.py                   -- データ品質チェック
    - (その他データ関連ユーティリティ)
  - strategy/
    - __init__.py                   -- 戦略層（拡張ポイント）
  - execution/
    - __init__.py                   -- 発注・証券会社連携（拡張ポイント）
  - monitoring/
    - __init__.py                   -- 監視・アラート（拡張ポイント）

---

## 開発・拡張ポイント

- strategy/ と execution/ は拡張用のプレースホルダです。戦略ロジックやブローカー接続の実装はここに移す想定です。
- DuckDB のスキーマは DataPlatform.md に基づく想定で詳細なテーブル設計を反映しています。カラム追加やインデックスの調整は schema.py を編集してください。
- news_collector は既知銘柄セット（known_codes）により記事と銘柄の紐付けを行います。銘柄マスターや別プロセスで known_codes を構築して渡す想定です。
- ETL のテストを行う際は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して環境依存の自動読み込みを抑制すると便利です。

---

## 注意事項 / セキュリティ

- news_collector は SSRF や XML Bomb、Gzip Bomb 等に対策を実装していますが、外部入力 URL を扱う際は追加の監査や許可済みソース管理を推奨します。
- 環境変数やトークン類は安全に管理し、公開リポジトリに `.env` をアップしないでください。
- DuckDB ファイルのバックアップやアクセス権限には注意してください。

---

疑問点や追加して欲しいドキュメント（使用例、CLI、CI 設定、requirements ファイルなど）があれば教えてください。README を用途に合わせて調整します。