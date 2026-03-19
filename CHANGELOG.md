# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム "KabuSys" の基本機能を実装しました。以下は主な追加点・設計上の要点です。

### Added
- パッケージのエントリポイントとバージョン情報
  - src/kabusys/__init__.py にて __version__="0.1.0"、主要サブパッケージをエクスポート。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動ロードする機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - .env のパースを独自実装。export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い、コメント判定ルールなどに対応。
    - Settings クラスで必要な環境変数をプロパティとして提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - デフォルト値の提供（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）と入力値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）。
    - is_live / is_paper / is_dev ユーティリティプロパティ。

- データ取得・保存（J-Quants クライアント）
  - src/kabusys/data/jquants_client.py
    - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
    - HTTP リクエスト共通処理で、指数バックオフによるリトライ（最大 3 回）、429 の Retry-After 優先、408/429/5xx をリトライ対象に設定。
    - 401 発生時は自動でリフレッシュトークンから id token を再取得して 1 回リトライするロジックを実装（再帰ループ防止）。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）。ON CONFLICT / DO UPDATE を利用し重複を排除。
    - データ型変換ユーティリティ (_to_float / _to_int) を実装。
    - 取得時に fetched_at を UTC ISO8601 で記録し、look-ahead bias のトレースを可能に。

- ニュース収集（RSS）
  - src/kabusys/data/news_collector.py
    - RSS フィードの収集と前処理パイプラインを実装。既定の RSS ソース（Yahoo Finance Business）を一つ提供。
    - セキュリティ配慮：defusedxml を利用して XML 攻撃を回避、HTTP(S) スキーム制限、受信サイズ制限（MAX_RESPONSE_BYTES=10MB）などを実装。
    - URL 正規化（小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）を実装。記事ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を担保。
    - バルク挿入のチャンク化（_INSERT_CHUNK_SIZE）とトランザクション単位での保存戦略。

- ファクター計算・研究モジュール
  - src/kabusys/research/factor_research.py
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を DuckDB の prices_daily を使って計算。
    - calc_volatility: 20日 ATR（true range の平均）および相対ATR (atr_pct)、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を明示的に扱う設計。
    - calc_value: raw_financials から直近の財務情報を取得し PER / ROE を計算（EPS が 0/欠損の場合は None）。
    - 計算は営業日ベースの窓／データ不足時に None を返す挙動を採用。

  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 与えたホライズン（デフォルト [1,5,21]）の将来リターンを一クエリで取得。
    - calc_ic: ファクター値と将来リターン間の Spearman のランク相関（IC）を計算。サンプル数不足時は None を返す。
    - factor_summary / rank: 基本統計量計算とランク変換ユーティリティ。
    - 研究用ユーティリティは pandas 等に依存せず標準ライブラリ + duckdb で実装。

- 戦略（特徴量作成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - build_features(conn, target_date): research モジュールの生ファクターを統合し正規化（zscore_normalize を利用）、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用、Z スコアを ±3 にクリップして features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性）。
    - 処理はルックアヘッドバイアスを避けるため target_date 時点のデータのみを使用。

  - src/kabusys/strategy/signal_generator.py
    - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成、signals テーブルへ日付単位で置換。
    - スコア計算:
      - コンポーネント: momentum / value / volatility / liquidity / news（AI スコア）
      - Z スコア → シグモイド変換（_sigmoid）、欠損コンポーネントは中立 0.5 で補完
      - デフォルト重みは momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。与えられた weights は検証・補完・正規化して利用。
    - Bear レジームフィルタ: ai_scores の regime_score 平均が負かつサンプル数充足時に BUY を抑制。
    - SELL 条件（実装済み）:
      - ストップロス: 終値 / avg_price - 1 < -0.08（-8%）
      - スコア低下: final_score < threshold
      - （未実装メモ: トレーリングストップ / 時間決済は positions テーブルの追加データが必要）
    - positions / prices を同一クエリで参照し、価格欠損や平均価格欠損に対する安全策（スキップ・警告）を実装。
    - signals テーブルへの挿入は日付単位の置換（トランザクション）で冪等性を確保。

- モジュール公開
  - src/kabusys/strategy/__init__.py、src/kabusys/research/__init__.py で主要 API をエクスポート。

### Security / Robustness
- ニュースパーサーで defusedxml を採用して XML 攻撃を防止。
- RSS の受信バイト数上限（10MB）でメモリ DoS を軽減。
- ニュース URL の正規化とトラッキングパラメータ除去により冪等性を強化。
- J-Quants クライアントでネットワーク障害・一時的な HTTP エラーに対してリトライ・バックオフを実装。
- API トークンはモジュールレベルでキャッシュし、必要に応じて自動リフレッシュ。再帰的リフレッシュを防止する設計。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須（未設定時は ValueError を送出）。
- 自動 .env ロードの挙動:
  - デフォルトでプロジェクトルートにある .env/.env.local を自動的に読み込みます。テストなどで無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- デフォルト DB パス:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
  - いずれも expanduser を使って展開されます。
- Strategy の既定値:
  - BUY 閾値: 0.60、ストップロス: -8%、Z スコアは ±3 でクリップ。
  - ユニバースフィルタ: 最低株価 300 円、20日平均売買代金 5 億円。
- DuckDB スキーマ（テーブル名: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）が前提です。実行前に適切なスキーマを準備してください。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

今後の予定（例）
- signals → execution 層の接続（発注ロジック・kabu API 統合）
- ポジション管理（peak_price, entry_date を含む positions 拡張）によるトレーリングストップ / 時間決済の実装
- AI ニューススコア生成パイプラインの追加・改善
- 単体テストと CI の整備

問い合わせ・バグ報告はリポジトリの Issue をご利用ください。