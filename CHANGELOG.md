# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-17

初回リリース。日本株の自動売買基盤のコアとなるモジュール群を追加しました。以下は実装内容の要約です。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。公開 API として data, strategy, execution, monitoring をエクスポート。
  - バージョン番号を `0.1.0` として初期化。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。
  - 自動ロードを環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。
  - .env パースロジックを実装（コメント、export プレフィックス、クォート付き値、インラインコメントの扱い等に対応）。
  - 必須環境変数取得関数と Settings クラスを実装。J-Quants / kabuステーション / Slack / DB パス / 環境判定等のプロパティを提供。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許可値チェック）を追加。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）を実装。
  - リトライロジック（指数バックオフ、最大3回）を実装。HTTP 408/429/5xx を再試行対象に含める。
  - 401 Unauthorized を検出した場合、リフレッシュトークンで id_token を自動更新して 1 回だけリトライする仕組みを実装。
  - ページネーション対応のデータ取得関数を提供:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への冪等保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - データパース用のユーティリティ関数を提供（_to_float, _to_int）。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias を防止するトレーサビリティを確保。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news に保存する機能を実装。
  - セキュリティ対策:
    - defusedxml を使用した XML パース（XML Bomb 対策）。
    - SSRF 対策（許可スキームは http/https のみ、プライベートアドレスへの接続拒否、リダイレクト時の事前検証）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - URL 正規化によりトラッキングパラメータを除去（utm_ 等）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - テキスト前処理（URL 除去、空白正規化）を実装。
  - DuckDB への保存をトランザクションでまとめ、INSERT ... RETURNING を利用して実際に挿入された ID 数を返す:
    - save_raw_news
    - save_news_symbols / _save_news_symbols_bulk（記事と銘柄コードの紐付け）
  - 銘柄コード抽出ロジック（4桁数字、known_codes によるフィルタ）を実装。
  - run_news_collection により複数ソースの収集と紐付けを実行。ソース単位でエラーハンドリング。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用の完全なスキーマを追加（Raw / Processed / Feature / Execution 層）。
  - 各テーブルの DDL（制約・チェック）を定義。
  - インデックス定義（頻出クエリパターン向け）を追加。
  - init_schema(db_path) によりデータベースファイルの親ディレクトリ作成とテーブル初期化を行う機能を提供。
  - get_connection(db_path) で既存 DB への接続を提供。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計方針に基づく差分更新パイプラインの土台を実装。
  - ETLResult dataclass を実装し、品質チェック結果やエラー情報を構造化して返却可能に。
  - テーブル存在確認や最大日付取得などのユーティリティを実装。
  - market_calendar を参照して営業日に調整するヘルパーを追加。
  - raw_prices / raw_financials / market_calendar の最終取得日を返すヘルパー関数を追加。
  - run_prices_etl の骨格を実装（差分算出・backfill の取扱い、fetch & save 呼び出し）。

### Security
- 複数のセキュリティ対策を導入:
  - defusedxml を用いた安全な XML パース。
  - SSRF 対策（スキーム検証、プライベートアドレス検出、リダイレクト検査）。
  - レスポンスサイズ制限と Gzip 解凍後のサイズ検査。
  - URL 正規化でトラッキングパラメータを除去し、ID 再現性を向上。

### Design / Reliability
- 冪等性を重視:
  - DuckDB への保存は ON CONFLICT で更新またはスキップする実装。
  - ニュース保存は INSERT ... RETURNING を用いて実際に追加されたレコードを正確に把握。
- API 安定性:
  - 固定間隔のレートリミッタと指数バックオフを備えたリトライ機構。
  - トークン自動リフレッシュ（401 に対して 1 回のみ）を実装。
- テスト容易性:
  - fetch_rss の内部ネットワーク呼び出し用ハンドラ（_urlopen）を差し替え可能に実装。

### Known limitations / TODO
- strategy, execution, monitoring パッケージはプレースホルダ（__init__.py だけ）で、具体的な戦略・発注制御・監視ロジックは未実装。
- run_prices_etl はファイル末尾で途中までの実装となっている（戻り値のタプルが未完）。追加の ETL ジョブ（財務データ・カレンダーの完全な統合、品質チェックフローの呼び出し）は今後の作業対象。
- 単体テスト・統合テストの追加が必要（現在はモジュール設計でテストしやすさを考慮）。

---

今後の予定:
- ETL の完全実装（財務・カレンダーの差分ETL、品質チェックの実行とレポート化）。
- strategy / execution モジュールの実装（シグナル生成 → 注文 → 約定処理 → ポジション管理）。
- 監視・通知（Slack 連携）や運用向け改善（ログ周りの設定強化、メトリクス）を追加。

（必要であれば、各モジュールごとの細かな実装ポイントや潜在的な変更履歴候補を追記します。）