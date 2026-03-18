# Changelog

全ての変更は Keep a Changelog の仕様に準拠しています。  
一覧は重要な変更点をカテゴリ（Added / Changed / Fixed / Security）ごとにまとめています。

最新リリース
------------

Unreleased
: 特になし（次のリリースに向けた準備中）

0.1.0 - 2026-03-18
-----------------

Initial release

Added
- パッケージ初期化
  - kabusys パッケージを追加。バージョンは 0.1.0 に設定。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート検出機能を実装（.git または pyproject.toml を探索）。これによりカレントワーキングディレクトリに依存せず自動ロードが動作。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用）。
  - .env パーサを独自実装（export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープ対応）。
  - Settings クラスを提供し、J-Quants リフレッシュトークン、kabuAPI パスワード、Slack トークン/チャンネル、DB パス等のプロパティを型安全に取得。
  - KABUSYS_ENV の検証（development/paper_trading/live）、LOG_LEVEL の検証（DEBUG/INFO/...）を実装。
  - duckdb/sqlite のデフォルトパス設定（expanduser 対応）。

- Data レイヤー: J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API から日次株価・財務データ・マーケットカレンダーを取得するクライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）を実装。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx を再試行対象とする。
  - 401 応答時は id_token を自動リフレッシュして 1 回リトライする仕組みを実装（無限再帰防止）。
  - ページネーション対応のフェッチ関数（fetch_daily_quotes, fetch_financial_statements）。
  - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等性を確保。
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias のトレースを可能に。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、不正値を安全に処理。

- Data レイヤー: ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集パイプラインを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃を防御。
  - SSRF 対策を複数実装:
    - URL スキーム検証（http/https のみ許可）
    - リダイレクト時にスキームとホスト検査を行うカスタム RedirectHandler（_SSRFBlockRedirectHandler）
    - ホストがプライベート/ループバック/リンクローカルかを検査する関数（_is_private_host）。DNS 解決の結果もチェック。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES）と gzip 解凍後のサイズチェックによりメモリ DoS を緩和。
  - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保（utm_* 等のトラッキングパラメータを削除する正規化実装）。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - 銘柄コード抽出（4桁数字）と既知銘柄セットによるフィルタリング機能を実装。
  - DuckDB への一括挿入はチャンク化してトランザクションで実行、INSERT ... RETURNING を用いて実際に挿入された件数を返す。

- Research レイヤー（kabusys.research）
  - feature_exploration モジュール:
    - calc_forward_returns: ある基準日から各ホライズン（デフォルト: 1,5,21 営業日）までの将来リターンを DuckDB の prices_daily テーブルから計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank, factor_summary ユーティリティ（ランクの平均同順位対応、基本統計量計算）。
    - 実装は標準ライブラリのみを原則としている（pandas 等に依存しない）。
  - factor_research モジュール:
    - calc_momentum: mom_1m/mom_3m/mom_6m、および 200 日移動平均乖離率（ma200_dev）を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）・相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播管理を実装。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得して PER / ROE を計算（EPS 欠損/0 は PER を None）。
    - 各関数は prices_daily / raw_financials のみを参照し、本番発注 API 等にはアクセスしないことを設計方針としている。

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw Layer 用テーブル DDL を実装（raw_prices, raw_financials, raw_news, raw_executions 等の定義）。
  - スキーマ定義を整理し初期化に利用できるようにした（DataSchema.md 準拠）。

- その他
  - モジュール単位でのロギング（各モジュールに logger を配置）を行いデバッグ・運用がしやすい設計。
  - research パッケージの __all__ に主要な関数をエクスポート。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Security
- RSS パーサに defusedxml を使用して XML パース攻撃に対処。
- HTTP リダイレクト検査・プライベートアドレス検知・スキーム検証により SSRF リスクを低減。
- 外部入力（.env）の読み込み時にエラーハンドリングと保護キー(protected)による既存 OS 環境変数の上書き制御を実装。

Notes / Known limitations
- research 内の処理は性能上 DuckDB を前提としており、大量データを扱う際はクエリ最適化が必要になる可能性がある。
- NewsCollector の URL 正規化 / トラッキング除去は既知のプレフィックスに基づく簡易的な実装で、すべてのトラッキングパラメータを網羅するわけではない。
- 一部モジュール（execution, strategy）の __init__.py は空であり、将来的に機能拡張を想定。

問い合わせ / 貢献
- バグ報告や小さな改善は issue を送ってください。重大な修正やセキュリティ問題はプライベートに連絡してください。

以上。