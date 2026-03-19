# CHANGELOG

すべての注目すべき変更点をここに記録します。
フォーマットは「Keep a Changelog」に準拠し、セマンティック バージョニングを採用します。

## [Unreleased]

（現在無し）

## [0.1.0] - 2026-03-19

初回リリース: 日本株向けの自動売買・リサーチ用コアライブラリを追加。

### Added
- パッケージ公開情報
  - kabusys パッケージ初期化。__version__ = 0.1.0、主要サブパッケージ（data, strategy, execution, monitoring）を __all__ に定義。

- 設定・環境変数管理（kabusys.config）
  - .env ファイル（.env / .env.local）をプロジェクトルート（.git または pyproject.toml）から自動読み込み。
  - 自動読み込みを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - 複雑な .env パース実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い。
    - クォート無し値の # コメント判定は直前が空白/タブの場合のみ。
  - 環境変数の取得ヘルパーと必須チェック（_require）。
  - デフォルト値とバリデーション:
    - KABUSYS_ENV（development, paper_trading, live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - DB パスの既定値（DUCKDB_PATH, SQLITE_PATH）
  - 必須環境変数の一覧（実行に必須）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID

- Data 層（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - レート制限: 120 req/min を固定間隔スロットリングで制御（_RateLimiter）。
    - 汎用 HTTP リクエストユーティリティ(_request) とリトライ戦略:
      - 指数バックオフ、最大 3 回、ステータスコード 408/429/5xx をリトライ対象。
      - 401 受信時はトークンを自動リフレッシュして1回リトライ（get_id_token と連携）。
      - ページネーション対応（pagination_key を利用）。
    - データ取得関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（マーケットカレンダー）
    - DuckDB への保存関数（冪等設計、ON CONFLICT DO UPDATE）:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - 入力整形ユーティリティ: _to_float, _to_int（安全なパース）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集と raw_news への保存ロジック。
  - セキュリティ／堅牢性設計:
    - defusedxml を利用して XML 攻撃を防止。
    - URL 正規化（トラッキングパラメータ削除、スキーム/ホスト小文字化、フラグメント除去、パラメータソート）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）や HTTP スキーム制限で SSRF / DoS を軽減。
    - 記事 ID を正規化 URL の SHA-256（先頭 32 文字）で生成し冪等性を担保。
    - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）で SQL 長制限やパフォーマンスを考慮。
  - デフォルト RSS ソース定義（例: Yahoo Finance のビジネス RSS）。

- Research 層（kabusys.research）
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（20日 ATR、相対ATR、20日平均売買代金、出来高比）
    - calc_value（PER、ROE：raw_financials と prices_daily 組合せ）
    - 各関数は DuckDB の prices_daily / raw_financials のみ参照、結果は (date, code) キーの dict リストを返す。
    - 欠損・データ不足時の扱いを明示（十分な行数がなければ None を返す等）。
  - feature_exploration:
    - calc_forward_returns（指定ホライズンの将来リターン: デフォルト [1,5,21]）
    - calc_ic（Spearman ランク相関による IC 計算、サンプル数 3 未満で None）
    - factor_summary（count/mean/std/min/max/median を計算）
    - rank（同順位は平均ランク、丸めによる ties 検出対策）
  - research パッケージの __all__ に主要ユーティリティを公開。

- Strategy 層（kabusys.strategy）
  - feature_engineering.build_features:
    - research の生ファクターを取得しユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 にクリップ。
    - 日付単位で features テーブルに置換（トランザクション + バルク挿入で原子性を確保）。
    - ルックアヘッドバイアス対策として target_date 時点のデータのみ使用。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して最終スコア（final_score）を計算。
    - コンポーネントスコア計算（momentum/value/volatility/liquidity/news）:
      - momentum: 複数のシグモイド平均
      - value: PER ベースの逆数モデル（PER = 20 で 0.5）
      - volatility: atr_pct の逆転シグモイド
      - liquidity: volume_ratio のシグモイド
      - news: ai_score をシグモイド変換（未登録は中立補完）
    - 重み付けの取り扱い: デフォルト重みを保持し、渡された weights は検証・補正（負値・NaN を無視、合計が 1 になるよう再スケール）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負 AND サンプル数 >= 3 の場合）で BUY シグナルを抑制。
    - SELL（エグジット）ロジック:
      - ストップロス: 終値 / avg_price - 1 < -8%（優先）
      - final_score が threshold 未満（デフォルト threshold = 0.60）
      - 価格欠損時は SELL 判定をスキップして誤クローズを防止
    - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。
  - strategy パッケージの __all__ に build_features / generate_signals を公開。
  - デフォルトの戦略パラメータを明確化（weights, threshold, stop_loss, etc.）。

- DuckDB とトランザクション設計
  - 主要な DB 書き込み処理（features/signals/raw_* 等）は日付単位の置換を採用し、BEGIN/COMMIT/ROLLBACK を用いて原子性を保証。
  - Insert の際の ON CONFLICT / DO UPDATE による冪等性。

### Changed
- （該当無し：初回リリース）

### Fixed
- （該当無し：初回リリース）

### Security
- ニュース XML のパースに defusedxml を使用。
- RSS/URL 関連での入力検証・正規化・受信サイズ制限を実施し、SSRF / XML 外部実行攻撃 / メモリ DoS を軽減。
- API クライアントはトークン自動リフレッシュとリトライ戦略を実装し、認証周りの不整合に対処。

### Notes / その他
- execution パッケージはプレースホルダ（初期状態、実行層は別途実装予定）。
- look-ahead bias を避ける設計思想が各所に反映されている（fetched_at の UTC 記録、target_date 時点のみ参照等）。
- 外部ライブラリへの依存を最小化する方針（research の統計処理は標準ライブラリで実装）。
- 将来的な拡張点（README/StrategyModel.md 等に言及される仕様に従って実装予定）:
  - positions テーブルに peak_price / entry_date を追加してトレーリングストップ等の追加条件を実装可能。
  - AI ニューススコアの投入フロー（ai_scores テーブルの生成）は別途実装・接続。

### Upgrade / Migration
- .env を使用する場合は .env.example を参考に以下の必須キーを設定してください:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードを無効化したいテスト・CI 環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定します。

---

開発・運用における追加の注記や既知の制約があればここに追記してください。