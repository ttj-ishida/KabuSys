# Changelog

すべての変更は Keep a Changelog 規約に従って記載しています。  
このプロジェクトの初期公開リリースを記録します。

## [0.1.0] - 2026-03-18

### 追加 (Added)
- パッケージ基盤
  - パッケージメタ情報を追加（kabusys/__init__.py、__version__ = "0.1.0"）。公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート自動検出機能を実装（.git または pyproject.toml を探索）し、プロジェクト配布後でも CWD に依存しない自動.envロードを実現。
  - .env 自動ロードの挙動:
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能
    - 既存 OS 環境変数は保護され、.env.local でも保護される
  - .env パースの強化: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの適切な扱い。
  - 設定項目の取得ユーティリティ（必須項目の検査 _require、デフォルト値、検証: KABUSYS_ENV / LOG_LEVEL の妥当性チェック、パス型変換）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - J-Quants API からのデータ取得関数を実装:
    - fetch_daily_quotes (日足 OHLCV、ページネーション対応)
    - fetch_financial_statements (四半期財務、ページネーション対応)
    - fetch_market_calendar (JPX カレンダー)
  - HTTP レイヤーに以下を実装:
    - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter
    - 再試行 (指数バックオフ、最大3回) とステータスに基づく制御（408/429/5xx）
    - 401 時の自動トークンリフレッシュ（1 回のみ）と id_token キャッシュ共有
    - ページネーション key の扱い（pagination_key を使った連続取得）
    - JSON デコードエラーやネットワークエラーに対する明確な例外処理とログ出力
  - DuckDB への保存関数（冪等性を考慮）:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへ冪等保存
    - save_market_calendar: market_calendar テーブルへ冪等保存
  - データ変換ユーティリティ:
    - _to_float / _to_int: 安全な数値変換ロジック（空値・不正文字列の扱い、"1.0"→int 変換ルール等）

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存するフルスタック実装:
    - fetch_rss: RSS 取得、gzip 解凍、XML パース（defusedxml を使用）、フィードフォーマットのフォールバック処理
    - save_raw_news: INSERT ... RETURNING を用いたチャンク単位の冪等保存（トランザクション管理、チャンクサイズ制御）
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存（ON CONFLICT を利用して重複をスキップ）
    - run_news_collection: 複数ソースの総合収集ジョブ（各ソースの個別エラーハンドリング、既知銘柄による紐付け）
  - セキュリティ・堅牢性強化:
    - SSRF 対策: リダイレクト時にスキームとホストの検査を行う _SSRFBlockRedirectHandler、取得前のホスト検査 (_is_private_host)
    - XML 攻撃対策: defusedxml を用いた安全な XML パース
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）
    - URL 正規化とトラッキングパラメータ除去 (_normalize_url / _TRACKING_PARAM_PREFIXES)
    - 記事 ID の冪等化: 正規化 URL の SHA-256 の先頭32文字を記事IDに使用
    - テキスト前処理（URL 除去・空白正規化）
    - 不正なスキームの排除（mailto:, javascript: 等）
  - 銘柄抽出: 本文・タイトルから 4 桁の銘柄コードを抽出し、known_codes フィルタで有効コードのみを返す extract_stock_codes 実装
  - デフォルト RSS ソースを定義 (DEFAULT_RSS_SOURCES に Yahoo Finance のカテゴリ RSS を含む)

- データスキーマ (kabusys.data.schema)
  - DuckDB 用の DDL を定義・初期化するスクリプトを実装（Raw / Processed / Feature / Execution 層の概念）
  - Raw 層のテーブル定義を追加:
    - raw_prices: 日足生データ（PK: date, code）
    - raw_financials: 財務生データ（PK: code, report_date, period_type）
    - raw_news: ニュース記事（PK: id）
    - raw_executions: 発注/約定の生ログ（テーブル定義の追加開始）
  - スキーマは安全な型チェック（CHECK 制約等）とデフォルト値を設定

- リサーチ・特徴量 (kabusys.research)
  - 特徴量探索・ファクター計算モジュールを追加:
    - feature_exploration.py:
      - calc_forward_returns: 指定基準日から複数ホライズンの将来リターンを一括取得
      - calc_ic: ファクターと将来リターンのスピアマンランク相関 (IC) を計算
      - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算
      - rank: 値リストを平均ランクでランク付け（丸め誤差対策あり）
    - factor_research.py:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離率）
      - calc_volatility: atr_20、atr_pct、avg_turnover、volume_ratio 等
      - calc_value: per（株価/EPS）および roe（raw_financials から最新財務を参照）
  - すべてのリサーチ関数は DuckDB の prices_daily/raw_financials テーブルのみを参照し、外部 API にアクセスしない設計
  - 結果は (date, code) をキーにした dict のリストとして返却し、欠損値は None を返すことで downstream が扱いやすい仕様

- ヘルパーの公開
  - kabusys.research.__init__ で主要なユーティリティを再エクスポート（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）

### 変更 (Changed)
- なし（初期リリース）

### 修正 (Fixed)
- なし（初期リリース）

### セキュリティ (Security)
- RSS / HTTP 関係で SSRF 対策と XML パースの安全化を実装（_SSRFBlockRedirectHandler、_is_private_host、defusedxml の使用）。
- レスポンスサイズ制限と gzip 解凍後の上限チェックを追加（メモリ DoS 対策）。

### パフォーマンス (Performance)
- J-Quants API 呼び出しに固定間隔の RateLimiter を導入し、想定レート（120 req/min）を厳守。
- DB への大量挿入はチャンク分割およびトランザクションでまとめることでオーバーヘッドを削減（news_collector の _INSERT_CHUNK_SIZE、save_raw_news のチャンク挿入）。
- DuckDB 側の集約は可能な限りウィンドウ関数で完結させ、ネットワーク往復を抑制。

### 既知の制限 (Known Issues)
- zscore_normalize は kabusys.data.stats から参照しているが、その実装はこの差分内では省略されている（別モジュールで提供される前提）。
- raw_executions テーブル定義はこの差分では途中まで（以降の拡張が必要）。
- 一部の関数は DuckDB のテーブル構造（prices_daily, raw_prices, raw_financials 等）を前提としているため、スキーマ初期化を事前に行う必要がある。

---

このリリースは初期実装（v0.1.0）です。今後、使い勝手の向上、追加ファクター、strategy / execution 層の具体実装、テストカバレッジ強化、ドキュメント充実などを予定しています。