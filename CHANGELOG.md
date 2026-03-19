# Changelog

すべての重要な変更はここに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

※本ファイルはソースコードから推測して作成しています。実装の詳細や設計意図は該当ソースの docstring / コメントを参照してください。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買プラットフォームのコア機能のプロトタイプ実装を含みます。

### 追加
- パッケージ基盤
  - kabusys パッケージの初期エントリポイントを追加（src/kabusys/__init__.py）。
  - サブパッケージとして data, strategy, execution, monitoring を公開（__all__）。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - プロジェクトルート検出機能: .git または pyproject.toml を基準に自動検出。
  - .env / .env.local の自動読み込み実装（環境変数優先、.env.local は上書き可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パースの強化:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、
    - コメント処理（クォート内は無視、非クォートは '#' 前の空白でコメント判断）。
  - Settings クラスを実装（プロパティ経由で設定取得）
    - J-Quants / kabu API / Slack / DB パス / 実行環境・ログレベル等を扱うプロパティ
    - env と log_level の値検証（許容値チェック）
    - is_live/is_paper/is_dev 補助プロパティ

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - RateLimiter 実装（120 req/min 相当の固定間隔スロットリング）。
  - リクエストユーティリティ `_request`：
    - ペイロード処理、JSON デコード、最大リトライ（指数バックオフ）、
    - リトライ対象ステータス（408/429/5xx）を考慮、
    - 401 の場合はトークンを自動リフレッシュして一回だけリトライ。
  - ID トークン取得（get_id_token）を実装（settings のリフレッシュトークン使用可能）。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存関数（冪等）を実装:
    - save_daily_quotes: raw_prices への upsert（ON CONFLICT DO UPDATE）
    - save_financial_statements: raw_financials への upsert
    - save_market_calendar: market_calendar への upsert
  - 型変換ユーティリティ `_to_float`, `_to_int`（安全な数値変換）

- ニュース収集（RSS）モジュール（src/kabusys/data/news_collector.py）
  - RSS フィード取得とパース（defusedxml 使用）を実装
  - セキュリティ対策の導入:
    - SSRF 対策: リダイレクト前後でスキーム検証およびプライベートアドレス判定（_SSRFBlockRedirectHandler, _is_private_host）
    - URL スキーム制限（http/https のみ）
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES, Gzip 解凍後も検査）
    - XML パース時の DefusedXmlException ハンドリング
  - URL 正規化とトラッキングパラメータ除去（_normalize_url）および SHA-256 ベースの記事 ID 生成（_make_article_id）
  - テキスト前処理（URL 除去、空白正規化）と RSS pubDate パース（_parse_rss_datetime）
  - DuckDB への保存:
    - save_raw_news: INSERT ... RETURNING id を用いたチャンク挿入（トランザクション内）
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンクで挿入（RETURNING で実際に挿入された件数を取得）
  - 銘柄コード抽出（extract_stock_codes）：本文から 4 桁コードを抽出し known_codes と照合
  - run_news_collection: 複数 RSS ソースを横断して収集・保存・銘柄紐付けを行う統合ジョブ。個別ソースの失敗は他を阻害しない設計。

- データスキーマ定義（src/kabusys/data/schema.py）
  - DuckDB 用 DDL 定義（Raw レイヤーのテーブル定義を含む）
    - raw_prices, raw_financials, raw_news, raw_executions などの CREATE TABLE 文（NOT NULL / CHECK / PRIMARY KEY 指定）
  - スキーマ初期化用モジュール基盤（DataSchema.md に準拠した設計思想をコメントで明記）

- 研究（Research）モジュール（src/kabusys/research）
  - feature_exploration.py:
    - calc_forward_returns: 指定日の将来リターン（複数ホライズン）を DuckDB の prices_daily から一括取得
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（NULL・ties 対応、サンプル数閾値）
    - rank: 同順位は平均ランクとするランク計算（浮動小数の丸めで ties 判定強化）
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算
    - 研究モジュールは外部ライブラリ（pandas 等）に依存しない純粋標準ライブラリ実装を志向
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を計算
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR の NULL 伝播制御あり）
    - calc_value: raw_financials と prices_daily を組み合わせて per, roe を計算（最新財務データの取得に ROW_NUMBER を利用）
  - research パッケージ初期化で主要関数と zscore_normalize（kabusys.data.stats から）を公開

### 改善 / 設計上の注意
- DuckDB へのデータ保存は冪等化（ON CONFLICT）を採用。raw 層に対する重複保護と fetched_at による取得日時トレースを設計に組み込んでいる。
- J-Quants クライアントはレートリミット・リトライ・トークンリフレッシュを組み合わせた堅牢な呼び出しフローを提供する。
- ニュース収集は SS R F / XML Bomb / Gzip Bomb / 大容量レスポンス対策など複数の防御を組み込み、安全に外部 RSS を取り込む設計。
- 研究用関数群は本番の発注 API にアクセスしないことを意図しており、DuckDB の prices_daily/raw_financials のみを参照する。

### 既知の制約 / 未実装点
- strategy / execution / monitoring パッケージはパッケージ階層として存在するが、具体的な発注ロジックや監視機能の実装は含まれていない（プレースホルダ）。
- 一部テーブル定義や DDL は Raw レイヤー中心で、Processed / Feature / Execution レイヤーの完全な DDL は未確認（実装継続予定）。
- 一部の挙動（例: fetch_* のページネーション仕様、J-Quants API のフィールド名）は外部 API 仕様に依存するため、実運用前の追加テストと検証が必要。

### セキュリティ
- RSS 処理における SSRF 対策、DefusedXML による XML パースの安全化、レスポンスサイズ制限、Gzip 解凍後のサイズチェックを導入。
- J-Quants クライアントのリトライ/バックオフ実装は過負荷・レート制限に対する耐性を向上させる。

---

（以降のリリースはここに追記してください）