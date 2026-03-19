# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠します。  
このプロジェクトはセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買プラットフォームのコアライブラリを提供します。以下の主要機能を実装しています。

### Added
- パッケージ基礎
  - パッケージエントリポイントを追加（kabusys.__init__）。公開 API: data, strategy, execution, monitoring。
  - バージョン: 0.1.0。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から検出）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサー実装: export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント対応。無効行のスキップ。
  - Settings クラスを提供し、J-Quants トークン、kabu API パスワード、Slack トークン・チャネル、データベースパス等をプロパティ経由で取得。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）。is_live / is_paper / is_dev ヘルパー。

- データ取得・保存（kabusys.data.jquants_client, schema）
  - J-Quants API クライアントを実装。主な機能:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装。
    - 冪等な保存（DuckDB への INSERT ... ON CONFLICT DO UPDATE）。
    - ページネーション対応（pagination_key）。
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対応）。429 の場合は Retry-After を考慮。
    - 401 時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュの共有。
    - fetch_* 系 API: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
    - DuckDB へ保存するユーティリティ: save_daily_quotes, save_financial_statements, save_market_calendar（fetched_at を UTC で記録）。
    - 入力変換ユーティリティ _to_float / _to_int（安全な変換、空値や不正値は None）。
  - DuckDB 用スキーマ定義モジュール（kabusys.data.schema）に初期テーブル DDL を追加（raw_prices / raw_financials / raw_news / raw_executions 等の定義を含む）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する一連の機能を実装。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを定義。
    - RSS の取得・パース（defusedxml を用いた安全な XML パース）。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES=10MB）および gzip 解凍時のサイズチェック（Gzip bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、ホストのプライベートアドレス判定、リダイレクト先検査用ハンドラ実装。
    - テキスト前処理（URL除去・空白正規化）。
    - DB 保存: チャンク化された INSERT ... ON CONFLICT DO NOTHING RETURNING を用い、実際に挿入された記事IDを返す（トランザクションでまとめて実行）。
    - 銘柄コード抽出（4桁数字）と news_symbols への紐付けを一括挿入するユーティリティを提供。
    - run_news_collection により複数ソースを順次収集し、エラーが起きても他ソースの収集を継続。

- リサーチ / ファクター計算（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日から各ホライズン先（デフォルト 1,5,21 営業日）の将来リターンを DuckDB の prices_daily から一括クエリで計算。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足や分散ゼロ時の保護。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を算出。
    - rank: 同順位は平均ランクで扱うランク関数（丸めで ties 対策）。
    - 実装は標準ライブラリのみで依存を最小化。
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）を prices_daily から計算。必要な行数が不足する場合は None を返す設計。
    - calc_volatility: 20日 ATR（true range の平均）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播に注意した実装。
    - calc_value: raw_financials の最新レコード（target_date 以前）と当日の終値を組み合わせて PER / ROE を計算（EPS が 0 または欠損の場合は None）。
  - kabusys.research.__init__ で主要関数を再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集でのセキュリティ対策を追加:
  - defusedxml による安全な XML パース（XML bomb 等への対策）。
  - SSRF 対策: URL スキーム制限、プライベートアドレス判定、リダイレクト時の事前検査。
  - レスポンスサイズ上限と gzip 解凍後のチェック（メモリ DoS 対策）。
- J-Quants クライアントは 401 処理やリトライにより認証/通信エラーに対する堅牢性を確保。

### Notes / Implementation details
- DuckDB を想定した SQL 実行を多用しており、prices_daily / raw_financials / raw_prices / raw_news 等のテーブル構造に依存します。実行には該当テーブルの存在が前提です。
- Research モジュールは外部ライブラリ（pandas 等）に依存しない設計で、簡潔かつテストしやすい実装になっています。
- jquants_client のレート制御は単純な固定間隔（スロットリング）方式で実装されています。厳密なトークンバケットが必要な場合は将来的な改善対象です。
- news_collector の既知銘柄抽出は単純な正規表現（4桁）と known_codes フィルタに依存します。誤抽出の可能性があるため、必要に応じてルール拡張を検討してください。

### Breaking Changes
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

---

この CHANGELOG はコードベースからの推測に基づいて作成しています。実際の設計ドキュメントやリリースノートと差異がある場合があります。必要であれば個別の機能ごとに詳細な変更履歴や使用例、移行ガイドを作成します。