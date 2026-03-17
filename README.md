# KabuSys

日本株向けの自動売買プラットフォーム基盤ライブラリです。  
データ取得（J-Quants）、ETL、データ品質チェック、ニュース収集、監査ログ／実行レイヤのスキーマ定義など、取引戦略および実行のための基礎機能を提供します。

---

## 主な特徴（抜粋）

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダー取得
  - API レート制御（デフォルト 120 req/min の固定間隔スロットリング）
  - リトライ（指数バックオフ、最大 3 回）、401 時のトークン自動リフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を防止
  - DuckDB へ冪等的に保存（ON CONFLICT DO UPDATE）

- ニュース収集（RSS）
  - RSS フィードから記事を取得、前処理、DuckDB へ冪等保存
  - URL 正規化・トラッキングパラメタ除去、記事 ID は正規化URLの SHA-256（先頭32文字）
  - SSRF 対策（スキーム検証／プライベートIP検出／リダイレクト検査）、受信サイズ制限、XML デシリアライズ安全化（defusedxml）
  - 銘柄コード抽出（テキスト中の 4 桁数字 → known_codes によるフィルタ）

- ETL パイプライン
  - 差分取得（最終取得日から未取得分のみ取得）、バックフィル対応（デフォルト 3 日）
  - カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損 / スパイク / 重複 / 日付不整合）
  - 各ステップのエラーハンドリングは独立（1ステップ失敗でも他は継続）

- DuckDB スキーマ（3 層）
  - Raw / Processed / Feature / Execution 層のテーブルを定義・初期化
  - 監査ログ用の別途スキーマ（signal_events, order_requests, executions）を用意
  - インデックス定義付きで典型的クエリに最適化

- データ品質チェック（quality モジュール）
  - 欠損、スパイク（前日比）、重複、将来日付や非営業日のデータ検出
  - 問題は QualityIssue オブジェクトで集約（error / warning）

---

## 前提（推奨環境）

- Python 3.10+
- 必須依存（抜粋）:
  - duckdb
  - defusedxml
- ネットワーク経路で J-Quants / RSS ソースへ接続可能であること

（プロジェクトを pip パッケージ化する際は requirements に上記を追加してください）

---

## セットアップ

1. リポジトリをクローン（またはパッケージをインストール）
   - 開発時: python パッケージとして編集可能インストール
     ```
     pip install -e .
     ```

2. 環境変数の設定
   - プロジェクトルートに `.env` / `.env.local` を配置すると自動で読み込まれます。
   - 自動ロードを無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト時など）。

   必須環境変数（少なくとも下記は設定してください）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
   - KABU_API_PASSWORD     : kabuステーション等の API パスワード（実行系使用時）
   - SLACK_BOT_TOKEN       : Slack 通知用トークン（通知を使う場合）
   - SLACK_CHANNEL_ID      : Slack チャンネル ID（通知を使う場合）

   任意 / デフォルトあり:
   - KABUSYS_ENV (development | paper_trading | live) — デフォルト `development`
   - LOG_LEVEL (DEBUG|INFO|WARNING|ERROR|CRITICAL) — デフォルト `INFO`
   - KABU_API_BASE_URL — デフォルト `http://localhost:18080/kabusapi`
   - DUCKDB_PATH — デフォルト `data/kabusys.duckdb`
   - SQLITE_PATH — デフォルト `data/monitoring.db`

3. DuckDB スキーマ初期化
   - 例: ファイルに保存する
     ```python
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # ファイルの親ディレクトリを自動作成
     ```
   - インメモリ利用: `" :memory:"` を指定できます。

4. 監査ログ専用スキーマ（必要に応じ）
   ```python
   from kabusys.data import audit, schema
   conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB 接続を取得
   audit.init_audit_schema(conn, transactional=True)
   ```

---

## 使い方（主要 API サンプル）

以下はライブラリの主要な使い方の例です。実運用ではログ出力や例外ハンドリングを適宜実装してください。

- 設定値参照
  ```python
  from kabusys.config import settings
  token = settings.jquants_refresh_token
  ```

- J-Quants: ID トークン取得 / データ取得
  ```python
  from kabusys.data.jquants_client import get_id_token, fetch_daily_quotes
  from datetime import date

  id_token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  records = fetch_daily_quotes(id_token=id_token, code="7203", date_from=date(2024,1,1), date_to=date(2024,12,31))
  ```

  - 特長: 自動リトライ、401 時の自動リフレッシュ、ページネーション対応、レート制御あり

- ETL（日次パイプライン）
  ```python
  from kabusys.data import schema, pipeline
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn, target_date=date.today())
  print(result.to_dict())
  ```

  - run_daily_etl は市場カレンダー→株価→財務→品質チェックの順で実行し、ETLResult を返します。

- ニュース収集
  ```python
  from kabusys.data import news_collector, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  known_codes = {"7203", "6758", "9984"}  # 事前に保持している銘柄コードセット
  results = news_collector.run_news_collection(conn, known_codes=known_codes)
  print(results)  # {source_name: 新規保存件数, ...}
  ```

- カレンダー夜間更新ジョブ
  ```python
  from kabusys.data import calendar_management, schema

  conn = schema.get_connection("data/kabusys.duckdb")
  saved = calendar_management.calendar_update_job(conn)
  print(f"saved {saved} rows")
  ```

- 品質チェック
  ```python
  from kabusys.data import quality, schema
  from datetime import date

  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn, target_date=date.today())
  for i in issues:
      print(i)
  ```

---

## 注意点 / 設計に関する重要事項

- レート制御: J-Quants API は 120 req/min を想定。モジュール内で固定間隔スロットリングを実装しています。
- トークン管理: get_id_token / _get_cached_token によりトークンをキャッシュし、401 時は1回だけ自動リフレッシュして再試行します。
- 冪等性: raw レイヤへの保存は ON CONFLICT を使って上書きまたはスキップする設計です（重複二重投入対策）。
- セキュリティ:
  - news_collector は defusedxml を利用し XML 攻撃を軽減します。
  - RSS フェッチはスキーム検証・プライベート IP 検査・リダイレクト時の追加検査（SSRF 対策）を行います。
  - レスポンスサイズ上限を実装してメモリ DoS を防止しています。
- DB 初期化:
  - schema.init_schema は冪等的にテーブルとインデックスを作成します。既存 DB に対しては get_connection を使って接続してください。
  - audit.init_audit_schema は UTC タイムゾーン固定やトランザクションオプションを備えています。

---

## ディレクトリ構成（主要ファイル）

プロジェクトの主要なソース構成（src/kabusys 以下）:

- src/kabusys/
  - __init__.py
  - config.py         — 環境変数 / 設定管理
  - data/
    - __init__.py
    - jquants_client.py   — J-Quants API クライアント（取得 / 保存）
    - news_collector.py   — RSS ニュース収集・前処理・保存
    - pipeline.py         — ETL パイプライン（run_daily_etl 等）
    - schema.py           — DuckDB スキーマ定義・初期化
    - calendar_management.py — カレンダー管理 / バッチ更新
    - audit.py            — 監査ログ（signal / order / execution）スキーマ
    - quality.py          — データ品質チェック
  - strategy/
    - __init__.py
  - execution/
    - __init__.py
  - monitoring/
    - __init__.py

（実装は data 以下に集約されており、strategy / execution / monitoring は将来的な拡張ポイントです）

---

## 開発・貢献

- テスト: 環境変数自動ロードをテスト時に無効化したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- 型とドキュメント: 各モジュールは詳細な docstring を持ち、ユニットテストと型チェック（mypy 等）の併用を推奨します。
- Pull Request: 機能追加・バグ修正は機能毎に小さな PR に分けてください。特に DB スキーマ変更は下位互換性に注意してください。

---

必要であれば README にサンプル .env.example、CI/CD 実行手順、より詳しい API リファレンス（各関数の引数と戻り値）を追加します。追加希望があれば教えてください。