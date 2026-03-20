# CHANGELOG

すべての注目すべき変更はここに記録します。フォーマットは「Keep a Changelog」に準拠します。

## [Unreleased]

## [0.1.0] - 2026-03-20

### Added
- パッケージ初版リリース (kabusys v0.1.0)。
- 基本パッケージ構成を追加:
  - kabusys.__init__ にバージョン情報と公開モジュール一覧を定義。
- 環境設定管理 (kabusys.config):
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を起点に探索。
  - 詳細な .env パーサ実装（コメント・export プレフィックス・クォート・エスケープ対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境名（development|paper_trading|live）などのプロパティを型付で取得可能に。
- データ収集・保存 (kabusys.data):
  - J-Quants クライアント (jquants_client) を実装:
    - API 呼び出しの固定間隔レートリミッタ（120 req/min）。
    - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。
    - 401 受信時の自動トークンリフレッシュを実装（リフレッシュは 1 回のみ）。
    - ページネーション対応の fetch_* 関数（株価・財務・マーケットカレンダー）。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices, raw_financials, market_calendar）を実装。
    - 型安全な数値変換ユーティリティ (_to_float / _to_int) を実装。
  - ニュース収集モジュール (news_collector) を実装:
    - RSS フィード取得、記事正規化、トラッキングパラメータ除去、SHA-256 による記事 ID 生成、raw_news への冪等保存（ON CONFLICT）を実装。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。
    - レスポンスサイズ上限、バルク挿入チャンク、URL/空白処理などを実装。
- 研究用ユーティリティ (kabusys.research):
  - ファクター計算モジュール (factor_research):
    - Momentum / Volatility / Value / Liquidity の主要指標計算を実装（prices_daily / raw_financials を参照）。
    - 200日移動平均・ATR・出来高比率等を算出。
  - 特徴量探索 (feature_exploration):
    - 将来リターン計算（複数ホライズン対応: デフォルト [1,5,21]）を実装。
    - IC（Information Coefficient、Spearman の ρ）計算、ランク変換ユーティリティ、ファクター統計サマリを実装。
  - zscore_normalize を kabusys.data.stats からエクスポート（研究向け正規化ユーティリティとの統合）。
- 戦略層 (kabusys.strategy):
  - 特徴量エンジニアリング (feature_engineering):
    - research モジュールで算出した生ファクターをマージ、ユニバースフィルタ（最低株価・平均売買代金）、Zスコア正規化、±3クリップ、features テーブルへの日付単位 UPSERT を実装。
    - DuckDB トランザクションで日付単位の置換（冪等）を保証。
  - シグナル生成 (signal_generator):
    - features と ai_scores を統合し、複数コンポーネント（momentum / value / volatility / liquidity / news）を重み付けして final_score を計算。
    - 重みのバリデーションとスケーリング、デフォルト重みを定義。
    - Bear レジーム判定（ai_scores の regime_score を平均して負なら Bear）と Bear 時の BUY 抑制。
    - BUY シグナル閾値、SELL（エグジット）条件（ストップロス / スコア低下）を実装。
    - signals テーブルへ日付単位で置換（トランザクション）して書き込み。
- 監視・実行層（パッケージ構成）:
  - execution / monitoring 用の名前空間を公開（将来的な拡張用のエントリポイントを確保）。

### Changed
- 仕様・設計に関する方針を明文化:
  - ルックアヘッドバイアス防止のため、target_date 時点のデータのみを使用する設計を徹底。
  - DuckDB への挿入はトランザクション＋バルク挿入で原子性を確保。
  - research モジュールは外部依存（pandas 等）を使わず標準ライブラリ＋DuckDB で完結する方針。
- ロギングを強化し、重要な操作（ROLLBACK 失敗・価格欠損・無効な重みなど）で警告/情報を出力するようにした。

### Fixed
- データ欠損・異常値への堅牢化:
  - .env パースや数値変換での不正データ（空文字列・非数値など）を安全に扱う。
  - prices や financials の欠損により不正な計算が行われないよう各関数で None チェック・finite チェックを徹底。
  - シグナル生成時、features に存在しない保有銘柄は final_score=0.0 扱いとし、価格が欠損しているケースは SELL 判定処理をスキップして誤クローズを防止。

### Security
- news_collector:
  - defusedxml を用いた XML パースで XML Bomb 等の攻撃を軽減。
  - URL 正規化でトラッキングパラメータ除去、HTTP/HTTPS スキームの検証、SSRF を意識した検査方針（注: 実装の一部は説明に記載、追加検査は今後の強化点）。
  - 受信サイズ上限（MAX_RESPONSE_BYTES）を導入してメモリ DoS を緩和。
- jquants_client:
  - トークンをモジュール内にキャッシュし、401 時は安全にリフレッシュすることで認証ループや不要な再試行を防止。
  - API レート制御とリトライポリシーにより外部 API への過負荷を回避。

### Notes / Known limitations
- 一部のエグジット条件（トレーリングストップ、時間決済）は positions テーブルの拡張（peak_price / entry_date 等）が必要で、現状では未実装。
- news_collector の完全な SSRF/ホストチェックや HTTPS 証明書検証などは将来的な強化対象。
- execution モジュールは現時点で実装がないため、signals から実際に発注する処理は別実装が必要。

---

（参考）公開 API の主なエントリ:
- kabusys.config.settings（Settings クラスのプロパティ）
- kabusys.data.jquants_client.fetch_* / save_*（データ取得・保存）
- kabusys.data.news_collector（RSS 取得・保存ロジック）
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.strategy.build_features / generate_signals

README・ドキュメントに記載の想定仕様（StrategyModel.md / DataPlatform.md 等）に従って実装されています。