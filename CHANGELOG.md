CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

フォーマット:
- Unreleased: 現在の開発中の変更・既知の問題
- 各リリース: 追加・変更・修正・セキュリティ等を区分して記載

Unreleased
----------
※コードベースから推測した現在の開発状態・既知問題

Added
- ETL パイプラインの骨組み（kabusys.data.pipeline に ETLResult 等の型、ヘルパー関数を追加）。
- run_prices_etl 関数（差分取得ロジック、backfill 処理、jquants_client 呼び出し）を追加。

Known issues / TODO
- run_prices_etl の戻り値が未完成（ソースファイルの末尾で "return len(records), " のように片方の値しか返していない箇所が存在）。正しくは (fetched, saved) の 2 要素タプルを返す想定。修正が必要。
- pipeline モジュール内で品質チェック（quality モジュール連携）や他の ETL ジョブ（財務データ、カレンダー等）の統合的な実行フローがまだ整備途中。テスト・例外ハンドリングの追加を推奨。

0.1.0 - 初期リリース (仮)
-----------------------

Added
- パッケージ概要
  - kabusys パッケージの初期実装。__version__ = "0.1.0" に設定。

- 環境設定管理 (src/kabusys/config.py)
  - プロジェクトルート検出機能: .git または pyproject.toml を起点に自動検出し、.env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサ: export 形式、シングル/ダブルクォート、インラインコメント処理、エスケープ処理に対応。
  - OS 環境変数保護: 自動ロード時に既存環境変数を保護する仕組みを導入（.env.local は override=true だが protected により OS 環境が上書きされない）。
  - Settings クラス: 各種必須設定（J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン・チャンネルなど）をプロパティで提供。環境名・ログレベルの検証ロジックあり。
  - デフォルト DB パス（DuckDB/SQLite）や KABU_API_BASE_URL のデフォルト値を提供。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ (_request): レート制限、リトライ（指数バックオフ、対象ステータス 408/429/5xx、最大 3 回）、JSON デコード検証、401 でのトークン自動リフレッシュ（1回）を実装。
  - 固定間隔レートリミッタ (_RateLimiter): 120 req/min を守る。
  - トークンキャッシュ機能: モジュールレベルの ID トークンキャッシュを共有してページネーション間の再利用を行う。
  - 認証: get_id_token により refresh_token から idToken を取得。
  - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar をページネーション対応で実装。
  - DuckDB 保存関数: save_daily_quotes, save_financial_statements, save_market_calendar。fetched_at を UTC ISO 形式で保存し、冪等性のために INSERT ... ON CONFLICT DO UPDATE を利用。
  - 型安全な変換ユーティリティ: _to_float / _to_int により入力の不正値を抑制。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集: fetch_rss により RSS を取得し、記事を正規化してリスト化。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定（DNS 解決して A/AAAA を検査）、リダイレクト時の検証を行う専用リダイレクトハンドラ (_SSRFBlockRedirectHandler) を使用。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）を設け、gzip 解凍後もサイズチェック。
  - コンテンツ前処理: URL 除去、空白正規化、content:encoded の優先採用などを実装。
  - 記事 ID の冪等化: _normalize_url でトラッキングクエリパラメータを削除し、SHA-256 の先頭 32 文字を記事 id として採用。
  - DB 保存: save_raw_news はチャンク化したバルク INSERT を行い、ON CONFLICT DO NOTHING と INSERT ... RETURNING により実際に挿入された ID を返す。news_symbols の単一/一括保存関数も実装。
  - 銘柄抽出: 正規表現で 4 桁の数字を抽出し、与えられた known_codes セットと照合する extract_stock_codes を実装。
  - 上記を組み合わせた統合ジョブ run_news_collection を提供（ソース毎に独立してエラー処理し続行）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution レイヤーにまたがる DDL を定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
  - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）やインデックス（銘柄×日付検索やステータス検索に有用なインデックス）を明示。
  - init_schema により DB ファイルの親ディレクトリ自動作成、全テーブル／インデックスの冪等作成を実装。
  - get_connection を提供（既存 DB への接続）。

- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass: ETL 実行結果の集計（取得数、保存数、品質問題、エラー等）を保持し、to_dict でシリアライズ可能。
  - テーブル存在確認・最大日付取得ユーティリティ（_table_exists, _get_max_date）。
  - 市場カレンダーに基づく営業日調整 (_adjust_to_trading_day)。
  - 差分更新ヘルパー: get_last_price_date, get_last_financial_date, get_last_calendar_date。
  - run_prices_etl を実装（最終取得日からの backfill 処理、jq.fetch_daily_quotes / jq.save_daily_quotes 呼び出し）。

Security
- defusedxml の採用により XML 関連の脆弱性を低減。
- RSS フェッチにおける SSRF 対策（スキーム検証、プライベートホスト判定、リダイレクト時検証）。
- .env ロード時に OS 環境を保護するロジックを導入。

Performance / Reliability
- J-Quants クライアントでのレートリミット実装とリトライ（指数バックオフ）により API 制限・一時的障害に耐性を持たせた。
- トークンキャッシュでページネーション耐性を向上。
- DuckDB 側はバルク挿入・チャンク化・トランザクションでオーバーヘッドを低減。
- ON CONFLICT を多用して冪等性を確保。

Internal / Developer notes
- kousys.config の自動 .env ロードはプロジェクトルート検出に依存するため、パッケージ配布後の動作を考慮した設計。ただしテスト時の制御用に KABUSYS_DISABLE_AUTO_ENV_LOAD を提供。
- news_collector._urlopen はテストでモック可能な設計（テスト容易性を考慮）。

Fixed
- （初期リリースのため該当なし）

Removed / Deprecated
- （初期リリースのため該当なし）

Security (注意)
- RSS フィードの処理は多数の防御策を導入しているが、外部 URL 取得に関わる処理は引き続き慎重な運用（プロキシやネットワーク ACL、追加のホワイトリスト）を推奨。

次の推奨作業
- run_prices_etl の戻り値バグ修正（fetched と saved の両方を返す）。
- pipeline の他ジョブ（財務データ / カレンダー / 品質チェック）の実装完了と統合ワークフロー作成。
- 単体テスト・統合テストの追加（外部 API のモック、_urlopen の差し替え等）。
- ドキュメント補強（DataPlatform.md / DataSchema.md 参照を README にまとめる等）。
- 運用向け: ローテーション/バックアップ方針、機密情報の管理（Vault 等）検討。

--- 

（注）本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のリリースノートやバージョン運用ポリシーと差異がある可能性があります。必要であれば、コミット履歴やリリースタグに基づく詳細な変更履歴に書き換えます。