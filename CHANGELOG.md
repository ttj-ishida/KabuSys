CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- 該当なし

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初版リリース。
- 基本パッケージ構成を追加:
  - kabusys.__init__ に __version__ と公開サブパッケージ一覧を追加。
  - 空のサブパッケージプレースホルダ: execution, strategy（将来の拡張用）。
- 環境設定管理 (kabusys.config):
  - .env / .env.local からの自動読み込み（OS 環境変数優先、.env.local は上書き可能）。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない自動ロード。
  - .env パース実装（export 形式、クォート処理、インラインコメント処理を考慮）。
  - 必須環境変数取得のユーティリティ _require と Settings クラス（J-Quants, kabuステーション, Slack, DBパス, 環境種別・ログレベル検証等）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
- J-Quants API クライアント (kabusys.data.jquants_client):
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダーのフェッチ機能を実装（ページネーション対応）。
  - レート制限制御（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行）。429 の場合は Retry-After ヘッダ優先。
  - 401 受信時はリフレッシュトークンから id_token を自動再取得して 1 回だけ再試行（無限再帰防止）。
  - ページネーション間で共有するモジュールレベルの id_token キャッシュ。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE による冪等保存、fetched_at を UTC で記録。
  - 値変換ユーティリティ (_to_float, _to_int) を追加し、型安全に変換失敗を None として扱う。
- ニュース収集モジュール (kabusys.data.news_collector):
  - RSS フィード取得と raw_news テーブルへの保存ワークフローを実装（fetch_rss, save_raw_news）。
  - URL 正規化、utm_* 等トラッキングパラメータ除去、SHA-256 ハッシュ（先頭32文字）による記事ID生成で冪等性を確保。
  - XML パースに defusedxml を使用して XML 攻撃に対する防御。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト先の事前検証を行うカスタム RedirectHandler（プライベート IP / ループバック / リンクローカルを拒否）。
    - ホスト名を DNS 解決し A/AAAA レコードを検査してプライベートアドレスを拒否。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）と Gzip 解凍後サイズ検査（Gzip bomb 対策）。
  - RSS の pubDate パースとフォールバック（パース失敗時は現在時刻で代替）。
  - テキスト前処理（URL 除去、空白正規化）と記事本文の抽出（content:encoded 優先）。
  - raw_news へのバルク挿入はチャンク化しトランザクションでまとめ、INSERT ... RETURNING により実際に挿入された ID を返す。
  - 銘柄コード抽出ロジック（4桁数字、known_codes によるフィルタ）と news_symbols への紐付け（チャンク挿入、重複排除）。
  - run_news_collection により複数 RSS ソースを独立して収集・保存（ソース単位でエラーを分離）。
- スキーマ管理 (kabusys.data.schema):
  - DuckDB 用スキーマ定義を実装（Raw / Processed / Feature / Execution レイヤ）。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed テーブル。
  - features, ai_scores など Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution テーブル。
  - 各テーブルの制約（PRIMARY KEY, CHECK, FOREIGN KEY）や推奨インデックスを定義。
  - init_schema(db_path) によりディレクトリ作成→テーブル作成→インデックス作成を行い DuckDB 接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を返す。
- ETL パイプライン (kabusys.data.pipeline):
  - ETLResult データクラスを追加（取得・保存件数、品質問題、エラー等を集約）。
  - 差分更新ヘルパー（get_last_price_date / get_last_financial_date / get_last_calendar_date）を追加。
  - 市場カレンダーを考慮したトレーディング日調整関数 _adjust_to_trading_day を実装。
  - run_prices_etl を実装（差分取得ロジック、backfill_days による再取得、J-Quants クライアントを利用して保存）。
  - ETL の設計方針として「Fail-Fast ではなく全件収集を継続」する動作を採用。
- その他:
  - データパイプライン設計に合わせたドキュメント文字列（DataPlatform.md / DataSchema.md に対応する実装方針の注記）。

Security
- XML パースに defusedxml を使用して XML Bomb 等を緩和。
- RSS フェッチでの SSRF 対策を実装:
  - URL スキーム検証（http/https のみ）。
  - リダイレクト先のスキーム・ホスト検証を行うカスタム RedirectHandler。
  - DNS 解決してプライベート IP を拒否する _is_private_host。
- HTTP レスポンスの読み込み量を制限（MAX_RESPONSE_BYTES）し、解凍後も再チェック（Gzip bomb 対策）。
- .env 読み込みで OS 環境変数を保護する protected パラメータ。自動ロード無効化オプションを提供。

Changed
- 該当なし（初回リリース）。

Fixed
- 該当なし（初回リリース）。

Deprecated
- 該当なし（初回リリース）。

Removed
- 該当なし（初回リリース）。

Notes / Limitations
- execution/strategy パッケージはプレースホルダで、発注ロジック・戦略実装は未実装（今後のリリース予定）。
- 自動環境読み込みはプロジェクトルートが検出できない場合はスキップされるため、配布後の実行環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を活用して明示的に制御してください。
- DB スキーマ初期化は init_schema() を明示的に呼ぶこと（get_connection() は初期化を行わない）。
- テスト・CI のために一部関数（例: news_collector._urlopen）をモック可能な設計にしているが、テストコードは同梱していません。

今後の予定（例）
- execution/strategy の実装（注文送信、注文管理、ポジション管理の実装）。
- 監視・アラート機能（Slack 通知の統合）。
- 品質チェックモジュール (kabusys.data.quality) の充実と ETL からの自動アクション対応。