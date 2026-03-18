# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
Semantic Versioning を採用しています。  

## [0.1.0] - 2026-03-18

初回公開リリース。以下の主要機能・実装を含みます。

### Added
- パッケージ基盤
  - パッケージエントリポイントを追加（src/kabusys/__init__.py）。バージョン情報を含む。
  - 空のサブパッケージ初期化ファイルを追加（src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py）。

- 設定管理
  - 環境変数・.env 管理モジュールを実装（src/kabusys/config.py）。
    - .env / .env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み（自動ロード無効化用に KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数を用意）。
    - .env のパースは export プレフィックス、クォート付き値、コメント（#）の扱い、エスケープシーケンスに対応。
    - OS 環境変数を保護するための protected キーと override オプションをサポート。
    - 必須変数チェック（_require）といくつかの検証（KABUSYS_ENV, LOG_LEVEL）を実装。
    - 設定アクセサ（Settings）で J-Quants トークンや Slack、DB パスなどを公開（例: jquants_refresh_token, duckdb_path, sqlite_path）。

- データ取得・保存（J-Quants）
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - API レート制限（120 req/min）を守る固定間隔レートリミッタを実装。
    - 再試行（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx を対象。
    - 401 Unauthorized を検出するとリフレッシュトークンで id_token を自動更新して再試行（1 回のみ）。
    - ページネーション対応の fetch_* 関数群を提供: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数を提供: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT を用いた upsert）。
    - レスポンスパース・型変換用ユーティリティを実装 (_to_float, _to_int)。
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead バイアス防止を意識。

- ニュース収集（RSS）
  - RSS ニュース収集モジュールを実装（src/kabusys/data/news_collector.py）。
    - RSS フィードの取得、記事前処理、ID 生成、DuckDB への冪等保存を行う。
    - 記事ID は URL 正規化後の SHA-256 (先頭32文字) を使用し冪等性を確保。
    - URL 正規化で utm_* 等のトラッキングパラメータを除去し、クエリをソート、スキーム/フラグメント除去を行う。
    - defusedxml を用いた XML パースで安全性を向上（XML Bomb 等を回避）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクトハンドラでリダイレクト先のスキーム・プライベートアドレス検査を実施。
      - 初回 URL と最終 URL の両方を検査し、プライベート IP へのアクセスを禁止。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の再チェックを実装（DoS 対策）。
    - コンテンツの前処理（URL 除去、空白正規化）を提供。
    - raw_news テーブルへのバルク INSERT をチャンク化してトランザクションで行い、INSERT ... RETURNING を使って実際に挿入された ID を返す。
    - 記事と銘柄の紐付け機能（extract_stock_codes, save_news_symbols, _save_news_symbols_bulk, run_news_collection）を提供。銘柄抽出は 4 桁数字と known_codes に基づく。

- データ処理・ファクター計算（Research）
  - 研究用ユーティリティとファクター計算を実装（src/kabusys/research/*）。
    - feature_exploration: calc_forward_returns（複数ホライズン対応、1/5/21 デフォルト）、calc_ic（スピアマンランク相関）、factor_summary（count/mean/std/min/max/median）、rank（同順位は平均ランク、丸め防止に round(v,12) を使用）。
    - factor_research: calc_momentum（mom_1m/3m/6m、ma200_dev）、calc_volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、calc_value（per, roe を raw_financials と prices_daily から計算）。
    - research パッケージ __init__ で主要関数をエクスポート（zscore_normalize は data.stats からインポート）。

- DB スキーマ
  - DuckDB 用スキーマ定義モジュールを実装（src/kabusys/data/schema.py）。
    - Raw レイヤーのテーブル DDL を追加（raw_prices, raw_financials, raw_news, raw_executions（途中定義））。
    - 将来的なレイヤー（Processed / Feature / Execution）構想に合わせたコメントと設計。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- news_collector における複数のセキュリティ対策を実装:
  - defusedxml を使用した安全な XML パース。
  - HTTP リダイレクト時のスキーム検証およびプライベートアドレス拒否による SSRF 防止。
  - レスポンスバイト数上限（最大 10MB）および gzip 解凍後の再チェックでメモリ攻撃を緩和。
  - URL スキーム制限（http/https のみ）。
- jquants_client の retry/backoff とトークン自動リフレッシュは API の不安定時・認証期限切れに対する耐性を向上。

### Breaking Changes
- 初回リリースのため該当なし。

### Notes / Implementation details
- 多くの処理は DuckDB 接続を受け取り prices_daily/raw_financials/raw_* テーブルのみ参照／操作する設計で、
  実際の発注 API や外部アクションは行わない（Research/データ収集は本番口座へ影響を与えない）。
- ファクター計算や統計処理は外部ライブラリ（pandas 等）に依存しない純粋な Python 実装を目指している。
- 一部ファイルにおいて実装途中のテーブル定義（raw_executions の続きなど）が存在するため、今後の拡張で DDL 完成や Execution 層の実装が行われる想定。

---

今後の予定（例）
- Execution 層（発注・約定・ポジション管理）実装。
- Processed / Feature 層の DDL 完成と変換パイプライン。
- ニュース収集のソース拡充と記事分類・感情分析パイプライン。
- テストカバレッジの拡充（単体テスト・統合テスト）。