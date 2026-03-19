# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
このファイルには公開バージョンおよび主要な機能追加・設計方針・注意点を日本語でまとめています。

NOTE: 現在のリリースは初版のため、主に「追加」項目を列挙しています。

すべての非互換（breaking）変更は明示します。

## [Unreleased]

- （なし）

## [0.1.0] - 2026-03-19

Added
- パッケージ初期公開
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - トップレベルエクスポート: data, strategy, execution, monitoring

- 環境変数/設定管理 (kabusys.config)
  - .env/.env.local を自動読み込みする仕組みを実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動読み込みの無効化: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 をサポート。
  - .env パーサを独自実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープ対応、インラインコメントルールの扱いを実装）。
  - Settings クラスを提供し、必須項目の取得や値検証を行うプロパティを追加。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID などの必須チェック。
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/INFO/...）の検証。
    - DB パス: DUCKDB_PATH / SQLITE_PATH のデフォルト値と Path 処理。
    - is_live / is_paper / is_dev ユーティリティプロパティ。

- J-Quants API クライアント (kabusys.data.jquants_client)
  - HTTP 要求ユーティリティを実装（JSON デコード、エラーハンドリング、ページネーション対応）。
  - レート制限制御: 固定間隔スロットリング（120 req/min に基づく _RateLimiter）。
  - 再試行ロジック: 指数バックオフで最大 3 回のリトライ（408/429/5xx 等を対象）、429 の Retry-After ヘッダ対応。
  - 認証トークン管理:
    - refresh_token から id_token を取得する get_id_token。
    - モジュールレベルで id_token をキャッシュし、401 受信時に自動で 1 回だけリフレッシュして再試行。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等性を重視、ON CONFLICT を使用）:
    - save_daily_quotes → raw_prices テーブルへ保存（fetched_at を UTC で記録）
    - save_financial_statements → raw_financials テーブルへ保存
    - save_market_calendar → market_calendar テーブルへ保存
  - 型変換ユーティリティ: _to_float / _to_int（空値や不正値の安全処理）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィード収集フローを実装（フェッチ → 前処理 → DB 保存 → 銘柄紐付け）。
  - セキュリティ対策:
    - defusedxml を使用した安全な XML パース（XML Bomb 等対策）。
    - SSRF 対応: リダイレクト時のスキーム/ホスト検査、初回 URL のプライベートアドレス検査、リダイレクト先再検証。
    - 許可スキームは http/https のみ。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の追加検査（Gzip bomb 対策）。
  - 記事ID の決定方法:
    - 記事 URL を正規化（スキーム/ホスト小文字化、トラッキングパラメータ削除、フラグメント削除、クエリソート）して SHA-256 の先頭 32 文字を ID として使用 → 冪等性確保。
  - 前処理ユーティリティ:
    - URL 除去、空白正規化（preprocess_text）
    - RSS pubDate の RFC 日付解析と UTC 変換（パース失敗時は警告ログと現在時刻で代替）
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いて実際に挿入された記事 ID のリストを返す。チャンク化 & 単一トランザクションで実行。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols テーブルへの紐付けをチャンクで安全に挿入（ON CONFLICT で重複を無視）。
  - 銘柄コード抽出:
    - 日本株の 4 桁数字パターンを抽出し、known_codes に基づいて有効コードのみを返す（重複除去）。

- DuckDB スキーマ定義・初期化 (kabusys.data.schema)
  - DataSchema.md に基づくレイヤー分離を反映した DDL を実装（Raw / Processed / Feature / Execution の設計方針）。
  - raw_prices / raw_financials / raw_news / raw_executions 等のテーブル DDL を定義（主キー・型・チェック制約を含む）。

- 研究用ユーティリティ (kabusys.research)
  - 特徴量探索 (feature_exploration):
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily を参照して一括計算。ホライズンは営業日数で検証（1〜252）。
    - calc_ic: ファクター値と将来リターン間のスピアマンランク相関（IC）を計算。欠損や非有限値を除外し、有効レコード数が 3 未満の場合は None を返す。
    - rank: 同順位は平均ランクを採用、丸め (round(v,12)) により浮動小数点誤差の影響を低減。
    - factor_summary: count/mean/std/min/max/median を計算（None を除外）。
  - ファクター計算 (factor_research):
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200 日移動平均乖離）を計算。データ不足時は None を返す。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算。TRUE RANGE の NULL 伝播を制御し、20 行未満は None。
    - calc_value: raw_financials の最新レコード（target_date 以前）と当日の株価を組み合わせ、per / roe を計算（EPS=0 や欠損時は None）。ROW_NUMBER を用いてターゲット以前の最新財務レコードを取得。
  - research パッケージ __init__ で主要関数を再エクスポート（calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank）。

Security / Reliability
- API クライアント・ニュース収集で以下を重視:
  - レート制限遵守、リトライ、トークンの安全な更新。
  - XML/URL 関連の脆弱性対策（defusedxml、SSRF 対策、レスポンスサイズ制限）。
- DB 保存は基本的に冪等（ON CONFLICT）かつトランザクション単位で処理し、部分挿入や重複の影響を抑制。

Notes / Migration
- 環境変数が不足していると Settings のプロパティで ValueError が発生します。開発前に .env（.env.example を参照）を準備してください。重要なキー例:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
- .env の自動ロードはプロジェクトルート検出に依存します。パッケージ配布後やテスト時に自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- ニュースコレクタは外部ネットワークを使用するため、テスト時は fetch_rss/_urlopen をモックすることを推奨します。

Fixed
- （初回リリースのため該当なし）

Changed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Acknowledgments
- 本リリースはデータ取得・前処理・特徴量生成・ニュース収集・設定管理・スキーマ定義に重点を置いた初期基盤実装です。将来的に戦略実行部（execution）やモニタリングの機能強化、テストカバレッジ追加、ドキュメント整備を予定しています。