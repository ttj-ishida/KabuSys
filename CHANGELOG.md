CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-20
--------------------

Added
- 初回リリース。日本株自動売買システム "KabuSys" の基礎機能を実装。
- パッケージエントリポイント
  - パッケージバージョンを src/kabusys/__init__.py にて __version__ = "0.1.0" として定義。
  - __all__ により公開モジュールを整理（data, strategy, execution, monitoring）。
- 環境設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - 読み込み優先度: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
  - .env パーサーはコメント行／export 形式／シングル／ダブルクォート／エスケープに対応。インラインコメント処理の挙動も実装。
  - 必須環境変数取得ヘルパー (_require) と Settings クラスを提供。主な必須キー:
    - JQUANTS_REFRESH_TOKEN
    - KABU_API_PASSWORD
    - SLACK_BOT_TOKEN
    - SLACK_CHANNEL_ID
  - デフォルト設定:
    - KABUSYS_ENV の許容値は development / paper_trading / live（不正値は ValueError）
    - LOG_LEVEL の許容値は DEBUG/INFO/WARNING/ERROR/CRITICAL（不正値は ValueError）
    - データベースパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
- データ取得・保存（src/kabusys/data/）
  - J-Quants クライアント（jquants_client.py）
    - API リクエストユーティリティを実装（ページネーション対応）。
    - レート制限管理: 120 req/min を固定間隔スロットリングで守る _RateLimiter 実装。
    - リトライロジック（指数バックオフ、最大 3 回）。408/429/5xx を再試行対象に設定。
    - 401 受信時は自動でリフレッシュトークンから ID トークンを再取得して 1 回リトライ（無限再帰防止）。
    - トークンキャッシュをモジュールレベルで保持（ページネーション間共有）。
    - fetch_* 系関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
    - DuckDB へ保存する save_* 系関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。いずれも冪等性を保つ ON CONFLICT / DO UPDATE を使用。
    - 数値変換ユーティリティ _to_float / _to_int を提供し、不正値は None に変換。
    - 設計上の配慮: fetched_at を UTC ISO 形式で記録し、Look-ahead バイアスを検査可能に。
  - ニュース収集モジュール（news_collector.py）
    - RSS フィードから記事を収集し raw_news へ保存する仕組みを実装（デフォルトソース: Yahoo Finance のビジネス RSS）。
    - URL 正規化（スキーム/ホストの小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）。
    - 記事 ID の生成方針（仕様）: 正規化後の URL を SHA-256 でハッシュ化し先頭 32 文字を ID として冪等性を確保（実装設計に基づく記述）。
    - XML パースに defusedxml を利用しセキュリティ（XML Bomb 等）に配慮。
    - HTTP 応答サイズ上限（MAX_RESPONSE_BYTES = 10MB）や SSRF 対策（HTTP/HTTPS スキームの検証）を考慮した設計。
    - バルク INSERT のチャンク処理とトランザクション集約により DB 書き込み効率化。
- 研究用ファクター計算（src/kabusys/research/）
  - factor_research.py: calc_momentum, calc_volatility, calc_value を実装。
    - モメンタム: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均に対する乖離）を計算。必要なデータが不足する場合は None。
    - ボラティリティ: 20 日 ATR（atr_20）, 相対 ATR（atr_pct）, 20 日平均売買代金（avg_turnover）, 出来高比（volume_ratio）を計算。true_range の NULL 伝播処理に注意。
    - バリュー: raw_financials から最新の財務（report_date <= target_date）を取得し PER/EPS/ROE を算出。EPS が 0/欠損の場合は per=None。
    - DuckDB のウィンドウ関数を活用して効率よく計算。
  - feature_exploration.py:
    - 将来リターン calc_forward_returns（複数ホライズン対応、データ不足なら None）。
    - ランク相関（Spearman）の IC 計算 calc_ic（有効サンプル < 3 の場合は None）。
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクで処理（丸めを用いて ties の検出漏れを低減）。
  - research パッケージは外部ライブラリ（pandas 等）に依存せず、DuckDB 接続を受ける設計。
- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date) を実装。
    - research モジュールの calc_* を呼び出して生ファクターを取得。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20 日平均売買代金 _MIN_TURNOVER=5e8 円）を適用。
    - 指定カラムを zscore_normalize（data.stats 由来）で標準化し ±3 (_ZSCORE_CLIP) でクリップ。
    - 日付単位で features テーブルに置換（DELETE → INSERT）のトランザクション処理で冪等・原子性を保証。
    - 設計方針: ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用。execution 層に依存しない。
- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装。
    - features と ai_scores を統合し、複数のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算して final_score を算出。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。重みは与えられた辞書で上書き可能。合計が 1.0 でない場合は正規化。
    - シグモイド変換・None の中立補完（0.5）による堅牢なスコアリング。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合）を行い、Bear 時は BUY シグナルを抑制。
    - BUY シグナル閾値のデフォルト _DEFAULT_THRESHOLD = 0.60。
    - SELL シグナル（エグジット）判定:
      - ストップロス: 終値 / avg_price - 1 < -0.08（-8%）
      - スコア低下: final_score < threshold
    - 未実装のエグジット条件を明記（トレーリングストップ、時間決済は positions に peak_price / entry_date 等が必要）。
    - signals テーブルへの日付単位置換（トランザクション）で冪等性を確保。
- strategy パッケージは build_features / generate_signals を公開 API としてエクスポート。

Security / Reliability / Logging
- 各所でログ出力（logger）を設置。重要な失敗時には警告ログ・例外で通知。
- 外部データ取り込みは入力検証・欠損スキップを実施し、整合性を保つ設計。
- DB 操作は明示的なトランザクション（BEGIN/COMMIT/ROLLBACK）で行い、エラー時にロールバックを試行。ロールバック失敗時は警告ログを出力。

Known issues / Unimplemented
- signal_generator._generate_sell_signals に記載の通り、以下は未実装:
  - トレーリングストップ（peak_price に基づく運用）
  - 時間決済（保有 60 営業日超過 等）
- news_collector 内の一部仕様（例: 実際の SHA-256 ハッシュ生成箇所や DB スキーマ依存処理）はドキュメントに設計方針を記載しているが、外部条件に依存するため運用時に追加の調整が必要な場合がある。
- 外部 API（J-Quants）とのやり取りに関してはネットワーク・認証要素が存在するため、実運用前に環境変数とアクセス権の事前準備が必要。

開発者向けメモ
- 主要な公開関数:
  - research: calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize（data.stats）
  - strategy: build_features, generate_signals
  - data.jquants_client: fetch_*/save_* 系
- 設定・環境変数の自動ロードをスキップしたいテスト等では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用する。

ライセンス・その他
- 本リリースは内部実装の初期段階（v0.1.0）です。API・関数シグネチャの安定化は今後のリリースで行います。