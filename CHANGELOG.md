# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠します。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-18
初回公開リリース。

### Added
- パッケージ構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0（src/kabusys/__init__.py にて定義）
  - 公開モジュール: data, strategy, execution, monitoring（__all__）

- 設定 / 環境変数処理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを提供。
  - 自動ロードの対象はプロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーはコメント、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - .env 読み込み時の上書き制御（override）と保護キー（protected）をサポートし、OS 環境変数を保護。
  - 必須設定を取得する _require 関数（未設定時は ValueError）。
  - サポートされる環境: development, paper_trading, live。LOG_LEVEL の検証ロジックを提供。
  - 設定プロパティ（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH など）。

- Data レイヤー（src/kabusys/data/*）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制限（120 req/min）を守る固定間隔スロットリング _RateLimiter を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回。HTTP 408/429/5xx やネットワークエラーをリトライ対象）。
    - 401 Unauthorized 受信時にはリフレッシュトークンでトークンを更新して 1 回リトライする仕組みを実装（無限再帰防止）。
    - ページネーション対応で fetch_daily_quotes / fetch_financial_statements を実装。
    - 市場カレンダー取得 fetch_market_calendar を実装。
    - DuckDB への保存用関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。各関数は冪等性を考慮して ON CONFLICT による更新を行う。
    - 値変換ユーティリティ _to_float / _to_int を提供（不正値に対する安全な変換を実装）。
    - 取得時刻（fetched_at）は UTC ISO8601 で記録して look-ahead bias のトレースを可能に。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードからニュース記事を取得して raw_news に保存する機能を追加。
    - セキュリティ対策:
      - defusedxml を使用した XML パース（XML Bomb 対策）。
      - リダイレクト時にスキーム検証およびプライベートアドレス判定を行う専用ハンドラ（_SSRFBlockRedirectHandler）で SSRF を防御。
      - 受信サイズ上限（MAX_RESPONSE_BYTES=10MB）や gzip 解凍後のサイズチェックを実装（メモリ DoS 対策）。
      - URL スキーム検証（http/https のみ許可）。
    - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）と記事 ID 生成（正規化 URL の SHA-256 先頭32文字）。
    - テキスト前処理（URL 除去、空白正規化）。
    - 銘柄コード抽出（4桁数値パターンを known_codes と照合）と、news_symbols テーブルへの紐付け保存（重複除去・バルク挿入）。
    - DB 保存はチャンク化・トランザクションで実行し、INSERT ... RETURNING により実際に挿入された件数/ID を正確に取得。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を定義。

  - DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
    - Raw レイヤー用 DDL 定義を用意:
      - raw_prices, raw_financials, raw_news, raw_executions（部分定義が含まれる）
    - DataSchema に基づいた 3 層（Raw / Processed / Feature / Execution）構想のための基礎を実装。

- Research / Feature 計算（src/kabusys/research/*）
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算 calc_forward_returns（horizons のサポート、DuckDB クエリでまとめて取得）。
    - Information Coefficient（IC）計算 calc_ic（Spearman の ρ 準拠。ties を考慮したランク計算）。
    - rank ユーティリティ（同順位は平均ランク。丸め誤差対策: round(v, 12) を利用）。
    - factor_summary（count, mean, std, min, max, median）を標準ライブラリのみで実装。
    - 設計方針として DuckDB の prices_daily テーブルのみを参照し外部 API にアクセスしないことを明記。

  - ファクター計算（src/kabusys/research/factor_research.py）
    - モメンタムファクター calc_momentum（mom_1m/mom_3m/mom_6m, ma200_dev）。
    - ボラティリティ・流動性ファクター calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）。
    - バリューファクター calc_value（raw_financials の最新財務データを用いて PER, ROE を計算）。
    - DuckDB SQL とウィンドウ関数を活用した実装。データ不足時は None を返す設計。
    - 研究用途に限定し、本番トレード API へはアクセスしない旨を明記。

  - research パッケージ初期エクスポート（src/kabusys/research/__init__.py）
    - calc_momentum, calc_volatility, calc_value, calc_forward_returns, calc_ic, factor_summary, rank と zscore_normalize（kabusys.data.stats 由来）を __all__ に追加。

### Changed
- （初回リリースのため変更履歴なし）

### Fixed
- （初回リリースのため修正履歴なし）

### Security
- ニュース収集での SSRF 対策、defusedxml による安全な XML パース、受信サイズチェックを実装。
- J-Quants クライアントでの認証リフレッシュ・HTTP リトライの取り扱いを安全に実装（無限再帰対策あり）。

### Notes / Limitations / TODO
- strategy/ と execution/ パッケージはパッケージとして存在しますが、今回のリリースでは具体的な戦略ロジックや発注ロジックの実装は含まれていません（ディレクトリの初期化のみ）。
- monitoring モジュールは __all__ に含まれますが、該当実装ファイルは今回の提供コードには含まれていません。
- research.__init__ は zscore_normalize を kabusys.data.stats から import していますが、その実装は本リリースの抜粋コードでは提示されていません。実態の有無に応じて後続リリースで整合性を確保してください。
- DuckDB スキーマ DDL は raw テーブルの定義を中心に含まれます。Processed / Feature / Execution 層の完全なスキーマは今後追加予定。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして使用する際は、テスト済み機能・既知の問題・互換性情報などを追記してください。