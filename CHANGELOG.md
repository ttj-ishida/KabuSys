CHANGELOG
=========

すべての変更は Keep a Changelog 規約に準拠して記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

既知のバージョン
----------------

0.1.0 - 2026-03-17
+++++++++++++++++

Added
-----
- パッケージ初期リリース: kabusys (バージョン 0.1.0)
  - パッケージ公開情報:
    - src/kabusys/__init__.py にて __version__="0.1.0" を設定。モジュールエクスポート: data, strategy, execution, monitoring。
- 環境設定管理機能 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: .git または pyproject.toml を起点に自動検出（CWD 非依存）。
  - .env 読み込みロジック:
    - export KEY=val 形式対応、クォート内エスケープ、インラインコメント処理、コメント行無視等の堅牢なパーサを実装。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / DB パス等のプロパティを提供（必須キーは未設定時に ValueError を送出）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - duckdb/sqlite のデフォルトパスを提供。
    - is_live / is_paper / is_dev ヘルパーを提供。
- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティ:
    - レート制限（120 req/min）を固定間隔スロットリングで厳守する RateLimiter を実装。
    - 冪等・堅牢なリトライ戦略: 指数バックオフ、最大3回再試行、408/429/5xx に対するリトライ、429 の Retry-After 優先。
    - 401 受信時にリフレッシュトークンから id_token を自動更新して1回だけリトライする仕組みを実装（トークンキャッシュ共有）。
    - JSON デコードエラーの判定と明示的エラー報告。
  - データ取得関数:
    - fetch_daily_quotes: 株価日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 四半期財務データをページネーション対応で取得。
    - fetch_market_calendar: JPX マーケットカレンダーを取得。
    - いずれも id_token の注入を許可し、モジュールレベルのトークンキャッシュと組み合わせてテスト容易性を確保。
  - DuckDB への保存:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - 保存は冪等（ON CONFLICT DO UPDATE）で fetched_at を UTC（Z）で記録し Look-ahead Bias 対策。
    - PK 欠損行はスキップして警告ログ出力。
  - 型変換ユーティリティ:
    - _to_float / _to_int を実装。空値や不正形式に対する安全な変換を保証（小数の切り捨て回避等）。
- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード収集フローを実装:
    - fetch_rss: RSS の取得・パース（defusedxml を利用）・記事リスト生成。
    - preprocess_text: URL 除去と空白正規化。
    - _normalize_url / _make_article_id: トラッキングパラメータ除去後に正規化し、SHA-256（先頭32文字）で記事IDを生成して冪等性を確保。
    - SSRF 対策:
      - _validate_url_scheme で http/https のみを許可。
      - _is_private_host によるホスト/IP のプライベート判定（DNS 解決した A/AAAA をチェック）。
      - リダイレクト検査用 _SSRFBlockRedirectHandler と専用オープナーを使用してリダイレクト先の検証を実施。
    - レスポンス防御:
      - 最大受信サイズ制限（MAX_RESPONSE_BYTES=10MB）を実装し、gzip 解凍後も上限検査（Gzip-bomb 対策）。
    - DB 保存:
      - save_raw_news: INSERT ... RETURNING を用いたチャンクバルク挿入、トランザクションまとめ、挿入された記事IDリストを返す（ON CONFLICT DO NOTHING）。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク挿入で保存。ON CONFLICT DO NOTHING を使用して重複回避。
    - 銘柄コード抽出:
      - extract_stock_codes: 正規表現による 4 桁数字候補抽出と known_codes によるフィルタリング。
    - run_news_collection: 複数 RSS ソースを順次処理し、エラー耐性を持って各ソースごとに処理継続。
    - デフォルト RSS ソース: yahoo_finance (https://news.yahoo.co.jp/rss/categories/business.xml) を提供。
- DuckDB スキーマ・初期化 (src/kabusys/data/schema.py)
  - Data Platform の3層構造（Raw / Processed / Feature / Execution）に基づいたスキーマを定義。
  - raw_prices, raw_financials, raw_news, raw_executions を含む Raw Layer。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols を含む Processed Layer。
  - features, ai_scores を含む Feature Layer。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance を含む Execution Layer。
  - インデックス定義（頻出クエリ向け）を複数作成。
  - init_schema(db_path) にて必要な親ディレクトリ作成・全DDL実行・インデックス作成を行い、DuckDB 接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供（初期化は行わない）。
- ETL パイプライン基盤 (src/kabusys/data/pipeline.py)
  - ETLResult dataclass: ETL 実行結果・品質問題・エラーの集約と to_dict 変換を実装。
  - 差分更新ヘルパー:
    - テーブル存在チェック、テーブルの最大日付取得ユーティリティ。
    - get_last_price_date / get_last_financial_date / get_last_calendar_date。
    - 市場カレンダ補助: _adjust_to_trading_day（非営業日を直近の営業日に調整）。
  - run_prices_etl:
    - 差分更新ロジック: DB の最終取得日から backfill_days（デフォルト3日）前から再取得することで API の後出し修正を吸収。
    - J-Quants client と連携して取得・保存を行う仕組みを実装。
  - 設計方針ドキュメント化: 差分更新、バックフィル、品質チェック（quality モジュール連携）、テスト容易性のための id_token 注入など。
- 空モジュールのプレースホルダ
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py を配置し、今後の拡張を見据えたパッケージ構成を準備。

Security
--------
- XML パースに defusedxml を使用して XML-bomb 等の攻撃を防止。
- RSS フェッチでの SSRF 対策:
  - URL スキーム制限（http/https のみ）。
  - リダイレクト先のスキーム・ホスト検証。
  - プライベート / ループバック / リンクローカル / マルチキャストのホスト拒否。
- 外部 API 呼び出しに対して例外ハンドリングとリトライ戦略を実装し、予期せぬ公開エラーや過負荷を緩和。
- DB へのバルク挿入はトランザクションでまとめ、失敗時はロールバックして一貫性を保持。

Performance / Reliability
-------------------------
- API コールを固定間隔でスロットリングしてレート制限（120 req/min）に適合。
- リトライと指数バックオフにより一時的な障害に耐性を持たせる。
- DuckDB へのバルク INSERT でチャンク化（_INSERT_CHUNK_SIZE）し、SQL 文長とパラメータ数を制御。
- ON CONFLICT を活用して冪等性を確保し再実行を安全に実施可能。

Notes (既知事項・今後の課題)
-----------------------------
- pipeline.run_prices_etl は差分更新ロジックを実装済み（date_from 自動計算・backfill 対応）。ETLResult への統合やエラー詳細の収集は既存の ETLResult 構造と合わせて拡張予定。
- strategy / execution / monitoring の中核ロジックは今後実装予定（現段階ではパッケージ構成とインターフェースの準備を実施）。
- quality モジュール（品質チェック）の実装詳細は別モジュールで管理され、ETL パイプラインから利用される想定。

Breaking Changes
----------------
- 初回リリースのため既存バージョンとの互換性問題はなし。

作者・連絡
----------
- コードから推測した内容を元にCHANGELOGを作成しました。実際の変更履歴やリリースノートはプロジェクト実情に合わせて調整してください。