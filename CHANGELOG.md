# CHANGELOG

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

リリース日付は 2026-03-19。

## [0.1.0] - 2026-03-19 (Initial Release)

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開。__version__ = "0.1.0" を定義。
  - モジュール公開: data, strategy, execution, monitoring をパッケージ外部公開対象としてエクスポート。

- 環境設定/ロード機能（kabusys.config）
  - .env/.env.local と環境変数からの設定読み込みを自動化（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（コメント・export プレフィックス、クォート／エスケープ処理、インラインコメントの取り扱い等に対応）。
  - Settings クラスを提供し、アプリケーションで使用する主要な設定値をプロパティ経由で取得可能に:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/... の検証）
    - is_live / is_paper / is_dev のブール判定プロパティ

- データ収集クライアント（kabusys.data.jquants_client）
  - J-Quants API 用クライアント実装:
    - 固定間隔スロットリングによるレート制限（120 req/min）を遵守する RateLimiter を導入。
    - HTTP リトライロジック（指数バックオフ、最大3回）。408/429/5xx などを再試行対象。
    - 401 レスポンス時のリフレッシュトークンを用いた自動トークン更新（1回のみリトライ）。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（四半期財務）
      - fetch_market_calendar（取引カレンダー）
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes -> raw_prices テーブル（ON CONFLICT DO UPDATE）
      - save_financial_statements -> raw_financials テーブル（ON CONFLICT DO UPDATE）
      - save_market_calendar -> market_calendar テーブル（ON CONFLICT DO UPDATE）
    - データの fetched_at を UTC で記録して Look-ahead バイアスをトレース可能に。
    - 型変換ユーティリティ (_to_float / _to_int) を提供。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集の基盤実装。
  - セキュリティ考慮:
    - defusedxml を利用して XML 攻撃を防止。
    - 受信サイズ上限 (MAX_RESPONSE_BYTES = 10MB) によるメモリ DoS 対策。
    - トラッキングパラメータ（utm_* 等）の除去と URL 正規化。
    - 記事ID を正規化URLの SHA-256 ハッシュ（先頭32文字）で生成し冪等性を担保。
    - SSRF 対策（スキームの検査等の想定設計）。
  - raw_news / news_symbols 等へのバルク挿入を想定したチャンク処理。

- リサーチ用ファクター計算（kabusys.research.*）
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離）計算。
    - calc_volatility: atr_20 / atr_pct / avg_turnover / volume_ratio 等のボラティリティ・流動性指標計算。
    - calc_value: target_date 以前の最新 raw_financials と株価を組み合わせて per / roe を計算。
    - すべて DuckDB の prices_daily / raw_financials を参照する実装（外部 API へは依存しない）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターン算出（1クエリでまとめて取得）。
    - calc_ic: Spearman のランク相関（IC）を実装（ties の平均ランク処理を含む）。有効サンプルが 3 未満のときは None を返す。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを計算。
    - rank: 平均ランク（同順位は平均ランク）を計算するユーティリティ。

- 戦略処理（kabusys.strategy）
  - feature_engineering.build_features:
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価300円・20日平均売買代金 >= 5 億円）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクション + バルク挿入）し冪等性を保証。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各種コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を算出。
    - デフォルト重み・閾値を実装（デフォルト閾値 0.60）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合に BUY を抑制）。
    - SELL（エグジット）判定ロジック:
      - ストップロス（現在価格 / avg_price - 1 <= -8%）
      - final_score が threshold 未満
      - （未実装だが設計に記載）トレーリングストップ / 時間決済は将来対応予定。
    - signals テーブルへ日付単位で置換して保存（冪等）。

### Changed
- （初回リリースのため過去の変更はなし）

### Fixed
- （初回リリースのため過去の修正はなし）

### Security
- news_collector: defusedxml を利用した XML パース、および受信サイズ制限などの多重防御により外部入力による攻撃リスクを低減。
- jquants_client: トークンリフレッシュとリトライ処理の明確化により認証失敗や一時的なネットワーク障害での誤動作を低減。

### Notes / Limitations / Migration
- 環境変数が多数必須（JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / KABU_API_PASSWORD 等）。start 前に .env を用意するか、OS 環境変数を設定してください。Settings._require は未設定で ValueError を投げます。
- 自動 .env ロードはプロジェクトルートの検出に依存するため、パッケージ配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してテスト用に制御してください。
- DuckDB 側のスキーマ（テーブル名・カラム）は実装中の関数が期待する形になっている必要があります。主に利用するテーブル:
  - prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news, news_symbols など。
- signal_generator の一部のエグジット条件（トレーリングストップ・時間決済）は未実装（TODO）。positions テーブルに peak_price / entry_date 等の拡張が必要。
- jquants_client のレート制限は固定間隔スロットリングで実装されています。高スループット一括取得時は API レート規約に注意してください。
- news_collector は既知の RSS ソース（デフォルトで Yahoo Finance のビジネス RSS）をサンプルにしているが、実運用では追加のフィード管理が必要です。
- research モジュールは外部ライブラリ（pandas 等）に依存しない設計で、純粋に標準ライブラリ + DuckDB SQL を用いています。大量データでのパフォーマンスは DuckDB の設定に依存します。

---

今後の予定（例）
- execution 層での発注 API 統合（kabuステーション連携）と注文管理の実装。
- モニタリング（Slack 通知や監視ジョブ）の実装・連携。
- 未実装のエグジット戦略（トレーリングストップ、時間決済）の追加。
- ニュース -> 銘柄マッピングの精度向上（NLP/ルール拡張）。

以上。