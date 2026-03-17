Keep a Changelog
=================

すべての重要な変更履歴をこのファイルで管理します。  
フォーマットは Keep a Changelog に準拠します。

※ 内容は与えられたコードベースから推測して記載しています（初期リリース想定）。

目次
----
- [未リリース](#unreleased)
- [0.1.0 - 2026-03-17](#010---2026-03-17)

## [Unreleased]

### Added
- （なし）

---

## [0.1.0] - 2026-03-17
初期リリース。日本株自動売買システム「KabuSys」のコア機能群を追加。

### Added
- パッケージの基本構成
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - モジュール区分: data, strategy, execution, monitoring（モジュール初期化ファイルを含む）

- 設定 / 環境変数管理（kabusys.config）
  - .env および .env.local からの自動ロード（プロジェクトルートの検出: .git または pyproject.toml を基準）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサーの実装：export 形式、クォート処理、インラインコメント処理に対応。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス等の設定プロパティを安全に取得。
  - KABUSYS_ENV / LOG_LEVEL の値検証（有効な値チェック）。
  - duckdb/sqlite のデフォルトパス設定をサポート。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダー取得の実装。
  - レートリミッタ実装（120 req/min を固定間隔で保証）。
  - 再試行（指数バックオフ）ロジック（最大リトライ3回、408/429/5xx を対象）。
  - 401 受信時の自動トークンリフレッシュ（1回のみ）とキャッシュ化された ID トークン共有（ページネーション間利用）。
  - ページネーション対応（pagination_key を用いたループ取得）。
  - 取得時刻（fetched_at）を UTC で記録して Look-ahead Bias を防止。
  - DuckDB への保存は冪等性を持たせた実装（INSERT ... ON CONFLICT DO UPDATE）。
  - 型変換ユーティリティ: _to_float / _to_int（堅牢な変換と不正値ハンドリング）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからの記事取得、前処理、DB 保存、銘柄紐付けの一連処理を実装。
  - 設計上の要点:
    - 記事ID は URL 正規化後の SHA-256 ハッシュ（先頭32文字）で生成し冪等性を確保。
    - トラッキングパラメータ（utm_* 等）を除去して URL 正規化。
    - defusedxml を用いて XML Bomb 等の攻撃を防止。
    - SSRF対策: スキーム検証（http/https のみ）、リダイレクト先検査、プライベートIP/ループバック/リンクローカルの排除。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10 MB）を導入しメモリ DoS を防止。gzip の取り扱いと解凍後のサイズチェックも実施。
    - テキスト前処理（URL除去、空白正規化）。
    - DuckDB へのバルク挿入はチャンク化してトランザクション内で実行、INSERT ... RETURNING により実際に挿入された ID を返す。
    - 銘柄コード抽出（4桁数字）と既知銘柄セットによるフィルタリング。
  - API: fetch_rss, save_raw_news, save_news_symbols, run_news_collection 等。

- DuckDB スキーマと初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution 層に分けたテーブル定義を追加（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等）。
  - 適切な制約（PRIMARY KEY, CHECK, FOREIGN KEY）や型を付与。
  - 検索性能を考慮したインデックス定義を追加。
  - init_schema(db_path) によりディレクトリ作成→テーブル作成→インデックス作成を行い、接続を返す API を提供。
  - get_connection(db_path) で既存 DB への接続を返す。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（差分取得）を中心とした ETL フローの骨格を実装。
  - バックフィル（backfill_days）をサポートし、API 後出し修正を吸収可能。
  - 市場カレンダーの先読み（_CALENDAR_LOOKAHEAD_DAYS）や最小データ開始日設定。
  - ETLResult dataclass により処理結果・品質問題・エラー情報を集約。
  - テーブル存在チェック、最終取得日取得ユーティリティ、取引日調整ロジックを提供。
  - run_prices_etl により差分取得→保存のワークフローを実装（取得/保存の数を返却）。

### Security
- RSS/XML 処理において defusedxml を使用して XML 関連攻撃を軽減。
- RSS フェッチ時に SSRF を防ぐための多層防御を実装:
  - URL スキーム検証（http/https のみ）
  - リダイレクトハンドラによるリダイレクト先チェック
  - ホスト名／IP のプライベートネットワーク判定（DNS 解決に基づく検査）
  - レスポンスサイズと gzip 解凍後サイズの上限チェック（リソース攻撃対策）
- 外部 API 呼び出しに対してレート制御・再試行戦略を実装し、サービス安定性を向上。

### Internal / Implementation notes
- 多くの保存処理は DuckDB のトランザクションと ON CONFLICT / RETURNING を活用して冪等性と正確な保存件数算出を実現。
- ロガー（logging）を各モジュールで利用し、運用時の監査・デバッグを容易にする。
- テスト容易性のため、一部 I/O 操作（例: _urlopen）の差し替えを想定した設計。

### Changed
- 初版のため適用なし。

### Deprecated
- 初版のため適用なし。

### Removed
- 初版のため適用なし。

### Fixed
- 初版のため適用なし。

---

注意事項
- 本 CHANGELOG はソースコードから推測して作成しています。実際のリリースノートとして使用する場合は、実装差分や意図した挙動と照合してください。
- ETL の一部関数・処理（例: pipeline.run_prices_etl の戻り値の形など）は実行環境や呼び出し側との整合性確認が必要です。