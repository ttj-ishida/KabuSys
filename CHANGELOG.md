CHANGELOG.md
=============

すべての重要な変更点を記録します。本ドキュメントは「Keep a Changelog」規約に準拠しています。

フォーマット:
- 変更はセクション (Added, Changed, Fixed, Security, etc.) に分類しています。
- バージョンは semver に従います。

Unreleased
----------
（現在なし）

0.1.0 - 2026-03-18
-----------------

Added
- 基本パッケージ構成を導入
  - パッケージメタ情報（src/kabusys/__init__.py）に __version__ = "0.1.0" を追加し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。
- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイル自動読み込み機能を追加（プロジェクトルート検出: .git または pyproject.toml 基準）。
  - .env/.env.local の読み込み順序と .env.local による上書き仕様を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化フラグを実装（テスト用）。
  - export KEY=val 形式、クォート/エスケープ、インラインコメントの取り扱いを考慮した .env パーサ実装。
  - OS 環境変数の保護（保護セット）を導入し、override フラグで上書き制御。
  - 必須環境変数取得時に未設定なら ValueError を投げる _require ユーティリティを追加。
  - KABUSYS_ENV / LOG_LEVEL の値検証ロジック（有効値チェック）と便利なプロパティ（is_live / is_paper / is_dev）を追加。
  - データベースパス用プロパティ（duckdb_path, sqlite_path）を追加。
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しのための共通 _request 実装（JSON デコード、パラメータ付与、ヘッダ管理）。
  - 固定間隔スロットリングによるレート制御（120 req/min 相当）の _RateLimiter を実装。
  - リトライ（指数バックオフ）ロジックを実装（最大リトライ回数、408/429/5xx の再試行、Retry-After 処理）。
  - 401 受信時の自動トークンリフレッシュを1回だけ行う仕組みを実装（再試行ループ内でのキャッシュ更新）。
  - get_id_token によるリフレッシュトークン→IDトークン取得（POST）を実装。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務四半期データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存ユーティリティ（ON CONFLICT DO UPDATE）を実装:
    - save_daily_quotes（raw_prices へ保存、PK欠損行スキップ）
    - save_financial_statements（raw_financials へ保存、PK欠損行スキップ）
    - save_market_calendar（market_calendar へ保存、HolidayDivision の解釈を実装）
  - 型安全な変換ユーティリティ _to_float / _to_int を実装（不正値は None を返す）。
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得・前処理・DB保存の統合モジュールを導入。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML-Bomb 等を緩和。
    - SSRF 対策: リダイレクト先のスキーム検証とプライベート IP/ホスト検査（_SSRFBlockRedirectHandler, _is_private_host）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MiB）と gzip 解凍後の再検査（Gzip-bomb 対策）。
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）、SHA-256 による記事ID生成（先頭32文字）を実装。
  - テキスト前処理（URL除去・空白正規化）を実装（preprocess_text）。
  - RSS の pubDate を UTC にパースするユーティリティ（_parse_rss_datetime）。
  - fetch_rss: フィード取得 → XML パース → 記事抽出（content:encoded の優先採用、guid の代替利用）を実装。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用いて実際に挿入された記事IDのみを返す実装（チャンク挿入・トランザクションでまとめる）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存（チャンク・トランザクション・INSERT ... RETURNING を利用）。
  - 銘柄コード抽出ロジック（4桁の数字を抽出して known_codes と照合する extract_stock_codes）を実装。
  - run_news_collection: 複数 RSS ソースの一括収集ジョブ実装（ソース単位のエラーハンドリング、既知銘柄紐付けの一括保存）。
- リサーチ / ファクター計算（src/kabusys/research/feature_exploration.py, factor_research.py, __init__.py）
  - 将来リターン計算: calc_forward_returns（DuckDB の prices_daily を参照、複数 horizon を一度に取得するSQL実装）。
  - IC（Information Coefficient）計算: calc_ic（Spearman ランク相関、欠損/非有限値の除外、最小レコード数検査）。
  - ランク変換 util: rank（同順位は平均ランク、丸め処理で ties 検出の安定化）。
  - ファクター統計サマリー: factor_summary（count/mean/std/min/max/median を計算、None 除外）。
  - モメンタム: calc_momentum（1m/3m/6m リターン、MA200 乖離率、スキャンバッファ実装）。
  - ボラティリティ/流動性: calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比率、NULL 伝播制御）。
  - バリュー: calc_value（raw_financials から最新報告を結合して PER / ROE を計算）。
  - 研究用 API は DuckDB の prices_daily/raw_financials のみ参照し、本番取引 API にはアクセスしない設計。
  - kabusys.research パッケージの __all__ に主要関数をエクスポート（zscore_normalize は data.stats からインポート）。
- DuckDB スキーマ定義（src/kabusys/data/schema.py）
  - DataSchema.md に基づく多層スキーマ導入（Raw / Processed / Feature / Execution 層の概念）。
  - raw_prices / raw_financials / raw_news / raw_executions 等の DDL 定義を追加（PRIMARY KEY / CHECK 制約を含む）。
  - ロギングと初期化のためのユーティリティを用意。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- RSS 取得まわりに複数の SSRF / XML-Bomb / Gzip-Bomb 対策を実装（news_collector）。
- API クライアントでのトークン管理とリトライ設計により、認証失敗時の安全なリフレッシュと再試行を導入（jquants_client）。

Notes / Known limitations
- DuckDB のスキーマ DDL の一部（raw_executions 等）はソース内で定義が続きますが、このリリースはスキーマ全体の骨組みを提供します。
- 研究用関数群は標準ライブラリ依存で実装されており、大量データ処理時の性能チューニングは今後の改善候補です。
- jquants_client のレート制限は固定間隔スロットリングで実装しているため、API サーバー側のバースト許容と併用する場合は調整が必要になることがあります。
- news_collector のホスト名プライベート判定は DNS 解決失敗時に安全側（非プライベート）とみなす設計になっており、厳格な環境では挙動確認が必要です。

貢献・バグ報告
- バグ報告・改善提案は Issue 経由でお願いします。今後のリリースではテストカバレッジやエラーハンドリングの強化を行っていきます。