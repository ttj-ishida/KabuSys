# Change Log

すべての重要な変更点をここに記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョンは 0.1.0 です。

## [0.1.0] - 2026-03-19

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（execution はスキャフォールドのみ）

- 環境設定管理（kabusys.config）
  - Settings クラスを提供し、環境変数からアプリケーション設定を取得する仕組みを実装。
  - 自動的に .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - サポートされる主な環境変数:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live、デフォルト: development）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト: INFO）

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（内部 RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
  - 401 の場合は自動トークンリフレッシュを行い 1 回リトライ。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（取引カレンダー）
  - DuckDB への保存関数（冪等性を確保する upsert 実装）:
    - save_daily_quotes → raw_prices（ON CONFLICT DO UPDATE）
    - save_financial_statements → raw_financials（ON CONFLICT DO UPDATE）
    - save_market_calendar → market_calendar（ON CONFLICT DO UPDATE）
  - 型変換ユーティリティ: _to_float / _to_int（安全に None を返す実装）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news テーブルへ保存するモジュール。
  - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
  - URL 正規化: スキーム/ホスト小文字化、トラッキングパラメータ除去（utm_* 等）、フラグメント削除、クエリをソート。
  - セキュリティ対策:
    - defusedxml を使用して XML 攻撃を防止
    - HTTP/HTTPS 以外のスキームを拒否（SSRF 対策）
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）
  - バルク INSERT のチャンク処理等で DB 負荷を抑制

- リサーチ・ファクター計算（kabusys.research）
  - ファクター計算モジュール（価格データ・財務データのみ参照、外部 API に依存しない）
  - 提供関数:
    - calc_momentum（mom_1m / mom_3m / mom_6m / ma200_dev）
    - calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - calc_value（per, roe）
    - calc_forward_returns（将来リターン fwd_1d / fwd_5d / fwd_21d を計算）
    - calc_ic（Spearman のランク相関による IC 計算）
    - factor_summary（列ごとの count/mean/std/min/max/median）
    - rank（値を平均ランクに変換）
  - 外部依存は使用せず、DuckDB の SQL と標準ライブラリで実装

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features(conn, target_date): research モジュールの生ファクターを統合し、
    ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
  - 正規化: zscore_normalize を利用、指定列を Z スコア正規化し ±3 でクリップ。
  - features テーブルへ日付単位で置換（トランザクションで原子性を確保）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - コンポーネントはシグモイド変換や PER に基づく変換を適用。
    - デフォルト重みを定義（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。ユーザー重みは検証・正規化される。
    - Bear レジーム判定（ai_scores の regime_score 平均が負で、十分なサンプルがある場合に BUY を抑制）。
    - BUY: final_score >= threshold（Bearの場合は抑制）
    - SELL（エグジット）: ストップロス（終値/avg_price -1 < -8%）、または final_score < threshold
    - signals テーブルへ日付単位の置換（トランザクションで原子性を確保）
  - SELL 判定で取り扱われていない将来実装候補（コメント付き）:
    - トレーリングストップ（peak_price 必要）
    - 時間決済（保有 60 営業日超過）

### Changed
- 初回リリースのため該当なし

### Fixed
- 初回リリースのため該当なし

### Deprecated
- 初回リリースのため該当なし

### Removed
- 初回リリースのため該当なし

### Security
- news_collector で defusedxml を利用し XML 関連の攻撃を防止。
- news_collector が受信サイズを制限（10 MB）してメモリ DoS を軽減。
- jquants_client で 401 時の自動トークンリフレッシュと再試行ロジックを組み込み、認証周りの堅牢性を向上。
- jquants_client のネットワークリトライは 429 の Retry-After を尊重する実装。

### Known issues / Notes
- execution パッケージは現時点で初期化のみ（実際の発注ロジック・ kabu ステーション連携は未実装の可能性あり）。
- signal_generator の一部エグジット条件（トレーリングストップ等）は positions テーブルに追加情報（peak_price / entry_date 等）が必要で、現状未実装。
- 関数は DuckDB のテーブル（prices_daily / raw_prices / raw_financials / features / ai_scores / positions / signals など）に依存するため、運用前にスキーマ整備とテーブル準備が必要。
- research モジュールは pandas 等に依存しないが、結果の操作やプロット等の研究用途では外部ツールの利用を想定。

---

今後の変更はこのファイルに逐次追加してください。