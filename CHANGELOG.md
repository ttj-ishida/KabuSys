# Changelog

すべての変更は Keep a Changelog の仕様に従って記載しています。  
重大な変更（API 互換性の破壊など）は明記します。

現在のリリース: 0.1.0

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-18
初期リリース。日本株自動売買システムのコア機能群（データ収集・スキーマ・リサーチ・設定管理・ニュース収集・J-Quants クライアント）を追加しました。

### Added
- パッケージ基盤
  - パッケージ初期化（kabusys/__init__.py）とバージョン情報（0.1.0）を追加。
  - サブパッケージ公開: data, strategy, execution, monitoring。

- 環境設定管理（kabusys.config）
  - .env ファイルと環境変数から設定を自動読み込みする機能を追加。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を検索。
    - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの強化:
    - export KEY=val 形式、シングル/ダブルクォート（バックスラッシュエスケープ対応）、行末コメント取り扱いをサポート。
  - Settings クラスを提供し、必須キー取得（_require）、型変換・検証を行うプロパティを追加。
    - J-Quants / kabuAPI / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの検証を実装。
    - is_live/is_paper/is_dev ヘルパーを追加。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - レート制限管理: 固定間隔スロットリング（120 req/min）を _RateLimiter で実装。
    - リトライ: 指数バックオフ + 最大リトライ回数（3回）、ステータス 408/429/5xx をリトライ対象に設定。
    - 401 応答時の自動トークンリフレッシュ（1回まで）とモジュールレベルの ID トークンキャッシュを実装。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB へ冪等保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）。
      - INSERT ... ON CONFLICT DO UPDATE による上書き（冪等化）。
    - データ型変換ユーティリティ _to_float / _to_int（変換ポリシーの明確化: 空値や不正値は None、"1.0" のような float 文字列は int に変換可能だが小数部がある場合は None）。
    - API 呼び出しにおける JSON デコードエラーハンドリング、Retry-After ヘッダの優先使用などを実装。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集および raw_news/news_symbols への保存機能を実装。
    - RSS フィード取得: fetch_rss（gzip 対応、最大応答サイズ制限、XML パース保護）。
    - DefusedXML を使った安全な XML パース（XML Bomb 等の対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト時のスキーム・ホスト検証を行うカスタム RedirectHandler を導入。
      - ホストがプライベート/ループバック/リンクローカルでないことを検査（DNS 解析および IP 判定）。
    - レスポンスサイズ保護: MAX_RESPONSE_BYTES（10 MB）を超える応答を拒否。
    - URL 正規化とトラッキングパラメータ除去（utm_* 等）、SHA-256 による記事 ID 生成（先頭32文字）で冪等性を担保。
    - テキスト前処理: URL 除去、空白正規化。
    - DB 保存:
      - save_raw_news: チャンク分割して INSERT ... ON CONFLICT DO NOTHING RETURNING id により新規挿入IDを取得、1トランザクションでコミット。
      - save_news_symbols / _save_news_symbols_bulk: 一括挿入（チャンク）と RETURNING による実挿入数取得、トランザクション処理、重複除去。
    - 銘柄抽出: 正規表現による 4 桁銘柄コード抽出（extract_stock_codes）と既知コードフィルタリング。
    - デフォルト RSS ソースとして Yahoo Finance のカテゴリー RSS を登録。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - モメンタム: calc_momentum（mom_1m/mom_3m/mom_6m、ma200_dev）。
    - ボラティリティ/流動性: calc_volatility（atr_20、atr_pct、avg_turnover、volume_ratio）。
    - バリュー: calc_value（per、roe。raw_financials の最新レコードを使用）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルを参照し、(date, code) 単位で結果を返す。
    - スキャン範囲のバッファや欠損データ時の None 返却ポリシーを実装。
  - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）:
    - 前方リターン計算: calc_forward_returns（複数ホライズン、営業日上の LEAD を使用）。
    - IC（Information Coefficient）計算: calc_ic（スピアマンランク相関、ties の平均ランク処理を実装）。
    - ランク関数: rank（同順位は平均ランク、丸めによる ties 検出漏れ対策）。
    - カラム統計サマリー: factor_summary（count/mean/std/min/max/median、None 除外）。
    - 設計上、外部ライブラリに依存せず標準ライブラリのみで実装（pandas など未使用）。
  - パッケージレベルでのエクスポートを追加（calc_momentum 他、zscore_normalize を data.stats からインポートして公開）。

- DuckDB スキーマ（kabusys.data.schema）
  - DuckDB 用 DDL と初期化用文字列を追加。
  - Raw Layer（raw_prices, raw_financials, raw_news, raw_executions ...）を含むテーブル定義を追加（主キー・チェック制約を含む）。
  - Data/Processed/Feature/Execution の 3 層（ドキュメントに基づく設計）を想定したスキーマ設計。

### Changed
- （初期リリースのためマイナーな内部仕様・設計決定を反映）
  - データ取得・保存処理は冪等化を優先。既存の行は ON CONFLICT により更新されるように設計。

### Fixed
- N/A（初期リリース）

### Security
- ニュース収集における SSRF 対策、defusedxml による XML パース保護、応答サイズ制限により外部入力の悪用を低減。
- J-Quants クライアントでトークン取り扱いと自動リフレッシュ時の無限再帰防止を実装。

### Notes / Limitations
- Research モジュールは標準ライブラリで完結する実装を優先しており、大規模データ処理や高速化のために pandas 等の外部ライブラリの導入を今後検討する余地があります。
- calc_forward_returns / calc_momentum 等は営業日を「連続レコード」で扱う前提のため、prices_daily テーブルの欠損や市場非開場日に注意が必要です。
- J-Quants API のレート制限やリトライポリシーは現状の定数に基づく運用を想定しています。運用状況に応じて調整してください。

---

配布・デプロイ時には .env.example を元に必須環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）を設定してください。