# Changelog

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。  
現在のパッケージバージョン: 0.1.0

## [Unreleased]
（今後の変更用）

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムのコアモジュール群を追加。

### Added
- パッケージ基盤
  - kabusys パッケージの初期エクスポートを追加（data, strategy, execution, monitoring）。
  - バージョン定義: __version__ = "0.1.0"。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
    - プロジェクトルート検出は __file__ から親ディレクトリを探索し .git または pyproject.toml を基準に判定。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - 読み込み順: OS 環境変数 > .env.local > .env（.env.local は上書き）。
  - .env パーサを実装（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理など）。
  - Settings クラスを提供し、必須環境変数取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）、デフォルト値（KABUSY_ENV, LOG_LEVEL, DB パス）および値検証を実装。
  - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）を Path 型で提供。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制限（120 req/min）を実装する RateLimiter。
    - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx 対応）。
    - 401 受信時の自動トークンリフレッシュ（1 回）とモジュールレベルの ID トークンキャッシュ。
    - ページネーション対応のフェッチ関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB へ冪等保存する save_* 関数（raw_prices, raw_financials, market_calendar）を実装。ON CONFLICT DO UPDATE により重複更新を防止。
    - レスポンス・パース時の型変換ユーティリティ (_to_float, _to_int) を実装。
    - fetch/save における PK 欠損行のスキップとログ警告。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからのニュース収集モジュールを追加。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化、フラグメント削除）。
    - defusedxml を利用した XML パース（XML Bomb 等の防御）。
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES、デフォルト 10MB）を導入してメモリ DoS を軽減。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
    - DB へのバルク INSERT チャンク処理、ON CONFLICT DO NOTHING の方針。

- ファクター計算・研究ツール (kabusys.research)
  - ファクター計算モジュールを実装（prices_daily / raw_financials を参照）。
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、volume_ratio を計算。
    - calc_value: 最新の財務データ（eps, roe）を用いて PER、ROE を計算。
  - 研究用ユーティリティ:
    - calc_forward_returns: 将来リターン（デフォルト [1,5,21]）の一括取得。
    - calc_ic: スピアマンのランク相関（IC）計算、サンプル不足時は None を返す。
    - rank, factor_summary: ランク付け・統計サマリを標準ライブラリのみで提供。
  - pandas 等外部ライブラリに依存しない設計。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research で計算済みの生ファクターを統合・正規化して features テーブルへ保存する build_features を実装。
    - ユニバースフィルタ: 最低株価 _MIN_PRICE=300 円、20 日平均売買代金 _MIN_TURNOVER=5e8 円 を適用。
    - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - 日付単位の置換（DELETE + INSERT）をトランザクションで行い冪等性・原子性を確保。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコア（final_score）を計算し BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news を個別計算。
    - デフォルト重み DEFAULT_WEIGHTS を実装（合計が 1.0 になるよう正規化）。
    - Sigmoid 変換、欠損コンポーネントは中立 0.5 で補完。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数 >= _BEAR_MIN_SAMPLES）により BUY を抑制。
    - BUY 閾値 DEFAULT_THRESHOLD=0.60 を実装。SELL のエグジット条件としてストップロス（-8%）とスコア低下を実装。
    - positions / prices_daily / features / ai_scores を参照し、signals テーブルへ同様に日付単位置換で保存。

- モジュール結合
  - strategy.__init__ で build_features / generate_signals を公開。
  - research.__init__ で主要関数を再エクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector にて defusedxml を使用し XML 攻撃を緩和。
- RSS パース時に受信サイズ上限を導入してメモリ DoS を軽減。
- news_collector の URL 正規化でトラッキングパラメータを除去、SSRF 対策として非 http/https スキームを扱わない方針（注: 実装箇所での検証に留意）。

### Known issues / Limitations
- signal_generator の一部エグジット条件は未実装（トレーリングストップ、時間決済）。positions テーブルに peak_price / entry_date 等が必要。
- execution パッケージは空（発注ロジックは含まれていない）。
- モジュールは DuckDB（duckdb パッケージ）に依存。利用時は対応するテーブルスキーマが必要。
- news_collector の一部実装（記事→銘柄の紐付けなど）は DataPlatform.md に依存する仕様のため、外部設定/追加処理が必要となる可能性がある。
- J-Quants クライアントはネットワーク・API 側の挙動に依存するため、実運用では監視・リカバリ（トークン管理・ログ）、および API レート変更への対応が必要。

### Migration
- 本バージョンは初期リリースのため破壊的変更はなし。今後 .env パース挙動や Settings API を変更する可能性あり。

---

貢献・バグ報告・改善提案はリポジトリの issue をご利用ください。