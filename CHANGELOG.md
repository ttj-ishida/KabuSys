# Changelog

すべての注目すべき変更点を記録します。これは Keep a Changelog の形式に従っています。

注: この CHANGELOG は与えられたコードベースから推測して作成しています。実装の詳細や実行時の挙動は実際のリポジトリやランタイム構成に依存します。

## [0.1.0] - 2026-03-18

初回公開リリース。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンは 0.1.0。
  - __all__ で公開モジュール (data, strategy, execution, monitoring) を定義。

- 環境設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を追加。読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動読み込みを無効化可能。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env パース実装: コメント/export 形式/クォート・エスケープ対応を含む堅牢な行パーサ。
  - Settings クラスを実装しアプリケーション設定をプロパティ経由で提供:
    - jquants_refresh_token (必須)
    - kabu_api_password (必須)
    - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token / slack_channel_id (必須)
    - duckdb_path (デフォルト: data/kabusys.duckdb)
    - sqlite_path (デフォルト: data/monitoring.db)
    - env / log_level 値検証（許容値を限定）
    - is_live / is_paper / is_dev ヘルパー

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限 (120 req/min) を守る固定間隔スロットリング (_RateLimiter) を導入。
  - 再試行（リトライ）ロジックを実装（指数バックオフ、最大試行回数、特定ステータスをリトライ対象）。
  - 401 受信時の ID トークン自動リフレッシュ実装（1 回のみリトライ）。
  - モジュールレベルの ID トークンキャッシュを提供（ページネーション間で共有）。
  - ページネーション対応のデータ取得関数:
    - fetch_daily_quotes
    - fetch_financial_statements
    - fetch_market_calendar
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes（raw_prices テーブル、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials テーブル、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar テーブル、ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ: _to_float, _to_int（不正値に安全に対応）

- ニュース収集 (kabusys.data.news_collector)
  - RSS 収集フロー実装（フェッチ・前処理・idempotent 保存・銘柄紐付け）。
  - セキュリティ対策:
    - defusedxml による XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証、リダイレクト前後でのホストプライベート判定、カスタムリダイレクトハンドラ。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後もサイズ検査（Gzip bomb 対策）。
    - URL の正規化とトラッキングパラメータ削除（utm_* 等）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - テキスト前処理: URL 除去・空白正規化。
  - DB 保存:
    - save_raw_news（チャンク分割、INSERT ... ON CONFLICT DO NOTHING、INSERT ... RETURNING を利用して実際に挿入された id を返却）
    - save_news_symbols / _save_news_symbols_bulk（銘柄紐付けを一括挿入、トランザクションで処理）
  - 銘柄コード抽出ユーティリティ (extract_stock_codes): テキスト中の4桁コード抽出（known_codes に基づくフィルタ、重複除去）。
  - 統合コマンド run_news_collection を提供（複数ソースの収集、各ソースは独立にエラーハンドリング）。

- リサーチ / ファクター (kabusys.research)
  - feature_exploration モジュール:
    - calc_forward_returns: 指定日の終値から将来リターンを複数ホライズンで一括計算（DuckDB の window 関数を使用）。
    - calc_ic: スピアマンランク相関（Information Coefficient）計算。ties 対応、データ不足時 None を返す。
    - factor_summary: ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 平均ランク（同順位は平均ランク）を計算するユーティリティ。
  - factor_research モジュール:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio 等のボラティリティ・流動性指標を計算（true range の扱いに注意）。
    - calc_value: raw_financials と prices_daily を組み合わせて per / roe を計算（最新の target_date <= report_date レコードを取得）。
  - research パッケージの __all__ に主要 API をエクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- スキーマ (kabusys.data.schema)
  - DuckDB 用スキーマ初期化用 DDL を追加（Raw / Processed / Feature / Execution 層の定義方針）。
  - Raw レイヤーのテーブル DDL を含む（raw_prices, raw_financials, raw_news, raw_executions 等の定義を含む）。

### 修正 (Changed)
- 設計上の注意点を README/ドキュメント相当の docstring に明記:
  - Research / Factor モジュールは DuckDB の prices_daily / raw_financials 以外に外部 API を呼ばない設計。
  - データ収集モジュールは取得時刻（fetched_at）を UTC で記録して Look-ahead bias を回避できるようにした。

### セキュリティ (Security)
- news_collector に複数の SSRF / XML / DoS 緩和策を導入（defusedxml, リダイレクト検査、プライベートアドレス拒否、受信サイズ制限、gzip 解凍後検査）。
- jquants_client の API 呼び出しでトークンの扱いを慎重に行い、401 時にトークンを再取得する際の再帰を防止。

### パフォーマンス (Performance)
- DuckDB 向けにウィンドウ関数を利用して複数ホライズンや移動平均を一度のクエリで計算し、SQL の走査コストを低減。
- news_collector / save_raw_news, _save_news_symbols_bulk においてチャンク化と 1 トランザクションでのバルク INSERT を採用してオーバーヘッドを削減。
- J-Quants クライアントに固定間隔スロットリングを導入しレート制限対応を効率的に行う。

### 既知の制約 / 注意点
- 設定値 (Settings) の必須項目が環境変数ベースになっているため、運用時は .env を用意するか適切に環境変数をセットする必要がある（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）。
- duckdb スキーマ定義はスニペットとして含まれているが、運用前に DB 初期化ロジックを呼び出す必要がある。
- research モジュールはいくつか外部ユーティリティ（例: zscore_normalize）を kabusys.data.stats から利用しているが、本 CHANGELOG のスコープで実装の有無は推測に基づく。

---

将来的なリリースでは、機能追加（例えば Execution 層の発注ロジック、monitoring の通知パイプライン、Strategy 実装のテンプレート化）やテスト・ドキュメントの充実、CI/CD の整備などが想定されます。