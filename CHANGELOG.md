CHANGELOG
=========

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。

[0.1.0] - 2026-03-17
--------------------

初回リリース — KabuSys: 日本株自動売買システムの基盤実装を追加。

Added
- パッケージ初期化
  - src/kabusys/__init__.py によりモジュール公開（data, strategy, execution, monitoring）とバージョン ("0.1.0") を定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local および OS 環境変数から設定を自動読み込み（プロジェクトルート判定: .git または pyproject.toml）。
    - .env パーサを実装（コメント行、export 形式、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱いに対応）。
    - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テスト用）。
    - 必須環境変数取得用 _require()、Settings クラスを提供（J-Quants、kabuステーション、Slack、DBパス、環境/ログレベルの検証を含む）。
    - KABUSYS_ENV / LOG_LEVEL の値検証を実装（許容値は定義済み）。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - /token/auth_refresh による id_token 取得（get_id_token）。
    - レート制限（120 req/min）を守る固定間隔スロットリング実装 (_RateLimiter)。
    - 冪等でのページネーション対応 fetch_* 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（JPXカレンダー）
    - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダ優先。
    - 401 受信時はトークン自動リフレッシュして 1 回リトライ（無限再帰回避のため allow_refresh フラグ）。
    - モジュールレベルの id_token キャッシュを共有（ページネーション間の再利用）。
    - DuckDB への保存関数（冪等性を担保）:
      - save_daily_quotes: raw_prices に INSERT ... ON CONFLICT DO UPDATE
      - save_financial_statements: raw_financials に INSERT ... ON CONFLICT DO UPDATE
      - save_market_calendar: market_calendar に INSERT ... ON CONFLICT DO UPDATE
    - fetched_at を UTC ISO8601 で記録し、Look-ahead Bias トレースを可能に。
    - データ型安全化ユーティリティ (_to_float, _to_int)。

- ニュース収集（RSS）モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィード取得および前処理・DB 保存の一連処理を実装。
    - セキュリティ/堅牢化:
      - defusedxml を用いた XML パース（XML Bomb 等対策）。
      - SSRF 対策: URL スキーム検証、ホストがプライベート/ループバック/リンクローカル/マルチキャストかを判定して拒否。
      - リダイレクト時にも検査を行うカスタムハンドラ (_SSRFBlockRedirectHandler)。
      - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入し読み込みで超過を検出。
      - gzip 圧縮の扱い（解凍後もサイズを検査）。
      - HTTP ヘッダ Content-Length の事前チェック。
    - URL 正規化と記事 ID の生成:
      - トラッキングパラメータ（utm_* 等）を除去、キーソートして正規化。
      - 正規化 URL の SHA-256 から先頭32文字を記事IDとして利用（冪等性確保）。
    - テキスト前処理（URL 除去、空白正規化）と pubDate パース（タイムゾーンを UTC に正規化）。
    - DB 保存（DuckDB）:
      - save_raw_news: チャンク化してトランザクション内で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDを返す。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをまとめて挿入、RETURNING を使って挿入件数を正確に取得。
    - 銘柄コード抽出:
      - 4桁数字パターンから既知コード集合に基づき抽出（重複除去）。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution 各レイヤーのテーブル DDL を定義。
    - raw_prices, raw_financials, raw_news, raw_executions などの Raw テーブル。
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
    - features, ai_scores 等の Feature テーブル。
    - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
    - 適切なチェック制約（CHECK）、主キー、外部キーを指定。
    - パフォーマンス向けインデックス定義群を追加。
    - init_schema(db_path) によりディレクトリ作成 → 全DDL・インデックス適用を行い接続を返す（冪等）。
    - get_connection(db_path) により既存 DB へ接続するヘルパを提供。

- ETL パイプライン（基礎）
  - src/kabusys/data/pipeline.py
    - ETLResult dataclass により ETL 実行結果（取得数、保存数、品質問題・エラー）を構造化。
    - 品質チェック結果の表現（quality.QualityIssue を参照）を考慮。
    - DB 存在チェック、テーブル最大日付取得ユーティリティ。
    - market_calendar を用いた営業日補正ヘルパ (_adjust_to_trading_day)。
    - 差分更新ヘルパ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
    - run_prices_etl の基本実装（差分更新ロジック、backfill_days による再取得の扱い、J-Quants からの取得と保存を結合）。

Security
- SSRF 対策、XML パースの安全化（defusedxml）、HTTP リダイレクト検査、レスポンスサイズ制限などを設計として組み込み。
- J-Quants クライアントは認証トークンの自動リフレッシュとキャッシュを実装し、トークン漏洩・誤操作リスク軽減には留意する設計。

Performance & Reliability
- API レート制限（120 req/min）を守る専用 RateLimiter を導入。
- 冪等（ON CONFLICT DO UPDATE / DO NOTHING）で再実行耐性を確保。
- リトライ（指数バックオフ）や 429 の Retry-After 処理により外部 API 呼び出しの堅牢性を高めた。
- DB バルク挿入はチャンク化してトランザクション内で実行、INSERT ... RETURNING で実際に挿入された行を正確に取得。

Testing / Extensibility
- config: KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト時の自動環境読み込みを無効化可能。
- news_collector: _urlopen をモックして外部アクセスを差し替え可能（テストフレンドリー）。
- jquants_client の id_token 注入等によりユニットテストが容易。

Notes / Design Decisions
- データの取得時刻（fetched_at）は UTC で記録し、Look-ahead Bias を避けるため「いつデータがシステムに到達したか」を明示的にトレース可能にしている。
- 銘柄コード抽出は簡潔な4桁数字マッチと既知コードセットでフィルタリングする方針。
- ETL は Fail-Fast を採らず、可能な限り全データを収集して品質チェックに委ねる設計。

Known issues / TODO
- strategy, execution, monitoring パッケージはパッケージ公開対象として存在するが、具象実装はこのリリースで含まれていない（スケルトン/プレースホルダ）。
- pipeline モジュールは ETL の骨組み（run_prices_etl 等）を実装しているが、品質チェック（quality モジュール）や他の ETL ジョブとの統合（financials / calendar の差分ロジックの呼び出し等）は引き続き整備が必要。
- 実稼働に際しては環境変数（API トークン、kabuAPI パスワード、Slack トークン等）の管理と権限周りの運用が必要。

---

今後のリリースでは以下を予定:
- strategy / execution / monitoring の具体的な実装（注文管理、約定処理、ポートフォリオ再配分、監視/アラート）。
- 品質チェックモジュール quality の実装と ETL への組み込み。
- より細かなログ・メトリクス、エラーレポーティングの強化。