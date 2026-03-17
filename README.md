# KabuSys

日本株向け自動売買・データ基盤ライブラリ KabuSys の README。

このリポジトリは、J-Quants API 等から市場データ・財務データ・ニュースを収集し、DuckDB に格納して
ETL・品質チェック・監査ログ・カレンダー管理・ニュース収集を行うためのモジュール群を提供します。
戦略実行・発注周りの骨組み（audit / execution / signal 等）も含まれており、独自戦略やブローカー連携を組み込める設計です。

---

## 主な特徴（機能一覧）

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務データ、JPX市場カレンダーを取得
  - レート制限（120 req/min）を守る RateLimiter 実装
  - リトライ（指数バックオフ）、401 時のトークン自動リフレッシュ対応
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead バイアスを防止
  - DuckDB へ冪等（ON CONFLICT）に保存するユーティリティ

- ニュース収集（RSS）
  - RSS から記事を収集して前処理し raw_news テーブルへ保存
  - URL 正規化（トラッキングパラメータ除去）、記事ID を SHA-256 ハッシュで生成
  - SSRF 対策（スキーム検証・プライベートIP拒否・リダイレクト検査）
  - defusedxml を使った XML の安全パース、レスポンスサイズ上限による DoS 対策
  - 銘柄コード抽出・news_symbols への紐付け機能

- ETL パイプライン
  - 差分更新（最終取得日から未取得範囲のみ取得）とバックフィル機構
  - 品質チェック（欠損・スパイク・重複・日付不整合）を実装
  - 市場カレンダー先読み（先90日など）

- DuckDB スキーマ定義
  - Raw / Processed / Feature / Execution 層のテーブルを定義して初期化
  - 監査ログ（signal_events, order_requests, executions）テーブルを別途初期化可能

- カレンダー管理
  - market_calendar に基づく営業日判定、next/prev_trading_day、期間内営業日取得などのユーティリティ
  - 夜間カレンダー更新ジョブ

- 監査（Audit）
  - シグナル→発注→約定のトレーサビリティを UUID 階層で保持
  - 発注要求の冪等キー（order_request_id）設計

---

## 前提（推奨環境）

- Python 3.10+
  - 型ヒントで `X | None` などを使用しているため Python 3.10 以降を推奨します
- 必要パッケージ（例）
  - duckdb
  - defusedxml

パッケージは後述の手順でインストールします。

---

## セットアップ手順

1. リポジトリをクローン／取得

   git clone してプロジェクトルートに移動します。

2. Python 仮想環境を作る（推奨）

   python -m venv .venv
   source .venv/bin/activate  # macOS / Linux
   .venv\Scripts\activate     # Windows

3. 依存パッケージをインストール

   pip install duckdb defusedxml

   （プロジェクトに requirements.txt / pyproject.toml があればそれに従ってください）
   開発用には pip install -e . を使う想定（パッケージ化済みであれば）。

4. 環境変数の設定

   このプロジェクトは .env / .env.local を自動で読み込みます（プロジェクトルートの判定は `.git` または `pyproject.toml` を基準とします）。

   自動ロードを無効化する場合は環境変数を設定します:
   KABUSYS_DISABLE_AUTO_ENV_LOAD=1

   必須の環境変数（Settings から）:
   - JQUANTS_REFRESH_TOKEN : J-Quants のリフレッシュトークン（必須）
   - KABU_API_PASSWORD     : kabuステーション API パスワード（必須）
   - SLACK_BOT_TOKEN       : Slack 通知用 Bot トークン（必須）
   - SLACK_CHANNEL_ID      : Slack チャンネルID（必須）

   任意（デフォルトあり）:
   - KABU_API_BASE_URL     : kabu API のベース URL（デフォルト: http://localhost:18080/kabusapi）
   - DUCKDB_PATH           : DuckDB ファイルパス（デフォルト: data/kabusys.duckdb）
   - SQLITE_PATH           : SQLite（監視用）パス（デフォルト: data/monitoring.db）
   - KABUSYS_ENV           : 実行環境（development|paper_trading|live、デフォルト: development）
   - LOG_LEVEL             : ログレベル（DEBUG/INFO/...、デフォルト: INFO）

   例（.env）:
   JQUANTS_REFRESH_TOKEN=your_refresh_token
   KABU_API_PASSWORD=your_kabu_password
   SLACK_BOT_TOKEN=xoxb-...
   SLACK_CHANNEL_ID=C01234567
   DUCKDB_PATH=data/kabusys.duckdb
   KABUSYS_ENV=development
   LOG_LEVEL=DEBUG

5. DuckDB スキーマ初期化

   Python REPL やスクリプトで次を実行してスキーマを初期化します。

   from kabusys.data.schema import init_schema
   conn = init_schema("data/kabusys.duckdb")

   監査ログ用テーブルは以下で初期化できます（既存 conn を渡す）:

   from kabusys.data.audit import init_audit_schema
   init_audit_schema(conn)

---

## 使い方（代表的な操作例）

以下は主要モジュールの使い方サンプルです。実際はアプリケーションの用途に合わせてラップしてください。

- DuckDB スキーマ初期化

  from kabusys.data.schema import init_schema
  conn = init_schema("data/kabusys.duckdb")

- J-Quants から日足を取得して保存

  from kabusys.data import jquants_client as jq
  records = jq.fetch_daily_quotes(date_from=date(2024,1,1), date_to=date(2024,1,31))
  saved = jq.save_daily_quotes(conn, records)

  注) get_id_token() は settings.jquants_refresh_token を参照して自動で ID トークンを取得します。401 で自動リフレッシュ、最大リトライ等が組み込まれています。API レートは 120 req/min に従います。

- 日次 ETL を実行（まとめてカレンダー・日足・財務・品質チェックを実行）

  from kabusys.data.pipeline import run_daily_etl
  result = run_daily_etl(conn)

  result は ETLResult オブジェクトで、保存件数や品質チェック結果・エラー一覧が含まれます。

- ニュース収集ジョブを実行

  from kabusys.data.news_collector import run_news_collection
  # known_codes があれば銘柄紐付けを行う（set of "7203" 形式）
  stats = run_news_collection(conn, known_codes={"7203","6758"})

  run_news_collection は各 RSS ソース単位でエラーを分離して処理します。RSS のフェッチには SSRF 対策・gzip 対応・XML 安全パース等が施されています。

- 市場カレンダーの夜間更新

  from kabusys.data.calendar_management import calendar_update_job
  saved = calendar_update_job(conn)

- 品質チェックを個別に実行

  from kabusys.data.quality import run_all_checks
  issues = run_all_checks(conn, target_date=None)
  for i in issues:
      print(i.check_name, i.severity, i.detail)

---

## 設計上の注意点 / 実装のポイント

- 環境変数の自動ロード
  - config.py はプロジェクトルート（.git または pyproject.toml の存在）を基に .env/.env.local を自動で読み込みます。
  - 読み込み順序: OS環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化できます（テスト等で有用）。

- J-Quants クライアント
  - レート制限: 固定間隔スロットリング（120 req/min）を尊重
  - リトライ: ネットワーク系エラー & 429/408 & 5xx に対する指数バックオフ（最大 3 回）
  - 401 発生時は refresh token から id_token を再取得して 1 回だけリトライ
  - ページネーション対応。fetched_at を UTC ISO8601 で保存し、いつデータを取得したかをトレース可能に

- ニュース収集
  - トラッキングパラメータ除去・URL 正規化で冪等 ID を生成（SHA-256の先頭32文字）
  - レスポンスサイズや gzip 解凍後のサイズ上限を設け、メモリDoS対策を実装
  - リダイレクト時にリダイレクト先のスキーム・ホストを検証して SSRF を防ぐ

- DuckDB スキーマ
  - Raw → Processed → Feature → Execution 層を定義
  - 多数の CHECK / PRIMARY KEY / FOREIGN KEY を使用しデータ整合性を担保
  - テーブル作成は冪等（IF NOT EXISTS）で安全に再実行可能

- 品質チェック
  - Fail-fast ではなく発見した問題をすべて列挙して返す設計
  - スパイク検出は前日比を基に閾値（デフォルト 50%）で検出

---

## ディレクトリ構成

リポジトリ内の主要ファイル／ディレクトリ構成（抜粋）:

- src/
  - kabusys/
    - __init__.py
    - config.py                      -- 環境変数・設定読み込み
    - data/
      - __init__.py
      - jquants_client.py            -- J-Quants API クライアント（取得＋保存）
      - news_collector.py            -- RSS ニュース収集・保存・銘柄抽出
      - pipeline.py                  -- ETL パイプライン（run_daily_etl 等）
      - schema.py                    -- DuckDB スキーマ定義・初期化
      - calendar_management.py       -- カレンダー管理（営業日判定・更新ジョブ）
      - audit.py                     -- 監査ログ（signal/order/execution）定義・初期化
      - quality.py                   -- データ品質チェック
    - strategy/                       -- 戦略関連（プレースホルダ）
      - __init__.py
    - execution/                      -- 発注実行関連（プレースホルダ）
      - __init__.py
    - monitoring/                     -- 監視関連（プレースホルダ）
      - __init__.py

data フォルダ内には DuckDB ファイル（デフォルト: data/kabusys.duckdb）が置かれます。

---

## 開発時のヒント

- 自動 .env 読み込みはプロジェクトルートの検出に依存するため、ローカルでテストする際は .git または pyproject.toml が存在することを確認してください。CWD に依存せず __file__ を基点に探索します。
- テスト時に外部ネットワークを切り替えたい／API コールをモックしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にしたり、モジュールレベル関数（例: news_collector._urlopen）をモックすることで簡単に差し替え可能です。
- DuckDB は軽量でインメモリモード(":memory:") が使えるためユニットテストで便利です（init_schema(":memory:")）。

---

## ライセンス / 貢献

（この README にライセンス情報は含まれていません。公開時は LICENSE ファイルを追加してください。）

バグや改善提案があれば Issue を立ててください。プルリクエスト歓迎です。

---

この README はコードベースの主要機能・設定・使い方のガイドです。個別モジュールの詳細な API は各モジュールの docstring を参照してください。