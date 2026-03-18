# Changelog

すべての変更は Keep a Changelog のガイドラインに従い、重要度の高い順に記載します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

（空）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システムのコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージ初期化: kabusys/__init__.py に version (0.1.0) と公開モジュール一覧を追加。
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を自動ロード。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式対応、クォート内のエスケープ処理、行末コメントの扱い等を実装。
  - 上書きルール:
    - .env は既存 OS 環境変数を保護する（protected set）。
    - .env.local は override=True で優先的に上書き。
  - Settings クラスを追加し、アプリケーション設定をプロパティで提供（J-Quants トークン、kabu API、Slack、DB パス、環境名・ログレベル検証など）。
    - 環境名 (KABUSYS_ENV) とログレベル (LOG_LEVEL) のバリデーションを実装。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 株価日足（/prices/daily_quotes）、財務データ（/fins/statements）、JPX マーケットカレンダー（/markets/trading_calendar）取得関数を実装。
  - レート制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
  - 再試行ロジック: 指数バックオフ、最大 3 回、対象ステータス (408, 429, 5xx)。
    - 429 時は Retry-After ヘッダを優先。
  - 認証: refresh_token から id_token を取得する get_id_token() と、401 時の自動リフレッシュ（1 回のみ）を実装。
  - id_token キャッシュ（ページネーション間で共有）実装。
  - データ取得時に fetched_at を UTC で記録し Look-ahead バイアスのトレーサビリティを確保。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を追加。
    - 冪等性を考慮し、INSERT ... ON CONFLICT DO UPDATE により重複を排除。
    - PK 欠損行はスキップし警告ログを出力。
  - 数値変換ユーティリティ (_to_float, _to_int) を追加し、不正な数値や小数切捨てを安全に扱う。
- RSS ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集する fetch_rss() を実装。
  - セキュリティ・堅牢性設計:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: URL スキーム検証、ホストがプライベート/ループバック/リンクローカル/マルチキャストの場合は拒否。
    - リダイレクト時にスキームとホストを検証する専用ハンドラ (_SSRFBlockRedirectHandler) を導入。
    - レスポンスサイズ上限 (MAX_RESPONSE_BYTES = 10MB) を導入しメモリ DoS を防止。gzip 解凍後も検証。
    - HTTP ヘッダで gzip を受け取れるようにし、解凍失敗時は安全にスキップ。
    - 記事 URL 正規化 (_normalize_url)、トラッキングパラメータ除去、SHA-256（先頭32文字）で記事ID生成(_make_article_id)。
  - 記事前処理 (preprocess_text): URL 除去、空白正規化。
  - DB 保存:
    - save_raw_news(): INSERT ... RETURNING id を用いて新規挿入IDのみを返す。チャンク単位挿入（_INSERT_CHUNK_SIZE）。
    - save_news_symbols(), _save_news_symbols_bulk(): news と銘柄コードの紐付けを一括で保存。トランザクション処理と ON CONFLICT 対応。
  - 銘柄抽出:
    - 4桁数字パターンから known_codes に含まれるものだけを抽出する extract_stock_codes。
  - テストしやすさ:
    - _urlopen をモックしてネットワーク呼び出しを差し替え可能。
- DuckDB スキーマ管理 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層のテーブル定義を包括的に実装（DDL群）。
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各種制約（PRIMARY KEY, FOREIGN KEY, CHECK）を明示的に定義。
  - インデックス定義（頻出クエリを想定）を追加。
  - init_schema(db_path) を実装し、親ディレクトリ自動作成、DDL & INDEX を idempotent に実行して接続を返す。
  - get_connection() を提供（初回は init_schema を推奨）。
- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass を実装し、ETL の実行結果（取得数、保存数、品質問題、エラー）を保持。
  - 差分更新ロジック: DB 内の最終取得日から backfill_days を考慮して再取得する設計。
    - デフォルト backfill_days = 3、最小データ日付 _MIN_DATA_DATE = 2017-01-01。
  - 市場カレンダーの先読み期間 _CALENDAR_LOOKAHEAD_DAYS = 90 を定義。
  - テーブル存在チェック、最大日付取得ユーティリティ(_table_exists, _get_max_date) を追加。
  - trading day へ調整するヘルパー (_adjust_to_trading_day) を実装。
  - run_prices_etl() を実装（差分計算、fetch_daily_quotes -> save_daily_quotes の連携）。  
    - （注）ファイル末尾で run_prices_etl の戻り値タプルの記述が途中で終わっているが、設計として差分取得と保存を行うことを反映。

### Changed
- （今回の初回実装のため該当なし）

### Fixed
- （今回の初回実装のため該当なし）

### Security
- RSS パーシングに defusedxml を採用し、XML パース関連の攻撃を軽減。
- ニュース取得側で SSRF 対策（スキーム検証、プライベートホスト検出、リダイレクト検査）を実装。
- .env 読み込みで OS 環境変数の上書きを制御し、意図しない上書きを防止。

### Notes / Implementation details
- 多くの DB 操作は DuckDB を前提としており、INSERT ... ON CONFLICT/RETURNING を利用して冪等性と正確な件数取得を目指しています。
- ネットワーク/外部API 呼び出しではログ出力、例外ハンドリング、再試行・バックオフ・レート制御を組み合わせて堅牢性を高めています。
- コード内のログメッセージや設計コメントは監査・運用時のデバッグに役立つよう配慮しています。
- 単体テストやモック差し替えを想定した設計（例: _urlopen の差し替え、id_token 注入可能）を行っています。

---

開発中に発見した未完部分や注意点:
- run_prices_etl() の戻り値の記述がファイル末尾で途中になっている（実装続きが必要）。実装の続きでは品質チェック呼び出しや ETLResult の集計が想定されます。

今後の改善候補:
- pipeline の品質チェックモジュール（kabusys.data.quality）を実装してエラーレポートの詳細化。
- 実行・監視（monitoring）や戦略（strategy）・発注（execution）モジュールの具体実装の追加。
- テストカバレッジと CI の整備（API モック、DB in-memory テストなど）。