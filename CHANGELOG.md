# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に従います。  

※ 本 CHANGELOG は与えられたコードベースから推測して作成した初回リリースの要約です。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19

### Added
- パッケージ初期リリース "KabuSys" を追加
  - パッケージ情報: src/kabusys/__init__.py にて version=0.1.0、外部公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理
  - src/kabusys/config.py: 環境変数管理（Settings クラス）を提供。
    - .env/.env.local 自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .env の堅牢なパーサを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ処理、インラインコメント扱い等に対応）。
    - 必須値取得用の _require と Settings プロパティ（J-Quants トークン、kabu API パスワード、Slack トークン・チャネル、DB パス、環境・ログレベル検証など）。
    - env 値検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）と便利なフラグ（is_live 等）。

- Data 層 (DuckDB) 周り
  - src/kabusys/data/schema.py: DuckDB 用スキーマ定義（Raw レイヤー）を追加。
    - raw_prices, raw_financials, raw_news, raw_executions 等の DDL を定義（制約・PRIMARY KEY を含む）。
  - src/kabusys/data/jquants_client.py: J-Quants API クライアントを実装。
    - レートリミッタ（120 req/min 固定間隔スロットリング）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回。408/429/5xx に対してリトライ、429 では Retry-After を優先）。
    - 401 発生時にリフレッシュトークンで自動的に ID トークンを再取得して 1 回だけリトライ。
    - ページネーション対応で fetch_* 系（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）を提供。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。ON CONFLICT DO UPDATE による冪等性を担保。
    - 入出力の型変換ユーティリティ（_to_float, _to_int）を実装し、不正値耐性を確保。
    - fetched_at を UTC ISO 8601 形式で記録し、Look-ahead bias のトレースを可能に。

- ニュース収集機能
  - src/kabusys/data/news_collector.py: RSS ベースのニュース収集・保存モジュールを実装。
    - RSS フェッチ（fetch_rss）: XML パース（defusedxml を使用）・gzip 対応・最大受信サイズ制限（10MB）・Content-Length 事前チェック・レスポンス上限超過検出を実装。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時にスキームとホストの事前検証を行うカスタム RedirectHandler を実装。
      - ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定して拒否。
    - セキュリティ: defusedxml を用いた XML パースと Gzip/Bomb 対策。
    - 記事前処理: URL 除去、空白正規化（preprocess_text）、tracking パラメータ除去（_normalize_url）。
    - 記事 ID: 正規化 URL の SHA-256 の先頭 32 文字で生成し冪等性を確保。
    - DB 保存:
      - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + RETURNING id を用いて実際に挿入された記事 ID を返す。チャンク化と一括トランザクションにより効率化。
      - save_news_symbols / _save_news_symbols_bulk: news_symbols への銘柄紐付けをチャンク INSERT + RETURNING で正確にカウントして保存。
    - 銘柄コード抽出: テキスト中の 4 桁数字を抽出し、与えられた known_codes と照合して重複排除して返す（extract_stock_codes）。
    - 集約ジョブ run_news_collection により複数ソースを順次処理。ソース単位でエラーを隔離し継続。

- リサーチ（特徴量・ファクター計算）
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: DuckDB の prices_daily を参照して複数ホライズンの将来リターンを一度のクエリで取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。NaN/None を排除し、有効レコード数が 3 未満の場合は None を返す。
    - rank: 同順位は平均ランクを割り当てるランク関数（浮動小数の丸め誤差に対処するため round(v,12) を使用）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
  - src/kabusys/research/factor_research.py:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を DuckDB のウィンドウ関数で算出。過去データ不足時は None を返すように設計。
    - calc_volatility: atr_20（20日 ATR の単純平均）/atr_pct/avg_turnover/volume_ratio を計算。true_range の NULL 伝播を適切に制御して cnt による閾値評価を実施。
    - calc_value: raw_financials から target_date 以前の最新財務を取得し、PER（eps が不正な場合は None）と ROE を算出。
  - src/kabusys/research/__init__.py: 上記ユーティリティ関数をエクスポート（zscore_normalize は data.stats からの取り込みを含む）。

### Changed
- （初回リリースのため変更履歴はなし。設計上のポイントとしてドメイン分離・本番 API へのアクセス禁止を明示）
  - Research / Factor モジュールは「prices_daily / raw_financials のみ参照し、本番発注 API へは一切アクセスしない」方針で実装。

### Fixed
- （初回リリース）主要な実装は初版として追加。堅牢性・エッジケース対策が多数実装されている（.env パース、HTTP エラー・再試行、XML/Gzip の脆弱性対策、SSRF 対策、DB トランザクション扱い等）。

### Security
- defusedxml の採用、RSS の受信サイズ制限、Gzip 解凍後サイズチェック、SSRF 向けのホスト/スキーム検証、リダイレクト時の追加検査など複数の安全策を実装。
- J-Quants クライアントは 401 処理でトークンリフレッシュを安全に行い、無限再帰を防止するフラグを導入。

### Notes
- DuckDB スキーマ定義は Raw レイヤーの DDL を含む。Processing / Feature / Execution レイヤーは設計に応じて拡張想定。
- J-Quants API のレート制御や retry 設定（120 req/min, max 3 retries, backoff base 2.0）はソース内定数として定義されているため運用時に調整可能。
- news_collector の既定 RSS ソースは Yahoo Finance のビジネスカテゴリを想定。ソースは引数で差し替え可能。

このリリースはコードベースからの推測に基づく CHANGELOG です。実運用上の変更点・公開日・互換性情報等はリポジトリ管理者にて追記してください。