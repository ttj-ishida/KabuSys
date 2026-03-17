CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従います。  
慣例により、重要な変更は大分類（Added / Changed / Fixed / Security / Notes）で記載します。

0.1.0 - 2026-03-17
------------------

Added
- 初回公開リリース。日本株自動売買システムの基盤モジュール群を実装。
  - パッケージ初期化:
    - kabusys.__init__ にバージョン情報と公開サブパッケージを定義。
  - 設定管理:
    - kabusys.config: .env ファイルまたは環境変数からの設定自動読み込みを実装。
      - プロジェクトルートを .git または pyproject.toml から検出して .env/.env.local を読み込む。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
      - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
      - OS 環境変数を保護する protected オプションを導入（.env.local での上書き制御）。
    - Settings クラスに各種必須設定プロパティを追加（J-Quants, kabuステーション, Slack, DB パス等）。
      - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値チェック）。
      - デフォルトの DB パス（ DuckDB / SQLite ）を設定。
  - データ取得クライアント:
    - kabusys.data.jquants_client:
      - J-Quants API クライアントを実装。
      - レート制限（120 req/min）を固定間隔スロットリングで厳守する RateLimiter を導入。
      - リトライ戦略（指数バックオフ、最大 3 回）と 408/429/5xx の再試行処理を実装。
      - 401 応答時はリフレッシュトークンから id_token を自動更新して一度だけ再試行するロジックを実装。
      - ページネーション対応のデータ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
      - DuckDB へ冪等に保存する保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
      - 取得タイムスタンプ（fetched_at）は UTC で記録し look-ahead bias のトレースを可能に。
      - 数値変換ユーティリティ（_to_float, _to_int）を実装。誤った小数→int変換を防ぐ処理を含む。
  - ニュース収集:
    - kabusys.data.news_collector:
      - RSS フィードから記事を取得して raw_news に保存するモジュールを実装。
      - トラッキングパラメータ削除と URL 正規化に基づく記事ID生成（SHA-256 先頭32文字）で冪等性を保証。
      - defusedxml を用いた XML パース、安全対策（XML Bomb 回避）。
      - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先のスキームとプライベートアドレス検査、DNS 解決済みアドレスの検査。
      - レスポンスサイズ上限（10MB）や gzip 解凍後のサイズ検査によるメモリDoS対策。
      - テキスト前処理（URL除去・空白正規化）、タイトル/本文の組み合わせによる銘柄コード抽出機能（4桁数字フィルタ + known_codes フィルタ）。
      - DB 保存はチャンク分割・1トランザクションで実行し、INSERT ... RETURNING で実際に挿入された件数を返す（save_raw_news, save_news_symbols, _save_news_symbols_bulk）。
      - デフォルト RSS ソースとして Yahoo Finance のカテゴリRSSを設定。
  - スキーマ管理:
    - kabusys.data.schema:
      - DuckDB 用のスキーマを定義（Raw / Processed / Feature / Execution の各レイヤー）。
      - 各テーブルのDDL（型・制約・PRIMARY KEY・外部キー）を網羅的に定義。
      - インデックスの定義（頻出クエリパターンに対応）。
      - init_schema(db_path) でファイル親ディレクトリ自動作成後にテーブル・インデックスを作成する初期化APIを提供。
      - get_connection() による既存DB接続取得APIを提供（初期化は行わない）。
  - ETLパイプライン基盤:
    - kabusys.data.pipeline:
      - ETL の設計方針・処理フロー（差分更新、保存、品質チェック）を実装。
      - ETLResult データクラスにより実行結果（取得数・保存数・品質問題・エラー）を表現。
      - テーブル存在チェック・最終取得日の取得ユーティリティを実装（_table_exists, _get_max_date, get_last_price_date 等）。
      - 市場カレンダーを考慮した営業日調整ヘルパー（_adjust_to_trading_day）。
      - run_prices_etl により株価日足の差分ETL処理を実装（差分計算、backfill_days による後出し修正吸収、fetch→save の流れ）。
  - パッケージ構成:
    - data, strategy, execution, monitoring のサブパッケージ構成を用意（空の __init__ が存在）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- セキュリティ面の配慮を多数実装:
  - defusedxml による XML パースで XXE / XML Bomb に対処。
  - RSS 取得時のリダイレクト前後でスキーム検証とプライベートアドレス検査を実行し SSRF を防止。
  - ネットワーク取得時の最大受信バイト数チェックや gzip 解凍後のサイズチェックによりメモリDoS対策。
  - .env ローダは OS 環境変数を保護する設計（protected set）。KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト時に自動ロードを止められる。
  - J-Quants API 認証トークンのキャッシュと 401 発生時の安全な1回だけのリフレッシュ処理。

Notes / Known limitations
- ETL と品質チェック:
  - pipeline モジュールは差分取得と保存の基本実装を提供。財務データ・カレンダー等の個別ETL（run_financials_etl 等）は今後追加/拡張予定。
  - 品質チェックモジュール（kabusys.data.quality）は参照されているが、このリリースに含まれる品質ルールの詳細は別途実装/文書化される見込み。
- NewsCollector:
  - 記事IDは URL 正規化に依存しているため、極端に異なるURL書式を持つ同一記事は別記事として扱われる可能性がある（一般的にはトラッキングパラメータ削除で十分冪等性は担保される想定）。
- テスト・メンテナンス:
  - ネットワーク/外部API に依存する部分はモックしやすい設計（例: _urlopen の差し替え、id_token 注入）になっているが、継続的な統合テストの整備が推奨される。

開発者向けメモ
- 環境変数:
  - 必須項目（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は Settings のプロパティ経由で取得すると ValueError を投げて明示的に通知される。
- DuckDB:
  - init_schema は ":memory:" を受け入れる。ファイルベースの DB を使う場合は親ディレクトリを自動作成する。
- ロギング:
  - 各モジュールで logger を利用しているため、アプリケーション側でログレベルやハンドラを設定することで詳細ログ（API リトライや保存スキップ等）を取得可能。

今後の予定（例）
- ETL の拡張: 財務データ・カレンダーの差分ETLを pipeline に統合。
- strategy / execution 層の実装強化（アルファ生成、発注ロジック、ポジション管理）。
- 監視/アラート機能（Slack 連携の実装拡張）。
- ユニット/統合テストと CI の整備。

もし CHANGELOG に追記してほしい点（例えば実際のリリース日付や追加の既知の問題、担当者情報など）があれば教えてください。