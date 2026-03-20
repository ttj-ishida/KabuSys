# CHANGELOG

すべての着目可能な変更は Keep a Changelog のフォーマットに従って記載しています。初回リリースとしてバージョン 0.1.0 を登録します。

全般
- バージョン: 0.1.0
- 日付: 2026-03-20
- 概要: 日本株自動売買システムのコア機能（設定読み込み、データ取得・保存、ファクター計算、特徴量作成、シグナル生成、ニュース収集、研究ユーティリティ）を実装。DuckDB をデータ層に用い、冪等性・トランザクション・エラー処理・セキュリティ考慮を組み込んでいる。

## [0.1.0] - 2026-03-20

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__ に __version__ = "0.1.0"、主要サブパッケージを公開）。
- 設定 / 環境変数読み込み（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト等で使用）。
  - .env パーサを堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート・バックスラッシュエスケープ処理
    - インラインコメント処理（クォートの有無に応じた扱い）
  - 必須キー取得時のバリデーション（未設定時は ValueError）。
  - 設定プロパティ: JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、KABU_API_BASE_URL、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）等。
  - 環境モード判定ユーティリティ（is_live / is_paper / is_dev）。

- データ取得・保存（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - APIレート制限遵守のための固定間隔スロットリング RateLimiter（120 req/min）。
  - リトライ & 指数バックオフ（最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - 401 受信時にはリフレッシュトークンから id_token を自動更新して1回だけ再試行（無限再帰防止）。
  - id_token のモジュールレベルキャッシュ（ページネーション間で共有）。
  - JSON デコードエラー検出と明確な例外メッセージ。
  - ページネーション対応の fetch_* 関数:
    - fetch_daily_quotes (日足 OHLCV)
    - fetch_financial_statements (四半期財務)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE を使用）:
    - save_daily_quotes → raw_prices テーブルへの保存（fetched_at を UTC ISO 形式で記録）
    - save_financial_statements → raw_financials テーブルへの保存
    - save_market_calendar → market_calendar テーブルへの保存
  - 入出力の堅牢化ユーティリティ (_to_float, _to_int)

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して raw_news に保存するための基盤を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML 攻撃を防止。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）設定。
    - トラッキングパラメータ（utm_*, fbclid 等）を削除し URL を正規化。
    - URL 正規化関数（スキーム/ホストの小文字化、クエリソート、フラグメント削除など）を実装。
    - DB 挿入時にバルクチャンク化（_INSERT_CHUNK_SIZE）でオーバーヘッド抑制。
  - 記事 ID の生成方針（docstring に記載）: URL 正規化後の SHA-256 を用いて冪等性を確保（実装方針記述）。

- リサーチ（src/kabusys/research/）
  - ファクター計算群（factor_research）実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）などを SQL ウィンドウで計算。
    - calc_volatility: ATR（20日）、atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 取り扱いに注意）。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を算出（price 組合せ）。
  - 特徴量探索（feature_exploration）実装:
    - calc_forward_returns: LEAD を用いた将来リターン（デフォルト 1/5/21 営業日）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（ランク付けは同順位の平均ランク、少数サンプルは None）。
    - factor_summary / rank ユーティリティ（標準ライブラリのみで実装）。
  - 上記関数群は DuckDB 接続を受け取り、prices_daily / raw_financials のみを参照する設計。

- 特徴量作成（src/kabusys/strategy/feature_engineering.py）
  - research で計算した生ファクターを取り込み、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
  - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ。
  - features テーブルへの日付単位での置換（トランザクション＋バルク挿入で原子性）。
  - 欠損・外れ値に対する扱い方やルックアヘッドバイアス回避を明示。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - features と ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）計算と重み付け（デフォルト weights と閾値を提供）。
  - weights のバリデーション・補完・正規化（不正値の無視、合計が 1.0 にスケール）。
  - AI レジームスコアの集計による Bear 判定（サンプル数閾値あり）で BUY を抑制。
  - エグジット判定（STOP-LOSS -8%、スコア低下等）に基づく SELL シグナル生成。
  - positions / prices_daily を参照して SELL 判定。価格欠損時の判定スキップやログ出力を実装。
  - signals テーブルへの日付単位の置換（トランザクション保証）。
  - すべて発注 API とは分離しており、execution 層への依存なし。

- パッケージエクスポート
  - strategy.build_features, strategy.generate_signals, research の主要関数群、data.stats の zscore_normalize を __all__ で公開。

### Changed
- このリリースは初版のため「変更」に相当する過去履歴はありません（初期実装）。

### Fixed
- このリリースは初版のため「修正」に相当する過去履歴はありません。

### Removed
- 該当なし（初版）。

### Security
- 外部データ処理におけるセキュリティ考慮を導入:
  - RSS 解析に defusedxml を使用（XML ベース攻撃防止）。
  - ニュース取得時の受信サイズ制限（メモリ DoS 対策）。
  - ニュース URL 正規化でトラッキングパラメータ除去。
  - J-Quants クライアントで HTTP エラー処理・リトライ制御を実装し、不正な状態遷移を最小化。

### Performance / Reliability
- DuckDB への書き込みはバルク挿入と ON CONFLICT を用いて冪等性を担保。
- feature/signals の置換処理はトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を確保。ROLLBACK 失敗時は warning を出力。
- J-Quants API 呼び出しは固定間隔スロットリングでレート制限を守る実装。

### Known issues / TODO
- signal_generator の SELL 条件について docstring にて未実装として明示された機能:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- calc_value: PBR・配当利回りは未実装（docstring に明記）。
- news_collector の docstring では記事 ID の SHA-256 ハッシュ生成等の方針を示しているが、実装全体（紐付け/INSERT RETURNING等）の詳細は今後拡充する余地あり。
- 一部のユーティリティ（例: kabusys.data.stats.zscore_normalize）の実装は別モジュールにあり、本リリースではその利用を前提としている（提供済みか別途実装が必要）。

---

注: 上記はコードベースのコメント / docstring / 実装内容から推測してまとめた CHANGELOG です。ステークホルダーの希望に応じて、各機能ごとの利用方法・環境変数一覧・DB スキーマやマイグレーション手順を別途ドキュメント化することを推奨します。