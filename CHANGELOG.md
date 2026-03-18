Changelog
=========
すべての変更は https://keepachangelog.com/ja/ に準拠して記載します。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-03-18
--------------------

Added
- 初回リリース。日本株向け自動売買/データプラットフォームの基盤機能を実装。
- パッケージ構成
  - kabusys パッケージ本体（src/kabusys/__init__.py）を導入。公開 API として data, strategy, execution, monitoring をエクスポート。
- 環境・設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - .env と .env.local の読み込み優先順位を実装（OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - export KEY=val 形式やクォート、インラインコメントなどを考慮した .env パーサを実装。
  - 必須環境変数取得時に明確なエラーを出す _require と Settings クラスを提供（J-Quants トークン、Kabu API パスワード、Slack トークン/チャンネル等）。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション、デフォルト値および is_live/is_paper/is_dev 補助プロパティ。
  - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）の Path 返却。

- データ収集クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter を実装。
  - リトライロジック（指数バックオフ、最大リトライ回数3回）と 408/429/5xx に対する再試行処理。
  - 401 受信時に自動でリフレッシュトークンから id_token を再取得して1回リトライする処理を実装（無限再帰回避のため allow_refresh フラグを採用）。
  - ページネーション対応の fetch_daily_quotes, fetch_financial_statements を提供。
  - JPX マーケットカレンダー取得 fetch_market_calendar を提供。
  - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。INSERT ... ON CONFLICT DO UPDATE を使って重複を排除。
  - データ変換ユーティリティ _to_float / _to_int を実装し、入力値の頑健な処理を行う。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース取得・前処理・DuckDB への保存までの一連処理を実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、スキーム/ホスト小文字化）と正規化 URL の SHA-256（先頭32文字）で記事ID生成。
  - defusedxml を用いた XML パース（XML Bomb 等への対策）。
  - SSRF 対策：URL スキーム検証（http/https のみ許可）、プライベートIP/ループバックへの接続拒否（DNS 解決済み IP 検査）、リダイレクト時の検証用ハンドラを実装。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
  - RSS の pubDate パース、URL/空白除去によるテキスト前処理、content:encoded の優先利用等のロジック。
  - raw_news テーブルへのチャンク・トランザクション挿入（INSERT ... ON CONFLICT DO NOTHING RETURNING id）と、news_symbols への紐付け保存（重複排除・チャンク挿入、トランザクション管理）。
  - 記事本文からの銘柄コード抽出（4桁数字・known_codes に基づくフィルタリング）。

- 研究用ファクター計算（src/kabusys/research）
  - feature_exploration.py
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、単一クエリで LEAD を利用）。
    - IC（Information Coefficient）計算 calc_ic（Spearman の ρ をランク経由で計算、欠損・非有限値・最小レコード数チェックを考慮）。
    - rank, factor_summary（count/mean/std/min/max/median）ユーティリティ。
    - 標準ライブラリのみでの実装（外部依存無し）を明示。
  - factor_research.py
    - calc_momentum（1M/3M/6M リターン、MA200 乖離率）。
    - calc_volatility（20日 ATR、相対ATR、平均売買代金、出来高比率）。
    - calc_value（最新の財務データと当日価格を組み合わせて PER/ROE を算出）。
    - DuckDB 上の prices_daily / raw_financials テーブルのみを参照する設計、データ不足時は None を返す仕様。

- スキーマ定義（src/kabusys/data/schema.py）
  - DuckDB 用のテーブル定義（raw_prices, raw_financials, raw_news, raw_executions の DDL を含む）。（ファイルはスキーマ群の一部を定義）

Security
- SSRF 対策を複数のレイヤで実装（URL スキーム検証、プライベートアドレス検出、リダイレクト時の検査）。
- XML パース時に defusedxml を使用して XML 攻撃を軽減。
- レスポンスサイズ上限・gzip 解凍後サイズ検査を導入してメモリ DoS / Gzip bomb を防止。
- 外部 API 呼び出し時の認証トークン自動リフレッシュと再試行の安全な実装。

Performance
- J-Quants API 呼び出しでレート制限を守る固定間隔スロットリングを実装（120 req/min）。
- calc_forward_returns や各ファクター計算は DuckDB のウィンドウ関数（LEAD, AVG, COUNT 等）を活用して単一クエリで効率的に集計。
- news_collector の DB 挿入はチャンク分割・トランザクションでバルク処理。

Internal
- DuckDB を中心としたデータパイプライン設計（Raw / Processed / Feature / Execution 層の方針）。
- ロギングを各処理に適切に配置（info/warning/exception/ debug）。
- 設定・環境読み込みはプロジェクトルート探索に依存することでパッケージ配布後も安定して動作するよう設計。

Breaking Changes
- なし（初回リリース）。

Notes / Limitations
- research モジュールは標準ライブラリのみで実装しており、大規模データ処理での最適化や NumPy/Pandas 等の利用による高速化は将来検討事項。
- スキーマ定義ファイルは一部（raw_executions 以降）で切れている箇所があり、execution 層の完全な DDL は今後補完されることを想定。
- 外部 API（Kabu/Slack 等）への連携は設定（環境変数）に依存する。テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。

Authors
- 実装内容は提供されたコードベースに基づいて推測して作成しました。