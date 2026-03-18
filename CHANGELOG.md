# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルには、リポジトリ内の現行コードベースから推測される主要な機能追加・設計上の決定点・注意点を記載しています。

注: 実際のコミット履歴がないため、以下はコード内容から推測してまとめた初期リリース向けの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-18
### Added
- パッケージ初版を追加。
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数の自動読み込み機能を実装。
    - 自動ロードはプロジェクトルート（.git または pyproject.toml）を起点に行われるため、CWDに依存しない。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 環境変数による自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応、インラインコメント処理を考慮）。
  - Settings クラスを実装し、J-Quants トークン、kabu API 設定、Slack トークン／チャンネル、データベースパス（DuckDB, SQLite）、実行環境（development/paper_trading/live）、ログレベル等をプロパティ経由で取得可能に。
  - env/log_level の値検証（許容値チェック）を実装。
  - デフォルト値: KABUSYS_ENV=development、KABU_API_BASE_URL=http://localhost:18080/kabusapi、DUCKDB_PATH=data/kabusys.duckdb、SQLITE_PATH=data/monitoring.db。

- データ収集クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッタ（120 req/min）を採用。
    - 指数バックオフによるリトライ（最大3回）を実装。リトライ対象ステータスや 429 の Retry-After を考慮。
    - 401 Unauthorized 受信時はリフレッシュトークンから ID トークンを再取得して 1 回だけリトライする仕組みを実装（トークンキャッシュあり）。
    - ページネーション対応で /prices/daily_quotes や /fins/statements を完全取得。
    - 取得データを DuckDB に冪等的に保存する関数を実装（ON CONFLICT DO UPDATE を使用）。
    - 取得データの型変換ユーティリティ（_to_float, _to_int）を実装。整数変換は小数部の切り捨てを避ける挙動。
    - fetched_at を UTC ISO8601 で記録し、Look-ahead bias のトレースを意識。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得と raw_news 保存の実装。
    - RSS の取得時に SS RF 対策（リダイレクト先スキーム検証、プライベート IP 検査）を行うカスタムリダイレクトハンドラを採用。
    - defusedxml を用いた XML パースで XML Bomb 等への対策を実装。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）を厳格に検査し、gzip 解凍後もバイト数を検証。
    - URL 正規化機能 (_normalize_url) を実装（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリのソート）。
    - 記事ID を正規化 URL の SHA-256 ハッシュ先頭 32 文字で生成し冪等性を担保。
    - テキスト前処理（URL 除去、空白正規化）を実装。
    - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING）をチャンク化して実行し、実際に挿入された記事IDリストを返す（INSERT ... RETURNING を利用）。
    - 銘柄コード抽出（4桁数字）と news_symbols テーブルへの紐付けを一括保存するユーティリティを提供（重複除去・チャンク挿入）。
    - デフォルト RSS ソース例: Yahoo Finance（news.yahoo.co.jp のビジネス RSS）。

- データスキーマ（kabusys.data.schema）
  - DuckDB 用スキーマ定義を実装（Raw / Processed / Feature / Execution 層の方針を明記）。
  - Raw 層のテーブル定義を追加（例: raw_prices, raw_financials, raw_news, raw_executions の DDL 定義。raw_executions は途中まで定義あり）。

- リサーチ機能（kabusys.research）
  - ファクター探索・評価モジュールを提供。
    - feature_exploration:
      - calc_forward_returns: 指定基準日から複数ホライズン（デフォルト [1,5,21] 営業日）における将来リターンを DuckDB の prices_daily テーブルから一括で計算。
      - calc_ic: ファクターと将来リターンのスピアマンランク相関（Information Coefficient）を計算。欠損や repeats を考慮し、有効件数が少なければ None を返す。
      - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
      - rank: ランク変換（同順位は平均ランク）で丸め誤差対策として round(..., 12) を使用。
      - 実装は標準ライブラリのみを想定、外部依存を避ける設計。
    - factor_research:
      - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を計算。データ不足時は None を返す。
      - calc_volatility: 20日 ATR（平均 true range）、ATR 比率、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を正しく扱う設計。
      - calc_value: raw_financials から基準日以前の最新財務を取得して PER（EPS が 0/欠損のときは None）・ROE を計算。
      - 各関数は prices_daily / raw_financials のみ参照し、本番APIや発注処理にはアクセスしないことを明記。

- モジュール公開 API（kabusys.research.__init__）
  - 主要関数を __all__ にまとめて再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- ニュース収集での SS RF 対策と XML パース保護（defusedxml）を追加。
- RSS URL のスキーム検証、リダイレクト先のホスト検査、プライベートIP拒否で内部ネットワークへのアクセスを防止。
- .env 読み込み時に OS 環境変数を保護する protected set を採用（.env.local で上書きは可能だが OS 環境を上書きしない等の方針を実装）。

### Notes / Migration
- .env 自動読み込みはデフォルトで有効。テストや CI で無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB および SQLite のデフォルトパスは settings で指定されているため、別パスを使用する場合は環境変数（DUCKDB_PATH / SQLITE_PATH）で変更してください。
- J-Quants API の認証に必要な JQUANTS_REFRESH_TOKEN、Slack 用に SLACK_BOT_TOKEN / SLACK_CHANNEL_ID、kabu API 用に KABU_API_PASSWORD 等の必須環境変数は Settings 経由で取得し、未設定時は ValueError が発生します。README/.env.example を用意して設定してください。

--- 

この CHANGELOG はコードベースを解析して推測した内容に基づいて作成しています。実際のリリースノートとして使用する場合は、実コミット・リリース歴に合わせて調整してください。