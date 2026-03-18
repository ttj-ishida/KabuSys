# Changelog

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」仕様に準拠しています。

フォーマット:
- すべての変更はセマンティックバージョニングに従っています。
- 日付はリリース日を示します（yyyy-mm-dd）。

---

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基礎機能を提供します。主な追加点は以下のとおりです。

### Added
- パッケージ基礎
  - パッケージ初期化: kabusys パッケージ（src/kabusys/__init__.py）を追加。バージョン情報（0.1.0）と主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数/.env ローダー（src/kabusys/config.py）
    - プロジェクトルートを .git / pyproject.toml から探索して .env/.env.local を自動読み込み。
    - .env のパースは export 構文・クォート・インラインコメント等に対応。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - 必須設定取得用 _require() と Settings クラスを提供（J-Quants / kabu API / Slack / DB パス等をプロパティで取得）。
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）と利便性プロパティ（is_live, is_paper, is_dev）。
- データ取得/永続化（DuckDB ベース）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - 日足・財務・取引カレンダー取得機能（ページネーション対応）。
    - RateLimiter によるレート制限（120 req/min 固定スロットリング）。
    - リトライ（指数バックオフ）と 401 発生時のトークン自動リフレッシュ。
    - 取得データに fetched_at を UTC で付与して Look-ahead バイアスのトレースを可能に。
    - DuckDB への冪等保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を提供（ON CONFLICT DO UPDATE）。
    - 入力値変換ユーティリティ（_to_float, _to_int）。
  - DuckDB スキーマ定義（src/kabusys/data/schema.py）
    - raw_prices, raw_financials, raw_news, raw_executions などのテーブル定義（DDL）を追加。
    - データレイヤ（Raw / Processed / Feature / Execution）の設計に基づくスキーマ骨格。
- ニュース収集（RSS）
  - RSS ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィード取得（gzip対応）、XML パース（defusedxml）と前処理、記事ID生成（正規化 URL の SHA-256 先頭32文字）。
    - URL 正規化（tracking params 除去、ソート、スキーム小文字化、フラグメント除去）。
    - SSRF 対策: リクエスト前のホスト検査、リダイレクト時の検査用ハンドラ、許可スキームは http/https のみ。
    - 受信サイズ上限（MAX_RESPONSE_BYTES＝10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - raw_news への冪等保存（INSERT ... ON CONFLICT DO NOTHING RETURNING id）および news_symbols への紐付けをバルクチャンク単位で実行。
    - 銘柄コード抽出ユーティリティ（4桁数値パターンと既知コードセットによるフィルタリング）。
    - run_news_collection による複数ソースの統合収集ジョブ。
- リサーチ / ファクター系
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（calc_forward_returns）: DuckDB の prices_daily を参照して複数ホライズン（デフォルト 1,5,21）を同時取得。
    - IC（Information Coefficient）計算（calc_ic）: Spearman（ランク相関）を実装、欠損＆同値処理、最小有効サンプル数判定。
    - ランク変換ユーティリティ（rank）: 同順位は平均ランク、丸め誤差対策に round(..., 12) を使用。
    - ファクター統計サマリー（factor_summary）: count/mean/std/min/max/median を計算（None 値除外）。
    - 設計方針として DuckDB の prices_daily のみ参照、外部 API 不使用、標準ライブラリのみで実装。
  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタム（calc_momentum）: mom_1m/mom_3m/mom_6m と 200日移動平均乖離率（ma200_dev）を計算。データ不足時は None を返す。
    - ボラティリティ/流動性（calc_volatility）: 20日 ATR、ATR/price（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。true_range の NULL 伝播を正しく扱う。
    - バリュー（calc_value）: raw_financials の最新財務レコードと当日の価格を結合して PER / ROE を算出（EPSが0/欠損時は None）。PBR/配当は未実装。
    - DuckDB の prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない設計。
  - research パッケージ初期エクスポート（src/kabusys/research/__init__.py）: 主要関数を __all__ で公開。
- その他ユーティリティ
  - data.stats の zscore_normalize を research パッケージから再エクスポート（参照での利用を想定）。

### Changed
- 設計ノート／安全性重視の実装方針を各モジュールに明記（Look-ahead 防止・SSRF 対策・受信サイズ制限・トランザクション単位の DB 操作など）。これは実装上の意図記述であり利用者向けの注意喚起を兼ねる。

### Fixed
- （初版のため特定の「修正」はなし。実装時点での堅牢化処理多数を含む。）

### Security
- RSS 処理において defusedxml を使用して XML 攻撃を軽減。
- RSS クライアントにおける SSRF 対策:
  - リクエスト前のホストチェック（プライベート / ループバック除外）。
  - リダイレクト時に新URLのスキームとホストを検証するカスタムハンドラを使用。
  - 許可スキームは http/https のみ。
- API クライアント側で認証トークンのリフレッシュ基盤を実装し、意図しない再帰を避ける設計（allow_refresh フラグ、キャッシュ管理）。
- ネットワーク/HTTP リトライで 429 の Retry-After ヘッダを尊重。

### Notes / Migration
- .env 自動読み込みを行うため、パッケージ配布後も .env をプロジェクトルートに配置すれば自動的に読み込まれます。自動ロードを無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト用途想定）。
- DuckDB のテーブルスキーマは初期DDLが定義されています。既存DB がある場合はスキーマ互換に注意してください。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指していますが、大規模データ処理を行う場合は性能評価・最適化が必要です。

---

（今後のリリースでは機能追加・API 互換性・バグ修正・セキュリティフィックス等を明示します）