CHANGELOG
=========

すべての注目すべき変更点を記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

[Unreleased]
------------

- なし

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を定義し、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に公開。

- 環境・設定管理
  - src/kabusys/config.py を追加:
    - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml で特定）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを抑制可能。
    - 厳密な .env パースロジック（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ処理等に対応）。
    - Settings クラスを提供し、アプリ設定をプロパティ経由で取得:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL,
        SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等をサポート。
      - KABUSYS_ENV の検証（development / paper_trading / live）。
      - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）と is_live / is_paper / is_dev ヘルパー。

- Data (J-Quants) クライアント
  - src/kabusys/data/jquants_client.py を追加:
    - J-Quants API からのデータ取得（株価・財務・カレンダー）をサポートする fetch_* 関数群（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - ページネーション自動処理。
    - 固定間隔レート制御（_RateLimiter）で 120 req/min を遵守。
    - リトライロジック（指数バックオフ、最大3回、408/429/5xx をリトライ対象）。
    - 401 受信時の ID トークン自動リフレッシュと再試行（キャッシュで共有）。
    - DuckDB へ冪等的に保存するヘルパー（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT による更新処理を実装。
    - 型安全な変換ユーティリティ (_to_float/_to_int)。

- ニュース収集
  - src/kabusys/data/news_collector.py を追加:
    - RSS フィード取得と記事保存の一連処理（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
    - セキュリティ・堅牢性強化:
      - defusedxml を利用した安全な XML パース。
      - SSRF 対策: URL スキーム検証 (http/https 限定)、プライベート/ループバック/リンクローカルアドレス検出、リダイレクト時の事前検査ハンドラ。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
      - トラッキングパラメータ除去および URL 正規化 (_normalize_url, _make_article_id)。
      - 記事ID は正規化 URL の SHA-256 の先頭 32 文字で冪等性を確保。
      - DB へのバルク挿入最適化（チャンクサイズ, トランザクション, INSERT ... RETURNING を使用して実際に挿入された件数を取得）。
    - 記事テキスト前処理 (preprocess_text)、RSS pubDate のパース (_parse_rss_datetime)。
    - テキストから銘柄コード抽出機能 (extract_stock_codes) と既知コードフィルタリング。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。

- Data スキーマ定義
  - src/kabusys/data/schema.py を追加:
    - DuckDB 用の DDL を提供（Raw Layer のテーブル定義を含む: raw_prices, raw_financials, raw_news, raw_executions 等）。
    - DataSchema に基づく三層構造（Raw/Processed/Feature/Execution）を想定。

- Research（特徴量・ファクター）
  - src/kabusys/research/feature_exploration.py を追加:
    - 将来リターン計算 (calc_forward_returns): DuckDB の prices_daily を参照して任意ホライズン（デフォルト 1,5,21 営業日）の将来リターンを一括取得。
    - IC（Information Coefficient）計算 (calc_ic): ファクター値と将来リターンのスピアマンランク相関を計算（欠損や ties を適切に扱う）。
    - ランキングユーティリティ (rank) とファクター統計サマリー (factor_summary) を提供。
    - 実装は pandas 等外部ライブラリに依存せず標準ライブラリのみで実装。

  - src/kabusys/research/factor_research.py を追加:
    - モメンタム (calc_momentum): 1M/3M/6M リターン、200 日移動平均乖離率 (ma200_dev) を計算。データ不足時は None を返す。
    - ボラティリティ/流動性 (calc_volatility): 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金 (avg_turnover)、出来高比 (volume_ratio) を計算。true_range の NULL 伝搬を考慮し正確にカウント。
    - バリュー (calc_value): raw_financials から基準日以前の最新財務を取得し PER/ROE を算出。価格と財務データの LEFT JOIN により欠損時は None を返す。
    - 設計方針としていずれの関数も prices_daily / raw_financials のみを参照し外部 API へはアクセスしない点を明記。

  - src/kabusys/research/__init__.py で主要関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

Security
- ニュース収集と RSS パーシング周りで複数のセキュリティ対策を導入:
  - defusedxml による XML パース、SSRF 対策、プライベート IP 検出、レスポンスサイズ制限、gzip 解凍後チェック等。

Notes / Design
- DuckDB を主要なオンディスク DB として想定。多くの処理は DuckDB 接続を受け取り SQL ウィンドウ関数を活用して一括計算する設計。
- Research モジュールは本番アカウントや発注 API にはアクセスしない（研究/解析専用の安全な設計）。
- 外部依存は最小限（duckdb, defusedxml 等）に留め、標準ライブラリ中心で実装。
- ロギング、入力検証、エラーハンドリングに注意して実装。

Removed
- なし

Deprecated
- なし

Fixed
- なし

Security
- 上述の通り RSS / HTTP 周りのセキュリティ強化を実施（SSRF, XML Bomb, Gzip bomb, 不正スキーム対策など）。

---

注: 本 CHANGELOG は提供されたコードベースの内容から推測して作成した初版リリースノートです。将来的なコミットやリファクタリングに伴い内容を更新してください。