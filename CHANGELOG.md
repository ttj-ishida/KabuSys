Changelog
=========

すべての重要な変更点をこのファイルで管理します。  
フォーマットは "Keep a Changelog" に準拠します。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-18
--------------------

Added
- 初期リリースを追加。
- パッケージ構成:
  - kabusys パッケージの公開 API を定義（__version__ = 0.1.0、data/strategy/execution/monitoring をエクスポート）。
- 環境変数/設定管理（kabusys.config）を追加:
  - .env / .env.local の自動ロード（プロジェクトルートの検出は .git または pyproject.toml を基準）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、コメント処理のルール。
  - override / protected 機能で OS 環境変数を保護して .env.local を上書き可能。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等をプロパティで取得。値検証（KABUSYS_ENV, LOG_LEVEL）を実施。
- J-Quants API クライアント（kabusys.data.jquants_client）を追加:
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得 API を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守（内部 RateLimiter）。
  - リトライ実装: 指数バックオフ、最大 3 回、ネットワーク系/429/408/5xx に対する再試行。
  - 401 応答時の自動 ID トークンリフレッシュ（1 回のみ）とトークンキャッシュの共有（ページネーション間で再利用）。
  - ページネーション対応（pagination_key を利用して全ページ取得）。
  - DuckDB へ保存する save_* 関数群（save_daily_quotes、save_financial_statements、save_market_calendar）を実装。ON CONFLICT ... DO UPDATE による冪等保存、fetched_at を UTC で記録。
  - JSON デコード失敗や HTTP エラー発生時の詳細ログと例外整備。
- ニュース収集モジュール（kabusys.data.news_collector）を追加:
  - RSS フィード取得 → テキスト前処理 → raw_news への冪等保存 → 銘柄紐付け の ETL フローを実装。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 等対策）。
    - SSRF 対策: リダイレクトハンドラでスキーム検査・プライベートアドレス検査（_SSRFBlockRedirectHandler）を実装。
    - URL スキーム制限（http/https のみ）とホストがプライベートかどうかの検査。
    - 応答サイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化URL の SHA-256 の先頭32文字）。
  - テキスト前処理（URL除去・空白正規化）と銘柄コード抽出（4桁数字パターン、known_codes と照合）。
  - DB 保存ロジック:
    - save_raw_news: チャンク分割・トランザクション・INSERT ... RETURNING により新規挿入IDを返却、ON CONFLICT DO NOTHING。
    - save_news_symbols / _save_news_symbols_bulk: 銘柄紐付けをまとめて挿入し新規件数を返却、トランザクション管理。
  - デフォルト RSS ソース（yahoo_finance のビジネスカテゴリ）を定義。
- DuckDB スキーマ（kabusys.data.schema）を追加:
  - DataPlatform 設計に基づく 3 層（Raw / Processed / Feature） + Execution レイヤのテーブル群を定義。
  - 主なテーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等。
  - 制約（PRIMARY KEY、CHECK、FOREIGN KEY）および検索用インデックス（code/date、status、order_id 等）を定義。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とテーブル／インデックス作成を行う（冪等）。
  - get_connection(db_path) を提供（スキーマ初期化は行わない）。
- ETL パイプライン基盤（kabusys.data.pipeline）を追加:
  - ETLResult データクラス: ETL 実行結果・品質問題リスト・エラーリストを格納し、辞書化機能を提供。
  - 差分更新サポート: DB 内の最終取得日から差分を決めるユーティリティ（get_last_price_date / get_last_financial_date / get_last_calendar_date）。
  - 営業日調整ユーティリティ (_adjust_to_trading_day) を実装（market_calendar に基づき、過去方向の最も近い営業日に調整）。
  - run_prices_etl の基本ロジックを実装: 最後の取得日から backfill_days 分を遡って差分取得、J-Quants クライアントで取得し save_daily_quotes で保存（差分更新・バックフィル機能）。
  - カレンダー先読み・バックフィルや品質チェック（quality モジュールを想定）の設計を反映。
- その他:
  - 各モジュールで詳細なログ出力を実装（情報・警告・例外）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- defusedxml, SSRF 防止ハンドラ、応答サイズ上限、URL スキーム検証等を導入し、外部データ取り込み時の攻撃ベクタ（XML Bomb / Gzip Bomb / SSRF / 不正スキーム）に対処。

Notes / Implementation details
- J-Quants クライアントは 120 req/min を前提とした固定間隔スロットリングを採用。429 の場合は Retry-After を優先して待機。
- DuckDB 側は可能な限り冪等性を確保（ON CONFLICT DO UPDATE / DO NOTHING）して再実行に強い設計。
- news_collector は既知の銘柄コード集合（known_codes）を渡すことで誤検出を低減する想定。
- Settings の env/log_level の値検証により、運用環境・ログレベル設定の誤入力を早期に検出。

Known limitations / TODO
- strategy と execution パッケージはエントリポイントを用意しているものの、具象実装は含まれていない（将来的な拡張対象）。
- quality モジュールは pipeline で参照される設計になっているが、実装の詳細は別途提供が必要（品質チェックの具体的なルールと実行）。
- run_prices_etl 等の ETL 関数は基本ロジックを実装済みだが、運用での例外処理・詳細な監査ログ・メトリクス出力は今後強化予定。

Acknowledgments
- 初期設計は DataPlatform.md / DataSchema.md 等の設計資料に基づき実装されています。