CHANGELOG
=========

すべての重要な変更履歴を記録します。フォーマットは「Keep a Changelog」に準拠しています。
リリース日はコードベースから推測して付与しています。

[Unreleased]
-------------

- （なし）

0.1.0 - 2026-03-18
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアモジュール群を実装
  - パッケージ初期化: バージョン情報と公開モジュールを定義 (kabusys/__init__.py)
- 環境設定管理 (kabusys.config)
  - .env ファイル自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env 行パーサ: export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などを実装
  - .env 読み込み時の上書き制御（override）と protected キー（OS 環境変数保護）をサポート
  - Settings クラス: 必須値チェック（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_* 等）、パス既定値（DuckDB/SQLite）、環境（development/paper_trading/live）とログレベルのバリデーション、便利プロパティ（is_live/is_paper/is_dev）
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足・財務データ・マーケットカレンダー取得の実装（ページネーション対応）
  - API レート制御（固定間隔スロットリング、120 req/min を想定）
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ共有
  - JSON デコードエラーの明示的ハンドリング
  - DuckDB への冪等的保存: save_daily_quotes / save_financial_statements / save_market_calendar が ON CONFLICT DO UPDATE を使用
  - fetched_at を UTC ISO 形式で記録し、データ収集時刻をトレース可能に
  - 型変換ユーティリティ（_to_float, _to_int）で不正値に耐性
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード取得・パース・前処理・DB保存の実装（DEFAULT_RSS_SOURCES を含む）
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等に対処
    - SSRF 対策: リダイレクト時にスキーム検証およびプライベートアドレス検査を行う専用 RedirectHandler を導入
    - URL スキーム検証（http/https のみ許可）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MB）および gzip 解凍後の再検査（Gzip bomb 対策）
  - URL 正規化とトラッキングパラメータ削除（utm_*, fbclid 等）
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保
  - テキスト前処理（URL 除去・空白正規化）
  - DuckDB へのバルク挿入: トランザクションでまとめ、INSERT ... ON CONFLICT DO NOTHING RETURNING を使用して実際に挿入された ID を取得
  - 銘柄コード抽出機能（4桁数字パターン、既知コードセットでフィルタ）
  - run_news_collection により複数ソースの独立エラーハンドリングと一括保存が可能
- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層にまたがる多数のテーブル DDL を実装（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signal_queue, orders, trades, positions, portfolio_performance 等）
  - 外部キー依存を考慮した作成順と、実運用を想定したインデックス群を定義
  - init_schema(db_path) によりディレクトリ自動作成・DDL 実行を行い初期化済みの接続を返す
  - get_connection(db_path) で既存 DB へ接続（初期化は行わない）
- ETL パイプライン (kabusys.data.pipeline)
  - 差分更新ロジックとユーティリティ（最終取得日取得、営業日調整）を実装
  - ETLResult dataclass により ETL 実行結果・品質問題・エラーメッセージを一貫して扱えるように設計
  - デフォルトバックフィル日数（_DEFAULT_BACKFILL_DAYS = 3）、市場カレンダー先読み（_CALENDAR_LOOKAHEAD_DAYS = 90）、および最短データ日付（_MIN_DATA_DATE = 2017-01-01）
  - run_prices_etl 等で jquants_client の fetch / save を組み合わせた差分 ETL を実行可能
  - 品質チェック基盤（quality モジュール）との連携点を用意（重大度フラグ対応）

Security
- defusedxml / サイズ制限 / SSRF 対策 / スキーム検証など、外部データ取り込みに関する複数の防御策を導入
- .env の読み込みで OS 環境変数を保護する仕組み（protected set）を導入し、意図しない上書きを防止

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Notes / 既知の問題と注意点
- run_prices_etl の戻り値について:
  - ソースコード断片では run_prices_etl の最後の return が単一要素のタプル（取得レコード数のみ）になっている箇所が確認できます。呼び出し側は (fetched, saved) のタプルを期待する設計になっているため、不整合が発生する可能性があります。実運用前に該当関数の戻り値が仕様どおり (fetched_count, saved_count) を返すことを確認・修正してください。
- スキーマや DDL は現状 DuckDB 向けに設計されています。別DBへの移植を行う場合はデータ型や制約の差異に注意してください。
- news_collector の DNS 解決失敗時は「安全側」として外部アクセスを許可する実装になっているため、運用環境のネットワークポリシーに応じて追加制約が必要になる場合があります。

Acknowledgments
- 実装は J-Quants API、DuckDB、defusedxml を想定した設計に基づいています。

（この CHANGELOG はコード内容からの推測に基づき作成しています。実際のコミット単位・履歴とは差異がある可能性があります。）