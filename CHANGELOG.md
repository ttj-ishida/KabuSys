# Changelog

すべての重要な変更点を記録します。本ファイルは Keep a Changelog の書式に準拠しています。  

- リリースポリシー: 重大な変更は Breaking Changes セクションに明記します。  
- 日付はリリース日を示します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

初回リリース（アルファ/ベータ相当）。以下の主要な機能群を実装しています。

### 追加 (Added)
- パッケージ初期化
  - src/kabusys/__init__.py にてバージョン情報と公開サブパッケージを定義（__version__ = "0.1.0", __all__ に data, strategy, execution, monitoring を追加）。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env および .env.local をプロジェクトルートから自動ロード（CWD に依存しない検出ロジック）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - export KEY=val 形式やクォート、インラインコメントを考慮した .env パーサ実装。
  - 必須環境変数取得ヘルパー (_require) と Settings クラスを提供。
  - 設定のバリデーション（KABUSYS_ENV: development/paper_trading/live、LOG_LEVEL の許容値チェック）。
  - データベースパス（DUCKDB_PATH, SQLITE_PATH）、Slack トークン等のプロパティを提供。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - 株価日足（OHLCV）、四半期財務データ、JPX マーケットカレンダーを取得する fetch_* 関数を実装（ページネーション対応）。
  - トークン取得用 get_id_token 実装（refresh token → id token）。
  - レート制限制御（120 req/min の固定間隔スロットリング）を実装する内部 RateLimiter。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx の再試行、429 の Retry-After 結合）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）と再試行。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。
    - 保存は冪等（ON CONFLICT DO UPDATE）で行い、fetched_at を UTC で記録。
    - 型変換ユーティリティ（_to_float, _to_int）を備え、入力の堅牢性を向上。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得と記事抽出（fetch_rss）を実装。
  - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。
  - defusedxml を用いた安全な XML パース（XML Bomb 等の防御）。
  - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再チェック。
  - SSRF/内部ネットワークアクセス対策:
    - URL スキーム検証 (http/https のみ許可)。
    - リダイレクト時のスキーム＆プライベートアドレス検査（専用 RedirectHandler）。
    - ホスト名の DNS 解決によるプライベート IP 判定。
  - 記事ID を正規化後の URL の SHA-256（先頭32文字）で生成し冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）。
  - raw_news テーブルへのバルク挿入（INSERT ... ON CONFLICT DO NOTHING RETURNING を用いたチャンク挿入、トランザクション）。
  - 銘柄紐付け機能（extract_stock_codes, save_news_symbols, _save_news_symbols_bulk）：本文から 4 桁銘柄コードを抽出し news_symbols に保存（チャンク & トランザクション、ON CONFLICT で重複除去）。

- DuckDB スキーマ定義と初期化 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution の各レイヤーに対応したテーブル定義を実装（raw_prices, raw_financials, raw_news, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
  - 検索を想定したインデックス群を定義。
  - init_schema(db_path) による初期化関数を提供（親ディレクトリ自動作成、冪等にテーブル作成）。
  - get_connection(db_path) で既存 DB への接続を取得。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - ETL の設計に基づく差分更新ロジックのためのユーティリティを実装。
  - ETLResult dataclass により ETL の集計結果・品質問題・エラーの収集・シリアライズを実現。
  - テーブル存在チェック、最大日付取得、取引日へ調整するヘルパー（_adjust_to_trading_day）を提供。
  - 差分更新のための get_last_* 関数群（get_last_price_date 等）。
  - run_prices_etl: 差分更新・バックフィル（デフォルト backfill_days=3）を行い、jquants_client の fetch/save を組み合わせて実行（差分取得・保存・ログ出力）。（ETL の考え方と品質チェック統合を実装）

- プレースホルダモジュール
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py を設置（将来の拡張用プレースホルダ）。

### 修正 (Fixed)
- なし（初回リリース）

### セキュリティ (Security)
- news_collector における複数の SSRF/DoS 緩和策を導入:
  - defusedxml による安全な XML パース。
  - URL スキーム検証、リダイレクト検査、プライベート IP 拒否。
  - レスポンスサイズ上限 (10 MB) と gzip 解凍後チェック（Gzip bomb 対策）。
- jquants_client の HTTP タイムアウトやリトライ制御で外部依存の不安定性に対処。

### 既知の制限 / 今後の作業予定
- strategy / execution / monitoring パッケージは実装の残りがある（プレースホルダ）。実運用での発注ロジック・ポジション管理やモニタリングは未実装。
- pipeline.run_prices_etl の後続処理（品質チェックの統合やカレンダー/財務 ETL の統合など）を拡張予定。
- 単体テスト・統合テストの整備（ネットワークリクエストのモック、DuckDB のテスト用初期化など）が必要。
- 秘密情報取り扱い（トークン）の更なる保護（シークレット管理サービス連携等）を検討。

---

作成者: 自動生成（コードベースから推測）  
注: 上記は提供されたソースコードの実装内容に基づく推測であり、実際のリリースノートはプロジェクトポリシーや変更履歴に合わせて調整してください。