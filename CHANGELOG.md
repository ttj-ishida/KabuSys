# Changelog

すべての重要な変更をここに記録します。  
このファイルは "Keep a Changelog" の形式に従っています。  
バージョニングは semver を採用します。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19
初回リリース — KabuSys 日本株自動売買システムのコア機能を実装。

### Added
- パッケージ初期化
  - `kabusys.__init__` を追加。バージョン (0.1.0) と公開サブパッケージ一覧 (`data`, `strategy`, `execution`, `monitoring`) を定義。

- 設定 / 環境変数管理 (`kabusys.config`)
  - プロジェクトルート自動検出機能を実装（`.git` または `pyproject.toml` を元に探索）。
  - `.env` / `.env.local` の自動読み込み（OS 環境変数を保護しつつ `.env.local` は上書き）を実装。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env パーサーは export プレフィックス、クォート文字、バックスラッシュエスケープ、インラインコメントへの対応を含む堅牢な実装。
  - 必須環境変数取得時に未設定なら明確なエラーメッセージを返す `_require` を提供。
  - `Settings` クラスを追加し、以下の設定をプロパティで提供:
    - J-Quants / kabuステーション / Slack トークン・チャンネル
    - DB パス（DuckDB / SQLite）
    - 環境 (`development`, `paper_trading`, `live`) と `log_level` の検証
    - 環境判定ユーティリティ (`is_live`, `is_paper`, `is_dev`)

- データ取得・保存クライアント (`kabusys.data.jquants_client`)
  - J-Quants API クライアント実装。
  - 固定間隔ベースのレートリミッター（120 req/min）を実装。
  - 再試行（指数バックオフ、最大3回）と 408/429/5xx のリトライハンドリングを実装。
  - 401 ステータス時の自動トークンリフレッシュ（1 回のみ）を実装し、トークンキャッシュを共有してページネーション間で利用。
  - ページネーション対応のフェッチ関数を実装:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (財務データ)
    - fetch_market_calendar (マーケットカレンダー)
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE/DO NOTHING を使用）:
    - save_daily_quotes → raw_prices
    - save_financial_statements → raw_financials
    - save_market_calendar → market_calendar
  - 型安全な数値変換ユーティリティ `_to_float`, `_to_int` を実装（不正値や小数誤変換を防止）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード取得と前処理の実装（デフォルトに Yahoo Finance のカテゴリRSS）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等に対抗）。
    - リダイレクト時のスキーム/ホスト検査や事前ホスト検証により SSRF を軽減（プライベート IP の検出と拒否）。
    - URL スキーム検証（http/https のみ許可）。
    - 最大受信バイト数制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズ検査（Gzip Bomb 対策）。
  - URL 正規化（トラッキングパラメータ削除・スキーム/ホスト小文字化・フラグメント削除・クエリキーソート）と記事ID生成（正規化 URL の SHA-256 の先頭 32 文字）。
  - テキスト前処理（URL 除去・空白正規化）を実装。
  - RSS の pubDate を安全にパースする `_parse_rss_datetime` を実装（失敗時は警告ログと現在時刻で代替）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING を使い、新規挿入された記事IDのリストを返す（チャンク & 単一トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存（チャンク分割 & トランザクション）。
  - 銘柄コード抽出ユーティリティ `extract_stock_codes`（4桁数値パターン & known_codes フィルタリング）。
  - 統合収集ジョブ `run_news_collection` を提供（ソース単位でフェイルセーフ、紐付け処理のバッチ化）。

- リサーチ / 特徴量探索 (`kabusys.research`)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト: 1,5,21営業日）の将来リターンを DuckDB 上の prices_daily から一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算（None や非有限値除外、レコード数が少ない場合 None を返す）。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（丸めで ties 検出漏れを防止）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - 実装は標準ライブラリのみで依存を最小化（pandas 等非依存）。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離率）を計算。データ不足は None。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播制御等を実装。
    - calc_value: raw_financials から最新財務データを取得し PER, ROE を計算（EPS が 0/欠損時は None）。
    - 各関数は DuckDB の prices_daily / raw_financials のみ参照し、本番 API へのアクセスなしで完結。
  - `kabusys.research.__init__` にて便利関数群を公開（zscore_normalize は data.stats からインポート）。

- スキーマ定義 (`kabusys.data.schema`)
  - DuckDB 用の DDL を定義（Raw / Processed / Feature / Execution 層を想定）。
  - Raw レイヤーのテーブル DDL を追加（例: raw_prices, raw_financials, raw_news, raw_executions 等。制約・型・PK を明示）。

### Changed
- 該当なし（初回リリース）。

### Fixed
- 該当なし（初回リリース）。

### Security
- ニュース収集における SSRF 対策、defusedxml による XML パースの安全化、受信サイズ上限・gzip 解凍後サイズ検査による DoS 対策を実装。
- J-Quants クライアントはトークンの自動リフレッシュを 1 回に制限し、allow_refresh フラグで無限再帰を防止。

### Notes
- 多くのデータ処理関数は DuckDB 接続（duckdb.DuckDBPyConnection）を受け取り、prices_daily / raw_financials 等のテーブルに依存します。事前にスキーマ初期化とデータロードが必要です。
- 外部依存は極力抑えているものの、RSS パースに defusedxml を使用しています（セキュリティ目的）。
- .env パーサーは標準的なケースに対応していますが、非常に特殊な .env フォーマットには注意してください。
- このバージョンは研究用・ペーパートレード用途から本番（live）環境までの運用を想定した設計を行っていますが、本番で発注を行うモジュール（execution 等）の実運用前には十分なテストと監査を推奨します。

--- 

（将来の変更はここに追記してください）