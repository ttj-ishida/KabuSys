# Changelog

すべての変更は Keep a Changelog の規約に準拠しています。  
現在のバージョン: 0.1.0

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基盤機能を提供します。主要な追加点は以下の通りです。

### Added
- パッケージ初期化
  - pakage `kabusys` を追加。バージョンは `0.1.0`。公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート（src/kabusys/__init__.py）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を起点に自動でプロジェクトルートを探索。
  - .env ファイルの堅牢なパーサ実装（コメント、export プレフィックス、クォート・エスケープ、インラインコメント等に対応）。
  - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用途）。
  - 設定ラッパー `Settings` を導入。以下の設定プロパティを提供:
    - J-Quants: `jquants_refresh_token`
    - kabuステーション API: `kabu_api_password`, `kabu_api_base_url`
    - Slack: `slack_bot_token`, `slack_channel_id`
    - データベースパス: `duckdb_path`, `sqlite_path`
    - 環境判定・ログレベル: `env`, `log_level`, `is_live`, `is_paper`, `is_dev`
  - `env` / `log_level` の値検証（許容値外は ValueError）。

- データクライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（OHLCV / 財務 / マーケットカレンダーの取得）。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を内部 RateLimiter で実装。
  - リトライロジック: 指数バックオフ、最大リトライ回数、対象ステータス（408, 429, 5xx）に対応。
  - 401 Unauthorized 時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ（モジュールレベル）。
  - ページネーション対応の fetch 関数（fetch_daily_quotes, fetch_financial_statements）。
  - DuckDB へ冪等に保存する save_* 関数:
    - save_daily_quotes: raw_prices テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - save_financial_statements: raw_financials テーブルへ INSERT ... ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ INSERT ... ON CONFLICT DO UPDATE
  - データ取得時点を UTC で記録する `fetched_at` を付与（Look-ahead bias トレース）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュースを取得し raw_news / news_symbols に保存する機能を実装。
  - セキュリティおよび堅牢性のための対策を多数導入:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証（http/https のみ許可）、リダイレクト先のスキーム/ホスト検査、プライベート IP の検出拒否。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_* 等）を除去して URL 正規化、SHA-256（先頭32文字）で記事 ID を生成し冪等性を保証。
    - テキスト前処理（URL 除去・空白正規化）。
    - DB 保存はチャンク化とトランザクションで実施。INSERT ... ON CONFLICT DO NOTHING と RETURNING を利用し、実際に挿入された ID / 件数を正確に取得。
    - 銘柄コード抽出機能（4桁数字）と既知コードセットによるフィルタリング。
  - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを登録（DEFAULT_RSS_SOURCES）。

- リサーチモジュール（src/kabusys/research/*）
  - 特徴量探索: calc_forward_returns, calc_ic, factor_summary, rank（src/kabusys/research/feature_exploration.py）。
    - 将来リターンを一括 SQL で高速取得。horizons の検証と最大ホライズンに基づくスキャン範囲制限。
    - Spearman ランク相関（IC）計算。ties を平均ランクで扱う rank 実装あり。
    - ファクターの基本統計量計算（count, mean, std, min, max, median）。
    - 標準ライブラリのみでの実装（外部依存なし）。
  - ファクター計算: calc_momentum, calc_volatility, calc_value（src/kabusys/research/factor_research.py）。
    - Momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）。データ不足時は None を返す設計。
    - Volatility / Liquidity: 20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）。true_range の NULL 伝播を厳密に扱い、必要行数未満で None を返す。
    - Value: raw_financials から最新財務データを取得し PER（EPS が有効な場合）および ROE を計算。target_date 以前の最新レコードを ROW_NUMBER を用いて取得。
    - DuckDB 上の prices_daily / raw_financials テーブルのみ参照。外部 API へアクセスしない設計。
  - リサーチの公開 API を package-level でエクスポート（src/kabusys/research/__init__.py）。

- データスキーマ（src/kabusys/data/schema.py）
  - DuckDB 用スキーマ（Raw / Processed / Feature / Execution 層）を定義するDDL を追加。初期 Raw テーブル定義を含む（raw_prices, raw_financials, raw_news, raw_executions 等）。
  - 型安全チェック（CHECK 制約）や PRIMARY KEY 指定を含むDDL。

- パフォーマンス・使い勝手
  - API クライアントのレート制御とページネーションで安定性向上。
  - DB 書き込みはバルク／チャンク化してオーバーヘッドを低減。
  - トランザクション周りは失敗時にロールバックするよう実装。

### Fixed
- 初期リリースのため該当なし。

### Security
- news_collector:
  - defusedxml による安全な XML パース（XML 攻撃対策）。
  - SSRF 緩和: リダイレクト前検査、プライベート IP 判定、許可スキーム制限。
  - レスポンスサイズ・gzip 解凍後サイズチェック（DoS/Bomb 対策）。
- jquants_client:
  - トークン自動リフレッシュ手順により、認証失敗時の安全な再認証を提供（無限再帰回避も実装）。

### Notes / Migration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須として取得されます。未設定時は ValueError が発生します。
- 自動 .env ロードはデフォルトで有効。テストや特殊環境で無効化する場合は環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください。
- DuckDB スキーマは初期DDLが含まれますが、環境や運用に応じてマイグレーションや追加テーブルの定義が必要になる場合があります。

### Known limitations / Future work
- strategy/, execution/, monitoring/ パッケージはエントリポイントとして存在するが、具象実装はこれから（空の __init__）。戦略の実装や発注ロジックは今後の課題。
- データスキーマファイルは初期DDLを含むが、一部のテーブル定義・制約の微調整やインデックス最適化は今後改善予定。
- research モジュールは pandas 等に依存しない実装だが、大規模データ処理の際は最適化（メモリ/IO）を検討。

---
メジャー・マイナーリリースに関する方針、バージョニングやリリースノートの詳細はプロジェクトドキュメントに従ってください。