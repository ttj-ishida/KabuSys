# Changelog

すべての重要な変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトの初回リリースを示すエントリを含みます。

## [Unreleased]

## [0.1.0] - 2026-03-18
初回リリース

### Added
- パッケージ基盤
  - パッケージ名を kabusys として公開（src/kabusys/__init__.py、__version__ = "0.1.0"）。
  - パブリック API として data, strategy, execution, monitoring を __all__ に定義。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルや環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動ロード（CWD 非依存）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装（export プレフィックス対応、クォート内エスケープ、行内コメント処理など）。
  - .env の読み込みで既存 OS 環境変数を保護する protected 機能、override フラグ対応。
  - Settings クラスを提供し、各種必須設定値をプロパティ経由で取得（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）。
  - 環境（KABUSYS_ENV）のバリデーション（development/paper_trading/live）とログレベル検証を実装。

- データ取得 / 保存 (src/kabusys/data/jquants_client.py)
  - J-Quants API クライアントを実装。
    - 固定間隔スロットリングによるレート制御（120 req/min）。
    - リトライロジック（指数バックオフ、最大 3 回。408/429/5xx を再試行対象）。
    - 401 レスポンス時はトークンを自動リフレッシュして 1 回のみ再試行。
    - ページネーション対応の fetch_* 関数（daily_quotes, financial_statements, market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices, raw_financials, market_calendar）を実装（ON CONFLICT DO UPDATE）。
    - 取得時刻（fetched_at）を UTC ISO8601 で記録し Look-ahead バイアスの追跡を可能に。
  - 型変換ユーティリティ _to_float / _to_int を実装し、入力の多様性に耐える堅牢な変換を提供。

- ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィード収集モジュールを実装。
    - defusedxml を使った安全な XML パース。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェック、gzip 解凍後も検査（Gzip-bomb 対策）。
    - URL 正規化・トラッキングパラメータ除去（utm_* 等）、SHA-256（先頭32文字）による記事ID生成で冪等性を担保。
    - SSRF 対策：URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルかの判定、リダイレクト時の事前検証ハンドラ実装。
    - RSS から抽出した記事を raw_news テーブルへチャンク挿入、INSERT ... RETURNING を使って実際に挿入された記事IDを返す。
    - 記事と銘柄コードを紐付ける news_symbols 保存機能（重複排除、チャンク挿入、トランザクション管理）。
    - テキスト前処理（URL 除去、空白正規化）および日本株銘柄コード抽出（4桁数字、既知コードセットによるフィルタリング）。
    - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを追加。

- DuckDB スキーマ (src/kabusys/data/schema.py)
  - Raw Layer の DDL 定義を追加（raw_prices, raw_financials, raw_news, raw_executions のスケルトン等）。
  - DataLayer の初期化のための基礎を提供（DDL をモジュール内で管理）。

- リサーチ（特徴量 / ファクター計算）(src/kabusys/research/)
  - feature_exploration.py
    - calc_forward_returns: ある基準日から指定ホライズン（営業日）後の将来リターンを DuckDB 上の prices_daily テーブルから一括取得。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。小さいサンプルや同順位（ties）を考慮。
    - factor_summary / rank: 基本統計量と同順位平均ランクを標準ライブラリのみで実装。
    - 設計方針として pandas 等の外部ライブラリに依存しない実装を採用。
  - factor_research.py
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算（ウィンドウ制御、必要行数チェック）。
    - calc_volatility: 20日 ATR、相対ATR(atr_pct)、20日平均売買代金、当日出来高比率を計算（true range の NULL 伝播制御等）。
    - calc_value: raw_financials の最新財務データと当日の株価を組み合わせて PER/ROE を計算（最新報告日以前の最新レコードを取得）。
  - research パッケージの __init__ で主要ユーティリティを再エクスポート（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

### Changed
- 設定のデフォルト値とバリデーションを明示化
  - KABU_API_BASE_URL の既定値は "http://localhost:18080/kabusapi"。
  - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
  - LOG_LEVEL と KABUSYS_ENV の許容値を厳格に検証し、無効値は ValueError を送出。

### Security
- ニュース収集における SSRF 対策を強化
  - URL スキーム検証（http/https のみ）、ホストのプライベートアドレス検出、リダイレクト時の検証ハンドラを導入。
  - defusedxml を利用して XML 関連の潜在的攻撃（XML Bomb 等）を軽減。
  - レスポンスサイズ制限および gzip 解凍後の再検査によりメモリ DoS を防止。
- 環境変数読み込み時に OS 環境変数を保護（override/protected 機能）し、テストや CI での誤上書きを防止。

### Internal / Documentation
- 各モジュールに詳細なドキュメンテーション文字列を追加し、設計方針・参照テーブル・副作用（DB 書き込み等）を明記。
- DuckDB を前提とする設計（prices_daily / raw_financials / raw_prices 等）を明示。
- J-Quants クライアントに関する運用要件（レートリミット、リトライ、トークンリフレッシュ、fetched_at のUTC記録）をコード内で明文化。

### Fixed
- 該当なし（初回リリース）。

---

注: 上記はソースコードの実装内容から推測して作成した CHANGELOG です。実際のリリースノート作成時はコミット履歴や実際の変更差分を基に調整してください。