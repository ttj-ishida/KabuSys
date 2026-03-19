# Changelog

すべての変更は Keep a Changelog の形式に従います。  
現在のパッケージバージョン: 0.1.0

※内容は提供されたコードベースから推測して記載しています（実装上の意図・設計方針を含む）。

## [Unreleased]
- （今後のリリースに向けたメモ）
  - Strategy / Execution パッケージの実装拡張（現在は __init__.py のみ）
  - テストカバレッジの拡充（ユニットテスト・統合テスト）
  - ドキュメント整備（API 仕様、データスキーマの詳細、運用手順）

## [0.1.0] - 2026-03-19

### Added
- 基本パッケージの骨組みを追加
  - パッケージ: kabusys (version 0.1.0)
  - サブパッケージ: data, strategy, execution, monitoring を __all__ に公開（strategy / execution は空の初期化ファイル）

- 環境変数 / 設定管理（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を追加
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサ実装: export プレフィックス対応、クォート処理、インラインコメント処理、エラーハンドリング
  - Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス / システム設定）
  - env 値 (development/paper_trading/live) と LOG_LEVEL のバリデーションを実装

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API リクエストユーティリティ実装（_request）
    - レート制限（120 req/min）を守る固定間隔 RateLimiter 実装
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx）
    - 401 受信時はリフレッシュトークンで自動トークン更新して 1 回リトライ
    - ページネーション対応（pagination_key）
    - JSON デコードエラーハンドリング
  - トークン管理: get_id_token / モジュールレベルの ID トークンキャッシュ
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB 保存関数（冪等操作を実装）:
    - save_daily_quotes → raw_prices に ON CONFLICT DO UPDATE
    - save_financial_statements → raw_financials に ON CONFLICT DO UPDATE
    - save_market_calendar → market_calendar に ON CONFLICT DO UPDATE
  - ユーティリティ: _to_float / _to_int（堅牢な型変換、空値・不正値を None 扱い）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード取得と前処理パイプラインを実装
    - フィード取得(fetch_rss)、XML パース、安全対策、gzip 対応、レスポンスサイズ上限チェック
    - defusedxml を利用して XML 関連攻撃に対処
    - 最大受信サイズ上限: 10 MB（MAX_RESPONSE_BYTES）
    - URL 正規化: 小文字化、トラッキングパラメータ除去（utm_ 等）、クエリソート、フラグメント除去
    - 記事 ID は正規化 URL の SHA-256 先頭 32 文字で生成（冪等性確保）
    - テキスト前処理: URL 除去、空白正規化
  - SSRF 対策:
    - _validate_url_scheme（http/https のみ許可）
    - _is_private_host（IP/ホスト名のプライベートアドレス判定）
    - _SSRFBlockRedirectHandler によるリダイレクト先検査
    - 初回 URL と最終 URL 両方でプライベートアドレスチェック
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING + INSERT ... RETURNING id を使い、実際に挿入された記事 ID を返す。チャンク挿入・トランザクション管理あり。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols に対してチャンク INSERT + ON CONFLICT DO NOTHING + RETURNING を用いて正確な挿入数を算出
  - 銘柄抽出:
    - extract_stock_codes: 正規表現で 4 桁コードを抽出し known_codes でフィルタ（重複除去）

- DuckDB スキーマ初期化（kabusys.data.schema）
  - Raw Layer の DDL を追加（raw_prices, raw_financials, raw_news, raw_executions の雛形）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature / Execution）の設計を反映する枠組み

- 研究モジュール（kabusys.research）
  - feature_exploration.py:
    - calc_forward_returns（指定日から各ホライズンの将来リターンを一括で取得）
    - calc_ic（ファクターと将来リターンの Spearman ランク相関を計算、ties を扱う）
    - rank（同順位は平均ランク、丸めで ties 検出を安定化）
    - factor_summary（count/mean/std/min/max/median を計算、None を除外）
    - 設計方針: DuckDB の prices_daily のみ参照、外部 API にアクセスしない、標準ライブラリのみで実装
  - factor_research.py:
    - calc_momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
    - calc_volatility（atr_20 / atr_pct / avg_turnover / volume_ratio）
    - calc_value（per / roe を raw_financials と prices_daily 組合せで算出）
    - 各関数でデータ不足時は None を返す設計、ウィンドウチェック・カウントによる安全処理
  - kabusys.research パッケージの __all__ に主要関数をエクスポート

### Security
- ニュース収集でのセキュリティ強化
  - defusedxml を利用して XML 攻撃を防止
  - SSRF を防ぐためのスキームチェックとプライベートホスト検査（DNS 解決による A/AAAA 検査含む）
  - レスポンスサイズ上限チェック（gzip 解凍後も検査）
  - URL のトラッキングパラメータ削除により ID の安定化（冪等性向上）

- J-Quants クライアントでの堅牢性
  - レートリミット厳守（_RateLimiter）
  - リトライと指数バックオフ、Retry-After ヘッダ優先処理（429 時）
  - 401 でのトークン自動リフレッシュ（無限再帰対策）

### Fixed
- データ保存時の冪等性を確保（raw_prices / raw_financials / market_calendar: ON CONFLICT DO UPDATE）
- save_daily_quotes / save_financial_statements / save_market_calendar で PK 欠損行をスキップして警告ログを出力するように改善
- save_raw_news / save_news_symbols でトランザクション・チャンク処理と例外時のロールバックを実装

### Changed
- なし（初期リリース）

### Removed
- なし（初期リリース）

### Known limitations / Notes
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリのみで実装されているため、大規模データや高度な統計処理ではパフォーマンス上の制約がある可能性がある
- schema.py に raw_executions の DDL が途中まで含まれているが、Execution レイヤーの完全な定義/実装は未完
- Strategy / Execution の実際の注文ロジックや kabuAPI 統合は未実装（kabu_api 関連設定は存在）
- J-Quants の API レスポンススキーマの変更や外部サービスの障害に対しては追加の監視/ハンドリングが必要

---

（以上）