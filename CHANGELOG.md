# Changelog

すべての注目すべき変更はこのファイルに記録します。  
※この CHANGELOG は提供されたコードベースの内容から推測して作成しています（コミット履歴ではありません）。

格式: Keep a Changelog 準拠

## [Unreleased]

（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-20

### Added
- パッケージ初回リリース（kabusys 0.1.0 相当）。
- 基本パッケージ構成を追加:
  - kabusys.config: .env / 環境変数の自動ロード（.env, .env.local）と厳格なパースロジックを実装。export プレフィックス、クォート文字列、インラインコメント等に対応。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを追加し、J-Quants / kabu API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等の設定をプロパティ経由で取得。未設定時の必須チェック（ValueError 発生）や値検証を含む。
- データ取得・保存モジュール（kabusys.data）:
  - jquants_client: J-Quants API クライアントを実装。固定間隔のレート制限（120 req/min）を守る RateLimiter、指数バックオフによるリトライ（最大3回）、401 時のリフレッシュトークン自動更新、ページネーション対応、取得日時（UTC, fetched_at）の記録を実装。
  - jquants_client: API から取得したデータを DuckDB に冪等に保存する save_* 関数（raw_prices, raw_financials, market_calendar）を実装（ON CONFLICT / DO UPDATE を使用）。
  - news_collector: RSS フィードから記事を収集して raw_news に保存するモジュールを実装。URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）、受信サイズ制限、XML の安全パース（defusedxml）、SSRF/不正 URL の抑止、バルク挿入のチャンク処理などを備える。
- リサーチ機能（kabusys.research）:
  - factor_research: prices_daily / raw_financials を参照してファクターを計算（momentum, volatility, value）。各ファクターは日付・銘柄単位の dict リストで返却。
  - feature_exploration: 将来リターン計算（複数ホライズン対応）、IC（Spearman ρ）計算、ランク付けユーティリティ、ファクターの統計サマリーを実装。外部ライブラリを使わず標準ライブラリのみで実装。
  - research パッケージの公開 API を整理（calc_momentum, calc_volatility, calc_value, zscore_normalize 等）。
- 戦略層（kabusys.strategy）:
  - feature_engineering.build_features: research で算出した生のファクターをマージ、ユニバースフィルタ（最低株価・平均売買代金）適用、指定列の Z スコア正規化、±3 クリップ、DuckDB の features テーブルへ日単位で置換（トランザクションで原子性保証）。
  - signal_generator.generate_signals: features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）から final_score を算出。Bear レジームの判定、BUY（閾値 0.60 デフォルト）・SELL（ストップロス・スコア低下）判定、signals テーブルへの日単位置換を実装。重みの入力検証・スケーリング、AI スコアの中立補完などを備える。
- DuckDB を前提とした SQL / Python 混在の実装により、データ集計・ウィンドウ関数を活用した効率的な計算を実装。
- パッケージメタ情報: __version__ を 0.1.0 に設定。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- news_collector にて defusedxml を使用し XML 関連の脆弱性（XML bomb 等）を軽減。
- news_collector で受信サイズの上限（10 MB）を導入し、メモリ DoS を軽減。
- news_collector の URL 正規化とトラッキングパラメータ除去により偽装や過剰な識別子の混入を抑制。
- jquants_client の HTTP エラー処理で 401 時のトークンリフレッシュとリトライ戦略を明確化。429 の Retry-After を尊重。

### Notes / Known limitations
- signal_generator のエグジットロジックでは、コード中に「未実装」と明記された条件（トレーリングストップ、時間決済など）が存在する（positions テーブルに peak_price / entry_date が必要）。今後の拡張項目。
- research/feature_exploration は外部依存を避ける設計だが、パフォーマンスや使い勝手向上のため pandas 等の導入検討余地がある。
- execution パッケージはプレースホルダ（直接の発注 API 依存なし）で、実際の注文送信ロジックは別実装が想定される。
- settings.env / log_level の値検証は厳密に行うため、不正な値で例外が発生する（利用側での環境設定に注意）。

---

以上。必要であれば各モジュールごとの詳細な変更点（関数一覧、引数仕様、返り値形式、SQL スキーマ推定など）をさらに展開してまとめます。どの形式・粒度で出力するか指示してください。