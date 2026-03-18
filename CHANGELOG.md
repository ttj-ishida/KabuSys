# Changelog

すべての重要な変更はこのファイルに記録します。  
形式は Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回公開リリース。

### Added
- パッケージおよび公開 API
  - パッケージルートを定義（kabusys v0.1.0）。__all__ で主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 設定/環境変数管理（kabusys.config）
  - .env ファイル自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml で検出）。
  - 読み込み順序: OS 環境 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーが export 形式、クォート、インラインコメント、バックスラッシュエスケープをサポート。
  - Settings クラスで各種必須/任意設定をプロパティとして提供（J-Quants トークン、kabu API、Slack、DB パス、環境名、ログレベル等）。入力値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を実装。
- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足・財務・マーケットカレンダー等の取得関数を実装（ページネーション対応）：fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
  - レート制御（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
  - リトライ／指数バックオフロジック（最大リトライ 3 回、408/429/5xx 対象）。429 の場合は Retry-After を尊重。
  - 401 Unauthorized を検出した場合の ID トークン自動リフレッシュ（1 回のみリトライ）を実装。
  - DuckDB への保存用ユーティリティ（冪等）：save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT を使用した upsert）。
  - 入力値を安全に変換するユーティリティ _to_float / _to_int 実装。
  - ページネーション時にトークンをモジュールキャッシュで共有する実装。
- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからニュースを収集し DuckDB に保存する一連の機能を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成し、冪等性を確保。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント除去）。
  - RSS パースで defusedxml を使用し XML 攻撃対策。
  - SSRF 対策:
    - URL スキーム検証（http/https のみ許可）。
    - リダイレクト時にスキーム・ホスト検証を行うカスタムハンドラ（_SSRFBlockRedirectHandler）。
    - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定してアクセスを拒否。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - コンテンツ前処理（URL 除去、空白正規化）、タイトル/本文から銘柄コード（4桁）を抽出する機能（extract_stock_codes）。
  - raw_news / news_symbols へのバルク挿入をチャンク化して実行、INSERT ... RETURNING を用いて実際に挿入された件数を正確に返す。
  - デフォルト RSS ソースとして Yahoo Finance を設定。
- Research / ファクター計算（kabusys.research）
  - 特徴量探索・ファクター計算モジュールを実装（feature_exploration, factor_research）。
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21 営業日）分の将来リターンを一度のクエリで計算。
    - calc_ic: Spearman（ランク相関）ベースの IC 計算を実装（欠損や ties を考慮）。
    - rank: 同順位は平均ランクを返すランク関数（丸めにより ties 検出漏れを防止）。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。
  - factor_research:
    - calc_momentum: mom_1m/3m/6m と 200日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: ATR(20), 相対ATR(atr_pct), 20日平均売買代金(avg_turnover)、出来高比(volume_ratio) を計算。true_range の NULL 伝播を慎重に扱う。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新の target_date 以前の財務データを採用）。
  - 設計方針として、DuckDB の prices_daily / raw_financials テーブルのみを参照し外部 API に依存しないことを明示。
  - research パッケージの __all__ を整備して主要関数を再公開。
- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw レイヤーの DDL 定義を追加（raw_prices, raw_financials, raw_news, raw_executions のスケルトン定義含む）。
  - スキーマ定義のドキュメントコメントを追加（Raw/Processed/Feature/Execution レイヤーの役割説明）。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- ニュース収集での SSRF 対策、defusedxml による XML 攻撃対策、レスポンスサイズ制限（DoS緩和）を導入。
- J-Quants クライアントでのトークン自動リフレッシュの実装により、認証エラー処理を安全に実行。

### Notes / Design decisions
- research モジュールは外部 API にアクセスしないことを明確化し、Look-ahead Bias の防止と本番口座への影響分離を意図。
- DuckDB への保存は基本的に冪等（ON CONFLICT）を採用してデータ重複を防止。
- .env 読み込みはプロジェクトルートを基準に行うため、CWD に依存しない設計。
- 大量データ挿入時の SQL パラメータ上限や性能に配慮してチャンク処理を導入している箇所がある（news_collector のバルク挿入など）。

もし特定の変更点やリリースノートの粒度（より詳細なモジュール別の項目分割や既知の制限事項の追記）を希望される場合はお知らせください。