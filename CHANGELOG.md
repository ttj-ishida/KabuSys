CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に従い、セマンティックバージョニングを採用します。

Unreleased
----------

（なし）


[0.1.0] - 2026-03-17
--------------------

初回公開リリース。日本株自動売買システム「KabuSys」の基盤モジュールを実装。

Added
- パッケージ基盤
  - kabusys パッケージの初期化（__version__ = 0.1.0、公開サブパッケージ定義）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み（プロジェクトルートの検出は .git または pyproject.toml を使用）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env 行パーサ実装（export プレフィックス、クォート内エスケープ、インラインコメントの考慮）。
  - Settings クラスを提供し、必要な環境変数の取得（J-Quants, kabuステーション, Slack 等）や型変換、妥当性検査（KABUSYS_ENV、LOG_LEVEL）を行う。
  - デフォルトの DB パス（DUCKDB_PATH、SQLITE_PATH）や環境判定ユーティリティ（is_live / is_paper / is_dev）を提供。
- J-Quants API クライアント (kabusys.data.jquants_client)
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数群を実装（ページネーション対応）。
  - レートリミッタ実装（120 req/min 固定間隔スロットリング）。
  - リトライ戦略（指数バックオフ、最大 3 回、対象: 408/429/5xx）。429 の場合は Retry-After ヘッダ優先。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの id_token キャッシュ。
  - DuckDB への保存関数 save_* を提供し、ON CONFLICT DO UPDATE による冪等性を確保。
  - データ取得時に fetched_at を UTC タイムスタンプで記録し、Look-ahead Bias を防止する設計。
- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集し raw_news に保存する fetch_rss / save_raw_news / save_news_symbols を実装。
  - 記事IDを正規化済み URL の SHA-256（先頭32文字）で生成し冪等性を保証。
  - URL 正規化でトラッキングパラメータ（utm_ 等）を除去、クエリソート、フラグメント削除を実施。
  - defusedxml を用いた XML パース（XML Bomb 等に対する安全対策）。
  - SSRF 対策：取得前のホスト確認、リダイレクト時のスキーム/プライベートアドレス検査（カスタム RedirectHandler）、http/https 限定。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ検査（Gzip bomb 対策）。
  - DB へはチャンク化（_INSERT_CHUNK_SIZE）したバルク INSERT をトランザクションで行い、INSERT ... RETURNING により実際に挿入された件数を返す。
  - テキスト前処理（URL 除去、空白正規化）と記事本文から銘柄コード抽出（4桁数字、既知コードフィルタリング）。
- DuckDB スキーマ定義 (kabusys.data.schema)
  - Raw / Processed / Feature / Execution の多層スキーマ定義を実装（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, features, ai_scores, signals, signal_queue, orders, trades, positions 等）。
  - 各種制約（PRIMARY KEY, CHECK, FOREIGN KEY）およびクエリパフォーマンス向けインデックスを定義。
  - init_schema(db_path) により冪等的にテーブルとインデックスを作成するユーティリティを提供。parent ディレクトリの自動作成対応。
  - get_connection(db_path) による既存 DB への接続取得を提供。
- ETL パイプライン基盤 (kabusys.data.pipeline)
  - ETLResult dataclass による ETL 実行結果の構造化（品質問題・エラーの集約、辞書化ユーティリティ）。
  - テーブル存在確認・最終取得日取得ユーティリティ。
  - market_calendar を用いた営業日補正ロジック（_adjust_to_trading_day）。
  - 差分更新の考え方に基づく run_prices_etl の実装（最終取得日からの backfill を考慮して差分取得→保存を実行）。
  - 設計上の方針（差分更新、backfill、品質チェックは Fail-Fast ではなく呼び出し元判断）を反映。

Security
- defusedxml を利用した安全な XML パースを採用。
- RSS 取得に対して SSRF 防止ロジックを導入（スキーム検証、プライベートアドレス判定、リダイレクト検査）。
- .env 読み取りでのファイル読み込み失敗は警告にとどめ処理継続。

Performance
- J-Quants API クライアントにレートリミッタとページネーション対応を実装し、レート制限遵守・効率的取得。
- ニュース保存はチャンク化＋1トランザクションで実行し、オーバーヘッドを低減。
- id_token をモジュールキャッシュしページネーション間で再利用。

Design / Reliability
- DuckDB への書き込みは ON CONFLICT DO UPDATE / DO NOTHING を利用して冪等性を確保。
- 取得時刻（fetched_at）や記事の生成方法によりデータソースの「システムがいつ知り得たか」をトレース可能に設計。
- ネットワーク障害や一時的エラーに対するリトライ・バックオフを実装。

Internal / Misc
- 各モジュールはロギング（logger）を使用し情報・警告・例外を適切に出力。
- 一部モジュール（strategy, execution, monitoring）のパッケージプレースホルダを配置（将来的な実装予定）。

Fixed
- 初回リリースのため該当なし。

Notes / Known limitations
- 現時点で execution / strategy / monitoring の具体的実装は含まれていません（パッケージ名は定義済み）。
- DuckDB を利用するため、運用環境でのファイルパス/パーミッションやバックアップ方針の検討が必要です。
- RSS フィードの多様なフォーマット（名前空間付き等）に対しフォールバック対応はあるものの、すべてのケースを網羅しているわけではありません。

今後の予定（例）
- execution モジュールの kabuステーション連携（注文送信・約定反映）の実装。
- monitoring / alerting（Slack 通知など）機能の追加。
- 品質チェック（kabusys.data.quality）の拡充と ETL 実行時の自動集計・レポート出力。

----- 

この CHANGELOG はソースコードの実装内容から推測して作成しています。実際のリリースノートとして公開する前に、必要に応じて日付や項目の調整を行ってください。