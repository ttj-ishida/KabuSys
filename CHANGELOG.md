CHANGELOG
=========
すべての注目すべき変更はここに記録します。
このファイルは「Keep a Changelog」の形式に準拠しています（日本語訳）。

[Unreleased]
------------

- なし

0.1.0 - 2026-03-18
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開情報: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 設定／環境変数管理 (src/kabusys/config.py)
  - プロジェクトルート自動検出: .git または pyproject.toml を基にルートを探索して .env ファイルを読み込む実装。
  - .env/.env.local の読み込み順序と上書きルールを実装（OS 環境変数を保護する protected set）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト向け）。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理等に対応。
  - Settings クラスを提供し、J-Quants トークン・kabu API パスワード・Slack トークン・DB パス等をプロパティ経由で取得。KABUSYS_ENV と LOG_LEVEL の値検証 (許容値チェック) を実装。
  - デフォルト値: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等。

- Data レイヤー（DuckDB）スキーマ定義 (src/kabusys/data/schema.py)
  - Raw / Processed / Feature / Execution 層のための DDL を定義。raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義（初期化用モジュール）。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
  - 認証ヘルパー: get_id_token（リフレッシュトークンから idToken を取得）。
  - HTTP レイヤ: 固定間隔スロットリングによる RateLimiter (120 req/min 固定) を実装。
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 の場合は Retry-After ヘッダを優先。
  - 401 発生時の自動トークンリフレッシュ（1 回のみ）とリトライ。モジュールレベルの ID トークンキャッシュを共有。
  - DuckDB への保存ユーティリティ: save_daily_quotes, save_financial_statements, save_market_calendar — 冪等性を保つため ON CONFLICT DO UPDATE を使用。
  - データ型変換ユーティリティ: _to_float / _to_int（変換ルール: 空値/不正値は None、"1.0" のような数値文字列 → int 変換の扱い等を明記）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからのニュース収集フローを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ/堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - HTTP レスポンスサイズ上限: MAX_RESPONSE_BYTES = 10MB。Content-Length と実際読み込みで制限。
    - gzip 圧縮の解凍と解凍後サイズ検査（Gzip bomb 対策）。
    - SSRF 対策: リダイレクト時にスキーム検証・プライベートアドレス検証を行うカスタム RedirectHandler と事前ホスト検査。
    - URL スキーム検証（http/https のみ許可）。
  - シャッフル対策と冪等性:
    - 記事 ID は URL 正規化（トラッキングパラメータ削除、クエリ並べ替え、フラグメント除去等）の SHA-256 ハッシュ先頭32文字で生成。
    - raw_news への挿入は ON CONFLICT DO NOTHING を利用し、INSERT ... RETURNING で実際に挿入された記事 ID のリストを取得。
    - news_symbols は重複除去・チャンク分割（デフォルトチャンク = 1000）・トランザクションでバルク挿入、INSERT ... RETURNING を利用して挿入数を正確に返す。
  - テキスト前処理: URL 除去、空白正規化（preprocess_text）。
  - 銘柄コード抽出: 4桁数字パターン（\b\d{4}\b）を検出して known_codes と照合する extract_stock_codes。

- Research / Feature モジュール (src/kabusys/research/*)
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 指定日の終値から複数ホライズン（default [1,5,21]）の将来リターンを一括で計算。DuckDB の LEAD を利用した単一クエリ実行。
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（Spearman ρ）を計算。rank ユーティリティは同順位を平均ランクで扱い、丸め処理で浮動小数点の ties 検出漏れを防止。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算（None 値は除外）。
    - 実装方針: DuckDB 接続を受け取り prices_daily テーブルのみ参照、外部 API へアクセスしない。
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m および 200 日移動平均乖離 (ma200_dev) を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、当日出来高比（volume_ratio）を計算。true_range 算出で NULL 伝播を制御。
    - calc_value: raw_financials から target_date 以前の最新財務データを取り、PER / ROE を価格と結合して計算。EPS 不在/0 の場合は PER を None にする。
    - 定数・スキャン幅の設計（例: MA200 を考慮したスキャン日数、ATR スキャンバッファなど）を明示。
  - research パッケージ公開 API（src/kabusys/research/__init__.py）:
    - calc_momentum, calc_volatility, calc_value, zscore_normalize (kabusys.data.stats から), calc_forward_returns, calc_ic, factor_summary, rank をエクスポート。

Changed
- 初版のため該当なし。

Fixed
- 初版のため該当なし。

Deprecated
- 初版のため該当なし。

Removed
- 初版のため該当なし。

Security
- RSS 処理における多数の堅牢化措置を導入:
  - defusedxml による安全な XML パース。
  - SSRF 対策（リダイレクト時のスキーム/ホスト検査、ホストのプライベートアドレス判定）。
  - レスポンスサイズと gzip 解凍後サイズの制限（DoS 対策）。
- J-Quants クライアント: API レート制限遵守、リトライとトークン自動リフレッシュにより安定した認証処理とフェイルオーバーを実装。

Notes / Implementation details
- DuckDB を一次保存先として利用する想定。各関数は DuckDB の接続オブジェクト（duckdb.DuckDBPyConnection）を引数に取る設計。
- 外部依存は最小限（defusedxml と duckdb が主な外部依存）。
- 多くの DB 書き込みを冪等化（ON CONFLICT）しているため、繰り返し実行が安全。
- news_collector の記事 ID 設計は URL 正規化に依存するため、URL の扱いが将来変わる場合は互換性に注意。

今後予定（推測）
- Execution 層（kabu ステーション連携、発注ロジック）の実装拡張。
- Feature 層の追加的なファクター（PBR・配当利回り等）や zscore 正規化の詳細強化。
- テストカバレッジの拡充および CI／デプロイ関連のドキュメント。

--- 
（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして公開する前に必要に応じて修正・補足してください。）