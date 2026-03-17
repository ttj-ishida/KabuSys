KEEP A CHANGELOG
=================

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
日付はリリース日を示します。コードベースの内容から推測して記載しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-03-17
--------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）
  - パッケージ構成:
    - src/kabusys/__init__.py にパッケージ名・バージョン定義。
    - サブモジュールプレースホルダ: data, strategy, execution, monitoring を公開。
  - 設定管理:
    - src/kabusys/config.py
      - .env ファイルと環境変数から設定を読み込む自動ローダーを実装。
      - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）により CWD 非依存で .env を読み込み。
      - export KEY=val 形式やクォート・インラインコメントに対応するパーサを実装。
      - 読み込み優先度: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
      - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 環境 / ログレベル等の設定を型安全に取得。
      - 環境値の検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）と必須キー取得時のエラー処理を実装。
  - J-Quants クライアント:
    - src/kabusys/data/jquants_client.py
      - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、市場カレンダーの取得機能を実装。
      - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
      - ネットワークリトライ（指数バックオフ、最大3回）と 408/429/5xx を対象とした再試行ロジック。
      - 401 発生時にリフレッシュトークンで id_token を自動更新して 1 回だけ再試行する仕組み。
      - ページネーション対応（pagination_key の連続取得）。
      - DuckDB へ冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE を利用）: save_daily_quotes, save_financial_statements, save_market_calendar。
      - データ型安全性のためのユーティリティ _to_float/_to_int を実装。
      - 取得時刻（fetched_at）を UTC ISO8601 で記録し Look-ahead Bias を抑止。
  - ニュース収集モジュール:
    - src/kabusys/data/news_collector.py
      - RSS フィードからニュースを収集し raw_news に保存する処理を実装。
      - セキュリティ対策:
        - defusedxml を用いた XML パース（XML Bomb 等への対策）。
        - SSRF 対策: リダイレクト検査ハンドラ（_SSRFBlockRedirectHandler）、ホストがプライベート/ループバック/リンクローカルかどうかの判定。
        - URL スキームの検証（http/https のみ許可）。
        - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）チェック、gzip 解凍後のサイズ検査。
      - 記事 ID は正規化後 URL の SHA-256（先頭32文字）で生成し冪等性を実現（utm_* 等トラッキングパラメータ削除）。
      - テキスト前処理（URL 除去、空白正規化）と記事要素抽出（title, content, pubDate）を実装。
      - DuckDB への保存:
        - save_raw_news はチャンク挿入、トランザクション管理、INSERT ... RETURNING による実際に挿入された記事IDの返却。
        - news_symbols / _save_news_symbols_bulk により記事と銘柄コードの紐付けを一括保存。
      - 銘柄コード抽出機能（4桁数字パターン）を提供し、既知銘柄セットでフィルタ。
      - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを設定。
  - DuckDB スキーマ定義:
    - src/kabusys/data/schema.py
      - Raw / Processed / Feature / Execution の多層スキーマを定義。
      - raw_prices, raw_financials, raw_news, raw_executions を含む Raw レイヤー。
      - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed レイヤー。
      - features, ai_scores の Feature レイヤー。
      - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution レイヤー。
      - 各テーブルに制約（PRIMARY KEY, CHECK, FOREIGN KEY）を設定。
      - 頻出クエリ用インデックスを作成する定義を用意。
      - init_schema(db_path) によりディレクトリ自動作成と DDL 実行で初期化可能。get_connection() を提供。
  - ETL パイプライン（骨組み）:
    - src/kabusys/data/pipeline.py
      - 差分更新の方針とユーティリティを実装:
        - テーブル存在チェック、最大日付取得ユーティリティ (_table_exists, _get_max_date)。
        - 市場カレンダーに基づいて非営業日を取り扱う _adjust_to_trading_day。
        - raw_* の最終取得日取得関数: get_last_price_date, get_last_financial_date, get_last_calendar_date。
      - run_prices_etl の導入（差分計算、backfill_days デフォルト 3 日、fetch->save フロー）。（実装中の戻り値記述箇所が末尾で切れているため部分実装）
      - ETLResult データクラスを用意し、取得数・保存数・品質問題・エラーを集約して返却できる設計。
      - 品質チェックモジュールとの連携ポイント（quality モジュール想定）を設計に含む。

Security
- news_collector にて SSRF、XML 脅威、メモリ DoS（巨大レスポンス）等に対する複数の防御策を導入。
- jquants_client におけるネットワークリトライ・バックオフ、トークン自動更新により堅牢な API 呼び出しを実現。

Changed
- 初版リリースのため変更履歴はなし。

Fixed
- 初版リリースのため修正履歴はなし。

Deprecated
- なし

Removed
- なし

Notes
- 多くの保存処理は DuckDB 上で冪等性（ON CONFLICT DO UPDATE / DO NOTHING）を維持する設計になっているため、繰り返し実行してもデータ整合性が保たれる想定。
- jquants_client のレート制御はモジュール単位の単純スロットリングで実装しており、プロセス外での並列化には注意が必要（複数プロセスから同時に叩くとレート違反の可能性あり）。
- run_prices_etl の戻り値部分がコード末尾で切れている（len(records), ）ため、今後の修正で ETL の戻り値および ETLResult 連携部分の完成が望まれる。

Contributing
- バグ修正・機能追加・セキュリティ改善は issue/PR を通して行ってください。README/CONTRIBUTING は別途整備推奨。

ライセンス
- 本 CHANGELOG はコードから推測して作成しています。実際のライセンス情報はリポジトリの該当ファイルを参照してください。