CHANGELOG
=========

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: 以下は提示されたコードベースから推測して作成した変更履歴です。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-18
-------------------

Added
- 基本パッケージ初期実装
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、公開モジュール指定（data, strategy, execution, monitoring）。
- 環境設定管理 (kabusys.config)
  - .env ファイル（.env.local を優先）と OS 環境変数を組み合わせて設定をロードする自動ロード機能を実装。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を導入し、CWD に依存しない読み込みを実現。
  - .env パーサーを実装（export プレフィックス、クォート文字列、インラインコメント、エスケープ対応）。
  - 必須設定取得用 _require(), Settings クラスを提供（J-Quants トークン、kabu API などのプロパティ）。
  - KABUSYS_ENV / LOG_LEVEL の妥当性検証とユーティリティプロパティ（is_live / is_paper / is_dev）。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - API 呼び出し共通ユーティリティ（HTTP リクエスト、JSON デコード）。
  - レート制御: 固定間隔スロットリングで 120 req/min を満たす _RateLimiter を実装。
  - 冪等性・堅牢性:
    - 最大リトライ（指数バックオフ、最大 3 回）を実装（408/429/5xx を対象）。
    - 401 受信時には ID トークンを自動リフレッシュして 1 回リトライ。
    - ページネーション対応（pagination_key を追跡して重複防止）。
    - fetched_at に UTC タイムスタンプを記録（Look-ahead bias 対策）。
  - データフェッチ関数:
    - fetch_daily_quotes（OHLCV 日足、ページネーション対応）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes（raw_prices、ON CONFLICT による UPDATE）
    - save_financial_statements（raw_financials、ON CONFLICT による UPDATE）
    - save_market_calendar（market_calendar、ON CONFLICT による UPDATE）
  - 型変換ユーティリティ _to_float / _to_int（安全変換のルールを明確化）。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集パイプラインを実装（fetch_rss / save_raw_news / save_news_symbols / run_news_collection）。
  - セキュリティ・頑健性強化:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - SSRF 対策: リダイレクト時のスキーム検査、ホストのプライベートアドレス検証（DNS 解決による A/AAAA チェック）、_SSRFBlockRedirectHandler。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後の再検証（Gzip bomb 対策）。
    - トラッキングパラメータ除去（utm_*, fbclid 等）による URL 正規化と SHA-256 ベースの記事 ID 生成（先頭32文字）。
  - テキスト前処理（URL 除去、空白正規化）。
  - 銘柄コード抽出（正規表現で4桁コード検出と既知コードフィルタリング）。
  - DB 保存の工夫:
    - チャンク化挿入（_INSERT_CHUNK_SIZE）で SQL 長とパラメータ数を制限。
    - トランザクション単位で挿入し、INSERT ... RETURNING を使って実際に挿入された件数を取得。
    - news_symbols の一括保存ユーティリティ（重複排除、チャンク挿入）。
  - デフォルト RSS ソースを定義（例: Yahoo Finance ビジネスカテゴリ）。

- データスキーマと初期化 (kabusys.data.schema)
  - DuckDB 用スキーマ定義（Raw Layer のテーブル DDL を実装: raw_prices, raw_financials, raw_news, raw_executions (途中)）。
  - 各テーブルの型制約・PRIMARY KEY・CHECK 制約を含む DDL を定義。

- 研究・特徴量モジュール (kabusys.research)
  - feature_exploration.py:
    - calc_forward_returns（将来リターンを DuckDB の prices_daily から一度のクエリで取得）
    - calc_ic（Spearman ランク相関（IC）計算、ランク処理・欠損/非有限値除外）
    - rank（同順位は平均ランク、丸めによる ties 対策）
    - factor_summary（count/mean/std/min/max/median を計算）
  - factor_research.py:
    - calc_momentum（mom_1m/mom_3m/mom_6m、ma200_dev。データ不足時は None を返す）
    - calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio。true_range の NULL 伝播を制御）
    - calc_value（raw_financials の最新財務データと株価を結合して per, roe を計算）
  - 設計方針:
    - DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照（外部 API にはアクセスしない）。
    - 外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装。
    - 結果は (date, code) ベースの dict リストで返却。
  - research パッケージ __init__ で主要関数を再公開（calc_momentum 等と zscore_normalize をインポートしてエクスポート）。

Changed
- （初リリースのため「変更」はなし）

Fixed
- （初リリースのため「修正」はなし）

Security
- RSS パーサーで defusedxml を使用、SSRF 対策（リダイレクト検査・プライベートアドレス拒否）、レスポンスサイズ制限、gzip 解凍後検証など複数の安全対策を導入。

Notes / Limitations
- research モジュールは外部依存を使わず実装されているため、大規模データ処理や高度な最適化は今後の改善対象。
- calc_value では PBR や配当利回りは未実装であり、今後拡張の余地あり。
- schema.py の raw_executions テーブル定義はコード断片で終わっており、Execution Layer の完全な DDL は追加実装が必要。
- J-Quants クライアントは urllib を使った実装であり、将来的に HTTP クライアント切替（requests / httpx）や非同期対応を検討可能。
- news_collector は URL 正規化 / 4桁コード抽出等に基づく紐付けを行うが、名称ベースの紐付けや自然言語処理による拡張は未実装。

Contributors
- コードベースの実装を元に作成（実際のコントリビュータはソース管理履歴を参照してください）。

-- END --