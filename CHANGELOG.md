Keep a Changelog に準拠した形式で、このコードベースから推測される変更履歴を日本語で作成しました。バージョンはパッケージ内の __version__ = "0.1.0" に合わせて初回リリースを 0.1.0 としています。実装の注意点・既知の問題点も併せて記載しています。

CHANGELOG.md
=============
すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog のガイドラインに従っています。

Unreleased
----------
- 次リリースで修正予定の既知の問題:
  - run_prices_etl の戻り値が不完全（関数末尾で saved 値が返されておらず、返り値の型注釈と実際の戻り値が一致しない）。ETL 結果として (fetched, saved) のタプルを返すべきところ、saved が返されていないため呼び出し側で不整合を引き起こす可能性がある。→ 修正予定。

0.1.0 - 2026-03-17
------------------
Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。公開サブパッケージ: data, strategy, execution, monitoring。バージョン: 0.1.0。

- 設定管理
  - 環境変数/設定管理モジュールを追加（src/kabusys/config.py）。
    - .env および .env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込み（優先順位: OS 環境 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .env 行パーサを実装（コメント行・export プレフィックス・引用符・インラインコメントの取り扱い、クォート内のエスケープ処理対応）。
    - 必須キーを取得する _require 関数、Settings クラスを提供（J-Quants / kabu / Slack / DB パス / 環境種別 / ログレベルなど）。
    - KABUSYS_ENV と LOG_LEVEL の許容値検証、is_live/is_paper/is_dev ユーティリティ。

- J-Quants クライアント
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - 株価日足（OHLCV）、財務データ、マーケットカレンダー取得の fetch_* 関数（ページネーション対応）。
    - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter 実装。
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408, 429, 5xx）、429 の Retry-After ヘッダ優先。
    - 401 受信時の id_token 自動リフレッシュ（1回のみ）と再試行、トークンキャッシュをモジュールレベルで保持。
    - DuckDB への保存関数 save_daily_quotes / save_financial_statements / save_market_calendar：fetched_at を UTC ISO で記録し、INSERT ... ON CONFLICT DO UPDATE により冪等性を確保。
    - 数値変換ユーティリティ（_to_float, _to_int）を実装し、不正値・空値に安全に対応。

- ニュース収集
  - RSS ベースのニュース収集モジュールを追加（src/kabusys/data/news_collector.py）。
    - RSS フィード取得（fetch_rss）、XML パース（defusedxml 使用で XML 攻撃対策）、gzip 解凍、レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES=10MB）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストがプライベート/ループバック/リンクローカルでないことを検査（直接 IP と DNS 解決の両方で判定）、リダイレクト時に事前検証するカスタム HTTPRedirectHandler を実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）、正規化 URL から SHA-256（先頭32文字）で記事IDを生成して冪等性を保証。
    - テキスト前処理（URL 除去・空白正規化）。
    - DuckDB への保存: save_raw_news（チャンク分割、トランザクション、INSERT ... ON CONFLICT DO NOTHING + RETURNING で実際に挿入された ID を返す）、save_news_symbols / _save_news_symbols_bulk（銘柄紐付けの一括保存）。
    - 銘柄コード抽出関数 extract_stock_codes（4桁数字パターン、既知コードセットでフィルタ、重複除去）。
    - 統合ジョブ run_news_collection を提供し、各ソースを独立して処理（1ソース失敗しても継続）し、既知銘柄に対する紐付けを一括登録。

- DuckDB スキーマ
  - データレイヤーのスキーマ定義と初期化モジュールを追加（src/kabusys/data/schema.py）。
    - Raw / Processed / Feature / Execution の各レイヤー向けテーブル定義（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance）。
    - テーブルの妥当性チェック（CHECK 制約）、外部キー、PRIMARY KEY を含むDDL。
    - よく使われるクエリ向けのインデックス定義を追加。
    - init_schema(db_path) によりディレクトリ自動作成とテーブル作成を行い、get_connection(db_path) を提供。

- ETL パイプライン
  - ETL パイプラインの骨組みを実装（src/kabusys/data/pipeline.py）。
    - 差分更新ロジック（DB 最終取得日に基づく date_from 自動算出、デフォルトの backfill_days=3）。
    - run_prices_etl 等のジョブ（fetch -> save の流れ）や schema/market_calendar のヘルパー (_table_exists, _get_max_date, _adjust_to_trading_day)。
    - ETL 実行結果を表現する ETLResult データクラス（品質チェック結果・エラー集約・辞書化メソッド）。
    - 最小データ開始日定義（_MIN_DATA_DATE）や市場カレンダーの先読み期間定義。

Security
- セキュリティに関する実装（主な項目）
  - XML パースに defusedxml を使用し XML Bomb 等の攻撃を防止。
  - RSS フィード取得で SSRF 対策を実装（スキーム検証、プライベートIP/ホスト検査、リダイレクト時の再検証）。
  - レスポンス読み取りで最大バイト数制限を設けメモリ DoS を防止。gzip 解凍後にもサイズチェックを実施。
  - .env 読み込み時、OS 環境変数の保護（protected set）および読み込みの上書き制御を実装。

Notable design decisions / details
- 冪等性優先:
  - raw_* テーブルへの保存は ON CONFLICT を使って更新/無視することで再実行可能に設計。
  - news の記事IDは正規化 URL のハッシュにより同一記事の多重登録を防止。
- API の堅牢性:
  - RateLimiter による固定間隔スロットリングで API レート制限を順守。
  - リトライ/バックオフ・トークン自動更新（401 リフレッシュ）で可用性を向上。
- DB 操作の効率化:
  - 大量挿入時はチャンク分割、トランザクションをまとめてオーバーヘッドを低減。
  - INSERT ... RETURNING を使い、実際に追加された行数/ID を正確に取得。

Fixed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Acknowledgements / Notes
- 一部の関数・モジュールはテストのためにモック差し替えを想定した設計（例: news_collector._urlopen のオーバーライド）。
- 実運用前に以下を確認することを推奨:
  - .env.example に基づく必須環境変数の設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など）。
  - DuckDB スキーマ初期化（init_schema）と適切な DB パス設定。
  - run_prices_etl 等 ETL 関数の返り値整合性（既知の問題参照）。
- 今後の改善候補:
  - pipeline.run_* の単体テストカバレッジ強化（ネットワーク依存コードの分離）。
  - ニュース解析の自然言語処理パイプライン（日本語固有の前処理と NE 抽出）。
  - モニタリング / Slack 通知統合の実装（monitoring サブパッケージの具現化）。

---  
（この CHANGELOG はコードベースの内容から推測して作成しています。実際の変更履歴やリリース日・詳細はリポジトリのコミット履歴やリリースノートに従って調整してください。）