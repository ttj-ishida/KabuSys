CHANGELOG
=========

すべての重要な変更履歴はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

Unreleased
----------

- 未解決/開発中の項目をここに記載します（詳細は下部の「既知の問題」を参照）。

[0.1.0] - 2026-03-18
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの骨組みを追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" を追加し、公開モジュール一覧を定義（data, strategy, execution, monitoring）。
  - 環境変数 / 設定管理
    - src/kabusys/config.py
      - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装（プロジェクトルート検出は .git / pyproject.toml を基準）。
      - .env 読み込みの細かいパース実装（export 形式、クォート／エスケープ、インラインコメント処理）。
      - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル等の取得・バリデーションを提供。
  - J-Quants API クライアント
    - src/kabusys/data/jquants_client.py
      - API 呼び出しユーティリティ（_request）を実装。120 req/min のレート制限を守る固定間隔スロットリング（_RateLimiter）。
      - リトライロジック（指数バックオフ、最大3回、408/429/5xx をリトライ対象）と 429 の Retry-After サポート。
      - 401 受信時の自動 id_token リフレッシュを1回まで行う仕組みを実装（無限再帰防止）。
      - get_id_token(), fetch_daily_quotes(), fetch_financial_statements(), fetch_market_calendar() を提供（ページネーション対応、ページネーションキー重複保護）。
      - DuckDB に対する保存関数 save_daily_quotes(), save_financial_statements(), save_market_calendar() を実装。ON CONFLICT DO UPDATE による冪等保存と fetched_at（UTC）記録。
      - 数値変換ユーティリティ _to_float(), _to_int()（安全なパースと不正値処理）。
  - ニュース収集モジュール
    - src/kabusys/data/news_collector.py
      - RSS フィード収集（fetch_rss）と前処理、記事ID生成、DuckDB への冪等保存（save_raw_news）および銘柄紐付け（save_news_symbols / _save_news_symbols_bulk）を実装。
      - 記事IDは URL 正規化後の SHA-256（先頭32文字）を採用して冪等性を確保。
      - URL 正規化で utm_* 等のトラッキングパラメータを除去、フラグメント除去、クエリ整列を実装。
      - Gzip 対応、最大受信サイズ（MAX_RESPONSE_BYTES=10MB）チェック、gzip 解凍後のサイズ検査（Gzip bomb 対策）。
      - defusedxml を用いた XML パースで XML ボム等を軽減。
      - SSRF 対策: スキーム検証（http/https 限定）、プライベートアドレス判定（直接 IP と DNS 解決の両方で判定）、リダイレクト時に検査するカスタムハンドラを実装。
      - チャンク化（_INSERT_CHUNK_SIZE）・トランザクション・INSERT ... RETURNING による正確な挿入件数取得。
      - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加（DEFAULT_RSS_SOURCES）。
      - 銘柄コード抽出関数 extract_stock_codes()（4桁数字・既知銘柄フィルタ）。
  - DuckDB スキーマ
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution の多層スキーマを定義する DDL を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
      - 各種 CHECK 制約、外部キー、PRIMARY KEY を定義してデータ整合性を担保。
      - 運用を考慮したインデックスを複数追加（頻出クエリパターンを想定）。
      - init_schema() でディレクトリ作成→DDL 実行→インデックス作成までを行い、接続を返すユーティリティを提供。get_connection() も提供。
  - ETL パイプライン基盤
    - src/kabusys/data/pipeline.py
      - ETLResult dataclass を追加（取得数／保存数／品質問題／エラー等を保持）。
      - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整ヘルパー（_adjust_to_trading_day）を実装。
      - 差分更新ロジックの設計（最終取得日からの backfill を行い API の後出し修正を吸収する方針）。
      - 個別 ETL ジョブのスケルトンとして run_prices_etl() を実装（date_from の自動決定、fetch→save の流れ）。
  - モジュール構成
    - data パッケージ内に各実装モジュールを配置。strategy/ execution のパッケージ初期化ファイルはプレースホルダとして存在。

Security
- ニュース取得に関して SSRF 対策を実装（スキーム検証、プライベートアドレス判定、リダイレクト時の検査）。
- XML パースに defusedxml を使用して XML 脅威を軽減。
- 外部コンテンツ読み込みに対して Content-Length と実際読み込みバイト数の上限チェックを実装（メモリ DoS 対策）。

Changed
- （初版のため、既存機能の「変更」は特になし）

Fixed
- （初版のため、修正履歴はなし）

Removed / Deprecated
- （初版のため、該当なし）

既知の問題 / 注意点
- run_prices_etl の実装がファイル末尾で途中（戻り値のタプルの記述が途中で終了）になっており、現状のスナップショットでは文法的に不完全です。実行時に SyntaxError / 予期しない挙動が発生する恐れがあります。
  - 該当箇所: src/kabusys/data/pipeline.py の run_prices_etl()（最後の return 行が "return len(records), " で終わっている）
  - 対処案: return (len(records), saved) のように取得レコード数と保存レコード数を返す形で修正してください。
- strategy/ execution / data/__init__.py 等に未実装のプレースホルダが存在します。実際の戦略・発注ロジックや監視機能は別途実装が必要です。
- DNS 解決失敗時は安全側（非プライベート）とみなして通過させる設計であるため、環境依存の挙動に注意してください（テストではモック推奨）。

補足メモ（実装上の設計方針）
- API 呼び出しはレート制限とリトライ、トークン自動リフレッシュを組み合わせて堅牢化。
- DuckDB 側の書き込みは冪等性を重視（ON CONFLICT DO UPDATE / DO NOTHING）。
- ニュース収集は記事ID の安定化（URL 正規化＋ハッシュ）によって重複挿入を防止。
- 設定は Settings クラスを通じて一箇所から取得・バリデーションすることで誤設定を早期に検出。

（今後）
- run_prices_etl 等の未完了箇所の修正、単体テスト / 結合テストの追加、CI 設定、strategy/execution モジュールの実装を予定しています。