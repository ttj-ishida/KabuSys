# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
現在のバージョン: 0.1.0（初回リリース）

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-18
初回リリース。日本株のデータ収集・特徴量計算・研究支援・環境設定を目的とした基礎ライブラリを実装。

### 追加
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - サブパッケージ公開: data, strategy, execution, monitoring。

- 設定・環境読み込み (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース実装（コメント・export プレフィックス・クォートとエスケープ対応、インラインコメント処理など）。
  - 設定アクセス用 Settings クラスを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH などのデフォルト値。
    - KABUSYS_ENV（development / paper_trading / live の検証）と LOG_LEVEL の検証ユーティリティ。
    - is_live / is_paper / is_dev のブールプロパティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ（_request）: JSON デコード、タイムアウト、ページネーション対応。
  - レート制限（固定間隔スロットリング）: _RateLimiter（120 req/min 想定）。
  - リトライ戦略: 指数バックオフ、最大リトライ回数 3（408/429/5xx を対象）、429 の場合は Retry-After 利用。
  - 401 レスポンス時にリフレッシュトークンで自動 id_token 更新を試行（1 回のみ）。
  - トークンキャッシュ（モジュールレベル）でページネーション間でトークンを共有。
  - データ取得関数:
    - fetch_daily_quotes（ページネーション対応、daily_quotes を取得）
    - fetch_financial_statements（statements を取得）
    - fetch_market_calendar（trading_calendar を取得）
  - DuckDB 保存関数（冪等性: ON CONFLICT DO UPDATE）:
    - save_daily_quotes -> raw_prices に保存
    - save_financial_statements -> raw_financials に保存
    - save_market_calendar -> market_calendar に保存
  - ユーティリティ: 型変換ヘルパー _to_float / _to_int（不正値を None に落とす等）。
  - Look-ahead bias 対策として fetched_at を UTC で記録。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード取得（fetch_rss）:
    - defusedxml による安全な XML パースを採用。
    - HTTP(S) スキーム検証、SSRF 対策（リダイレクト先のスキーム/ホストチェック）を実装。
    - プライベート IP / ループバック / リンクローカルの検出（_is_private_host）により内部アドレスへのアクセスを拒否。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェック、gzip 解凍後のサイズ検証（Gzip bomb 対策）。
    - トラッキングパラメータ除去を含む URL 正規化、記事 ID は正規化 URL の SHA-256（先頭32文字）を使用して冪等性を確保。
    - content:encoded を優先して本文を取得、テキスト前処理（URL 除去、空白正規化）。
    - デフォルト RSS ソース（例: Yahoo Finance のカテゴリ RSS）を用意。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING をチャンク挿入し、実際に挿入された記事IDを返す（INSERT ... RETURNING を利用）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを冪等に保存、チャンク・トランザクションで効率化。
  - 銘柄コード抽出: テキストから 4 桁数字（日本株）を抽出し、既知コード集合でフィルタ（extract_stock_codes）。
  - 高レベルジョブ run_news_collection を提供（各ソース独立にエラーハンドリング、既知銘柄での紐付け処理を実行）。

- DuckDB スキーマ定義 (src/kabusys/data/schema.py)
  - Raw Layer のテーブル DDL を定義:
    - raw_prices（date, code, open/high/low/close/volume/turnover, fetched_at、PK(date, code)）
    - raw_financials（code, report_date, period_type, eps, roe 等、PK(code, report_date, period_type)）
    - raw_news（id, datetime, source, title, content, url, fetched_at、PK(id)）
    - raw_executions（発注/約定関連の生データ用テーブル定義の一部を含む）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）の設計方針に準拠。

- 研究（Research）モジュール (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns: DuckDB の prices_daily を参照して複数ホライズン（デフォルト 1,5,21 日）で将来リターンを一括取得。営業日とカレンダー日バッファを考慮したスキャン範囲。
    - calc_ic: Spearman（ランク相関）による IC 計算（rank 関数を使用、同順位は平均ランク）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を標準ライブラリのみで計算。
    - rank: 同順位を平均ランクとするランク付けの実装（丸め誤差対策で round(..., 12) を使用）。
  - factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日移動平均乖離率）を DuckDB 上で計算。データ不足時は None を返す。
    - calc_volatility: atr_20（20 日 ATR）/atr_pct/avg_turnover/volume_ratio を計算。true_range の NULL 伝播を制御して精度を担保。
    - calc_value: raw_financials の最新財務データ（target_date 以前）と prices_daily を結合して per / roe を計算。ROW_NUMBER による最新レコード選択。
  - 設計方針:
    - DuckDB 接続を受け取り prices_daily/raw_financials のみ参照、外部 API にはアクセスしない。
    - pandas 等に依存せず標準ライブラリ + DuckDB SQL で実装。
    - 結果は (date, code) をキーとする dict のリストで返却。

### 改善（設計上の注目点）
- セキュリティ
  - XML パースに defusedxml を利用、SSRF 対策、URL スキーム検証、プライベートホスト拒否、レスポンスサイズ制限など、外部データ取り込み時の安全性に注力。
- 冪等性 / データ整合性
  - DuckDB への挿入は ON CONFLICT を用いることで冪等性を確保。
  - news の記事ID生成・INSERT RETURNING により重複を正確に扱える設計。
- 運用性
  - API クライアントにレートリミッタ・リトライ・自動トークンリフレッシュを備え、安定したデータ取り込みを目指す。
  - 設定周りは明示的な必須チェックと値の検証（KABUSYS_ENV, LOG_LEVEL）を実装。

### 既知の制限
- Research モジュールは標準ライブラリと DuckDB のみで実装されており、pandas 等の高速データ処理ライブラリは利用していない（将来的な拡張余地あり）。
- 一部テーブル定義（raw_executions 等）の実装はスニペットの範囲で継続実装が必要な箇所が存在する。

---

（注）この CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノートは運用上の詳細（既知のバグ、マイグレーション手順、互換性ポリシーなど）を追記してください。