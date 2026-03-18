# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
本リリースはプロジェクトの初期公開版（0.1.0）を想定して、コードベースから推測できる追加・仕様・安全対策等をまとめています。

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。モジュール集合: data, strategy, execution, monitoring を公開。
- 設定管理
  - 環境変数/`.env` ファイル読み込み機能を追加（src/kabusys/config.py）。
  - プロジェクトルート判定: .git または pyproject.toml を探索して自動的に .env/.env.local を読み込む仕組みを実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - `.env` 行パーサーを実装し、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱いに対応。
  - Settings クラスを提供し、主要設定値（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）をプロパティ経由で取得。KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を導入。
    - ページネーション対応のフェッチ関数: fetch_daily_quotes, fetch_financial_statements。
    - market calendar 取得関数: fetch_market_calendar。
    - リトライロジック（最大3回、指数バックオフ）を実装。HTTP 408/429/5xx などでリトライ。
    - 401 受信時は ID トークンを自動リフレッシュして 1 回再試行する仕組みを実装（トークンキャッシュ含む）。
    - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を使用）。
    - 値変換ユーティリティ：_to_float/_to_int（不正な文字列を安全に None にするなど）。
- ニュース収集
  - RSS ベースのニュース収集モジュールを実装（src/kabusys/data/news_collector.py）。
    - RSS 取得（fetch_rss）と記事前処理（URL 除去、空白正規化）を提供。
    - defusedxml を使った安全な XML パース（XML Bomb 対策）。
    - gzip 圧縮応答の解凍対応、レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - ホストがプライベート/ループバック/リンクローカルでないことを検査（DNS 解決と IP 判定）。
      - リダイレクト先の事前検証を行うカスタムハンドラ（_SSRFBlockRedirectHandler）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント削除）と記事ID生成（正規化 URL の SHA-256 先頭32文字）。
    - raw_news テーブルへの冪等保存（save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id）と news_symbols 紐付け保存（save_news_symbols / _save_news_symbols_bulk）。
    - 記事内からの銘柄コード抽出ユーティリティ（extract_stock_codes、4桁コード検出）。
    - デフォルト RSS ソースとして Yahoo Finance を設定。
- リサーチ（特徴量・ファクター）
  - 特徴量探索・解析モジュールを追加（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（calc_forward_returns）: DuckDB の prices_daily を参照して複数ホライズンのリターンを一度に取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関（ランク化ユーティリティ rank を含む）。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算。
    - 標準ライブラリのみでの実装に留意（pandas 等非依存）。
  - ファクター計算モジュールを追加（src/kabusys/research/factor_research.py）。
    - Momentum（calc_momentum）: 1M/3M/6M リターン、200日移動平均乖離率。
    - Volatility / Liquidity（calc_volatility）: 20日 ATR、相対 ATR、20日平均売買代金、出来高比。
    - Value（calc_value）: raw_financials から最近の財務データを取得して PER / ROE を算出。
    - DuckDB の prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない設計。
  - research パッケージの __init__ にて主要関数群をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
- スキーマ/初期化
  - DuckDB スキーマ定義を追加（src/kabusys/data/schema.py）。
    - Raw Layer テーブル定義（raw_prices, raw_financials, raw_news, raw_executions 等）を含む DDL を定義。
    - Data Platform に基づく 3 層（Raw / Processed / Feature / Execution）構造を想定。

### 変更 (Changed)
- ロギング出力の強化
  - 主要処理（fetch, save, calc）で情報ログ/警告ログを出力するように整理（logger を各モジュールで使用）。
- API クライアントの設計方針明文化
  - 取得タイミングのトレーサビリティ（fetched_at を UTC で記録）や冪等性ポリシーを実装文書化。

### 修正 (Fixed)
- データ変換の堅牢化
  - 数値変換時に不正な文字列や小数部がある整数文字列を適切にハンドリングするユーティリティを実装（_to_int の挙動明確化）。
- .env パーサの頑健化
  - クォート内のエスケープ処理や inline コメントの扱い、export プレフィックス対応などを実装して実運用での .env パース欠陥を低減。

### セキュリティ (Security)
- RSS 処理に関する対策
  - defusedxml を採用し XML 実行攻撃を緩和。
  - レスポンスサイズ上限、gzip 解凍後のサイズチェックで Gzip bomb を防止。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ）。
    - ホストのプライベート IP 判定（直接 IP / DNS 解決の両方を検査）。
    - リダイレクト時にも検証を行うカスタムハンドラを導入。
- J-Quants API クライアント
  - トークン自動リフレッシュは allow_refresh フラグを用いて無限再帰を回避。
  - HTTP リトライ時に Retry-After ヘッダを尊重（429 の場合）。

### 既知の制約 / 注意点 (Known issues / Notes)
- DuckDB スキーマの一部（raw_executions の定義など）がソース内で途切れている箇所があるため、完全な実装・DDL の最終化が必要。
- research モジュールは pandas 等外部ライブラリ非依存で実装されているため、大規模データでの高速化やメモリ効率は今後の改善ポイント。
- NewsCollector の DNS 解決失敗は安全側の扱い（非プライベートとみなす）としているため、特殊なネットワーク環境では想定外の挙動となる可能性あり。
- Settings の必須環境変数未設定時は ValueError を投げるため、デプロイ前に .env を整備する必要がある。

---

今後のリリース案（例）
- 0.2.0: schema の完成、Processed/Feature レイヤーの初期 ETL ジョブ、strategy/execution/monitoring の実装拡充
- Patch リリース: バグ修正・ロギング改善、外部依存の許容やパフォーマンス最適化

（以上）