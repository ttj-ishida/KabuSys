Keep a Changelog
=================

すべての変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  
<https://keepachangelog.com/ja/1.0.0/>

Unreleased
----------

（なし）

0.1.0 - 2026-03-19
------------------

Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys/__init__.py）。バージョンは 0.1.0。
  - strategy, execution パッケージのスケルトンを追加（将来の戦略・発注モジュールの土台）。
- 環境設定/ロード（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能をプロジェクトルート（.git または pyproject.toml を探索）に依存して実装。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ: export プレフィックス対応、クォート文字列のエスケープ処理、行内コメント処理、無効行スキップ等に対応。
  - 設定プロパティ群（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、環境判定・ログレベル検証等）を提供。KABUSYS_ENV / LOG_LEVEL のバリデーション実装。
- Data レイヤー（kabusys.data）
  - DuckDB スキーマ定義（kabusys.data.schema）: raw_prices / raw_financials / raw_news / raw_executions など Raw Layer 用 DDL を追加（スキーマ定義文字列を提供）。（DataSchema.md に基づく階層設計コメントを含む）
  - J-Quants API クライアント（kabusys.data.jquants_client）
    - ベース URL とエンドポイント実装（トークン取得、日足・財務・マーケットカレンダー取得）。
    - ページネーション対応（pagination_key を用いたループ取得）。
    - レートリミッタ（固定間隔スロットリング、120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回）と対象ステータスの扱い（408/429/5xx）を実装。429 の場合は Retry-After を優先。
    - 401 (Unauthorized) 受信時は ID トークン自動リフレッシュを 1 回試行する仕組みを実装。モジュールレベルでトークンキャッシュを保持。
    - DuckDB へ保存するための冪等保存（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。ON CONFLICT DO UPDATE を利用して重複更新を回避。
    - レスポンス値変換ユーティリティ（_to_float / _to_int）を提供。型安全・不正値耐性を強化。
  - ニュース収集（kabusys.data.news_collector）
    - RSS フィード取得・パース機能（fetch_rss）と記事保存（save_raw_news）・銘柄紐付け（save_news_symbols / _save_news_symbols_bulk）を実装。
    - セキュリティ/堅牢化:
      - defusedxml を使った XML パース（XML Bomb 対策）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバックかを検査、リダイレクト時にも検査するカスタム RedirectHandler を使用。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と超過チェック、gzip 解凍時のサイズ二重チェック（Gzip bomb 対策）。
      - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント削除）と SHA-256 による記事 ID 生成（先頭32文字）。
      - 記事本文の前処理（URL 削除、空白正規化）と 4 桁銘柄コード抽出（既知コードのみ）。
    - DB 保存はチャンク分割してトランザクション内で INSERT ... RETURNING を行い、実際に挿入された ID を正確に取得。新規記事の銘柄紐付けは一括挿入で処理。
    - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを設定。
- Research（kabusys.research）
  - feature_exploration モジュール
    - 将来リターン計算 calc_forward_returns（複数ホライズンに対応、単一クエリで取得、営業日→カレンダー日スキャン幅調整）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランクで算出、欠損/有限値の除外、サンプル数閾値）。
    - ランク変換ユーティリティ rank（同順位の平均ランク処理、丸めによる ties 検出安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - factor_research モジュール
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離率）を計算。過去データ不足時は None。
    - calc_volatility: atr_20（20 日 ATR）、atr_pct（ATR / close）、avg_turnover（20 日平均売買代金）、volume_ratio（当日出来高 / 20 日平均）を計算。真の true_range 計算で NULL 伝播を厳密に扱う。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS が 0 または欠損時は PER を None）。
  - research パッケージ __init__ にて主要関数群を再公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
    - （zscore_normalize は kabusys.data.stats で提供される前提）
- ロギング: 各主要処理で logger を用いた情報・警告・デバッグログを追加（取得件数・スキップ件数・失敗時の例外ログ等）。

Security
- RSS パーサに defusedxml を使用し XML 攻撃を軽減。
- RSS フェッチで SSRF を考慮したリダイレクト検査とプライベートアドレス検出を実装。
- RSS レスポンスサイズの上限チェックと gzip 解凍後の再チェックを実施（DoS 対策）。
- J-Quants クライアントでの HTTP リトライ／トークンリフレッシュにより不正な例外に対する耐性を向上。

Notes
- DuckDB スキーマ文字列は定義されているが、スキーマ作成ユーティリティ関数（例: create_schema() などのエクスポート）は現時点でソース上に明示されていません。DDL を用いて外部から初期化する想定です。
- strategy / execution パッケージはスケルトンのみで、実際の発注・戦略ロジックは未実装。
- 一部モジュール（例: kabusys.data.stats の zscore_normalize）は参照されているものの、このリリースに含まれるコード断片では実装が提示されていません（別ファイルで提供される想定）。

Acknowledgements
- 本リリースはコードベースから推測した初期実装内容に基づき CHANGELOG を作成しました。実際のリリースノートとして利用する際は日付・項目の確定や追加情報の検証を推奨します。