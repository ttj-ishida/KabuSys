# CHANGELOG

すべての重要な変更はこのファイルに記録します。形式は「Keep a Changelog」に準拠しています。

全般方針:
- バージョンは semantic versioning を想定しています。
- 日付はリリース日を表します。
- 各項目はコード内容から推測して記載しています。

## [Unreleased]
- 今後の変更・追加予定を記載してください。

## [0.1.0] - 2026-03-18
初回リリース（ベース実装）

### Added
- パッケージ初期化
  - パッケージ名 kabusys、バージョン 0.1.0 を導入。__all__ に主要サブパッケージ（data, strategy, execution, monitoring）を定義。

- 環境変数 / 設定管理（kabusys.config）
  - .env / .env.local ファイルと OS 環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート探索は __file__ を起点に .git または pyproject.toml を探索するため、CWD に依存しない自動読み込みを実現。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能（テスト用途）。
  - .env のパース実装:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - コメント（#）の扱いとクォート外での取り扱いを実装。
  - OS 環境変数を保護する protected set の概念を導入し、.env.local による上書き時にも明示的保護を行う。
  - Settings クラスでアプリケーション設定を取得:
    - 必須項目（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）は未設定時に ValueError を発生させる。
    - KABUSYS_ENV（development/paper_trading/live）や LOG_LEVEL（DEBUG/INFO/...）のバリデーションを実装。
    - Path 型で duckdb/sqlite のデフォルトパスを提供。
    - is_live / is_paper / is_dev のユーティリティプロパティを提供。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - 基本 API 呼び出しユーティリティと認証フローを実装。
  - レート制限: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を導入（最小間隔 = 60 / 120 秒）。
  - 冪等性のため、DuckDB への保存は ON CONFLICT DO UPDATE を使用する save_* 関数を実装。
  - リトライロジック:
    - 指数バックオフ（base=2 秒）、最大 3 回のリトライ。
    - ステータスコード 408, 429, 5xx をリトライ対象。
    - 429 の場合は Retry-After ヘッダを優先。
  - 401 Unauthorized を検出した場合は自動でリフレッシュトークンから id_token を再取得して 1 回だけリトライ（無限再帰防止のフラグ実装）。
  - データ取得関数:
    - fetch_daily_quotes（株価日足、ページネーション対応）
    - fetch_financial_statements（財務データ、ページネーション対応）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数:
    - save_daily_quotes（raw_prices に保存、主キー重複時は更新）
    - save_financial_statements（raw_financials に保存、主キー重複時は更新）
    - save_market_calendar（market_calendar に保存、主キー重複時は更新）
  - 取得タイミングのトレースのため、fetched_at を UTC タイムスタンプ（ISO 8601 Z）で記録。
  - 数値変換ユーティリティ:
    - _to_float: 空値・不正値は None を返す。
    - _to_int: "1.0" のような float 文字列は float 経由で変換するが、小数部が 0 以外の場合は None を返し不意の切り捨てを防止。

- ニュース収集モジュール（kabusys.data.news_collector）
  - RSS フィードからニュース記事を収集して raw_news テーブルへ保存する機能を実装。
  - セキュリティ・堅牢化対策:
    - defusedxml を用いて XML Bomb 等を防止。
    - リダイレクト時にスキームとホストの検証を行う _SSRFBlockRedirectHandler を導入し、内部アドレス（プライベート/ループバック/リンクローカル/マルチキャスト）へのアクセスを拒否。
    - 初回 URL のホストに対する前置的なプライベート検査を追加。
    - スキームは http/https のみ許可。
    - レスポンスサイズの上限（MAX_RESPONSE_BYTES = 10 MB）を実装し、事前チェックと実際の読み込み上限でメモリ DoS を防止。
    - gzip 圧縮の解凍後もサイズ上限を検証（Gzip bomb 対策）。
  - URL 正規化:
    - スキーム/ホストの小文字化、フラグメント削除、トラッキングパラメータ（utm_* 等）の除去、クエリをキーでソートする _normalize_url を実装。
    - 記事ID は正規化 URL の SHA-256 の先頭32文字を採用して冪等性を担保。
  - 前処理:
    - preprocess_text で URL 除去・空白正規化・トリムを実施。
    - RSS pubDate のパースを行い、UTC naive datetime を扱う。パース失敗時は現在時刻で代替（NOT NULL 制約を満たす設計）。
  - DB 保存:
    - save_raw_news は INSERT ... ON CONFLICT DO NOTHING RETURNING id を使い、実際に挿入された記事 ID のリストを返す。チャンク（デフォルト 1000 件）と 1 トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk で (news_id, code) の紐付けを一括挿入。ON CONFLICT で重複をスキップし、INSERT ... RETURNING で挿入数を正確に取得。
  - 銘柄抽出:
    - extract_stock_codes は本文中の 4 桁数字候補を抽出し、known_codes に含まれるものだけを返す（重複除去）。
  - run_news_collection：複数 RSS ソースを順次取得し、raw_news 保存 → 新規記事に対して銘柄紐付けを行う統合ジョブを実装。各ソースは独立してエラーハンドリング（1 ソース失敗でも他は継続）。

- DuckDB スキーマ定義（kabusys.data.schema）
  - DataSchema.md に基づく 3 層（Raw, Processed, Feature）＋Execution 層のテーブル定義を実装。
  - 主なテーブル:
    - Raw: raw_prices, raw_financials, raw_news, raw_executions
    - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature: features, ai_scores
    - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - インデックスも主要クエリパターン（code×date スキャン、status 検索など）に合わせて作成。
  - init_schema(db_path) によりディレクトリ自動作成（必要なら）→ テーブルとインデックスを冪等に作成して DuckDB 接続を返す。
  - get_connection(db_path) で既存 DB への接続を返す（スキーマ初期化は行わない旨を明記）。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計に沿った差分更新フロー（差分算出、J-Quants からの取得、保存、品質チェック呼び出し）を実装。
  - ETLResult データクラスを導入し、結果・品質問題・エラーの集約を提供。to_dict() により品質問題をシリアライズ可能。
  - 差分ロジックとヘルパー:
    - テーブル存在チェック、最終取得日の取得ユーティリティを実装。
    - 市場カレンダー未取得時のフォールバックや営業日調整ロジック（_adjust_to_trading_day）を実装。
    - run_prices_etl:
      - 最終取得日からの backfill_days（デフォルト 3 日）を用いた差分再取得ロジックを実装。
      - jq.fetch_daily_quotes と jq.save_daily_quotes を呼んで取得・保存を行う。
  - ETL は id_token を注入可能でテスト容易性に配慮。

### Changed
- 新規リリースのため該当なし（初版）。

### Fixed
- リリース時点での既知の安定化・堅牢化を含む（RSS の XML パース失敗等は警告ログで処理継続）。

### Security
- NewsCollector：
  - defusedxml を採用し XML 関連の脆弱性対策を実施。
  - SSRF 対策としてリダイレクト時と最終 URL 両方でスキーム/プライベートホスト検査を実施。
  - レスポンスサイズ上限と gzip 解凍後のサイズ検査を行い、メモリ攻撃を緩和。
- J-Quants クライアント：
  - トークン自動リフレッシュ時に無限再帰を防止するフラグ管理を実装。

### Known issues / Notes
- モジュールの雛形
  - kabusys.execution と kabusys.strategy の __init__.py は存在するが実装は含まれておらず、発注ロジック／戦略コアは未実装。
- run_prices_etl の戻り値
  - ソースコード最終部（提供コード断片）では run_prices_etl の return が "return len(records)," のみで保存件数を返していないように見える（タプルを想定しているが保存数が含まれていない）。実際の戻り値仕様は (fetched, saved) のタプルであるべきため、ここは修正が必要かもしれません。
- テスト・ドキュメント
  - テストコードや外部ドキュメント（DataPlatform.md / DataSchema.md などの参照ファイル）はコード中で参照があるが、今回のリポジトリ断片には含まれていないため、運用時は補完が必要です。
- 環境変数保護
  - .env/.env.local のロード順・上書きルールは設計上明示されているが、運用時は OS 環境変数と .env の整合性に注意してください。

---

今後のリリースでは、以下を優先的に予定することを推奨します:
- execution / strategy の具体実装（発注・ポジション管理ロジック、シミュレーション・paper_trading 実装）
- run_prices_etl の戻り値/エラーハンドリングの整合性確認と単体テスト追加
- end-to-end の統合テスト（J-Quants モック、RSS フィードモック、DuckDB インメモリ利用）
- ドキュメント（DataPlatform.md / DataSchema.md 等）の同梱と README の整備

（以上はコードから推測して記載しました。実装・設計方針の意図と差異がある場合は適宜調整してください。）