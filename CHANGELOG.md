# Changelog

すべての重要な変更点をこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
https://keepachangelog.com/ja/

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主にデータ収集・保存・スキーマ定義・環境設定・ETL パイプラインの基盤となるモジュールを含みます。

### Added
- パッケージ初期化
  - `kabusys.__init__` にバージョン情報 `0.1.0` と公開モジュール一覧を追加。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装（優先度: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出ロジック（`.git` または `pyproject.toml` を起点）を実装し、CWD に依存しない自動読み込みを実現。
  - .env パーサーの実装（`export KEY=val`、クォート内のエスケープ、行内コメント処理をサポート）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を導入（テスト用）。
  - 必須環境変数取得ヘルパ `_require` と `Settings` クラスを実装。J-Quants／kabuステーション／Slack／DB パス等の設定プロパティを提供。
  - 環境（development/paper_trading/live）とログレベルの検証を実装。`is_live` / `is_paper` / `is_dev` ヘルパ付き。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API クライアントを実装。日足（OHLCV）、四半期財務、マーケットカレンダーの取得関数を追加。
  - レート制限 (120 req/min) を守る固定間隔スロットリング `_RateLimiter` を導入。
  - リトライ戦略（指数バックオフ、最大 3 回、対象ステータスコード 408/429/5xx）を実装。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動的に id_token を更新して 1 回リトライする処理を実装（再帰防止フラグあり）。
  - id_token のモジュールレベルキャッシュを導入し、ページネーション間で再利用。
  - ページネーション対応（pagination_key）で全件フェッチする実装。
  - DuckDB への保存関数（`save_daily_quotes` / `save_financial_statements` / `save_market_calendar`）を実装。いずれも冪等性を保つため ON CONFLICT 句で更新を行う。

- RSS ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードから記事を収集する `fetch_rss` / `run_news_collection` を実装。
  - RSS の XML パースに defusedxml を採用し XML-Bomb 等の攻撃対策を行う。
  - URL 正規化（スキーム・ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）と SHA-256 による記事 ID 生成（先頭32文字）を採用し冪等性を確保。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）
    - ホスト/IP がプライベート/ループバック/リンクローカル/マルチキャストであれば拒否
    - リダイレクト時にスキームとホストを検査する専用ハンドラ `_SSRFBlockRedirectHandler`
  - レスポンスサイズ制限（最大 10MB）と gzip 解凍後のサイズチェックを実装（メモリ DoS 対策）。
  - RSS の pubDate をパースして UTC に正規化するユーティリティを提供（失敗時は警告ログと現在時刻で代替）。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DuckDB への保存処理:
    - `save_raw_news`: チャンク挿入、トランザクション、`INSERT ... ON CONFLICT DO NOTHING RETURNING id` により新規挿入IDを正確に取得。
    - `save_news_symbols` / `_save_news_symbols_bulk`: 記事と銘柄コードの紐付けをバルク挿入（ON CONFLICT DO NOTHING RETURNING 1）で正確にカウント。
  - 銘柄コード抽出ユーティリティ `extract_stock_codes`（4桁数字、既知コードセットとの照合、重複排除）を追加。
  - デフォルト RSS ソースに Yahoo Finance（ビジネスカテゴリ）を追加。

- DuckDB スキーマ定義と初期化 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を追加。
  - 各テーブルの制約（CHECK, PRIMARY KEY, FOREIGN KEY）とインデックスを定義。
  - `init_schema(db_path)` でディレクトリ作成 → DuckDB 接続 → 全 DDL とインデックスを実行して初期化するユーティリティを実装（冪等）。
  - `get_connection(db_path)` で既存 DB の接続を取得（スキーマ初期化は行わない）。

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL の設計に基づく差分更新ロジックとヘルパ関数を追加:
    - DB 最終取得日を取得するユーティリティ (`get_last_price_date` / `get_last_financial_date` / `get_last_calendar_date`)。
    - 非営業日調整 `_adjust_to_trading_day`（market_calendar を参照し最大 30 日遡る）。
    - ETL 実行結果を表すデータクラス `ETLResult`（品質問題やエラーの集約、シリアライズ用 `to_dict`）。
  - 株価差分ETL `run_prices_etl`（差分取得、backfill 日数考慮、J-Quants からの取得 → DuckDB 保存）を追加。
  - 初回ロード用の最小データ日付定義 `_MIN_DATA_DATE`、カレンダー先読み・バックフィル等の定数を定義。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- RSS 周りで以下の対策を実装（SSRF / XML / DoS 対策）
  - defusedxml を用いた安全な XML パース。
  - リクエスト先のスキーム検証（http/https のみ）。
  - リダイレクトの事前検査（スキーム/ホスト検証）で内部アドレスへの到達を防止。
  - DNS 解決したすべての A/AAAA レコードを検査してプライベート IP を検出、拒否。
  - レスポンス読み込み上限（10 MB）と gzip 解凍後のサイズ検査。
- J-Quants クライアントにおいて、認証トークン更新時の無限再帰を防止する設計（allow_refresh フラグ、1 回のみのリフレッシュ）。

---

開発中の注意点 / 既知の制約
- DuckDB スキーマは初期化時に作成されるため、スキーマ変更（DDL 追加・変更）はマイグレーションを別途検討する必要があります。
- J-Quants API のレート制限・リトライ動作は実行環境の時間精度やネットワーク状況に依存します。テスト時は `_rate_limiter` や id_token のキャッシュをモックすることを推奨します。
- RSS フェッチ用の低レベル関数 `_urlopen` はテストのために差し替え可能に設計されています（モック推奨）。
- news_collector の記事 ID は URL 正規化ルールに依存するため、URL 正規化ルールを変更すると既存 ID と一致しなくなり重複挿入のリスクが発生します。

今後の予定（例）
- ETL の品質チェックモジュール（quality）との統合強化、及び品質問題に対する通知/アクション実装。
- 戦略実装層（strategy）と発注実行層（execution）の具体的な実装追加。
- マイグレーション機能の追加（スキーマ変更対応）。
- 単体テストの充実（外部 API やネットワークに依存する部分のモック整備）。

（以上）