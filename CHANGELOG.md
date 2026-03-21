# CHANGELOG

すべての注目すべき変更点を記録します。本ファイルは Keep a Changelog の書式に準拠します。  
初期リリースに含まれる機能・設計上の決定や公開 API の要点を日本語でまとめています。

全般
- パッケージバージョン: 0.1.0
- パッケージ説明: KabuSys - 日本株自動売買システム（モジュール群: data, strategy, execution, monitoring をエクスポート）
- リリース日: 2026-03-21

## [0.1.0] - 2026-03-21

### Added
- 基本構成
  - src/kabusys/__init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージ（data, strategy, execution, monitoring）を公開。

- 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動読み込みロジック:
    - プロジェクトルートを .git または pyproject.toml から探索して特定（CWD に依存しない実装）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能（テスト用途）。
  - .env のパース機能を実装（コメント・export プレフィックス・シングル/ダブルクォート・エスケープやインラインコメント処理に対応）。
  - 上書き保護（protected set）ロジックを実装し、OS 環境変数を意図せず上書きしない仕組みを導入。
  - 設定値検証:
    - KABUSYS_ENV は development/paper_trading/live のいずれかのみ許容。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
  - Settings で主要な必須環境変数をプロパティとして公開（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - DB パス（DUCKDB_PATH/SQLITE_PATH）は既定値を持ち Path 型で返却。
  - _require による必須環境変数未設定時の ValueError を導入。

- Data: J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API との通信クライアントを実装。
  - レート制限制御（120 req/min）を固定間隔スロットリングで管理する _RateLimiter を導入。
  - HTTP リクエストの共通処理 _request を実装:
    - ページネーション対応。
    - 指数バックオフによるリトライ（最大 3 回）。リトライ対象ステータス: 408, 429 および 5xx。
    - 429（Too Many Requests）時は Retry-After ヘッダを優先。
    - 401 Unauthorized は自動でトークンをリフレッシュして 1 回再試行するロジックを実装（再帰ループ回避のため allow_refresh フラグを使用）。
    - モジュールレベルで ID トークンキャッシュを保持し、ページネーション間でトークンを共有。
    - JSON デコード失敗時に明確なエラーメッセージを出力。
  - 認証ユーティリティ get_id_token を実装（リフレッシュトークンから idToken を取得）。
  - データ取得関数（ページネーション対応）を実装:
    - fetch_daily_quotes: 株価日足（OHLCV）取得
    - fetch_financial_statements: 財務データ取得
    - fetch_market_calendar: JPX マーケットカレンダー取得
  - DuckDB への保存関数を実装（冪等）:
    - save_daily_quotes / save_financial_statements / save_market_calendar
    - ON CONFLICT DO UPDATE を利用して重複を排除
    - fetched_at を UTC ISO-8601 形式で記録し、Look-ahead バイアスのトレースを可能に
  - ユーティリティ関数 _to_float / _to_int を追加（安全な型変換、変換失敗時は None を返す）。

- Data: ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を取得して raw_news に保存するための基盤を追加。
  - セキュリティ・堅牢性対策:
    - defusedxml の利用（XML Bomb 等の防御）。
    - HTTP/HTTPS スキームの検証、IP/SSRF に対する注意（設計に言及）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）によるメモリ DoS 対策。
  - URL 正規化（_normalize_url）を実装。トラッキングパラメータ（utm_*, fbclid 等）の除去、スキーム/ホスト小文字化、フラグメント除去、クエリのソートなどを行う。
  - 記事 ID を URL 正規化後の SHA-256 ハッシュで生成する方針（冪等化を保証）。
  - 挿入はバルクでまとめてトランザクション内に実行する設計（チャンクサイズ制御あり）。

- Research（研究用ユーティリティ）:
  - src/kabusys/research/factor_research.py:
    - calc_momentum: mom_1m/mom_3m/mom_6m、MA200 乖離（ma200_dev）を計算。
    - calc_volatility: ATR(20)、相対 ATR (atr_pct)、20日平均売買代金 (avg_turnover)、volume_ratio を計算。
    - calc_value: target_date 以前の最新財務情報と当日の株価から PER・ROE を計算（EPS が 0/欠損の場合は None）。
    - DuckDB を用いた Window 関数／移動集計による実装。営業日欠損（祝日等）を吸収するためにカレンダーバッファを採用。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算（LEAD を利用した実装）。
    - calc_ic: ファクターと将来リターンのスピアマン rank 相関（Information Coefficient）を計算。サンプル数不足（<3）時は None を返す。
    - rank: 同順位は平均ランクとする実装（丸めによる ties 検出の補正）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算する統計サマリ関数を実装。
  - 研究モジュールは prices_daily / raw_financials のみ参照し、本番環境の API や発注層に依存しない設計。

- Strategy（戦略本体）
  - src/kabusys/strategy/feature_engineering.py:
    - build_features を実装。研究側で算出した生ファクターを結合しユニバースフィルタを適用、Z スコア正規化（外部 zscore_normalize を使用）、±3 でクリップして features テーブルに UPSERT（日付単位で削除→挿入の冪等処理）を行う。
    - ユニバースフィルタ条件: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
    - DuckDB トランザクションを用いた日付単位の原子置換を実装。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを使用する方針。
  - src/kabusys/strategy/signal_generator.py:
    - generate_signals を実装。features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、最終スコア final_score を重み付きで算出。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。ユーザ渡しの weights は検証・正規化してマージ（未知キー・無効値は無視、合計が 1 でなければ再スケール）。
    - スコア変換にシグモイド関数を使用。欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定: ai_scores の regime_score 平均が負で、サンプル数が閾値以上である場合に BUY シグナル抑制。
    - BUY シグナル: final_score >= threshold（デフォルト 0.60）でランク付け。Bear レジーム時は BUY を抑制。
    - SELL シグナル（エグジット判定）:
      - ストップロス（終値 / avg_price - 1 < -8%）を最優先。
      - final_score が閾値未満（score_drop）。
      - 価格欠損時は SELL 判定をスキップして安全側に動作。
      - positions テーブルに関する未実装の条件（トレーリングストップ、時間決済）についてドキュメント化。
    - signals テーブルへ日付単位の置換（トランザクション）を実装。
    - ログ出力で欠損データや不正パラメータの警告を行う。

- Research パッケージのエクスポートを追加（src/kabusys/research/__init__.py）: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

### Security
- ニュースパーサ: defusedxml を使用して XML の脆弱性（XML Bomb 等）に対処。
- 外部リクエストで受信サイズ上限を設けることでメモリ DoS を軽減。
- _request で 401 時の自動トークンリフレッシュにより認証情報の安全な更新をサポート（再帰ループ回避の実装あり）。
- RSS URL の正規化でトラッキングパラメータを除去し、冪等性とプライバシーを改善。

### Notes / Migration
- 環境変数:
  - 必須項目（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は Settings のプロパティ経由で取得すること。未設定時は ValueError が発生します。
  - 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ:
  - 各モジュールは特定のテーブル（raw_prices/raw_financials/prices_daily/features/ai_scores/positions/signals/market_calendar など）を参照・更新します。運用前にスキーマ定義の整合性を確認してください。
- Look-ahead バイアス対策:
  - 取得タイムスタンプ（fetched_at）は UTC で記録し、戦略・研究モジュールは target_date 時点のデータのみを使用する設計です。

---

将来的なリリースでは以下を検討中（仕様書内に言及あり）
- Execution 層の発注 API 実装（現在 execution パッケージは空の初期化のみ）。
- signals/positions に保持する追加メタ情報（peak_price, entry_date 等）に基づくトレーリングストップや時間決済の実装。
- ニュース記事 → 銘柄紐付け処理の具体実装（news_symbols テーブルの更新など）。

以上。