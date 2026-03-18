# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはリポジトリの現状のコードベースから推測して作成した初期リリース向けの変更履歴です。

All notable changes to this project will be documented in this file.

## [0.1.0] - 2026-03-18 (初期リリース)

### Added
- 基本パッケージの追加
  - パッケージ名: kabusys
  - エクスポート: data, strategy, execution, monitoring（各サブパッケージのエントリポイントを公開）

- 環境設定 / 設定管理（kabusys.config）
  - .env 自動読み込み機能を追加（プロジェクトルートは __file__ から探索し、.git または pyproject.toml を基準に判定）
  - 読み込み優先順位: OS環境変数 > .env.local > .env
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応（テスト用途）
  - .env ファイル行のパーサ実装（export プレフィックス、クォート/エスケープ、インラインコメントの取り扱い）
  - Settings クラスを追加し、環境変数をプロパティ経由で取得
    - J-Quants / kabuステーション / Slack / DB パス 等の設定プロパティ
    - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）
    - duckdb/sqlite のパスを Path 型で提供
    - is_live / is_paper / is_dev といったヘルパープロパティ

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティを実装（JSON デコード・エラーハンドリング）
  - レート制限制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を導入
  - 再試行ロジック: 指数バックオフ（最大 3 回）、408/429/5xx に対するリトライ、429 の Retry-After ヘッダを優先
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とトークンキャッシュ共有
  - ページネーション対応の取得関数:
    - fetch_daily_quotes (株価日足)
    - fetch_financial_statements (四半期財務)
    - fetch_market_calendar (JPX カレンダー)
  - DuckDB への冪等保存関数（ON CONFLICT DO UPDATE）:
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - 型変換ユーティリティ: _to_float, _to_int（不正データに対して安全な変換）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を取得・前処理・保存する ETL を実装
  - 主要機能:
    - URL 正規化（トラッキングパラメータ除去・ソート・フラグメント削除）
    - 記事ID は正規化 URL の SHA-256（先頭32文字）を利用し冪等性を保証
    - テキスト前処理（URL 除去・空白正規化）
    - defusedxml を利用して XML Bomb 等の攻撃を防止
    - SSRF 対策:
      - URL スキーム検証（http/https のみ）
      - ホスト/IP のプライベート判定（DNS 解決して A/AAAA を確認）
      - リダイレクト時にも検証を実施する専用ハンドラを導入
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍時のチェック（Gzip bomb 対策）
    - DB 保存: DuckDB へのチャンク単位 INSERT、トランザクション、INSERT ... RETURNING を使って挿入された件数を正確に返す
    - 銘柄コード抽出ロジック（4桁数字、既知コードセットでフィルタリング）
  - デフォルト RSS ソース: Yahoo Finance のビジネスカテゴリ（DEFAULT_RSS_SOURCES）

- DuckDB スキーマ / 初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層に対応したテーブル群を定義
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種 CHECK 制約、PRIMARY KEY、外部キーを定義（データ整合性重視）
  - 頻出クエリ向けインデックスを用意
  - init_schema(db_path) でディレクトリ作成 → テーブル・インデックス作成、get_connection() を提供

- データ ETL パイプライン（kabusys.data.pipeline）
  - ETL 用データクラス ETLResult を導入（品質問題・エラーの集約）
  - テーブル存在チェック、最終取得日取得、営業日調整のヘルパー関数
  - run_prices_etl: 差分更新ロジック（最終取得日からの backfill、_MIN_DATA_DATE ガード）、jquants_client を利用した取得→保存のフローを実装
  - 設計方針: 差分更新・backfill による後出し修正吸収、品質チェックは最終的な判定を呼び出し元に委ねる

### Security
- ニュース収集に関して複数のセキュリティ対策を導入
  - defusedxml による安全な XML パース
  - SSRF 対策（スキーム検証・プライベートホストの拒否・リダイレクト検査）
  - レスポンスサイズの上限設定と gzip 解凍後のチェック（メモリ DoS / Gzip bomb 対策）
- J-Quants クライアントは認証/トークンリフレッシュを安全に扱う（allow_refresh フラグで再帰を防止）

### Known issues / TODO
- run_prices_etl の戻り値処理が途中で終わっている箇所（コード末尾に "return len(records), " のような未完了の返却が見られます）。これによりパイプライン関数の挙動が意図した通りに動作しない可能性があります。修正（保存件数 saved を返す等）が必要です。
- strategy, execution, monitoring サブパッケージの __init__.py が空であり、主要な戦略ロジックや発注実行・監視ロジックは未実装です。これらは今後の実装対象です。
- 単体テスト・統合テストの記述はコードからは確認できません（テスト用のモック注入ポイントはいくつか存在するため、テストは容易に追加可能）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

---

翻訳・要約・設計意図はコードから推測したものであり、実際のコミット履歴ではありません。必要であれば、個々のモジュールごとにより詳細な変更点や実装上の注意点（例: 各関数の引数説明、返却値、例外動作）を追記します。