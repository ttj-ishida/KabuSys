# Changelog

すべての重要な変更は Keep a Changelog のガイドラインに従って記録します。  
このファイルはリポジトリのコードから推測して生成された初期リリース向けの変更履歴です。

フォーマット:
- 変更カテゴリ: Added / Changed / Fixed / Security / Removed / Deprecated
- バージョンは semver を想定

なお、日付はこのドキュメント作成日です。

## [Unreleased]
- 次回リリースに向けた未確定の変更点はここに記載します。

---

## [0.1.0] - 2026-03-17
初期公開リリース

### Added
- パッケージ基盤
  - kabusys パッケージの初期エントリポイントを追加（src/kabusys/__init__.py）。
  - パッケージの公開モジュールとして data, strategy, execution, monitoring をエクスポート。

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local および環境変数から設定を自動読み込みする機能を追加。
  - プロジェクトルートを .git または pyproject.toml から特定するロジックを実装（CWD 非依存）。
  - .env のパースはコメント、export プレフィックス、シングル/ダブルクォート、エスケープ文字、インラインコメント等に対応。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - OS 環境変数を保護するための protected keys の概念を導入（.env.local の上書き制御など）。
  - 必須環境変数取得関数 _require を実装。settings オブジェクトを提供し、J-Quants / kabu / Slack / DB / システム設定をプロパティで取得可能。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL のバリデーションを追加。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - API クライアントを実装。以下の機能を含む:
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter 実装。
    - リトライロジック（最大 3 回、指数バックオフ）を導入。HTTP 408/429/5xx に対応。
    - 401 受信時に refresh token から id_token を自動更新して 1 回リトライする仕組みを実装（無限再帰を避ける allow_refresh フラグ）。
    - ページネーション対応のデータ取得（fetch_daily_quotes, fetch_financial_statements）。
    - market calendar 取得（fetch_market_calendar）。
    - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE）を実装（raw_prices/raw_financials/market_calendar）。
    - データ収集時の fetched_at を UTC で記録し、Look-ahead Bias のトレースを可能にする設計方針を反映。
    - 型変換ユーティリティ (_to_float, _to_int) を実装し、空値・不正値への耐性を追加。
    - モジュールレベルで id_token をキャッシュし、ページネーション間で共有。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからニュースを収集して DuckDB に保存する機能を実装。
  - 主な機能/設計:
    - RSS 取得（fetch_rss）: defusedxml を用いた安全な XML パース、gzip 対応、最大受信バイト数制限（デフォルト 10MB）で DoS 対策。
    - SSRF 対策:
      - fetch 前にホストがプライベート/ループバック/リンクローカルか検証する _is_private_host。
      - リダイレクト時にもスキームとリダイレクト先がプライベートでないことを検証するカスタムリダイレクトハンドラ _SSRFBlockRedirectHandler。
      - http/https 以外のスキームを拒否する _validate_url_scheme。
    - URL 正規化（_normalize_url）とトラッキングパラメータ除去（utm_ 等）。
    - 記事ID は正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
    - テキスト前処理（URL 除去、空白正規化）関数 preprocess_text。
    - DuckDB への保存:
      - save_raw_news: チャンク化バルク INSERT、トランザクションで一括保存、INSERT ... RETURNING で実際に挿入された ID を取得。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存（ON CONFLICT DO NOTHING）をチャンク・トランザクションで実装。
    - 銘柄コード抽出関数 extract_stock_codes（4桁数字パターン＋既知コードフィルタ）。
    - run_news_collection: 複数ソースの独立したエラーハンドリング、既知銘柄との紐付け処理をまとめたジョブ。

- DuckDB スキーマ（src/kabusys/data/schema.py）
  - DataPlatform 設計に基づく 3 層 + 実行レイヤーのテーブル定義を追加（Raw / Processed / Feature / Execution）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 運用上の頻出クエリ向けインデックス群を定義（idx_prices_daily_code_date など）。
  - init_schema(db_path) によりデータベースファイル作成（親ディレクトリ自動作成）、DDL を順序に従って冪等的に実行する初期化処理を追加。
  - get_connection(db_path) で既存 DB 接続を取得するヘルパ関数。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL 実行結果を表す ETLResult dataclass を追加（品質問題・エラー集約・シリアライズ用 to_dict を含む）。
  - 差分更新支援のユーティリティ:
    - テーブル存在チェック _table_exists。
    - 最大日付取得 _get_max_date。
    - 市場カレンダーを参照して非営業日を直近営業日に調整する _adjust_to_trading_day。
    - raw_prices / raw_financials / market_calendar の最終日取得ヘルパ（get_last_price_date 等）。
  - run_prices_etl（株価差分 ETL）の骨組みを追加:
    - 最終取得日からの差分算出、バックフィル日数（デフォルト 3 日）を考慮した再取得、jquants_client の fetch/save 呼び出しによる保存、ログ出力。

### Fixed
- 各所で入力データに対する堅牢性を向上：
  - .env パーサでコメントやクォート、エスケープを正しく扱うように修正（誤解析による環境変数欠損を低減）。
  - RSS 取得時のサイズ超過・gzip 解凍失敗・XML パース失敗時に明示的な警告を出力して安全にスキップする挙動を実装。
  - DuckDB への保存はトランザクションでまとめ、例外時にロールバックすることで部分コミットを防止。

### Security
- ニュース収集部分で複数のセキュリティ対策を導入:
  - defusedxml の採用による XML 関連攻撃対策（XML Bomb 等）。
  - SSRF 対策（ホスト検証・リダイレクト検査・スキーム制限）。
  - 外部レスポンスサイズ制限（MAX_RESPONSE_BYTES）と gzip 解凍後サイズチェックによるメモリ DoS 対策。
  - URL 正規化とトラッキング除去による ID 衝突およびデータ漏洩リスク低減。

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Notes / Known issues
- run_prices_etl の戻り値に関する実装は部分的（本コードスニペットの最後で return が途切れているように見える）。実際の利用時は完全な戻り値（取得数、保存数など）を返すことを確認してください。
- settings._require は未設定時に ValueError を投げる設計のため、CI/デプロイ前に必要な環境変数を確実に設定すること。
- DuckDB のスキーマは多くの外部キー・チェックを含むため、マイグレーションやスキーマ変更は慎重に行うこと。
- デフォルトの RSS ソースは Yahoo Finance（news.yahoo.co.jp）を設定。運用ではソース一覧のカスタマイズが推奨。

---

この CHANGELOG はコードベースの現状から推測して作成したものです。実際のコミット履歴・リリースノートが存在する場合はそれらを優先して更新してください。