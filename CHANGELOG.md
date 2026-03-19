# Changelog

すべての重要な変更履歴をここに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース。主要な機能群と基盤ユーティリティを実装しました。

### 追加 (Added)
- パッケージ全体
  - パッケージ初期化とバージョン情報を追加（kabusys v0.1.0）。
  - モジュール分割: data, strategy, execution, monitoring 等のパッケージ構成を用意。

- 環境設定 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は .git または pyproject.toml を基準に行う（CWD 非依存）。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパース機能を実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - Settings クラスを提供し、以下の主要設定をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを持つ）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
  - 環境種別判定ユーティリティ（is_live / is_paper / is_dev）を提供。

- データ取得・保存（J-Quants クライアント） (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装:
    - 日足（prices/daily_quotes）、財務データ（fins/statements）、マーケットカレンダー取得。
    - ページネーション対応（pagination_key を利用）。
    - モジュールレベルの id_token キャッシュ（ページネーション間で共有）。
    - get_id_token によるリフレッシュ（POST）を実装。
  - レート制御: 固定間隔スロットリング（120 req/min 相当）を実装（_RateLimiter）。
  - リトライ戦略: 指数バックオフ、最大 3 回のリトライ（対象: 408, 429, 5xx、429 は Retry-After を尊重）。
  - 401 発生時の自動トークンリフレッシュを 1 回だけ行う仕組みを実装（無限再帰回避）。
  - DuckDB への保存ユーティリティを実装（冪等性を確保する ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes: raw_prices テーブルへ保存（PK 欠損行はスキップ）。
    - save_financial_statements: raw_financials テーブルへ保存。
    - save_market_calendar: market_calendar テーブルへ保存（HolidayDivision を解釈）。
  - 型変換ユーティリティ（_to_float, _to_int）を実装し、入力の健全性を担保。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集パイプラインを実装:
    - fetch_rss: RSS 取得・XML パース・記事構築を行う（defusedxml を使用して XML 攻撃を軽減）。
    - preprocess_text: URL 除去・空白正規化。
    - _normalize_url / _make_article_id: URL 正規化と SHA-256（先頭32文字）による記事ID生成で冪等性を確保。
    - fetch_rss はデフォルトソースを持つ（例: Yahoo Finance のビジネスカテゴリRSS）。
  - セキュリティ・堅牢化機能:
    - SSRF 対策: スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないことを検査。
    - リダイレクト検査用ハンドラ（_SSRFBlockRedirectHandler）を導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を超えるレスポンスを拒否（gzip 解凍後も検査）。
  - DB 保存ユーティリティ:
    - save_raw_news: チャンク分割で INSERT INTO ... ON CONFLICT DO NOTHING RETURNING id を用い、新規挿入された記事ID一覧を返す。（トランザクション内で処理）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括で保存（ON CONFLICT DO NOTHING / INSERT ... RETURNING を使用）し、実際に挿入された件数を正確に返す。
  - 銘柄抽出機能:
    - extract_stock_codes: テキスト中の4桁数字を抽出し、与えられた known_codes セットに含まれるもののみを返す（重複除去）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - DataSchema に基づき Raw / Processed / Feature / Execution 層のスキーマ定義用モジュールを追加。
  - Raw 層の DDL を実装（例: raw_prices, raw_financials, raw_news, raw_executions のテーブル定義を含む）。
    - 各テーブルは PRIMARY KEY／CHECK 制約や fetched_at を含む設計。

- 研究用（Research）モジュール (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily から一括取得して計算。
    - calc_ic: Spearman のランク相関（Information Coefficient）を実装（None 値・非有限値を除外、3 件未満で None）。
    - rank: 同順位は平均ランクとするランク関数（丸め誤差回避のため round(..., 12) を使用）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、および ma200_dev を計算（200 日 MA の行数チェックあり）。
    - calc_volatility: 20 日 ATR（平均 true_range）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算（true_range の NULL 伝播を慎重に扱う）。
    - calc_value: raw_financials の最新財務データと当日終値を組み合わせて PER / ROE を計算（EPS が 0 または NULL の場合は None）。
  - research パッケージ __init__ にて主要関数を再エクスポート（zscore_normalize は kabusys.data.stats から参照）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- ニュース収集に関する SSRF 対策を実装:
  - URL スキーム検証、DNS 解決によるプライベートアドレス判定、リダイレクト先検査を導入。
  - defusedxml を使用して XML 関連攻撃を防止。
  - レスポンスサイズの上限チェックと gzip 解凍後の検査で Gzip bomb 等のメモリ DoS を軽減。
- J-Quants クライアントでは機密トークンの自動リフレッシュを安全に取り扱い、無限再帰を防止。

### ドキュメント (Documentation)
- 各モジュールに関数・設計方針・引数/戻り値の説明（docstring）を充実させ、内部設計・利用上の注意を明記。

### 既知の制限・今後の課題
- data.stats モジュール（zscore_normalize）は参照されているが、この差分では実装ファイルの提示がないため、外部に依存している可能性あり。
- schema.py の execution 層の DDL は途中まで提示されている（リリース後に完全な定義を確認・補完する予定）。
- 本リリースでは外部ライブラリ（pandas など）に依存しない実装方針を採用しているため、大規模データ処理時の最適化やメモリ/速度に関する追加改善の余地あり。

---

注: 上記はコードベースから推測してまとめた CHANGELOG です。実際のリリースノート作成時はコミット履歴やリリース時の変更点（バグ修正・チケット番号等）を補完してください。