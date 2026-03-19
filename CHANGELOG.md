Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
リリースはセマンティックバージョニングに従います。

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-03-19
-------------------

Added
- パッケージ初回リリース。
- 基本パッケージ構成とエントリポイント
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポートモジュール: data, strategy, execution, monitoring

- 環境設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）と OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの探索を .git または pyproject.toml を基準に行い、CWD に依存しない自動ロードを実現。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント対応）。
  - 必須環境変数チェックを提供（ValueError を送出）。
  - 主要設定プロパティ:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（_RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回）。リトライ対象ステータス: 408, 429, 5xx。
  - 401 Unauthorized の場合は ID トークンを自動リフレッシュして 1 回だけ再試行。
  - ページネーション間で使えるモジュールレベルの ID トークンキャッシュ。
  - fetch_* 系関数:
    - fetch_daily_quotes: 日足取得（ページネーション）
    - fetch_financial_statements: 財務データ取得（ページネーション）
    - fetch_market_calendar: 市場カレンダー取得
  - DuckDB への保存関数は冪等（ON CONFLICT DO UPDATE / DO NOTHING）:
    - save_daily_quotes → raw_prices テーブル
    - save_financial_statements → raw_financials テーブル
    - save_market_calendar → market_calendar テーブル
  - 型変換ユーティリティ (_to_float / _to_int) を用意（異常値は None）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集機能。
  - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
  - defusedxml を用いた XML パーシングで XML Bomb 等の攻撃を防止。
  - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10 MiB）でメモリ DoS を軽減。
  - URL 正規化: スキーム/ホストの正規化、トラッキングパラメータ除去（utm_*, fbclid 等）、フラグメント削除、クエリソート。
  - DB へのバルク挿入はチャンク化して実施（_INSERT_CHUNK_SIZE）。
  - デフォルト RSS ソースに Yahoo Finance を追加。

- 研究・ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離率（ma200_dev）を計算。
    - calc_volatility: 20日 ATR, atr_pct, 20日平均売買代金, volume_ratio を計算。
    - calc_value: per, roe を raw_financials と prices_daily から計算。
    - 計算は DuckDB 上の SQL ウィンドウ関数中心で実装（外部 API を使用しない）。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: Spearman ランク相関（IC）を計算する実装。
    - factor_summary: count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクになるように処理（浮動小数の丸めで ties の検出を安定化）。
  - 研究用 API は本番発注・実行層に依存しない設計。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date)
    - research の calc_* 関数を組み合わせて features テーブル用の特徴量を構築。
    - ユニバースフィルタ（最小株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - 日付単位での置換（DELETE + INSERT をトランザクションでラップ）により冪等性と原子性を保証。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して最終スコア final_score を計算。
    - コンポーネントスコア: momentum, value, volatility, liquidity, news（AIスコア）。
    - weights はデフォルト値を持ち、入力の検証・スケーリングを行う（負値や非数値は無視）。
    - Bear レジーム検知（ai_scores の regime_score の平均が負で十分なサンプル数がある場合）により BUY シグナルを抑制。
    - SELL シグナル判定にストップロス（終値/avg_price - 1 < -8%）を実装。その他（トレーリングストップ、時間決済）は未実装（コード内に注記）。
    - ポジションや価格情報が欠損するケースの挙動（スキップや警告）を明確化。
    - signals テーブルへの日付単位置換による冪等保存。

Changed
- （初回リリースのため変更履歴なし）

Fixed
- （初回リリースのため修正履歴なし）

Security
- news_collector: defusedxml の採用、受信サイズ制限、トラッキングパラメータ除去など複数のセキュリティ対策を実装。
- jquants_client: トークンリフレッシュ処理を慎重に扱い、allow_refresh フラグで無限再帰を回避。

Notes / Known limitations
- 一部の売却ルール（トレーリングストップ、保有日数による時間決済）は positions テーブルに peak_price / entry_date 等の追加が必要であり未実装。
- feature_engineering は per を features に直接保存しない（filter 用に avg_turnover を参照するが features テーブルには含めない点に注意）。
- research モジュールは pandas 等に依存せず標準ライブラリ + DuckDB のみで実装されているため、大規模データでのメモリ/性能調整は利用環境に応じて検討が必要。
- NewsCollector の SSRF / IP 判定や接続先ホワイトリストなど追加のネットワーク制御は今後の改善ポイントとして注記あり。

マイグレーション / 利用上の注意
- 必須環境変数をセットしてから利用してください（不足時は ValueError が発生します）。
- 開発・テスト環境で自動 .env 読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB に必要なテーブル（raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news 等）を事前に作成しておく必要があります（スキーマは実装の SQL 期待カラムに従ってください）。
- J-Quants API 利用時はレート制限と認証トークン管理に注意してください（クライアントは自動で制御しますが、アカウント側制限を超えない運用が必要です）。

お問い合わせ / コントリビューション
- 初回リリースに関する問題報告や提案はリポジトリの Issue に記載してください。