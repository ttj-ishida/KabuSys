# Changelog

すべての重要な変更をこのファイルに記録します。本ファイルは「Keep a Changelog」の形式に準拠します。現在のバージョンは 0.1.0 です。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（未リリースの変更はここに記載）

---

## [0.1.0] - 2026-03-18

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。主な追加点と設計方針は以下の通りです。

### Added
- パッケージの基本情報
  - パッケージ名とバージョンを定義（kabusys.__version__ = "0.1.0"）。
  - 公開モジュール一覧 (__all__) を定義。

- 環境変数 / 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD に依存しない自動読み込み。
  - .env の読み込み優先順位：OS 環境変数 > .env.local > .env。
  - 自動読み込みを無効化するフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - 環境変数パーサの実装（コメント / export キーワード / クォート・エスケープの取り扱い）。
  - 必須設定を要求するヘルパー _require() と Settings クラス:
    - J-Quants: JQUANTS_REFRESH_TOKEN
    - kabuステーション: KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト値あり）
    - Slack: SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パス: DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - 実行環境 env 判定（development / paper_trading / live）とログレベル検証

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（価格・財務・マーケットカレンダーの取得）。
  - レート制御（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
  - リトライ戦略（指数バックオフ、最大 3 回、HTTP 408/429/5xx のリトライ）。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルのトークンキャッシュ。
  - ページネーション対応（pagination_key を使用して全件取得）。
  - DuckDB への保存用ユーティリティ（raw_prices, raw_financials, market_calendar）:
    - fetched_at を UTC ISO フォーマットで記録（Look-ahead bias 対策）
    - 挿入は冪等（ON CONFLICT DO UPDATE）で実装
    - 型変換ユーティリティ (_to_float / _to_int) により入力値の寛容なパースを実現

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集と前処理パイプラインを実装（デフォルトに Yahoo Finance のビジネス RSS を含む）。
  - セキュリティ対策:
    - defusedxml による安全な XML パース（XML Bomb などに対処）
    - SSRF 対策（許可スキームは http/https のみ、ホストのプライベート IP 検査、リダイレクトハンドラでの検証）
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後も検査（Gzip bomb 対策）
    - トラッキングパラメータ除去（utm_* 等）と URL 正規化
  - 記事 ID を URL 正規化 → SHA-256 の先頭 32 文字で生成し冪等性を確保
  - テキスト前処理（URL 除去、空白正規化）
  - raw_news テーブルへのバルク挿入（チャンク処理、INSERT ... RETURNING を使用して実際に挿入された ID を取得）
  - news_symbols（記事と銘柄コードの紐付け）機能と一括挿入ユーティリティ（重複排除、トランザクション管理）
  - 銘柄コード抽出ロジック（4桁数値を抽出し known_codes と照合）

- DuckDB スキーマ定義（kabusys.data.schema）
  - Raw レイヤ（raw_prices, raw_financials, raw_news, raw_executions のスキーマの一部）を定義する DDL を追加
  - スキーマ初期化用モジュールの骨組みを提供

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - モメンタム（mom_1m, mom_3m, mom_6m, ma200_dev）
    - ボラティリティ / 流動性（atr_20, atr_pct, avg_turnover, volume_ratio）
    - バリュー（per, roe、raw_financials の最新レコードを結合）
    - 各ファクターは prices_daily / raw_financials のみ参照し、本番 API には接続しない設計
    - 一連の計算は DuckDB のウィンドウ関数を活用して効率化
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算（calc_forward_returns、複数ホライズンを同一クエリで取得）
    - IC（Information Coefficient）計算（Spearman のランク相関 calc_ic）
    - ランク化ユーティリティ（rank、同順位の平均ランク処理、丸めで ties 検出を安定化）
    - ファクター統計サマリー（count, mean, std, min, max, median を計算）
    - 「標準ライブラリのみ」による実装方針（外部依存を避ける）

- モジュール間のエクスポート整備
  - kabusys.research.__init__ から主要ユーティリティを再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize など）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector における SSRF 対策、XML パースの安全化、受信サイズ制限などを導入。
- J-Quants クライアントでのトークン管理と 401 リフレッシュ処理により認証周りの堅牢性を向上。

### Known issues / Notes / Future work
- execution / strategy / monitoring モジュールの実装は最小限または空の初期状態となっており、発注ロジックやモニタリング周りの実装は今後追加予定。
- schema.py に raw_executions の DDL が途中まで（提供コードの断片）であるため、Execution レイヤの完全なスキーマ定義は継続して作業が必要。
- research モジュールは外部ライブラリ（pandas 等）に依存しない設計だが、大規模データ処理や高度な統計解析では性能や利便性の観点から検討の余地あり。
- テストカバレッジやエンドツーエンドでの統合テストは今後整備が必要。

---

バージョニングは semver を想定しています。重大な変更（後方互換を壊す変更）がある場合はメジャー番号を更新してください。