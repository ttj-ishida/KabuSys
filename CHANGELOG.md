# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

- 変更履歴はセマンティックバージョニングに従います。
- 影響範囲（API / DB / 環境変数）なども併せて記載しています。

## [Unreleased]

（現時点のコードは初期リリース相当のため、未リリース項目はありません）

## [0.1.0] - 2026-03-19

初回リリース。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API には data, strategy, execution, monitoring を想定（src/kabusys/__init__.py）。
  - パッケージバージョン: 0.1.0。

- 設定・環境変数管理
  - .env ファイル自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。CWD に依存しない実装（src/kabusys/config.py）。
  - .env パーサを強化:
    - export KEY=val 形式対応
    - シングル／ダブルクォート、バックスラッシュエスケープ対応
    - インラインコメント処理（クォート有無に応じた挙動）
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を追加。
  - Settings クラスを導入し、必要な環境変数をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN（必須）
    - SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
  - is_live / is_paper / is_dev の便宜プロパティ。

- Data 層 (J-Quants)
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）:
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を導入。
    - リトライ（指数バックオフ、最大3回）、429 の Retry-After 優先処理、408/429/5xx を再試行対象に設定。
    - 401 受信時に refresh token を用いて自動リフレッシュ＋1回リトライの仕組みを実装。
    - ページネーション対応の fetch_* API:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務）
      - fetch_market_calendar（取引カレンダー）
    - DuckDB への保存関数（冪等）:
      - save_daily_quotes → raw_prices テーブルへ ON CONFLICT DO UPDATE
      - save_financial_statements → raw_financials テーブルへ ON CONFLICT DO UPDATE
      - save_market_calendar → market_calendar テーブルへ ON CONFLICT DO UPDATE
    - データ取得時刻を UTC の ISO 形式で fetched_at に記録（Look-ahead bias 対策）。
    - モジュールレベルの ID トークンキャッシュでページネーション間のトークン共有を実装。

- Data 層 (ニュース)
  - RSS から記事を収集・正規化して raw_news へ保存する基盤を実装（src/kabusys/data/news_collector.py、以降の処理を含む）:
    - defusedxml を用いた安全な XML パース
    - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）
    - 記事ID は正規化 URL の SHA-256 の先頭32文字を利用し冪等性を確保
    - SSRF/不正スキーム対策、挿入時はバルク/トランザクションで効率的に保存
    - デフォルト RSS ソース: Yahoo Finance の business カテゴリ

- Research 層
  - factor_research モジュールを実装（src/kabusys/research/factor_research.py）:
    - calc_momentum（mom_1m/mom_3m/mom_6m、ma200_dev）
    - calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）
    - calc_value（per, roe。raw_financials から target_date 以前の最新財務データを取得）
    - 実装は DuckDB の SQL ウィンドウ関数中心で、営業日欠損を考慮したスキャンバッファを使用
  - feature_exploration モジュールを実装（src/kabusys/research/feature_exploration.py）:
    - calc_forward_returns（指定ホライズンの将来リターン、デフォルト [1,5,21]）
    - calc_ic（Spearman の ρ をランク計算で算出。サンプル不足時 None を返す）
    - factor_summary（count/mean/std/min/max/median の集計）
    - rank（同順位は平均ランク、round(v,12) による tie 対策）
  - research パッケージの __all__ を整備。

- Strategy 層
  - feature_engineering（src/kabusys/strategy/feature_engineering.py）:
    - 研究環境の raw ファクターを集約・正規化して features テーブルへ UPSERT（日付単位の置換で冪等性を保証）
    - ユニバースフィルタ（最低価格 300 円、20日平均売買代金 5 億円）
    - 正規化は zscore_normalize を利用し、対象カラムを ±3 でクリップ
    - target_date 時点のデータのみ使用してルックアヘッドバイアスを防止
  - signal_generator（src/kabusys/strategy/signal_generator.py）:
    - features と ai_scores を統合し final_score を算出（モメンタム/バリュー/ボラ/流動性/ニュースの重み付け）
    - デフォルト重み・閾値（weights デフォルト、threshold=0.60）
    - AI レジームスコアの集計による Bear 判定（サンプルが _BEAR_MIN_SAMPLES 未満なら Bear とは判定しない）
    - BUY シグナルは降順スコアで閾値超を採用（Bear では BUY を抑制）
    - SELL シグナル生成（ストップロス -8% / final_score < threshold）
    - positions / prices_daily / ai_scores / features を参照し、signals テーブルへ日付単位で置換して書き込む（トランザクションで原子性確保）
    - weights のバリデーション／正規化（未知キーや不正値は無視、合計が 1 でない場合は再スケール）

- その他ユーティリティ
  - data.stats.zscore_normalize を参照して標準化処理の統合利用（各所で利用）
  - 多くの DB 操作でトランザクション + バルク挿入を採用し原子性・効率性を確保

### Changed
- 初回リリースのため過去の変更はなし（設計文書に基づく初期実装を反映）。

### Fixed
- 初回リリースのためなし。

### Security
- news_collector: defusedxml を使用して XML 攻撃（XML Bomb 等）を緩和。
- news_collector: レスポンスサイズ上限を設定しメモリ DoS を緩和。
- jquants_client: トークン処理・リトライで不正な再帰や過剰リトライを防ぐ設計（allow_refresh フラグ、1回のみのリフレッシュ）。
- config の .env パーサでクォートやエスケープを正しく扱い、予期しないパースを減らす。

### Known issues / Limitations
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装。positions テーブルに peak_price / entry_date が必要になる旨をコメントとして残している。
- news_collector の一部処理（例: 外部記事と銘柄紐付けのロジックや挿入時の RETURNING を用いた正確な挿入数の取得）は実装の想定はあるが、利用状況に応じて追加実装が必要。
- DuckDB のテーブルスキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news 等）は本 CHANGELOG に詳細記載していないため、別途スキーマ定義を参照すること。
- jquants_client の _BASE_URL は固定値（https://api.jquants.com/v1）を使用。モックやテスト時は settings.jquants_refresh_token 等の環境変数操作や _RateLimiter の挙動に注意。
- news_collector の URL 正規化/SSRF 対策は基本実装だが、さらなるセキュリティ検査（IP フィルタリング・ホワイトリスト等）が推奨される。

---

今後の予定（例）
- position に peak_price / entry_date を取り込み、トレーリングストップや時間決済を実装
- signals → execution 層の接続（発注ロジック）の追加
- News と AI スコアの結合ロジック強化（自然言語処理によるスコア化パイプライン）
- 単体テスト・統合テストの整備（モック API / DuckDB のテスト用データ）

（必要があれば各ファイル・関数単位での更に詳細な変更点／実装ノートを追記します。）