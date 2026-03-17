CHANGELOG.md
=============

すべての重要な変更点を記録します。形式は「Keep a Changelog」に準拠しています。
（以下の記載は提示されたコードベースの内容から推測して作成しています。）

Unreleased
----------

（なし）

[0.1.0] - 2026-03-17
-------------------

初回公開リリース（推測）。日本株自動売買プラットフォームのコア機能群を実装しています。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring サブパッケージを定義。
  - バージョン番号を `__version__ = "0.1.0"` として設定。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能: プロジェクトルート（.git または pyproject.toml）を検出して .env/.env.local を読み込む（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - .env パーサは export プレフィックス、シングル/ダブルクォートやバックスラッシュエスケープ、行内コメントの扱いに対応。
  - 必須変数取得時の検証（未設定時は ValueError）。
  - 環境モード（development, paper_trading, live）とログレベル（DEBUG/INFO/...）の検証プロパティを提供。
  - DB ファイルパス（DuckDB/SQLite）や Slack / kabu station / J-Quants のトークン設定プロパティを提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 株価日足、財務データ（四半期 BS/PL）、JPX マーケットカレンダーの取得関数を実装（ページネーション対応）。
  - RateLimiter による固定間隔スロットリングで API レート制限（120 req/min）を順守。
  - リトライロジック（指数バックオフ、最大3回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized 受信時の自動トークンリフレッシュ（1 回のみ）と再試行を実装。
  - get_id_token によるリフレッシュトークン→IDトークン取得（POST）。
  - データ取得は「取得日時（fetched_at）」を UTC で記録し、Look-ahead bias のトレースを可能に。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等性を確保（ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し不正値に対処。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得し raw_news テーブルへ保存する一連の処理を実装。
  - 記事IDは URL 正規化（トラッキングパラメータ除去、クエリ整列、スキーム/ホストの小文字化、フラグメント削除）後に SHA-256 の先頭32文字で生成し冪等性を確保。
  - defusedxml を使用した XML パース（XML Bomb 等への対策）。
  - SSRF 対策:
    - fetch 時に HTTP リダイレクト先のスキームとホストを検査するカスタムリダイレクトハンドラを導入。
    - プライベート/ループバック/リンクローカル/マルチキャストアドレスへのアクセスを拒否（DNS 解決で A/AAAA を検査）。
    - http/https スキーム以外を拒否。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後のサイズ検査を導入（メモリDoS/Gzip-bomb 対策）。
  - トラッキングパラメータ（utm_*, fbclid 等）をクエリから削除。
  - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存はチャンク単位・トランザクションで行い、INSERT ... RETURNING を用いて実際に挿入された行だけを返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
  - 銘柄コード抽出（4桁数字）と既知銘柄セットによるフィルタリング（extract_stock_codes）。
  - デフォルト RSS ソース（例: Yahoo Finance のビジネスカテゴリ）を定義。
  - run_news_collection により複数ソースの収集→保存→銘柄紐付けを一括実行（ソース単位で障害隔離）。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema.md を想定した DuckDB の DDL を実装し、Raw / Processed / Feature / Execution 層のテーブルを定義。
  - テーブル例: raw_prices, raw_financials, raw_news, market_calendar, prices_daily, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス（頻出クエリ向け）を定義。
  - init_schema(db_path) でディレクトリ作成→スキーマ作成（冪等）→接続返却。get_connection は既存 DB への接続を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult データクラスを導入し、ETL 結果・品質問題・エラーを集約できる設計。
  - 差分更新ユーティリティ（最終取得日の照会、営業日調整）を実装（get_last_price_date, get_last_financial_date, get_last_calendar_date, _adjust_to_trading_day 等）。
  - run_prices_etl 実装（差分取得、backfill_days による遡り、jquants_client の fetch/save 呼び出し）。品質チェック（quality モジュール）を統合する設計になっている（quality モジュールは別途実装想定）。
  - ETL の設計指針: 差分更新、後出し修正吸収（backfill）、品質チェックはエラー重大度に応じて呼び出し元が対処する方針（Fail-fast しない）。

### Security
- ニュース収集における SSRF 対策、defusedxml による XML パースの安全化、受信サイズ・gzip 解凍後サイズのチェックを追加。
- .env 読み込みで OS 環境変数を保護する仕組み（.env.local の上書き制御や protected set）を実装。

### Performance / Reliability
- J-Quants クライアントでレート制限と指数バックオフ付きリトライを導入し API 呼び出しの安定性を向上。
- DuckDB へのバルク INSERT をチャンク化しトランザクションをまとめることでオーバヘッドを削減。
- ニュースの銘柄紐付けや raw_news 保存において ON CONFLICT / RETURNING を使用し冪等性と正確な集計を実現。

### Known / Noted
- run_prices_etl を含む ETL モジュールは設計に従った実装を行っているが、提示されたコードは一部が抜粋されているため（末尾の処理が途中で切れている箇所あり）完全実装は別箇所で継続されている可能性があります。
- quality モジュールは参照されているが、このスナップショット内に定義は含まれていません（別ファイルで実装想定）。

### Deprecated
- なし

### Removed
- なし

References
----------
- この CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートや履歴はプロジェクトの git 履歴やリリース管理（タグ・コミットログ）に基づいて正式に作成してください。