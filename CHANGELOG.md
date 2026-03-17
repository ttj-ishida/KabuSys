# Changelog

すべての変更は Keep a Changelog の形式に従っています。  
安定版リリース前の初期実装として公開された内容を記載します。

## [0.1.0] - 2026-03-17

### Added
- パッケージの初期リリース。パッケージ名: `kabusys`、バージョン 0.1.0。
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。

- 環境設定管理
  - src/kabusys/config.py
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
      - 読み込み優先順位: OS 環境変数 > .env.local > .env。
      - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
      - プロジェクトルート判定は .git または pyproject.toml を起点に探索（CWD に依存しない）。
    - .env の行パーサ実装: export プレフィックス、クォート文字、エスケープ、インラインコメント処理に対応。
    - Settings クラスを公開（settings）。J-Quants / kabuステーション / Slack / DB パス / 環境変数検証（env, log_level）などのプロパティを提供。
    - 必須環境変数が未設定の場合は明確なエラーメッセージを投げる `_require` を実装。

- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py
    - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得用の fetch_* 関数を実装（ページネーション対応）。
    - HTTP リクエストユーティリティ `_request` を実装:
      - レート制限（固定間隔スロットリング、120 req/min）を尊重する RateLimiter 実装。
      - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。
      - 401 受信時はトークンを自動リフレッシュして 1 回リトライ。
      - ページネーション用に module-level の ID トークンキャッシュを共有。
    - get_id_token(refresh_token=None) でリフレッシュトークンから ID トークンを取得する処理を実装。
    - DuckDB へ保存する save_* 関数を実装（冪等: ON CONFLICT DO UPDATE）:
      - save_daily_quotes, save_financial_statements, save_market_calendar。
      - fetched_at を UTC ISO 形式で記録（Look-ahead bias のトレースに寄与）。
      - PK 欠損行をスキップして警告ログ出力。

- ニュース収集モジュール
  - src/kabusys/data/news_collector.py
    - RSS フィードからニュース記事を収集し DuckDB の raw_news テーブルに保存する一連の機能を実装。
    - セキュリティ・頑健性設計を導入:
      - defusedxml による XML パースで XML Bomb 等を防御。
      - リダイレクト時や最終 URL の検証により SSRF を防止（スキーム検査、プライベートアドレス拒否）。
      - レスポンス長の上限（MAX_RESPONSE_BYTES = 10 MB）でメモリ DoS を防止、gzip 解凍後もチェック。
      - URL 正規化（トラッキングパラメータ除去、順序ソート、フラグメント除去）と記事 ID を SHA-256（先頭32文字）で生成し冪等性を保証。
      - 記事テキストの前処理（URL 除去・空白正規化）。
    - fetch_rss(url, source, timeout) を実装（パースエラー/ネットワークエラーのハンドリングとログ）。
    - DB 保存関数:
      - save_raw_news(conn, articles): チャンク挿入、トランザクション管理、INSERT ... RETURNING による新規挿入 ID の返却。
      - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コード紐付けの一括保存（ON CONFLICT DO NOTHING、トランザクション管理）。
    - 銘柄コード抽出: extract_stock_codes(text, known_codes)（4桁数字パターン、既知コードのみ返却）。

- DuckDB スキーマ定義と初期化
  - src/kabusys/data/schema.py
    - Raw / Processed / Feature / Execution の複数レイヤーに渡るテーブル DDL を定義。
    - 各種制約（NOT NULL、CHECK、PRIMARY KEY、FOREIGN KEY）を付与。
    - パフォーマンスを考慮したインデックス定義を追加。
    - init_schema(db_path) でディレクトリ自動作成、全テーブルおよびインデックスを冪等に作成して接続を返す。
    - get_connection(db_path) で既存 DB への接続を取得可能（スキーマ初期化は行わない旨を明記）。

- ETL パイプライン基盤
  - src/kabusys/data/pipeline.py
    - 差分更新ロジック（最終取得日からのバックフィル、デフォルト backfill_days=3）と ETL の流れを実装。
    - 市場カレンダー先読み（LOOKAHEAD）に関する定数を導入。
    - ETLResult データクラスを実装（取得数/保存数/品質問題/エラーの集約、has_errors 等のプロパティ）。
    - DB の最大日付取得や営業日調整などのユーティリティを実装（_get_max_date, _adjust_to_trading_day, get_last_price_date 等）。
    - run_prices_etl の骨組みを実装（差分取得 → jq.fetch_daily_quotes → jq.save_daily_quotes）。※ ファイル末尾での return が途中で切れているため（下記参照）、以降のジョブも同様に構成を予定。

### Fixed
- 各種 I/O/パースでの堅牢化:
  - .env 読み込み時にファイルオープン失敗を warnings.warn で通知して読み込み継続。
  - RSS 取得において Content-Length の不正値や gzip 解凍失敗を検出して安全にスキップ。
  - RSS pubDate のパース失敗時は警告ログを出して現在時刻で代替（raw_news.datetime は NOT NULL のため）。

### Security
- SSRF 対策（news_collector）:
  - リダイレクト先を検査するカスタム HTTPRedirectHandler を実装して、スキーム検査とプライベートアドレス拒否を行う。
  - 初回 URL および最終 URL のホストに対してプライベートアドレス判定を実施。
  - 許可されるスキームを http/https のみに限定。
- XML パースの安全化:
  - defusedxml を使用して XML による攻撃を緩和。
- ネットワーク/リソース攻撃緩和:
  - レスポンス読み取りに最大バイト数を設け、gzip 解凍後も上限チェック。

### Known issues / Notes
- run_prices_etl の最後の return が途中で切れている（ファイル末尾でタプルの返却が不完全に見える）。リポジトリ内の該当箇所は実行時に Syntax/Runtime エラーとなる可能性があるため、実装の続き（戻り値の完全な返却）を要確認・修正。
- pipeline 内の品質チェック（quality モジュール）との連携は設計方針としてあるが、quality モジュールの実装状態によって ETL の振る舞いが変わる。品質問題は収集継続を優先する設計。

### Removed
- なし（初回リリース）。

### Deprecated
- なし（初回リリース）。

---

開発者向け補足:
- 自動環境読み込みは CI/テスト時に影響する可能性があるため、テスト実行時は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して無効化してください。
- DuckDB スキーマは init_schema() を通して初回作成することを推奨します。既存 DB に対しては get_connection() を使用してください。