CHANGELOG
=========

すべての重要な変更は Keep a Changelog の慣例に従って記録しています。
（https://keepachangelog.com/ja/ より参照）

[0.1.0] - 2026-03-18
-------------------

Added
- 初回リリース: パッケージ "kabusys" を追加。
  - パッケージ公開バージョンは src/kabusys/__init__.py にて __version__ = "0.1.0"。
  - サブパッケージ想定: data, strategy, execution, monitoring（strategy/execution/monitoring は初期状態では空の __init__）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を基準）により CWD に依存しない読み込み。
  - .env のパースは以下をサポート:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式の対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォートの有無で挙動を変える）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数を保護する protected オプションを採用。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト向け）。
  - Settings クラスを提供し、アプリケーション設定（J-Quants リフレッシュトークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）をプロパティ経由で取得。
  - KABUSYS_ENV / LOG_LEVEL の値検証および便利プロパティ（is_live / is_paper / is_dev）を実装。

- J-Quants クライアント (kabusys.data.jquants_client)
  - API 呼び出しユーティリティを実装（BASE_URL/認証/JSON パース）。
  - レート制限制御（固定間隔スロットリング）を実装し、J-Quants の 120 req/min を厳守する設計。
  - リトライロジック（指数バックオフ、最大 3 回、対象ステータス 408/429/5xx）を実装。
  - 401 Unauthorized を検出した際の自動トークンリフレッシュ（1 回のみ）と再試行。
  - ID トークンのモジュールレベルキャッシュを実装（ページネーション間で共有可能）。
  - ページネーション対応の取得関数を提供:
    - fetch_daily_quotes（株価日足: OHLCV）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes / save_financial_statements / save_market_calendar は ON CONFLICT DO UPDATE により重複を排除。
    - PK 欠損行はスキップし警告ログを出力。
  - データ変換ユーティリティ (_to_float, _to_int) を実装し入力値の堅牢な扱いをサポート。

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードからの記事収集機能を実装（デフォルトソースに Yahoo Finance を設定）。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防止。
    - URL スキーム検証（http/https のみ許可）とプライベートホスト判定による SSRF 対策。
    - リダイレクト検査（専用 HTTPRedirectHandler を導入）によりリダイレクト先の検証を実施。
    - レスポンス受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）を設け、受信時・gzip 解凍後ともにチェック。
  - URL 正規化・トラッキングパラメータ除去（utm_ 等）により記事ID を SHA-256（先頭32文字）で生成し冪等性を担保。
  - テキスト前処理（URL 除去・空白正規化）と pubDate の堅牢なパース。
  - DB 保存:
    - save_raw_news: チャンク単位で INSERT ... ON CONFLICT DO NOTHING RETURNING id を用い、実際に挿入された記事IDのみを返す。トランザクション単位での処理とロールバック対応。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT で重複排除）し挿入件数を正確に返す。
  - 銘柄コード抽出ユーティリティ extract_stock_codes（4桁数値を候補にして known_codes でフィルタ、重複除去）。
  - run_news_collection: 複数 RSS ソースを走査し記事の取得→保存→銘柄紐付けを実行。個別ソースは独立してエラーハンドリング。

- DuckDB スキーマ定義と初期化 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution 層にまたがるテーブル DDL を定義:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 頻出クエリ向けのインデックス定義を追加（code/date、status 等）。
  - init_schema(db_path) によりディレクトリ作成を含めた初期化を行い、全テーブルとインデックスを作成（冪等）。
  - get_connection(db_path) で既存 DB へ接続するユーティリティを提供。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL 実行結果を表す ETLResult dataclass を実装（品質チェック結果・エラー収集を含む）。
  - データベースの最終取得日取得ユーティリティ（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 非営業日の調整ロジック (_adjust_to_trading_day) を実装（market_calendar を参照）。
  - run_prices_etl: 差分更新ロジック（最終取得日からの backfill、デフォルトバックフィル日数 = 3）と J-Quants からの取得→保存の流れ（fetch_daily_quotes / save_daily_quotes）を実装。取得範囲の自動算出・ログ出力あり。
  - ETL 設計方針として品質チェックは Fail-Fast にならない実装（処理継続し呼び出し元に判断を委ねる）。

Security
- ニュース収集での SSRF 対策、defusedxml の採用、レスポンスサイズ制限、URL スキーム検査。
- J-Quants クライアントでのタイムアウト・再試行制御・トークンリフレッシュにより外部 API 呼び出しの堅牢性を強化。

Performance / Reliability
- API 呼び出しに対するレートリミッタ、指数バックオフ、Retry-After の尊重（429 時）。
- ID トークンキャッシュ・ページネーション対応により効率的なデータ取得。
- DuckDB 側は ON CONFLICT / チャンク挿入 / トランザクションにより冪等性とバルク処理性能を確保。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Known issues / TODO
- strategy、execution、monitoring パッケージは骨組みのみで具体的な実装は未着手（今後の実装予定）。
- pipeline モジュールは ETL 基盤を提供しているが、品質チェックモジュール（kabusys.data.quality）との統合および全 ETL ジョブ（financials / calendar など）の完全なワークフロー化は継続作業が必要。
- ドキュメント参照 (DataPlatform.md, DataSchema.md 等) がコード内に言及されているが、リポジトリ内に同梱されていない場合は補完が必要。
- （実装注意）pipeline.run_prices_etl の戻り値や一部の実装は追加レビュー・テストにて調整の余地あり（実装途中のスニペットが存在する可能性）。

Acknowledgements / Notes
- 各モジュールはテスト容易性を意識して設計（例: _urlopen の差し替えや id_token の注入が可能）。
- 実運用では Secrets 管理、監視、リトライポリシーのチューニング、バックフィル戦略の検証、及び DB マイグレーション方針の確立を推奨。

(作成者注: 上記は提供されたソースコードから推測してまとめた初期 CHANGELOG です。実際のリリースノートにはコミットハッシュや差分、影響範囲の詳細を追記してください。)