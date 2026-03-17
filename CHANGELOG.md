# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-17
初回リリース — 日本株自動売買システムの骨子を実装。

### Added
- パッケージ初期化
  - パッケージメタ情報と公開モジュールを定義（src/kabusys/__init__.py、バージョン: 0.1.0）。
  - 空のサブパッケージ スタブを追加（strategy、execution、data、monitoring を公開）。

- 環境設定管理（src/kabusys/config.py）
  - プロジェクトルート自動検出: .git または pyproject.toml を基準に .env 自動ロード。
  - .env ファイルパーサ実装:
    - `export KEY=val` 形式やシングル/ダブルクォート、バックスラッシュエスケープに対応。
    - 行末コメントの扱いや無効行スキップ処理。
  - .env の読み込み順序: OS 環境変数 > .env.local > .env、.env.local は上書き（protected 機能により OS 環境変数は保護）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テスト用途）。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの取得とバリデーションを行う。
  - is_live/is_paper/is_dev の便利プロパティを追加。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しの共通実装:
    - レート制限（固定間隔スロットリング）を実装（120 req/min を遵守する RateLimiter）。
    - リトライロジック（指数バックオフ、最大3回）。429 の場合は Retry-After ヘッダを尊重。
    - 401 受信時の自動トークンリフレッシュ（1回のみ）とモジュールレベルのトークンキャッシュ。
    - JSON デコード失敗時の明確なエラーメッセージ化。
    - ページネーション対応（pagination_key を使った連続取得）。
  - データ取得関数を追加:
    - fetch_daily_quotes（株価日足 OHLCV、ページネーション対応）
    - fetch_financial_statements（四半期財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB 保存関数（冪等性を重視）:
    - save_daily_quotes / save_financial_statements / save_market_calendar：ON CONFLICT を用いた upsert 実装。
    - fetched_at を UTC タイムスタンプで記録し、Look-ahead Bias を追跡可能に。
  - 型変換ユーティリティ _to_float / _to_int を追加し、空値や不正値に対する堅牢性を確保。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集処理を実装（デフォルトに Yahoo Finance を含む）。
  - セキュリティおよび堅牢性強化:
    - defusedxml を使用した XML パース（XML Bomb 等対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストがプライベート/ループバック/リンクローカルかを判定してブロック、リダイレクトハンドラでリダイレクト先も検査。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を導入し、読み込み超過時はスキップ。
    - gzip 圧縮応答の安全な解凍とサイズ再検査。
  - コンテンツ処理:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリキーソート）。
    - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
    - テキスト前処理（URL 除去、空白正規化）。
    - 日本株銘柄コード抽出（4桁数値、known_codes によるフィルタリング）。
  - DB 保存:
    - save_raw_news：チャンク化して一括 INSERT、ON CONFLICT DO NOTHING、INSERT ... RETURNING で実際に挿入された記事IDを返す、トランザクションでまとめて性能と一貫性を確保。
    - save_news_symbols / _save_news_symbols_bulk：記事と銘柄の紐付けを一括保存、重複除去、チャンク処理、INSERT ... RETURNING により実際に新規挿入された件数を返す。

- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataSchema.md に基づく多層スキーマを定義:
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルの制約（PRIMARY KEY、CHECK、FOREIGN KEY）を整備。
  - 頻出クエリ向けインデックス定義を追加。
  - init_schema(db_path) を実装し、親ディレクトリ自動作成とテーブル/インデックスの冪等作成を行う。
  - get_connection(db_path) で既存 DB への接続を取得可能。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL の設計方針に基づく初期実装:
    - 差分更新ロジック（DB の最終取得日を参照し未取得分のみ取得）。
    - backfill_days による数日前からの再取得で API の後出し修正を吸収（デフォルト 3 日）。
    - 市場カレンダーの先読み（lookahead 日数定義あり）。
    - ETLResult dataclass を導入し、取得数／保存数／品質問題／エラー等を集約して返却可能に。
    - テーブル存在チェック、最大日付取得ユーティリティを提供（get_last_price_date 等）。
    - run_prices_etl の骨組み（date_from 自動計算、fetch→save を実行）を追加。
  - 品質チェック（quality モジュール）との連携ポイントを用意（品質問題は ETLResult に保持）。

### Security
- RSS パーサで defusedxml を使用（XML パーサ攻撃対策）。
- ニュース収集で SSRF 対策を実装（スキーム検証、プライベートホスト検出、リダイレクト検査）。
- .env 読み込み時に OS 環境変数を保護する仕組みを導入（.env.local の上書き制御と protected set）。

### Internal
- モジュールレベルのトークンキャッシュ（jquants_client）を導入し、ページネーション間でトークン再利用と効率化を実現。
- レート制御やリトライの共通ロジックを centralize（jquants_client._request, _RateLimiter）。
- news_collector でテスト時に _urlopen を差し替え可能にしてモックを容易にする設計。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Breaking Changes
- （初回リリースのため該当なし）

---

注:
- 本 CHANGELOG はコードベース（src/ 以下）から推測して作成しています。実際の設計文書（DataPlatform.md、DataSchema.md 等）や追加のユーティリティ・外部依存（quality モジュール等）はリポジトリ外にある想定です。