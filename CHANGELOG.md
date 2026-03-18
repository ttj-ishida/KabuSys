Keep a Changelog に準拠した形式で、このコードベースから推測される変更履歴を日本語で作成しました。初回リリース（v0.1.0）としての追加内容・設計意図・セキュリティ対応等をまとめています。

CHANGELOG.md
=============

このプロジェクトの変更履歴は Keep a Changelog の形式に従っています。
https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （今後の変更をここに記載）

0.1.0 - 2026-03-18
------------------

Added
- 初期リリース。パッケージ名: kabusys、バージョン 0.1.0 を導入。
- パッケージの公開 API を定義（src/kabusys/__init__.py）。
- 環境設定モジュールを追加（src/kabusys/config.py）
  - .env / .env.local の自動読み込み機能（プロジェクトルート判定は .git または pyproject.toml を参照）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサは export KEY=val、クォートやインラインコメント、バックスラッシュエスケープに対応。
  - 必須環境変数取得ヘルパー _require と Settings クラス（J-Quants、kabu API、Slack、DB パス、環境/ログレベル判定など）。
  - 環境値のバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と利便性プロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアントを追加（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - API レート制御: 固定間隔スロットリング実装で 120 req/min を遵守（内部 RateLimiter）。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の Retry-After ヘッダ優先。
  - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止の allow_refresh フラグ）。
  - ページネーション対応（pagination_key を使ったフェッチ）。
  - JSON デコード失敗やネットワークエラーの明示的なハンドリング。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等性を考慮（ON CONFLICT DO UPDATE）し、PK 欠損レコードはスキップして警告ログ出力。
  - 辞書→型変換ユーティリティ（_to_float, _to_int）を提供し不正値を安全に扱う。
  - get_id_token: リフレッシュトークンから idToken を取得する POST 実装。

- ニュース収集モジュールを追加（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news / news_symbols へ保存する ETL（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ・堅牢性:
    - defusedxml を利用した XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト前後のスキーム検証、ホストのプライベート/ループバック/リンクローカル判定（IP 直接判定 + DNS 解決）。
    - 許可スキームは http/https のみ。
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - リダイレクト検査用ハンドラ（_SSRFBlockRedirectHandler）と交換可能な _urlopen（テスト用にモック可能）。
  - 記事 ID は URL を正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）した上で SHA-256（先頭32文字）で生成して冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）と pubDate の RFC2822 -> UTC 変換。
  - DB 操作:
    - save_raw_news はチャンク分割して INSERT ... ON CONFLICT DO NOTHING RETURNING id を利用し、実際に挿入された記事IDリストを返す。トランザクションでまとめて処理し失敗時はロールバック。
    - save_news_symbols / _save_news_symbols_bulk も INSERT ... RETURNING を使用し正確な挿入数を返す。重複除去・チャンク処理・トランザクションをサポート。
  - 銘柄コード抽出ユーティリティ（4桁数字パターンと known_codes フィルタ）を提供。
  - デフォルト RSS ソースに Yahoo! Finance のビジネスカテゴリ RSS を追加。

- DuckDB スキーマ定義モジュールを追加（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層を含む包括的なテーブル定義を提供（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）。
  - 各カラムに CHECK 制約や PRIMARY KEY / FOREIGN KEY を付与してデータ整合性を担保。
  - 頻出クエリ向けのインデックスを複数定義。
  - init_schema(db_path) でファイルの親ディレクトリ自動作成、DDL を一括実行して初期化（冪等）。get_connection は既存接続を返すヘルパー。

- ETL パイプラインの骨組みを追加（src/kabusys/data/pipeline.py）
  - 差分更新 方針（最終取得日からの差分・backfill_days による再取得）を実装するユーティリティ群。
  - ETLResult dataclass により ETL 結果（取得/保存数、品質チェック結果、エラー一覧）を集約。品質問題はシリアライズ可能。
  - テーブル存在チェック、最大日付取得ヘルパー（_table_exists, _get_max_date）。
  - 市場カレンダーに基づき営業日へ調整する _adjust_to_trading_day。
  - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供。
  - run_prices_etl の骨組みを追加（差分算出、fetch -> save 呼び出し、ログ出力）。バックフィル・最小データ日付の考慮あり。

- テスト容易性を考慮した設計箇所を多数追加
  - _urlopen の差し替え、id_token 注入、allow_refresh フラグ、モジュールレベルのトークンキャッシュなど。

Security
- セキュリティ対策を明確に実装:
  - RSS 周りでの SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト時の検査）。
  - XML パースに defusedxml を利用。
  - レスポンスサイズ制限・gzip 解凍後チェックによるメモリ DoS / Gzip bomb 対策。
  - 外部 API への再試行制御とバックオフ、認証トークンの安全なリフレッシュ処理。

Documentation / Logging
- 各モジュールに詳細な docstring を追加（設計原則や処理フロー、引数/戻り値/例外の説明）。
- 主要処理にログ出力を追加し、運用時のトラブルシュートに配慮。

Notes / Implementation details
- DB 保存は基本的に冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING、INSERT ... RETURNING）。
- API クライアントはページネーション・トークン共有・キャッシュを考慮。
- 数値変換ユーティリティは不正な浮動小数・空文字を None として扱うことでデータ品質を保つ。
- run_news_collection はソース単位でエラーハンドリングを行い、1 ソースの失敗が他に影響しないように設計。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security (追加情報)
- RSS フィード処理での外部からの攻撃面（SSRF、XML Bomb、巨大レスポンス）に対して複数の防御層を導入。
  - これにより外部フィード取り込み時の運用リスクを低減。

今後の予定（想定）
- pipeline モジュールの品質チェック（quality モジュール）統合と自動エラー対応ルールの実装。
- execution 層の実装（kabu ステーションとの発注連携、注文監視、ポジション管理）。
- 単体テスト・統合テスト・CI の整備とドキュメント整備（設定例、運用ガイド）。
- 追加の RSS ソースやニュース解析（自然言語処理）機能の強化。

もしリリース日や記載の粒度を別途指定したい場合、あるいは各モジュールごとにより詳細な CHANGELOG を分けてほしい場合は指示してください。