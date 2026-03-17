# CHANGELOG

すべての重要な変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の形式に従っています。  

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- セキュリティ (Security)

## [0.1.0] - 2026-03-17

初回リリース。

### 追加
- パッケージ全体
  - kabusys パッケージを追加。バージョンは `0.1.0`（src/kabusys/__init__.py）。
  - サブパッケージ構成: data, strategy, execution, monitoring を公開。

- 環境設定 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml で探索して .env / .env.local を自動読み込み。
    - OS 環境変数を保護するための上書き制御（override/protected）。
    - 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みを無効化可能。
  - .env パーサーの強化:
    - export キーワード対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメント処理。
  - Settings によるプロパティ:
    - J-Quants / kabu ステーション / Slack / DB パス等の必須・既定値設定。
    - KABUSYS_ENV / LOG_LEVEL の検証と convenience プロパティ（is_live, is_paper, is_dev）。

- J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API からのデータ取得機能を実装:
    - 株価日足 (fetch_daily_quotes)
    - 財務データ (fetch_financial_statements)
    - JPX マーケットカレンダー (fetch_market_calendar)
  - 認証: リフレッシュトークンから ID トークンを取得する get_id_token を実装。モジュールレベルのトークンキャッシュを導入。
  - レート制御:
    - 固定間隔スロットリングによる 120 req/min 制限を実装（_RateLimiter）。
  - 再試行ロジック:
    - 指数バックオフ、最大 3 回リトライ。対象は 408/429/5xx 系。
    - 429 の場合は Retry-After を優先。
    - 401 受信時はトークンを自動リフレッシュして 1 回リトライ（無限再帰防止処理あり）。
  - データ保存:
    - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を提供。
    - 保存は冪等（INSERT ... ON CONFLICT DO UPDATE）で重複を排除。
    - 取得時刻 (fetched_at) を UTC ISO 形式で記録し、Look-ahead Bias のトレースを可能に。
  - 入力数値変換ユーティリティ: _to_float, _to_int（安全な数値変換と不正値処理）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS からニュース記事を収集し raw_news / news_symbols に保存する一連の機能を実装。
  - 設計上の特徴:
    - 記事ID は URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保。
    - トラッキングパラメータ（utm_ 等）を除去して URL 正規化を実施。
    - defusedxml を用いた XML パース（XML Bomb 等の対策）。
    - SSRF 対策:
      - URL スキーム検証（http/https のみ許可）。
      - リダイレクト先のスキームとホスト検証を行うカスタム RedirectHandler を実装。
      - ホスト名の DNS 解決結果や直接指定 IP の判定でプライベートアドレス/ループバック等を検出し拒否。
    - レスポンス長の制限（MAX_RESPONSE_BYTES、デフォルト 10 MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - ヘッダの Content-Length による事前チェック。
    - チャンク化されたバルク INSERT（_INSERT_CHUNK_SIZE）およびトランザクションでパフォーマンスと整合性を確保。
    - INSERT ... RETURNING を用いて実際に挿入された ID/件数を正確に取得。
  - 公開 API:
    - fetch_rss(url, source, timeout): RSS をパースして NewsArticle リストを返す。
    - save_raw_news(conn, articles): raw_news テーブルに保存し新規挿入 ID を返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付け保存（ON CONFLICT DO NOTHING、RETURNING で正確な件数取得）。
    - extract_stock_codes(text, known_codes): テキストから 4 桁銘柄コードを抽出（既知コードとの照合、重複除去）。
    - run_news_collection: 複数ソースを横断して収集・保存・銘柄紐付けを行うジョブ。ソース単位で障害を分離して継続。

- スキーマ定義 / 初期化 (src/kabusys/data/schema.py)
  - DuckDB のスキーマを DataSchema.md に基づき実装（Raw / Processed / Feature / Execution レイヤー）。
  - 主要テーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約（PK/FOREIGN KEY/チェック制約）を定義し、データ品質の前段担保を実装。
  - よく使われるクエリ用のインデックスを定義（idx_prices_daily_code_date など）。
  - init_schema(db_path) により DB ファイル作成（親ディレクトリ自動作成含む）と全テーブル・インデックス作成を行う。
  - get_connection(db_path) で既存 DB への接続を取得可能。

- ETL パイプライン (src/kabusys/data/pipeline.py)
  - 差分更新を行う ETL ジョブの基盤を実装。
  - 特徴:
    - DB の最終取得日を使った差分取得の自動計算（backfill_days デフォルト 3 日で後出し修正を吸収）。
    - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS）。
    - 品質チェックモジュール（quality）との連携（重大度の扱いは ETL 側で判断可能）。
    - テスト容易性を意識した設計（id_token の注入など）。
  - 公開ユーティリティ:
    - get_last_price_date, get_last_financial_date, get_last_calendar_date: 各テーブルの最終取得日取得。
    - run_prices_etl: 株価差分 ETL 実装（取得→保存→ログ）。（注: ファイル末尾で return の途中で切れているが、設計に基づく差分 ETL の実装あり）

### セキュリティ
- ニュース収集モジュールで SSRF 対策を導入:
  - URL スキーム制限、プライベート IP / ループバック判定、リダイレクト先の検査を実施。
  - defusedxml による XML パースで XML に対する攻撃を軽減。
  - レスポンスサイズ制限と gzip 解凍後の再チェックで DoS / 圧縮爆弾を防御。
- .env 読み込み時に OS 環境変数を保護する設計（protected set）。

### テスト性・運用性
- 関数設計でテストしやすさを考慮:
  - jquants_client の id_token を注入可能。
  - news_collector の _urlopen をテストでモック可能に実装。
- ログ出力（logger）を各所に挿入し、運用時のトラブルシュートを容易に。

### 既知の制限
- pipeline.run_prices_etl の末尾がコード断片で終了しており、戻り値の返却箇所が途中で切れている（リリース時点の実装断片に注意）。実際のアプリケーションで使用する場合は該当箇所の最終化を確認してください。
- strategy / execution / monitoring の各 __init__.py は現状空であり、各レイヤーの具体的実装はこれから。

## 以前のリリース
- なし（初回リリース）。

もし CHANGELOG に追加してほしい項目（例: 日付修正、実装の細かな言及、影響範囲の追記等）があれば指示してください。