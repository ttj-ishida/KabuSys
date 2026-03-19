CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（現在のリリースは 0.1.0 です。新しい変更はここに記載します。）

0.1.0 - 2026-03-19
------------------

Added
- パッケージ初期リリース。主要モジュールを追加。
  - kabusys.__init__.py
    - パッケージバージョンを "0.1.0" として公開。
  - kabusys.config
    - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
    - project root を .git または pyproject.toml で探索して .env 自動読み込みを行う（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env パーサを実装（export 形式やクォート付き値、コメント処理、エスケープ対応）。
    - 環境変数検証（KABUSYS_ENV, LOG_LEVEL の許容値検査）および必須項目取得ヘルパーを提供。
    - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等の扱いを実装。

  - データ取得 / 永続化（kabusys.data）
    - jquants_client
      - J-Quants API クライアントを実装（ページネーション対応）。
      - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
      - リトライ（指数バックオフ、最大 3 回。408/429/5xx 対象）と 401 でのトークン自動リフレッシュ対応を実装。
      - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を実装。
      - DuckDB への冪等保存関数を実装: save_daily_quotes / save_financial_statements / save_market_calendar（ON CONFLICT による更新）。
      - 型安全なパースユーティリティ _to_float / _to_int を追加。
      - 取得時刻（fetched_at）をUTCで記録し、look-ahead バイアスのトレーサビリティを確保。
    - news_collector
      - RSS フィード収集処理の骨格を実装。
      - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除、小文字化）を実装。
      - defusedxml による安全な XML パース、HTTP レスポンスサイズ上限（10MB）等の安全対策を導入。
      - デフォルト RSS ソースとして Yahoo Finance ビジネスカテゴリを設定。
      - DB 保存はバルク挿入・チャンク処理を想定（INSERT チャンクサイズ定義）。
  - 研究（kabusys.research）
    - factor_research
      - Momentum / Volatility / Value のファクター計算（prices_daily / raw_financials を参照）を実装。
      - 短中長期のリターン、MA200 乖離、ATR、avg_turnover、volume_ratio、PER/ROE を算出。
      - 欠損やデータ不足時の扱い（None を返す）を明確化。
    - feature_exploration
      - 将来リターン計算（calc_forward_returns）を実装（任意ホライズン、最大 252 営業日制限）。
      - IC（スピアマンのランク相関）計算（calc_ic）を実装。rank / factor_summary ユーティリティを追加。
    - research.__init__ に公開 API を整備。
  - 戦略（kabusys.strategy）
    - feature_engineering
      - research で算出した生ファクターのマージ、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化、±3 クリップ、features テーブルへの日付単位 UPSERT（トランザクション）を実装。
      - DuckDB を用いた冪等処理を採用。
    - signal_generator
      - features と ai_scores を統合して最終スコア（final_score）を計算、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換する処理を実装。
      - コンポーネントスコア（momentum/value/volatility/liquidity/news）算出ロジックを実装。シグモイド変換・欠損時の中立補完（0.5）を採用。
      - ウェイトの検証・正規化（既知キーのみ受け付け、合計が 1 になるようリスケール）を実装。
      - Bear レジーム検知（AI の regime_score 平均が負 → BUY を抑制）を実装。
      - エグジット判定（ストップロス -8% / final_score が閾値未満）を実装。売り優先で BUY から除外するポリシーを採用。
      - 既に保持しているポジションの価格欠損時は SELL 判定をスキップする安全処理を実装。
    - strategy.__init__ で build_features / generate_signals を公開。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Deprecated
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Security
- news_collector で defusedxml を使用し XML ボム等を防止。
- news_collector で受信サイズ上限を設けてメモリ DoS を軽減。
- URL 正規化でスキーム検査やトラッキングパラメータ除去により SSRF /トラッキング対策を考慮。
- jquants_client のトークン管理は自動リフレッシュを行い、401 での誤動作を軽減。

Known limitations / TODO
- signal_generator のエグジット条件としてトレーリングストップ（peak_price 依存）や時間決済（保有 60 営業日超）については未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の RSS パース→DB保存のフルパイプラインは骨格実装。記事ID生成や news_symbols との紐付けなど運用的な細部は拡張を想定。
- execution/monitoring パッケージは初期構造のみで、ブローカー API 連携や注文実行ロジック、監視アラートの実装は今後の作業。
- 一部関数（特に外部 API を叩く部分）はネットワーク依存のため統合テストが必要。

Notes / Design decisions
- 全体を通して「ルックアヘッドバイアスの防止」「冪等性（DB の UPSERT / 日付単位置換）」「トレーサビリティ（fetched_at を UTC で記録）」を重視して設計。
- DuckDB を主要な分析ストアとして前提化。SQL ウィンドウ関数に依存した実装が多い。
- 外部依存を最小化（research の一部は標準ライブラリのみで実装）し、テスト・配布を容易にする方針。

その他
- ロギングを各モジュールで適切に出力するように実装（WARNING/INFO/DEBUG を使用）。
- この CHANGELOG はコードから推測して作成しています。実際のリリースノートには追加の運用情報や互換性情報を記載することを推奨します。