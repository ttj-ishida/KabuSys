Keep a Changelog
=================

すべての注目すべき変更点をこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ初期リリース。
  - src/kabusys/__init__.py にてバージョンを "0.1.0" として公開。

- 環境設定 / 初期化
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする仕組みを追加。
    - 自動読み込みを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env ファイルのパース機能を強化（export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱いなど）。
    - 環境変数の保護（OS 環境変数を protected として .env.local で上書きしない等）を実装。
    - Settings クラスを追加：J-Quants / kabuAPI / Slack / DB パス / 実行環境（development/paper_trading/live）/ログレベルの取得と検証を提供。無効な値の場合は例外を投げる。

- データ取得クライアント
  - src/kabusys/data/jquants_client.py
    - J-Quants API クライアントを実装（トークン取得、ページネーション対応、価格・財務・カレンダー取得関数）。
    - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を導入。
    - リトライロジック（指数バックオフ、最大試行回数）と 401 時の自動トークンリフレッシュを実装。
    - JSON デコード失敗やネットワークエラーに対する堅牢なエラーハンドリング。
    - DuckDB へ保存するための冪等性を考慮した保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。fetched_at を UTC で記録、ON CONFLICT DO UPDATE を使用して重複を更新。

- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py
    - RSS フィード取得・解析・前処理・DuckDB への冪等保存ワークフローを実装。
    - defusedxml を用いた安全な XML パース（XML Bomb 対策）。
    - SSRF 対策：URL スキーム検証、リダイレクト先のスキーム/ホスト検証、プライベート IP の検出。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や gzip 解凍後のサイズチェックによるメモリ DoS 対策。
    - URL 正規化とトラッキングパラメータ除去、SHA-256（先頭32文字）による記事ID生成で冪等性を確保。
    - テキスト前処理、記事の抽出・保存（INSERT ... RETURNING を利用）、記事と銘柄コードの紐付けをバルクで行う機能を実装。
    - 銘柄コード抽出ユーティリティ（4桁数字、known_codes に基づくフィルタ）を追加。

- DuckDB スキーマと初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 層を想定した DuckDB のテーブル DDL 定義を追加（raw_prices, raw_financials, raw_news などの定義を含む）。
    - 各テーブルの制約やデフォルト（fetched_at）を定義し、データ整合性を強化。

- データ処理・特徴量生成（Research）
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算（calc_forward_returns）：複数ホライズン対応、単一クエリでの効率的取得。
    - IC（Information Coefficient）計算（calc_ic）：Spearman（ランク相関）実装、NaN/None の除外、少数データ時の None 処理。
    - ランク変換ユーティリティ（rank）：同順位は平均ランク、浮動小数の丸めで ties 漏れを低減。
    - ファクター統計サマリー（factor_summary）：count/mean/std/min/max/median の計算。

  - src/kabusys/research/factor_research.py
    - モメンタム（calc_momentum）：1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を算出。データ不足は None。
    - ボラティリティ/流動性（calc_volatility）：20日 ATR（atr_20）、相対 ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）。
    - バリュー（calc_value）：raw_financials から最新財務を取得して PER・ROE を計算（EPS 欠損／ゼロの扱いに注意）。
    - いずれも DuckDB 接続を受け取り prices_daily/raw_financials のみを参照する設計で、本番発注 API 等にはアクセスしない。

  - src/kabusys/research/__init__.py
    - 主要ユーティリティ（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）をエクスポート。

- 型変換・ユーティリティ
  - src/kabusys/data/jquants_client.py の内部ユーティリティで堅牢な型変換を実装（_to_float, _to_int）。
  - ニュースモジュールのテキスト前処理・URL 正規化等のユーティリティを追加。

Performance
- J-Quants クライアントと NewsCollector の両方でページネーション処理やバルク INSERT（チャンク化）により効率的なデータ取得・保存を実装。
- RateLimiter によるリクエスト間隔制御でレート上限遵守。

Security
- RSS の XML パースに defusedxml を使用し、XML による攻撃を緩和。
- RSS フェッチ時の SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト時の検証）。
- 外部入力（.env）パースの堅牢化により予期せぬ文字列処理を低減。

Changed
- 該当なし（初期リリース）。

Fixed
- 該当なし（初期リリース）。

Breaking Changes
- 該当なし（初期リリース）。

Notes / Implementation details
- すべてのデータ取得／集計関数は本番発注等の副作用を持たない設計（DuckDB の読み取り/保存とローカル計算に限定）。
- データの取得時刻を明示するため fetched_at を UTC ISO 形式で記録。
- エラーハンドリングはログに詳細を出しつつ、可能な限り処理継続を試みる（ニュース収集はソース単位でフォールトトレランス）。

今後の予定（例）
- Strategy / Execution 層の実装（実売買ロジック、kabu API 統合）。
- 追加の特徴量（Liquidity の拡張、財務指標の追加）、テストカバレッジの強化。
- ドキュメント・運用リファレンスの整備。