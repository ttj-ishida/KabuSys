# Changelog

すべての重要な変更履歴は Keep a Changelog の形式に従って記述します。  
フォーマットの詳細: https://keepachangelog.com/（本 CHANGELOG はコードの内容から推測して作成しています）

なお、本記載は提供されたコードベース（バージョン __version__ = 0.1.0）から実装意図と設計方針を推測してまとめた初期リリース相当の変更履歴です。

## [Unreleased]
- なし（現状は初期リリースを記録）

## [0.1.0] - 2026-03-18
初期リリース（コードベース解析に基づく推定）

### Added
- パッケージ基盤
  - kabusys パッケージの初期モジュール（src/kabusys/__init__.py、バージョン 0.1.0）。
  - モジュール階層: data, strategy, execution, monitoring（__all__ に宣言）。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動で読み込む自動ロード機能を実装（プロジェクトルート判定：.git または pyproject.toml）。
  - .env と .env.local の読み込み順と override 挙動（OS 環境変数は保護）。
  - 行パーサーは export プレフィックス、クォートエスケープ、インラインコメント（スペース直前の # で判定）に対応。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途）。
  - Settings クラスを提供し、J-Quants / kabuAPI / Slack / DB パス / システム環境（env, log_level）などのプロパティを型付けして取得。env と LOG_LEVEL の値検証を実施。
  - DuckDB / SQLite のデフォルトパス設定を提供。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日次株価（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得用 API クライアントを実装。
  - レート制限対応: 固定間隔スロットリング（120 req/min）を実装する RateLimiter。
  - 再試行ロジック（指数バックオフ、最大 3 回）および 408/429/5xx のリトライ処理。
  - 401 Unauthorized 受信時にリフレッシュトークンで自動取得を試みる仕組み（1 回だけリフレッシュして再試行）。
  - ページネーション対応（pagination_key）とモジュールレベルの ID トークンキャッシュの実装。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）で冪等性を保つ ON CONFLICT DO UPDATE を利用。
  - レスポンス JSON のデコードエラーや HTTP エラーを整然と扱う設計。
  - 数値変換ユーティリティ（_to_float, _to_int）を提供し、入力のバリデーションを行う。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードからの記事収集、前処理、DuckDB への冪等保存、銘柄紐付けを行う実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - SSRF 対策: リダイレクト時のスキーム検査とプライベートアドレスチェック（カスタム RedirectHandler）。
    - ホスト名の DNS 解決に基づくプライベート/ループバック判定（IPv4/IPv6 両対応）。
    - URL スキーム検証（http/https のみ許可）、受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、gzip 解凍後のサイズ再チェック。
  - 記事 ID は URL 正規化（トラッキングパラメータ除去等）後の SHA-256（先頭32文字）で生成し、冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DB 保存はチャンク化されたバルク INSERT（INSERT ... RETURNING）を使用し、新規挿入された ID を正確に返す。
  - 銘柄コード抽出ロジック（4桁数字）と既知銘柄セット（known_codes）によるフィルタリングを実装。
  - 統合収集ジョブ run_news_collection を実装し、各ソースの独立したエラーハンドリングと銘柄紐付けの一括保存を行う。

- DuckDB スキーマと初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の 3 層（+ Raw の execution）に対応するテーブル群を定義。
  - 各テーブルに対する制約（NOT NULL, CHECK, PRIMARY KEY, FOREIGN KEY）を細かく設定。
  - 頻出クエリ向けのインデックス群を定義（銘柄×日付、ステータス検索など）。
  - init_schema(db_path) によりディレクトリ自動作成・全DDL実行して接続を返す機能を提供。get_connection() による既存 DB 接続 API も提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新の挙動を実装（DB の最終取得日から backfill を行うデフォルト挙動）。
  - 市場カレンダーの先読み（lookahead 日数定義）。
  - ETLResult dataclass により ETL 実行結果（取得数／保存数／品質問題／エラー）を構造化して返却できる設計。
  - テーブル有無判定、最終取得日取得ユーティリティを実装（get_last_price_date 等）。
  - run_prices_etl（株価差分 ETL）の骨組み実装: date_from 自動算出、fetch + save の呼び出し、ログ出力。backfill_days デフォルト値は 3 日。
  - 設計原則として品質チェックは Fail-Fast をしない（quality モジュールと連携予定）。

### Security
- 環境変数の自動ロードにおいて OS 環境変数を保護する仕組みを導入（protected set）。
- RSS 処理における SSRF/ZIP/XML 攻撃、メモリ DoS を防ぐ対策を実装（size 上限、defusedxml、リダイレクト検査、プライベートアドレスチェック）。
- HTTP タイムアウトや User-Agent 設定など、外部通信の安全性・診断性を考慮。

### Performance / Reliability
- API クライアントにレートリミッタとリトライ（指数バックオフ）を実装し、外部 API の制約への耐性を強化。
- DuckDB へのバルク挿入・チャンク化・トランザクション管理（begin/commit/rollback）により大量データ処理時の効率と整合性を確保。
- 冪等性を意識した INSERT ... ON CONFLICT 処理を多用（raw データの重複対策）。

### Testing / Extensibility
- テスト用フック: news_collector._urlopen をモック差し替え可能な設計。
- jquants_client の id_token を外部注入可能（id_token 引数）で単体テストが可能。
- Settings クラスと _require で明示的なエラーを出す設計により問題検出を容易化。

### Notes / Known limitations（コードから推測）
- pipeline.py の実装は一部（ファイル末尾）が切れている／未完の可能性あり（run_prices_etl の戻り値ハンドリングなど未完箇所が見受けられる）。
- quality モジュールの実装参照は存在するが、該当モジュールの詳細は本コードからは確認できない（品質チェックの具体的実装は未提供）。
- src/kabusys/execution/__init__.py と src/kabusys/strategy/__init__.py は現状空のプレースホルダ（今後の実装が予定されている）。
- Slack 周り（通知）の使用箇所は設定項目があるが、実際の通知送信コードは今回のスニペットに含まれていない。

## Future / TODO（推測）
- pipeline の残りジョブ（財務・カレンダー ETL、品質チェックの適用、監査ログ出力）を実装する。
- strategy / execution の具象実装（シグナル生成、注文送信、kabuAPI 連携）を追加する。
- 単体テスト・統合テストの追加（外部 API モック、DB の in-memory テスト）。
- スキーマ移行・バージョン管理対応（DDL の管理、マイグレーション仕組み）。
- 監視・アラート（Slack 通知等）の追加実装。

---

メモ:
- 上記は提供されたソースコードの実装内容とドキュメント文字列から推測して作成した CHANGELOG です。実プロジェクトのリリース履歴や日付、詳細な変更点は実際のコミット履歴に基づいて調整してください。