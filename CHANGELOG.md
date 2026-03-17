CHANGELOG
=========

すべての重要な変更履歴をここに記載します。フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（なし）

0.1.0 - 2026-03-17
------------------

Added
- パッケージ初版を追加（バージョン 0.1.0）。
  - パッケージ名: kabusys
  - __all__ に data/strategy/execution/monitoring を公開

- 環境変数・設定管理（kabusys.config）
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索（CWD に依存しない）。
  - .env パーサ:
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のエスケープ処理に対応
    - インラインコメント処理（クォートあり/なしの差異を考慮）
    - ファイル読み込み失敗時は警告を出力して無害にフォールバック
  - 上書き挙動:
    - .env を読み込む際、既存 OS 環境変数は保護（protected set）して上書きを制御
    - .env → .env.local の順で上書き（.env.local は override=True）
  - Settings クラスを提供（プロパティベースでアクセス）:
    - J-Quants / kabuステーション / Slack / DB パスなど主要設定を定義
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）
    - duckdb/sqlite パスを Path 型で返却
    - is_live / is_paper / is_dev のブールヘルパー

- J-Quants API クライアント（kabusys.data.jquants_client）
  - API 呼び出しユーティリティ実装:
    - ベース URL、クエリ/ボディサポート、JSON デコード検証
  - レート制限 (120 req/min) を固定間隔スロットリング（_RateLimiter）で実装
  - 再試行ロジック（指数バックオフ）を実装:
    - 最大リトライ回数 3 回
    - 再試行対象ステータス: 408, 429, 5xx
    - 429 の場合は Retry-After を優先して待機
  - 401 Unauthorized はトークン自動リフレッシュ（1回のみ）後に再試行
  - id_token キャッシュをモジュールレベルで保持してページネーション間で共有
  - ページネーション対応の取得関数:
    - fetch_daily_quotes（OHLCV 日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等設計、ON CONFLICT DO UPDATE）:
    - save_daily_quotes、save_financial_statements、save_market_calendar
    - fetched_at を UTC で記録して Look-ahead Bias を抑制
  - 型・変換ユーティリティ:
    - _to_float / _to_int（空値・不正値の安全変換）
  - 設計上の注記:
    - 最大タイムアウトやエラーハンドリングを明確化
    - ログ出力を充実（info/warning）

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードから記事を収集し raw_news に保存するフル実装
  - セキュリティ・堅牢性対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）
    - SSRF 対策:
      - リダイレクト時にスキームとホストを検査するカスタム RedirectHandler を導入
      - ホスト/IP がプライベート/ループバック/リンクローカル/マルチキャストかどうかを判定し拒否
      - 最終 URL の再検証も実施
    - URL スキームは http/https のみ許可
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設定し、超過時はスキップ
    - gzip 解凍後のサイズチェック（Gzip bomb 対策）
  - フィードパース:
    - channel/item のフォールバック検索
    - content:encoded を優先、なければ description を使用
    - pubDate を RFC2822 → UTC naive datetime に変換（失敗時は現在時刻で代替）
    - URL の正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）
    - 記事 ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保
  - DB 保存:
    - save_raw_news: チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を使用し、実際に挿入された記事IDを返す
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルク挿入（トランザクション、チャンク）
  - テキスト前処理（URL 除去、空白正規化）
  - 銘柄コード抽出ユーティリティ（4桁数字パターンと known_codes によるフィルタ）
  - 統合収集ジョブ run_news_collection を実装（各ソースは独立して失敗しても継続、保存結果を返す）
  - テスト容易性:
    - _urlopen をモック差替可能

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw / Processed / Feature）＋Execution 層のテーブルを定義
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 制約・チェック・主キーを付与（NULL/型/値範囲チェック）
  - インデックスを定義し、典型的なクエリに最適化（code×date スキャン、status 検索など）
  - init_schema(db_path) でファイルの親ディレクトリ自動作成後に全 DDL を実行（冪等）
  - get_connection(db_path) を提供（初期化は行わない）

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新フローを実装するためのユーティリティ群
  - ETLResult dataclass を導入（取得件数、保存件数、品質問題、エラー一覧を保持）
  - テーブル存在チェック・最大日付取得ユーティリティ（_table_exists, _get_max_date）
  - 市場カレンダー補助: 非営業日の場合に直近の営業日に調整する _adjust_to_trading_day
  - 差分更新補助:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date を提供
  - run_prices_etl を実装（差分取得、backfill_days による再取得、J-Quants からの取得および保存）
  - 設計方針:
    - 差分更新のデフォルト単位は「営業日1日分」
    - backfill_days により最終取得日の数日前から再取得して API の後出し修正を吸収
    - 品質チェック（quality モジュール）との連携ポイントあり（品質問題があっても ETL を継続）

Security
- RSS パーサで defusedxml を採用し、XMLに起因する攻撃を緩和
- SSRF 対策を複数レイヤで実装（リダイレクト検査・最終 URL 再検査・プライベート IP 判定）
- 外部 URL のスキーム検証（http/https のみ）
- レスポンスサイズ制限と Gzip 展開後チェックを導入（DoS/Zip bomb 対策）
- .env 読み込み時に OS 環境変数を保護（保護されたキーは上書きされない）

Testing / Extensibility
- HTTP 呼び出しやトークン取得に対して注入・モック化しやすい設計を意識:
  - jquants_client: id_token を引数で注入可能（テスト容易性）
  - news_collector: _urlopen を差し替え可能（テストでの HTTP 応答モック）
  - モジュールレベルのトークンキャッシュと強制再取得フラグを提供

Known Issues / Notes
- run_prices_etl の最後の return が不完全に見える（ソース末尾が切れている）。
  - 現状ファイルでは `return len(records),` のように saved の戻り値が欠けているため、呼び出し側で期待される (fetched, saved) タプルが得られない可能性があります。修正が必要です。
- 現状は初回リリースのため品質チェック（quality モジュール）の実装依存箇所や外部統合のテストが必要です。
- DuckDB の SQL 実行で使用している動的 SQL（プレースホルダ連結等）は SQL インジェクションに注意（現状は値をパラメータ化しているが長大なプレースホルダ列の生成は監査対象）。

Breaking Changes
- なし（初版リリースのため破壊的変更はありません）

Acknowledgements / References
- 設計上のドキュメント参照:
  - DataPlatform.md（ニュース・ETL 設計）
  - DataSchema.md（スキーマ設計）
  - 実装はこれら設計に基づいて行われています。

---

今後の予定（例）
- run_prices_etl の戻り値不備修正
- quality モジュールとの統合テスト強化
- strategy / execution / monitoring モジュールの実装拡充（現在はパッケージ公開のみ）