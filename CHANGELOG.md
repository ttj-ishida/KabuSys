# Changelog

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

なお、本CHANGELOGは提供されたコードベースの内容から推測して作成しています。実際のコミット履歴とは差異がある可能性があります。

## [0.1.0] - 2026-03-17

初回リリース（ベースライン実装）。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ構成
  - kabusys パッケージを導入し、主要サブパッケージとして data, strategy, execution, monitoring を公開。
  - バージョン情報: `kabusys.__version__ = "0.1.0"`。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを導入。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を起点）を採用し、CWD に依存しない自動ロードを実現。
  - .env と .env.local の読み込み順序をサポート（OS 環境変数を優先、.env.local は上書き可能）。
  - 読み込みを無効化するための環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加（テスト用）。
  - .env パース機能の強化（export 形式、クォート内エスケープ、インラインコメントの扱い）。
  - Settings クラスを導入し、アプリ設定をプロパティ経由で取得可能に：
    - J-Quants / kabu ステーション / Slack / DB パス等の必須・既定値を定義。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値のチェック）。
    - パスは Path 型で返却（expanduser を考慮）。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本機能:
    - ID トークン取得（get_id_token）
    - 日足（fetch_daily_quotes）、財務データ（fetch_financial_statements）、マーケットカレンダー（fetch_market_calendar）の取得。
    - ページネーション対応およびページ間でのトークンキャッシュ共有。
  - 信頼性・レート制御:
    - 固定間隔スロットリングでレート制限（120 req/min）を守る RateLimiter を実装。
    - 再試行ロジック（指数バックオフ、最大3回、HTTP 408/429/5xx を対象）。
    - 401 受信時は自動トークンリフレッシュを行い1回リトライ（無限再帰を防止）。
  - 永続化（DuckDB）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - INSERT ... ON CONFLICT DO UPDATE による冪等保存を実装（重複更新対応）。
    - fetched_at を UTC タイムスタンプで記録し、データ取得時刻をトレース可能に。
  - データ整形ユーティリティ:
    - _to_float / _to_int による安全な型変換（空値・不正値は None を返す、float文字列の int 変換の扱いなど）。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィード収集とデータベース保存のフルパイプラインを実装。
  - セキュリティ・堅牢性:
    - defusedxml を使用して XML Bomb 等対策。
    - SSRF 対策: リダイレクト先ごとにスキームとホスト/IP の検査を行う `_SSRFBlockRedirectHandler` を導入。
    - URL スキーム検証（http/https のみ許可）、プライベートアドレス検出によるブロック。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後のサイズチェック。
  - 記事処理:
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、クエリソート、フラグメント除去）。
    - 記事ID は正規化後 URL の SHA-256 の先頭32文字で生成（冪等性確保）。
    - テキスト前処理（URL 除去、空白正規化）。
    - pubDate のパース（タイムゾーン処理）とフォールバック。
  - DB 保存:
    - save_raw_news: チャンク INSERT + トランザクション + INSERT ... RETURNING で実際に挿入された記事IDを返す（ON CONFLICT DO NOTHING）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク処理で永続化し、挿入数を正確に返す。
  - 銘柄コード抽出:
    - 日本株の4桁コード抽出ロジック（正規表現）と known_codes によるフィルタリング。

- DuckDB スキーマ管理（kabusys.data.schema）
  - DataSchema.md 相当の3層（Raw / Processed / Feature）+ Execution 層のテーブル定義を含む DDL を実装。
  - テーブル一覧（例）:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックス定義（頻出クエリ向け）。
  - init_schema(db_path) によりディレクトリ自動作成と全DDL実行（冪等）を実装。
  - get_connection(db_path) を提供（初回は init_schema を推奨）。

- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新を行う ETL パイプラインの基盤を実装。
  - ETLResult dataclass により ETL 実行結果（取得数 / 保存数 / 品質チェック結果 / エラー）を構造化して返却。
  - 差分ロジック:
    - DB の最終取得日からの差分計算、backfill_days による一部再取得対応（デフォルト 3 日）。
    - 市場カレンダー先読み（デフォルト 90 日）。
    - 最小データ日（_MIN_DATA_DATE = 2017-01-01）の定義。
  - 補助関数:
    - テーブル存在チェック、最大日付取得、非営業日調整（直近営業日に調整）等を実装。
  - 個別ジョブ:
    - run_prices_etl: 差分取得 -> jq.fetch_daily_quotes -> jq.save_daily_quotes を行う処理を実装（backfill を考慮）。
  - 品質チェック統合ポイント（quality モジュール参照、実際の checks は別モジュールへ委譲）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- ニュース収集における SSRF 対策と XML パースの安全化（defusedxml）を実装。
- 外部からの .env 上書きを保護するため OS 環境変数を読み取り専用扱いにする設計（protected set）。
- HTTP レスポンスサイズの上限・gzip 解凍後の検査を導入しメモリ DoS を軽減。

### Performance & Reliability
- 外部 API 呼び出しでのレート制御（固定スロットリング）とリトライ（指数バックオフ、Retry-After の尊重）を実装。
- DuckDB 側はチャンク化・トランザクション・ON CONFLICT を用いた冪等化を実装し、大量データ挿入時の効率と整合性を確保。
- ニュースの ID 生成や URL 正規化により同一記事の重複挿入を防止。

### Notes / Known limitations
- strategy, execution, monitoring サブパッケージはパッケージ構成として存在するが、今回提供されたコードでは実装が薄い（プレースホルダ）。今後の機能追加で戦略実装・発注ロジック・監視機能が拡充される想定。
- pipeline.run_prices_etl の末尾が提供コード内で途中（戻り値タプルの最後が切れている）になっているため、本稿は現状の実装に基づく推測を含みます。実際のリリースでは細部（戻り値、例外処理、品質チェック呼び出しなど）を確定させる必要があります。
- quality モジュールの詳細チェック実装は別モジュールに委譲されているため、ETL 内の品質判定は外部実装依存。

---

今後のリリースで期待される項目（例）
- 完全な ETL ワークフロー（全ジョブの統合、スケジューリング）。
- strategy と execution の実装（シグナル生成、注文送信、ポジション管理、kabu ステーション連携）。
- 監視＆アラート（Slack連携の実装、モニタリングダッシュボード）。
- 単体テスト／統合テストの追加と CI 設定。
- 性能チューニング（大規模データ処理時の最適化）およびさらに厳密なセキュリティ監査。