# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。

最新の変更履歴は常に Unreleased に記載します。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-17

初期リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - パッケージルート (src/kabusys/__init__.py) にバージョン `0.1.0` を追加。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 設定・環境変数管理 (`kabusys.config`)
  - .env/.env.local ファイルの自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト向け）。
  - .env 解析ロジックを実装（export プレフィックス対応、クォート処理、インラインコメントの挙動等）。
  - 環境変数必須チェック用の _require と Settings クラスを提供（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス、実行環境／ログレベルなど）。
  - 環境値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を実装。

- データ取得クライアント (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。株価日足、財務データ、JPX マーケットカレンダーの取得関数を提供。
  - API レート制限対応: 固定間隔スロットリング（120 req/min）を実装する内部 RateLimiter。
  - リトライ戦略: 指数バックオフ（最大3回）、対象ステータス(408, 429, 5xx)でリトライ。429 の場合は Retry-After ヘッダを優先。
  - 401 に対する自動トークンリフレッシュ（1 回のみ）を実装。トークン取得は get_id_token で行う。
  - ページネーション対応（pagination_key に基づく繰り返し取得）。
  - DuckDB への冪等保存関数を実装（save_daily_quotes, save_financial_statements, save_market_calendar）。各関数は ON CONFLICT（DO UPDATE）で重複更新を処理。
  - データ型変換ユーティリティ (_to_float, _to_int) を実装し、異常値・空値に対する寛容な処理を行う。
  - データ取得時に「いつデータを知り得たか」を記録する fetched_at を UTC で付与（Look-ahead Bias への配慮）。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィードからニュース記事を取得・前処理・DuckDB へ保存する機能一式を実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection など）。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、ホストのプライベートアドレス判定、リダイレクト先の事前検査（カスタム HTTPRedirectHandler）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、読み込み超過は拒否。gzip 解凍後のサイズチェックも実施。
  - 記事 ID は URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保（utm_* 等のトラッキングパラメータ除去、クエリソート、フラグメント削除）。
  - テキスト前処理（URL 除去・空白正規化）を実装。
  - INSERT ... RETURNING を用いた新規挿入判定、チャンク分割挿入（トランザクション内）による効率化。
  - 銘柄コード抽出ユーティリティ（4桁数字）と、既知銘柄セットと突合する抽出ロジックを実装。
  - run_news_collection により複数 RSS ソースを順に処理し、個別ソース失敗時も他ソースは継続する堅牢な処理フローを提供。

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - DataPlatform 設計に基づくスキーマを定義（Raw / Processed / Feature / Execution レイヤー）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブルを定義。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブルを定義。
  - features, ai_scores 等の Feature テーブルを定義。
  - signals, signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブルを定義。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）およびインデックスを定義。
  - init_schema(db_path) によりファイル親ディレクトリの自動生成、全 DDL とインデックスの作成（冪等）を実行。
  - get_connection(db_path) により既存 DB へ接続するユーティリティを提供。

- ETL パイプライン (`kabusys.data.pipeline`)
  - ETL の設計要件に従った基盤を実装（差分更新、バックフィル、品質チェックの呼び出しポイントなど）。
  - ETL 実行結果を表す dataclass ETLResult を追加（品質問題・エラー情報の集約、辞書化ユーティリティ）。
  - テーブル存在確認、最大日付取得ユーティリティ（_table_exists, _get_max_date）を実装。
  - market_calendar を参照して営業日に調整するヘルパー (_adjust_to_trading_day) を実装。
  - 差分ETL のヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - run_prices_etl を実装（差分判定、バックフィル、J-Quants からの取得 → 保存の流れ）。（初回ロードは _MIN_DATA_DATE=2017-01-01 を使用）
  - pipeline は品質チェックモジュール (kabusys.data.quality) と連携する設計になっている（quality モジュールは品質判定ロジックを別途実装）。

- その他
  - デフォルト DB パス: DuckDB は data/kabusys.duckdb、SQLite は data/monitoring.db をデフォルトとして設定。
  - ログ出力（各処理での info/warning/exception ログ）を多用して監査・デバッグを容易に。

### Security
- RSS/XML 周りで以下の対策を導入:
  - defusedxml を使用した安全な XML パース
  - SSRF 対策（スキーム検証、プライベートホスト判定、リダイレクト検査）
  - レスポンスサイズ制限と gzip 解凍後の再チェック（メモリ DoS、gzip bomb 対策）

### Notes / Known limitations
- strategy/execution/monitoring パッケージはパッケージ階層を用意した状態（初期スタブ）で、戦略ロジックや発注実行ロジックの実装は別途。
- quality モジュールは参照されているが、品質チェックの詳細実装は別途作成される想定。
- run_prices_etl 等の ETL 関数は主要なロジックを実装しているものの、ジョブスケジューリングや並列実行、詳細な品質ルールは今後の改善対象。
- J-Quants API のレート制御は単一プロセス内での実装（_RateLimiter）。分散実行環境では追加の制御が必要。
- SQLite 用の監視 DB との連携や Slack 通知等は設定項目・トークンを用意しているが、通知処理はこのリリースには含まれていない。

### Breaking Changes
- 初版のため破壊的変更はなし。

---

将来的な改善案（非網羅）
- 分散環境・複数ワーカーにおけるグローバルなレートリミッタ実装（外部ストアを利用）
- news_collector のフィードフェッチ並列化（ソース毎のタイムアウト・リトライ設定拡張）
- pipeline の完全な ETL ワークフロー実装（品質チェックのルールセット追加、アラート・自動ロールバック）
- strategy / execution の実装（バックテスト、paper/live 切替、kabu ステーション接続）

以上。