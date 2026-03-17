# KabuSys

日本株向け自動売買（データ基盤＋ETL＋監査）ライブラリ / フレームワーク

KabuSys は J-Quants 等の外部データソースから市場データ・財務データ・ニュースを取得し、DuckDB に格納・品質チェック・監査ログを残せることを目的とした日本語ドメイン向けのライブラリ群です。ETL パイプライン、カレンダー管理、ニュース収集、データ品質チェック、監査スキーマなどの機能を備えています。

---

## 主な特徴

- J-Quants API クライアント
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーの取得
  - API レート制限（120 req/min）を遵守する固定間隔スロットリング
  - リトライ（指数バックオフ、最大 3 回）、401 時の自動トークンリフレッシュ
  - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアスを抑制
  - DuckDB への保存は冪等（ON CONFLICT ... DO UPDATE）

- ニュース収集
  - RSS フィードからの記事取得、前処理（URL 除去・空白正規化）
  - URL 正規化 → SHA-256（先頭 32 文字）で記事 ID を生成して冪等挿入
  - SSRF / XML Bomb 対策（スキーム検証・プライベート IP 検出・defusedxml）
  - DuckDB へトランザクション単位で一括挿入（INSERT ... RETURNING）

- ETL パイプライン
  - 差分更新（最終取得日からの差分のみ取得）、バックフィル機能で後出し修正を吸収
  - 市場カレンダー先読み（デフォルト 90 日）
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実行して結果を返す

- マーケットカレンダー管理
  - DB に保存されたカレンダーを用いて営業日判定、前後営業日の取得、期間内営業日リスト取得
  - カレンダー未取得時は曜日（週末除外）によるフォールバック

- 監査ログ（Audit）
  - シグナル → 発注要求 → 約定に至るトレースを UUID ベースで完全に追跡
  - すべてのテーブルは UTC タイムスタンプ、冪等・ステータス管理を考慮した設計

---

## 必要な環境（概略）

- Python 3.10+（typing と新しい型ヒントを使用）
- 外部ライブラリ
  - duckdb
  - defusedxml

インストール例:
```bash
pip install duckdb defusedxml
```

（プロジェクトに requirements.txt があればそちらを利用してください）

---

## 環境変数（必須 / 任意）

KabuSys は環境変数またはプロジェクトルートの `.env` / `.env.local` から設定を自動読み込みします（CWD ではなくパッケージのファイル位置からプロジェクトルートを探索）。自動ロードを無効にするには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定します。

必須（getters が ValueError を投げる）:
- JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン
- KABU_API_PASSWORD      : kabuステーション等の API パスワード
- SLACK_BOT_TOKEN        : Slack 通知に使用する Bot トークン
- SLACK_CHANNEL_ID       : Slack チャネル ID

任意:
- KABUSYS_ENV : environment（development / paper_trading / live）デフォルト: development
- LOG_LEVEL   : ログレベル（DEBUG/INFO/...）デフォルト: INFO
- KABUSYS_DISABLE_AUTO_ENV_LOAD : 自動 .env ロード抑止（1 或いは存在で無効化）
- DUCKDB_PATH : デフォルト `data/kabusys.duckdb`
- SQLITE_PATH : デフォルト `data/monitoring.db`
- KABUS_API_BASE_URL : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）

例 .env（参考）
```
JQUANTS_REFRESH_TOKEN=your_refresh_token_here
KABU_API_PASSWORD=your_kabu_password
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C01234567
KABUSYS_ENV=development
LOG_LEVEL=INFO
DUCKDB_PATH=data/kabusys.duckdb
```

---

## セットアップ手順（ローカル開発向け）

1. リポジトリをクローン
2. Python 仮想環境を用意して依存パッケージをインストール
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install duckdb defusedxml
   ```
3. プロジェクトルートに `.env`（または `.env.local`）を作成して必要な環境変数を設定
4. DuckDB スキーマ初期化
   - Python REPL またはスクリプトで:
     ```py
     from kabusys.data import schema
     conn = schema.init_schema("data/kabusys.duckdb")  # path は必要に応じて変更
     ```
   - 監査ログ用 DB を別途初期化する場合:
     ```py
     from kabusys.data import audit
     conn_audit = audit.init_audit_db("data/kabusys_audit.duckdb")
     ```
   - init_schema は親ディレクトリを自動作成します。":memory:" も可。

---

## 使い方（主要 API / サンプル）

- J-Quants トークン取得
  ```py
  from kabusys.data.jquants_client import get_id_token
  token = get_id_token()  # settings.jquants_refresh_token を使用して取得
  ```

- 株価・財務・カレンダーの取得（個別）
  ```py
  from kabusys.data import jquants_client as jq
  token = jq.get_id_token()
  prices = jq.fetch_daily_quotes(id_token=token, date_from=date(2024,1,1), date_to=date(2024,1,31))
  financials = jq.fetch_financial_statements(id_token=token, date_from=date(2023,1,1))
  calendar = jq.fetch_market_calendar(id_token=token)
  ```

- ETL 日次パイプライン実行
  ```py
  from kabusys.data import schema, pipeline
  conn = schema.init_schema("data/kabusys.duckdb")
  result = pipeline.run_daily_etl(conn)  # target_date を指定可能
  print(result.to_dict())
  ```

- ニュース収集ジョブ
  ```py
  from kabusys.data import news_collector, schema
  conn = schema.get_connection("data/kabusys.duckdb")  # 既存 DB へ接続
  results = news_collector.run_news_collection(conn, sources=None, known_codes={"7203","6758"})
  print(results)  # {source_name: saved_count}
  ```

- 品質チェック単体実行
  ```py
  from kabusys.data import quality, schema
  conn = schema.get_connection("data/kabusys.duckdb")
  issues = quality.run_all_checks(conn)
  for i in issues:
      print(i)
  ```

注意点:
- ETL は各ステップで例外をハンドリングして続行を試みます。戻り値の ETLResult にエラー詳細・品質問題が含まれます。
- J-Quants へのリクエストは内部でレートリミッタ・リトライ・トークン自動更新を行います。

---

## 開発者向けの実装上のポイント（簡潔）

- 自動 .env ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行われます。テストで自動ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- J-Quants クライアントはページネーションに対応し、pagination_key を次のリクエストに流す設計です。レスポンスの fetched_at は UTC で記録します。
- news_collector は SSRF 対策・XML 脆弱性対策・受信サイズ上限（10MB）等を施しています。
- DuckDB 側の DDL は data/schema.py にまとまっています。init_schema() は冪等的に全テーブル・インデックスを作成します。
- 監査（audit）用スキーマは別関数で初期化でき、TimeZone を UTC に固定します。

---

## ディレクトリ構成

（主要ファイルを抜粋）

- src/kabusys/
  - __init__.py
  - config.py                      — 環境変数 / 設定管理（.env 自動読み込み、Settings クラス）
  - data/
    - __init__.py
    - jquants_client.py             — J-Quants API クライアント（取得/保存ロジック）
    - news_collector.py             — RSS ニュース取得・前処理・DB 保存
    - pipeline.py                   — ETL パイプライン（差分更新 / run_daily_etl）
    - schema.py                     — DuckDB スキーマ定義と初期化（init_schema/get_connection）
    - calendar_management.py        — マーケットカレンダーの管理ロジック・バッチ
    - audit.py                      — 監査ログ用スキーマ（signal/order/execution）
    - quality.py                    — データ品質チェック
  - strategy/
    - __init__.py                   — 戦略関連のエントリ（拡張ポイント）
  - execution/
    - __init__.py                   — 発注・執行関連のエントリ（拡張ポイント）
  - monitoring/
    - __init__.py                   — 監視関連（未実装の拡張ポイント）

---

## 今後の拡張 / 注意事項

- strategy / execution / monitoring はモジュールプレースホルダが用意されています。実運用では戦略ロジック、注文送信ドライバ、監視アラート等を実装してください。
- セキュリティ: `.env` やシークレットはソース管理に入れないでください。運用環境では Vault 等の秘密管理システムを検討してください。
- テスト: ネットワーク呼び出しについてはモック可能な設計（例えば news_collector._urlopen の差し替え）になっています。単体テストでは自動 .env ロードを無効化すると良いです。

---

必要であれば、README に動作フロー図や具体的なコード例（戦略実装テンプレート、発注処理サンプル、CI 用スクリプトなど）を追加します。どの情報を優先して追加しましょうか？