CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。本プロジェクトは "Keep a Changelog" の形式に準拠しています。
バージョニングは SemVer を採用します。

フォーマット:
- Added: 新機能
- Changed: 変更
- Deprecated: 非推奨
- Removed: 削除
- Fixed: 修正
- Security: セキュリティ関連

Unreleased
----------

（未リリースの変更はここに記載）

[0.1.0] - 2026-03-18
-------------------

Added
- 初回リリース (0.1.0)
  - パッケージ概要: 日本株自動売買システムのコアモジュール群を提供（kabusys パッケージ、src/kabusys）
  - パッケージメタ: __version__ = "0.1.0", 公開 API として data, strategy, execution, monitoring を __all__ に定義（src/kabusys/__init__.py）。

- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード実装。
  - プロジェクトルートの検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない自動ロード。
  - .env のパース機能を独自実装（export プレフィックス、引用符付き値のエスケープ、インラインコメント処理などに対応）。
  - ロード優先順位: OS環境変数 > .env.local > .env。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを提供: J-Quants / kabu ステーション / Slack / DB パス / 環境（development/paper_trading/live）/ログレベルの取得と検証（不正値で ValueError）。

- データ収集クライアント（J-Quants）（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装:
    - レート制限（120 req/min）を固定間隔スロットリングで守る RateLimiter 実装。
    - 再試行戦略（指数バックオフ、最大 3 回）と HTTP ステータスコードによるリトライ判定（408/429/5xx）。
    - 401 Unauthorized を検出した場合の ID トークン自動リフレッシュ（1 回のみ）とトークンキャッシュ。
    - ページネーション対応 fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（save_daily_quotes / save_financial_statements / save_market_calendar）。ON CONFLICT による重複更新。
    - 型変換ユーティリティ (_to_float / _to_int) により外部データの検証・正規化を実施。
  - Look-ahead bias 対策として fetched_at を UTC タイムスタンプで記録。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集して DuckDB の raw_news / news_symbols に保存する機能。
  - 安全対策:
    - defusedxml による XML パースで XML Bomb 等に対処。
    - SSRF 対策: リダイレクト先のスキーム検証、ホストがプライベートアドレスかの判定（直接 IP と DNS 解決の両方）を実施。
    - リクエスト受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後のサイズチェック。
    - 許可スキームは http/https のみ。
  - URL 正規化とトラッキングパラメータ除去（utm_* 等）により記事ID を SHA-256 の先頭 32 文字で生成して冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）と pubDate の堅牢なパース。パース失敗時は現在時刻で代替し NOT NULL 制約に対応。
  - DB 保存:
    - save_raw_news はチャンク化して INSERT ... ON CONFLICT DO NOTHING + RETURNING id で新規挿入 ID を返す（トランザクション内で実行）。
    - save_news_symbols / _save_news_symbols_bulk により (news_id, code) の紐付けを効率的に保存（重複排除、チャンク挿入）。
  - 銘柄コード抽出機能（4桁数字パターン）と run_news_collection による統合ジョブ。既知銘柄セット（known_codes）を受け取り紐付けを行う。

- リサーチ / ファクター計算（src/kabusys/research/）
  - feature_exploration.py:
    - calc_forward_returns: 指定日から将来リターン（例: 1/5/21 日）を DuckDB の prices_daily テーブルから一度のクエリで取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。無効レコードや ties を扱う実装。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）計算。
    - 主要設計: pandas 等に依存せず標準ライブラリのみで実装。
  - factor_research.py:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を prices_daily から計算。データ不足時は None。
    - calc_volatility: 20日 ATR（true_range の平均）、atr_pct、avg_turnover、volume_ratio を計算。NULL 伝播やカウントによる有効判定を実施。
    - calc_value: raw_financials から target_date 以前の最新財務データを取得し PER / ROE を計算（EPS が 0/欠損なら PER は None）。
    - DuckDB のウィンドウ関数を活用した SQL ベースの計算で高パフォーマンスを想定。

- スキーマ定義（src/kabusys/data/schema.py）
  - DuckDB 用のテーブル定義（Raw レイヤーの DDL を含む）。少なくとも raw_prices / raw_financials / raw_news / raw_executions（スニペットに続きあり）を定義する設計。
  - テーブル定義には型チェック（CHECK）や PRIMARY KEY を含め、データ整合性を重視。

Security
- news_collector と jquants_client において外部入力・通信に対する安全対策を組み込んでいる点を明記:
  - RSS: defusedxml、SSRF 対策、受信サイズ制限、スキーム検証。
  - J-Quants: トークン管理、再試行/バックオフ、レート制限により API 制限や認証の失敗を安全に扱う。

Notes / Breaking changes
- 本バージョンは初回リリースのため互換性の過去バージョンは存在しません。
- Settings の必須環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）を設定していない場合、Settings プロパティは ValueError を送出します。デプロイ時は .env を用意してください（.env.example を参照する想定）。
- research モジュールは外部ライブラリ（pandas 等）に依存しないため、既存の pandas ベースのワークフローとは直接互換性がありません。DuckDB 接続を渡す API を採用しています。

依存関係（実装上想定）
- duckdb
- defusedxml
- 標準ライブラリの urllib, datetime, logging 等

今後の予定（例）
- Execution 層の発注ロジックと kabu ステーション連携の実装（execution パッケージの充実）
- Feature レイヤーの追加、機械学習用前処理ユーティリティの強化
- 単体テスト・統合テストの追加（ネットワーク IO を持つコードのモック化）

署名
- 作成日: 2026-03-18
- バージョン: 0.1.0

もし特定の変更点をより詳しく追記してほしい（例: 個々の関数の挙動や SQL 定義の完全一覧、リリースノート英語版など）、指示をください。