# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

最新リリース
------------

### [0.1.0] - 2026-03-18

Added
- パッケージ骨組みを追加
  - パッケージ名: kabusys、バージョン 0.1.0
  - __all__ に data/strategy/execution/monitoring を公開

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数からの設定読み込みを実装
  - プロジェクトルート検出ロジック: .git または pyproject.toml を基準に探索（CWD に依存しない）
  - .env/.env.local の読み込み優先度を実装（OS 環境変数 > .env.local > .env）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト向け）
  - .env パーサー: export 形式、クォート（エスケープ対応）、行末コメント判定などに対応
  - Settings クラス: J-Quants / kabu / Slack / DB パス / ログレベル / 環境（development/paper_trading/live）の取得とバリデーション
  - 必須キー未設定時に分かりやすいエラーメッセージを投げる _require()

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアント実装
    - 固定間隔レートリミッタ（120 req/min）
    - リトライ（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象
    - 401 の場合は ID トークン自動リフレッシュを行い 1 回リトライ
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements
    - JPX マーケットカレンダー取得用 fetch_market_calendar
  - DuckDB への冪等保存ロジック
    - save_daily_quotes/save_financial_statements/save_market_calendar: ON CONFLICT（UPSERT）で重複を排除
    - fetched_at を UTC ISO8601 で付与して取得時刻を記録（Look-ahead バイアス可視化）
  - HTTP 呼び出しの JSON デコード失敗時や最大リトライ到達時の明確なエラー処理
  - 型変換ユーティリティ: _to_float / _to_int（不正値や小数誤変換を安全に扱う）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプライン実装
    - fetch_rss: RSS 取得・XML パース・記事整形（content:encoded 優先）
    - preprocess_text: URL 除去・空白正規化
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
    - トラッキングパラメータ除去（utm_ 等）、クエリソート、フラグメント除去による正規化
    - gzip 圧縮対応、レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）
    - defusedxml を使用して XML Bomb 等の攻撃対策
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキーム・プライベートアドレス検査、_SSRFBlockRedirectHandler による事前検査
    - _urlopen を分離してテストでモック可能
  - DB 保存
    - save_raw_news: INSERT ... RETURNING で実際に挿入された記事IDを返す。チャンク分割と 1 トランザクションで効率的に挿入
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄の紐付けを一括挿入（ON CONFLICT DO NOTHING）。チャンク処理、トランザクション管理
    - run_news_collection: 複数ソースを順に処理。ソース単位で独立したエラーハンドリング（1 ソース失敗でも他は継続）
  - 銘柄抽出: 正規表現ベースで 4 桁銘柄コードを抽出し、known_codes でフィルタして重複排除

- リサーチ / ファクター計算（kabusys.research）
  - feature_exploration
    - calc_forward_returns: 指定日基準で複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで計算
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）計算（必要レコード数チェック）
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸めで ties の検出漏れを減らす）
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー
  - factor_research
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200 日移動平均乖離）を計算。データ不足は None を返す
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、当日出来高比率を計算。true range の NULL 伝播制御により正確なカウント
    - calc_value: raw_financials から最新財務（target_date 以前）を結合して PER/ROE を算出。EPS 0/欠損は None
  - 設計方針: DuckDB 接続のみを受け取り prices_daily / raw_financials テーブルを参照。外部 API にはアクセスしないことを明示

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用 DDL を追加（Raw 層のテーブル定義を含む）
    - raw_prices, raw_financials, raw_news, raw_executions など（Raw / Processed / Feature / Execution の層設計に準拠）
  - 初期化用モジュールとしてログ出力を含む

- モジュール公開
  - kabusys.research.__init__ で主要関数を再エクスポート（calc_momentum/calc_value/calc_volatility/zscore_normalize 等）

Security
- SSRF、XML 攻撃、メモリ DoS などを念頭に置いた実装
  - defusedxml の使用による XML 攻撃対策
  - URL スキーム検証とプライベートホスト検査による SSRF 対策
  - リダイレクト時にも検査を行うハンドラを導入
  - レスポンスバイト上限（MAX_RESPONSE_BYTES）と gzip 解凍後の再チェック
  - .env 読み込み時に OS 環境変数（protected）を保護し、意図しない上書きを防止

Logging / Observability
- 各主要処理に logger の info/debug/warning を追加
  - データ取得件数や保存件数、スキップ件数、リトライログ、トランザクション失敗時の例外ログ等を出力

Notes / Misc
- テストしやすさへの配慮
  - 環境自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）
  - _urlopen の差し替えでネットワーク呼び出しをモック可能
- 汎用ユーティリティの細かな挙動設計（例: rank の丸め精度、_to_int の小数切捨て防止）

---

未記載の細かな内部実装や将来的な変更はソースコードを参照してください。今後のリリースでは Breaking Changes/Fixed/Changed の区分で明確に記載します。