# CHANGELOG

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-20

### 追加
- 初回リリース。KabuSys 日本株自動売買フレームワークの基本機能を実装。
- パッケージ構成
  - kabusys パッケージを公開（サブパッケージ: data, strategy, execution, monitoring）。
  - strategy パブリック API: build_features, generate_signals をエクスポート。
- 環境設定 (kabusys.config)
  - .env / .env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env パーサーは export プレフィックス、クォート、インラインコメント、エスケープ等に対応。
  - Settings クラスによる型安全なアクセス（必須環境変数チェックと値検証）。
  - 既定の環境変数:
    - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - オプション: KABUSYS_ENV (development|paper_trading|live, default=development)、LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL)
    - DB パスのデフォルト: DUCKDB_PATH=data/kabusys.duckdb, SQLITE_PATH=data/monitoring.db
- Data モジュール
  - J-Quants クライアント (kabusys.data.jquants_client)
    - レート制限対応（120 req/min 固定間隔スロットリング）。
    - リトライ（最大 3 回、指数バックオフ）、408/429/5xx を対象。
    - 401 受信時はリフレッシュ→1回再試行するトークン自動更新ロジック。
    - ページネーション対応（pagination_key を利用）。
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等（ON CONFLICT DO UPDATE）。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - 入力パースユーティリティ: _to_float, _to_int。
  - ニュース収集 (kabusys.data.news_collector)
    - RSS からの記事取得と raw_news への冪等保存。
    - URL 正規化（トラッキングパラメータ除去、ソート、スキーム/ホスト小文字化、フラグメント削除）。
    - セキュリティ対策: defusedxml を用いた XML パース、受信バイト数制限（10 MB）、HTTP/HTTPS スキーム検証（SSRF 対策）。
    - 挿入バルクのチャンク化、記事ID を URL 正規化後の SHA-256 ハッシュで生成して冪等性を確保。
- Research モジュール
  - factor_research: calc_momentum, calc_volatility, calc_value を実装（DuckDB の prices_daily / raw_financials を参照）。
    - モメンタム: 1M/3M/6M リターン、200 日移動平均乖離率（データ不足時は None）。
    - ボラティリティ/流動性: 20 日 ATR、atr_pct、avg_turnover、volume_ratio。
    - バリュー: PER / ROE（財務データは target_date 以前の最新レコードを使用）。
  - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman の ρ）、factor_summary（統計サマリー）、rank（同順位は平均ランク）。
  - 研究 API は外部ライブラリに依存しない（標準ライブラリ + DuckDB）。
- Strategy
  - feature_engineering.build_features
    - research の生ファクターを取得し、ユニバースフィルタ（最低株価 300 円・20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を使用）、±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT。失敗時は ROLLBACK）。
  - signal_generator.generate_signals
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - 最終スコア final_score = 重み付き合算（デフォルト重みを定義。ユーザ指定はバリデーション・再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数 >= 3）。
    - BUY（閾値デフォルト 0.60）および SELL（ストップロス -8% / スコア低下）シグナルを生成。
    - SELL 優先ポリシー（SELL 銘柄は BUY から除外）、signals テーブルへ日付単位で置換（トランザクション）。
- ロギングとエラーハンドリングの基本実装（各モジュールで logger を使用し警告・情報を出力）。

### セキュリティ
- ニュースパーサ: defusedxml を採用して XML 関連の脆弱性（XML Bomb など）に対処。
- ニュース URL 正規化・スキーム検証により SSRF やトラッキングパラメータの影響を軽減。
- J-Quants クライアントでレスポンス JSON のデコード失敗時に明示的なエラーを投げる。

### 既知の制限 / 注意点
- positions テーブルに peak_price / entry_date 等が存在しないため、トレーリングストップや時間決済（保有 60 営業日超）などは未実装（コード内に未実装コメントあり）。
- generate_signals:
  - AI ニューススコアが欠損した場合は中立（0.5）で補完。
  - ユーザ指定の weights は既知キーのみ受け付け、無効値は無視して再スケールされる。
- feature_engineering は zscore_normalize を利用する前提（kabusys.data.stats に依存）。
- DB スキーマ（テーブル名・カラム）は本実装が想定する形になっているため、運用前にスキーマの準備が必要:
  - 例: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news など。
- RSS デフォルトソースは yahoo_finance のビジネスカテゴリのみ。追加ソースは DEFAULT_RSS_SOURCES を拡張可能。
- J-Quants API のレート制限およびリトライのポリシーは固定（120 req/min, 最大 3 回）。運用環境に応じた調整は将来的に必要となる場合あり。

### マイグレーション / 利用上の注意
- 必須の環境変数（JQUANTS_REFRESH_TOKEN 等）を設定してください。設定がない場合は Settings プロパティが ValueError を送出します。
- 開発/本番の切り替えは KABUSYS_ENV を設定（development / paper_trading / live）。
- 自動 .env ロードが不要なテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。

### 破壊的変更
- なし（初回リリース）

--- 

今後の予定（例）
- トレーリングストップ・時間決済などのエグジット戦略追加。
- ニュース収集のソース拡充・自然言語処理を用いたスコアリング強化。
- execution（発注）層の実装（kabuステーション連携）とモニタリング機能の充実。