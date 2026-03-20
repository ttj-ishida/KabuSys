# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-03-20
初回リリース。日本株自動売買システムのコアライブラリを追加。

### Added
- パッケージ基盤
  - kabusys パッケージ初期導入。バージョンは 0.1.0。
  - __all__ を通じて data / strategy / execution / monitoring 名前空間を公開。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル / .env.local と OS 環境変数を統合して自動読み込みする仕組みを実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込みを実現。
  - 行パーサで export プレフィックス・クォート・インラインコメント等に対応（エスケープ考慮）。
  - 自動ロード無効化のための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供（J-Quants / kabuAPI / Slack / DB パス / 環境 (development/paper_trading/live) / ログレベル 等）。
  - 必須環境変数未設定時に明示的な ValueError を発生させる _require ユーティリティ。
  - デフォルト DB パス（duckdb: data/kabusys.duckdb、sqlite: data/monitoring.db）を設定。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - レート制限保護（固定間隔スロットリング、120 req/min を既定）を実装する RateLimiter。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After を優先。
  - 401 発生時にリフレッシュトークンを用いて ID トークンを自動更新し 1 回だけ再試行する挙動を実装。
  - ページネーション対応（pagination_key による連続取得）。
  - fetch_* 関数群: fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar。
  - DuckDB への保存ユーティリティ: save_daily_quotes / save_financial_statements / save_market_calendar。いずれも冪等（ON CONFLICT … DO UPDATE）での保存を行う。
  - データ取得時の fetched_at を UTC ISO8601 形式で記録し、Look-ahead バイアス対策をサポート。
  - 型変換ユーティリティ (_to_float, _to_int) により不正値を安全に扱う。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存するモジュールを実装。
  - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）と記事ID生成（正規化後の SHA-256 先頭）による冪等性確保。
  - defusedxml を利用した XML 攻撃耐性、受信サイズ上限（10MB）によるメモリ DoS 対策、SSRF 回避（HTTP/HTTPS スキーム限定）などのセキュリティ対策を採用。
  - バルク挿入のチャンク化（デフォルトチャンクサイズ 1000）と単一トランザクションでの保存により性能と整合性を両立。
  - デフォルトRSSソースに Yahoo Finance のカテゴリフィードを追加。

- 研究用モジュール (kabusys.research)
  - ファクター計算・解析用の関数群を追加。
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系のファクターを計算。
    - calc_forward_returns: 将来リターン（デフォルト 1,5,21 営業日）を一括で取得。
    - calc_ic: スピアマン順位相関（IC）計算。サンプル不足（<3）時は None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクを与えるランク関数（浮動小数の丸め処理あり）。
  - DuckDB のみに依存（外部ライブラリに依存しない実装方針）で、研究環境向けに設計。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date): research モジュールで計算した生ファクターを統合し、ユニバースフィルタ（最低株価 300 円・20日平均売買代金 5 億円）を適用。
  - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 にクリップして外れ値影響を抑制。
  - DuckDB の features テーブルへ日付単位で置換（DELETE + INSERT）することで冪等性と原子性を保証（トランザクション使用）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合して final_score を算出し、BUY / SELL シグナルを生成して signals テーブルへ保存（冪等）。
  - モデル設計に基づくコンポーネント:
    - momentum / value / volatility / liquidity / news の重み合算（デフォルト重みを搭載）。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
  - エグジット条件（ストップロス -8% / final_score が閾値未満）を実装。未実装の条件（トレーリングストップ・時間決済）はコメントで明示。
  - 重複・不整合への堅牢性: 不正な重みは警告して無視、合計が 1 でない場合は再スケール、保存はトランザクションで原子操作。

### Security
- 外部データ取り込み時の堅牢化:
  - news_collector: defusedxml、受信上限、URL検証等を導入。
  - jquants_client: ネットワークエラーや HTTP エラーへのリトライとログ、トークン自動リフレッシュで安定性を向上。

### Performance / Reliability
- DuckDB を用いた高速な列指向検索とウィンドウ関数活用により大量データの集計を最適化。
- bulk executemany / チャンク化 / トランザクションの利用で DB 操作のオーバーヘッドを低減。
- API レート制御により外部 API 側のレート制限違反を回避。

### Notes
- 本リリースの研究向け関数群は prices_daily / raw_financials / features / ai_scores / positions 等のテーブル定義前提で動作します。スキーマ整備は利用側で行ってください。
- execution / monitoring 名前空間は公開されていますが、実行層の具体的な発注処理は本バージョンでは含まれていません（分離設計）。
- 自動 .env ロードはプロジェクトルートが検出できない場合はスキップされます。テスト環境等で自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。