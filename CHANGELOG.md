CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
リリースはコードベースから推測された内容に基づき記述しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - 基本モジュール構成を追加
    - kabusys.__init__ にパッケージ情報と公開サブパッケージ定義を追加。
    - 空のパッケージステブ: kabusys.execution, kabusys.strategy（将来の実装用）。
  - 環境設定管理 (kabusys.config)
    - .env ファイルおよび環境変数からの設定自動読み込み機能を実装。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD 非依存で自動ロード。
    - .env / .env.local の読み込み順序と既存 OS 環境変数の保護（protected set）を実装。
    - export KEY=val 形式、クォート文字列のエスケープ、インラインコメント処理などをサポートする .env パーサを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
    - 必須キー取得時に未設定なら ValueError を投げる _require() を提供。
    - 設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等。
  - J-Quants API クライアント (kabusys.data.jquants_client)
    - 株価日足 (OHLCV)、財務データ（四半期 BS/PL）、JPX 市場カレンダー取得機能を実装。
    - API への呼び出しで以下設計を実装:
      - レートリミッタ（固定間隔スロットリング、デフォルト 120 req/min）による制御。
      - 再試行ロジック（指数バックオフ、最大 3 回）。408/429/5xx を対象。429 の場合は Retry-After を優先。
      - 401 (Unauthorized) 受信時はリフレッシュトークンで自動的にトークンを更新して 1 回だけリトライ。
      - ページネーション対応（pagination_key を使用して複数ページを連結）。
      - get_id_token()：リフレッシュトークンから idToken を取得する POST エンドポイント呼び出し。
      - モジュールレベルの id_token キャッシュを導入しページネーション間で共有。
    - DuckDB への保存ユーティリティ:
      - save_daily_quotes, save_financial_statements, save_market_calendar：ON CONFLICT DO UPDATE による冪等保存。
      - 取得時刻 (fetched_at) を UTC ISO8601 形式で記録（Look-ahead bias を防止する目的で記録）。
      - PK 欠損レコードをスキップし警告ログを出力。
    - ユーティリティ変換関数 _to_float / _to_int を提供（型安全性と不正値耐性）。
  - ニュース収集モジュール (kabusys.data.news_collector)
    - RSS フィードからニュース記事を収集して raw_news に保存する ETL ロジックを実装。
    - 設計上のセキュリティおよび堅牢性機能:
      - defusedxml を使用した XML パース（XML Bomb 等の対策）。
      - HTTP リダイレクト時の事前検証ハンドラ（_SSRFBlockRedirectHandler）でスキームとプライベートアドレスをチェックし SSRF を防止。
      - URL スキーム検証（http/https のみ許可）。
      - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再チェック（Gzip bomb 対策）。
      - 最終 URL の再検証（リダイレクト後も安全性を二重検査）。
      - トラッキングパラメータ (utm_*, fbclid, gclid, ref_, _ga 等) を除去する URL 正規化。
      - 記事ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を担保。
    - フロント処理:
      - URL 除去・空白正規化を行う preprocess_text。
      - pubDate のパースを行い UTC naive datetime に正規化（失敗時は現在時刻で代替して警告）。
      - content:encoded を description より優先して利用。
    - DuckDB への保存:
      - save_raw_news：チャンク化 INSERT ... ON CONFLICT DO NOTHING ... RETURNING を使い、新規挿入記事 ID を正確に返却。1 トランザクション内でチャンク毎に挿入。
      - save_news_symbols / _save_news_symbols_bulk：記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING で挿入数を正確に返す）。
    - 銘柄コード抽出:
      - テキストから 4 桁数字を検出し、known_codes に含まれるもののみを返却する extract_stock_codes を実装（重複除去）。
    - run_news_collection：複数ソースを独立して処理、ソース単位のエラーハンドリング、既知銘柄が与えられれば新規記事に対して銘柄紐付けを実行。
    - デフォルト RSS ソースに Yahoo Finance のビジネスカテゴリを追加。
  - データベーススキーマ (kabusys.data.schema)
    - DuckDB 用のスキーマを網羅的に定義（Raw / Processed / Feature / Execution レイヤー）。
    - 主なテーブル:
      - raw_prices, raw_financials, raw_news, raw_executions
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - features, ai_scores
      - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 適切な型、CHECK 制約、主キー、外部キーを定義してデータ整合性を確保。
    - 頻出クエリを想定したインデックス群を作成。
    - init_schema(db_path) によりディレクトリ自動作成・DDL 実行・インデックス作成を行い接続を返す（冪等）。
    - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない）。
  - ETL パイプライン (kabusys.data.pipeline)
    - ETLResult データクラスを導入し、ETL 実行結果、品質問題、エラー一覧の集約をサポート。
    - 差分更新/バックフィルの設計:
      - 市場データの最小取得日 _MIN_DATA_DATE を定義（2017-01-01）。
      - デフォルトの backfill_days = 3（最終取得日の数日前から再取得して後出し修正を吸収）。
      - カレンダー先読み _CALENDAR_LOOKAHEAD_DAYS = 90。
    - テーブル存在 / 最大日付取得のヘルパー関数を実装（_table_exists, _get_max_date, get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - 非営業日を営業日に調整する _adjust_to_trading_day を実装（market_calendar 未取得時はフォールバック）。
    - run_prices_etl の骨子を実装:
      - DB の最終取得日から date_from を算出し差分取得。
      - jq.fetch_daily_quotes と jq.save_daily_quotes を組み合わせて取得・保存するロジック。
  - 依存ライブラリの利用:
    - duckdb を主要なデータストアとして利用。
    - defusedxml を安全な XML パースのために使用。

Fixed
- なし（初期リリース）

Changed
- なし（初期リリース）

Removed
- なし

Security
- RSS パーサと HTTP クライアント周りで SSRF・XML Bomb・Gzip Bomb 等に対する複数の防御策を追加。

Known issues / Notes
- run_prices_etl の戻り値
  - run_prices_etl の実装終端が return len(records), で終わっており、意図される (fetched_count, saved_count) のタプルが正しく返らない（保存数 saved を返していない・末尾のカンマにより形式が不明瞭）。次回リリースで修正が必要。
- パッケージの空スタブ
  - kabusys.execution, kabusys.strategy は現在 __init__.py が空のまま（将来的な実装箇所）。API/内部設計は未実装。
- テスト・エラーハンドリングの注意
  - ネットワーク関連（URLopen）のテスト性のために _urlopen を差し替え可能にしているが、実運用ではネットワーク例外の扱いとログが重要になるため運用時に監視が必要。
- 設定の必須項目について
  - settings の一部プロパティは未設定時に ValueError を投げる（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN 等）。環境変数設定が必須であることに注意。

今後の予定（想定）
- run_prices_etl の戻り値修正と追加の ETL ジョブ（financials, calendar）の完成。
- execution / strategy モジュールの実装（シグナル生成・発注・ポジション管理）。
- 品質チェックモジュール (kabusys.data.quality) の実装と ETL 連携。
- 監視・アラート (Slack 統合) の実装。

-----------

注意:
- 上記は提示されたソースコードから推測して作成した CHANGELOG です。実際のコミット履歴・リリースノートに基づくものではありません。必要であれば日付や細部の表現を実プロジェクトの方針に合わせて調整します。