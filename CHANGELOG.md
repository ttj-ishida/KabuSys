# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
比較的安定したリリース履歴を人間が把握しやすいように、機能追加・変更・修正・セキュリティ対策を分類しています。

※バージョンおよび日付はソース内の __version__（0.1.0）および本ファイル作成日を基にしています。

## [Unreleased]
- （現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期リリース: kabusys 0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"、公開モジュール: data, strategy, execution, monitoring）。
- 環境設定管理モジュール（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env 行パーサ（export プレフィックス、シングル/ダブルクォート、インラインコメント対応）。
  - 必須環境変数取得関数と Settings クラス（J-Quants / kabu API / Slack / DB パス / 環境・ログレベルの検証プロパティなど）。
  - 環境値の妥当性チェック（KABUSYS_ENV, LOG_LEVEL の許容値検証）。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しの共通実装（_request）を提供。JSON デコードチェック、タイムアウト設定、詳細ログ出力。
  - レート制御（120 req/min を満たす固定間隔スロットリング _RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
  - 401 応答時の id_token 自動リフレッシュ（1 回のみ）とトークンキャッシュ共有（ページネーション間での再利用）。
  - データ取得関数：fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（いずれもページネーション対応、フェッチ時のログ）。
  - DuckDB へ冪等保存する save_* 関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT を使った更新処理を実装。
  - fetched_at を UTC ISO8601 で記録し、データ取得時刻を明示（Look-ahead bias 対策）。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し不正値を安全に扱う。
- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得・記事整形・DB 保存の一連処理を提供（DEFAULT_RSS_SOURCES に Yahoo Finance の RSS を追加）。
  - セキュリティと堅牢性:
    - defusedxml を使用した XML パース（XML Bomb 等に対する防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベート/ループバック/リンクローカルの拒否、リダイレクト時の事前検証ハンドラ（_SSRFBlockRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - User-Agent / Accept-Encoding 設定。
  - URL 正規化（トラッキングパラメータ除去、フラグメント除去、クエリソート）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - RSS からのパース（content:encoded 優先、description 代替、pubDate の RFC 2822 パース）と記事型 NewsArticle。
  - DuckDB へのバルク保存:
    - save_raw_news：チャンク化、トランザクション、INSERT ... ON CONFLICT DO NOTHING RETURNING id により実際に挿入された記事 ID を返す。
    - save_news_symbols / _save_news_symbols_bulk：記事と銘柄コードの紐付けをバルク保存、ON CONFLICT による重複排除と実挿入数の返却。
  - 銘柄コード抽出ロジック（4桁数字パターン、既知コードセットによるフィルタリング、重複除去）。
  - 統合収集ジョブ run_news_collection：複数ソースを順次処理、ソース毎に独立してエラーハンドリング、既知銘柄コードに対する紐付け処理を実施。
- スキーマ定義・初期化モジュール（src/kabusys/data/schema.py）
  - DuckDB 用スキーマを定義（Raw / Processed / Feature / Execution の 3 層＋実行層）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw レイヤー、prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー、features, ai_scores の Feature レイヤー、signals / signal_queue / orders / trades / positions / portfolio_performance 等の Execution レイヤーを定義。
  - 各テーブルに型チェック・制約（CHECK、PRIMARY KEY、FOREIGN KEY）を設定。
  - パフォーマンスを考慮したインデックスを作成（頻出クエリパターンに基づく）。
  - init_schema(db_path) により DB ファイルの親ディレクトリを作成し、DDL を順次実行して初期化。get_connection() を提供。
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETLResult データクラス（結果、品質問題、エラーの集約、has_errors / has_quality_errors プロパティ、to_dict メソッド）。
  - 差分更新ヘルパー（テーブル存在チェック、最終取得日取得 get_last_* 系関数）。
  - 市場カレンダーを考慮した trading day 補正関数 _adjust_to_trading_day（最大30日遡る）。
  - run_prices_etl：差分取得ロジック（最終取得日から backfill_days を使って再取得）、デフォルト backfill_days = 3、_MIN_DATA_DATE（2017-01-01）を考慮した初回ロードフォールバック。取得→保存の流れを実装。
  - 品質チェックモジュール（quality）との連携点を想定（実装は外部モジュールを参照する形）。
- テスト性を考慮した設計
  - _urlopen 等一部関数をモック差し替え可能にしてユニットテスト容易化。
  - id_token 注入可能（テスト用token注入でリクエストの副作用を制御）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集における複数のセキュリティ対策を追加:
  - defusedxml による安全な XML パース。
  - SSRF 対策（スキーム検証、ホストのプライベートアドレスチェック、リダイレクト検査）。
  - レスポンスサイズ上限と gzip 解凍後のサイズ検証による DoS / Bomb 対策。
  - 不正スキームやローカル資源へのアクセスを拒否。

### Notes / Design Decisions
- API レート制御は固定間隔スロットリングを採用（簡潔で確実なレート順守を優先）。
- リトライは指数バックオフを採用し、429 の場合は Retry-After ヘッダを優先。
- DuckDB への保存はできる限り冪等（ON CONFLICT ... DO UPDATE / DO NOTHING）にして再実行耐性を確保。
- データ取得時刻（fetched_at）を UTC で必ず記録し、将来的な検証・監査・Look-ahead バイアス解析に利用可能。
- ニュース記事 ID の生成はトラッキングパラメータ除去後の正規化 URL をハッシュ化して安定した重複排除を実現。

---

If you want, 次のことができます:
- リリースノートを英語版でも生成
- マイナーバージョンの変更方針・チケット管理スタイルに合わせたテンプレート調整
- 実際の変更日やコミットハッシュを追記する

必要なら追加で出力します。