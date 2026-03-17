# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
各項目はコードベースから推測できる機能追加／設計意図や注意点をまとめたものです。

## [0.1.0] - 2026-03-17

### Added
- パッケージ初期構成を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート: data, strategy, execution, monitoring を __all__ で公開

- 環境設定モジュール (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を実装
    - プロジェクトルート判定: .git または pyproject.toml を基準に自動検出（CWD 非依存）
    - 読み込み順序: OS 環境変数 > .env.local > .env
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能
  - .env パーサ実装（コメント処理、export 形式対応、クォート内のバックスラッシュエスケープ処理など）
  - .env 読み込み時に OS 環境変数を保護する protected 機能（override オプション付き）
  - Settings クラス実装（プロパティ経由で各種設定を取得）
    - J-Quants / kabu API / Slack / DB パス等の設定プロパティ
    - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）
    - is_live / is_paper / is_dev のヘルパー

- J-Quants API クライアント (kabusys.data.jquants_client)
  - 基本設計:
    - API レート制限厳守（120 req/min = min interval 約0.5s）
    - 冪等性を考慮した DuckDB への保存（ON CONFLICT DO UPDATE）
    - リトライ（指数バックオフ、最大 3 回）、408/429/5xx をリトライ対象
    - 401 発生時はトークンを自動リフレッシュして 1 回リトライ
    - 取得時刻（fetched_at）を UTC で記録し Look-ahead Bias を抑制
  - レートリミッタ実装（固定間隔スロットリング）
  - id_token のモジュールレベルキャッシュと強制リフレッシュ機構
  - 汎用リクエストユーティリティ _request 実装
  - 認証用 get_id_token 実装（refresh_token を使用）
  - データ取得 API 実装（ページネーション対応）
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務データ）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）
    - save_daily_quotes（raw_prices テーブルへ ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials テーブルへ ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar テーブルへ ON CONFLICT DO UPDATE）
  - ユーティリティ関数: _to_float, _to_int（堅牢な型変換）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードから記事を収集して raw_news に保存する一連の実装
  - セキュリティ・堅牢性対策
    - defusedxml を用いた XML パース（XML Bomb 等の防御）
    - SSRF 対策: リダイレクト検査ハンドラ、スキーム検証（http/https のみ許可）、ホストのプライベートアドレス検査
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策（gzip 解凍後も検査）
    - 受信ヘッダの Content-Length による事前チェック
  - URL 正規化と記事ID設計
    - トラッキングパラメータ除去（utm_ 等）
    - 正規化後の SHA-256 の先頭 32 文字を記事 ID として使用（冪等性）
  - テキスト前処理（URL 除去、空白正規化）実装（preprocess_text）
  - RSS 取得処理 fetch_rss（名前空間対応、pubDate パース、content:encoded 優先など）
  - DuckDB への保存関数（トランザクションまとめ、チャンク挿入、INSERT ... RETURNING を利用）
    - save_raw_news: 新規挿入された記事IDのリストを返す
    - save_news_symbols: 記事と銘柄コードの紐付けを保存（RETURNING ベースで正確に挿入数を取得）
    - 内部関数 _save_news_symbols_bulk: 一括保存（重複除去・チャンク処理）
  - 銘柄コード抽出機能
    - 4桁数字パターンに基づく抽出（known_codes によるフィルタ・重複除去）

- DuckDB スキーマ定義・初期化モジュール (kabusys.data.schema)
  - DataSchema に基づく多層（Raw / Processed / Feature / Execution）テーブル定義を追加
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 多数の制約（CHECK、PRIMARY KEY、FOREIGN KEY）を設定しデータ整合性を担保
  - 検索パフォーマンス向けのインデックス定義（頻出クエリパターンに基づく）
  - init_schema 関数: DB ファイルの親ディレクトリを自動作成し、DDL/インデックスを実行して接続を返す（冪等）
  - get_connection: 既存 DB への接続を返す（スキーマ初期化は行わない）

- ETL パイプライン (kabusys.data.pipeline)
  - ETLResult dataclass による ETL 結果管理（品質問題やエラーの収集、辞書化 to_dict）
  - 差分更新ロジック（最終取得日取得、backfill_days による再取得）
  - 市場カレンダーの先読み（lookahead）、非営業日の調整ヘルパー _adjust_to_trading_day
  - テーブル存在チェック・最大日付取得ユーティリティ
  - run_prices_etl の一部実装（差分算出、fetch/save 呼び出し、backfill の扱い）
  - 設計方針として品質チェック（quality モジュール）との連携を想定（重大度を保持し ETL は継続）

### Security
- news_collector に SSRF 対策、スキームホワイトリスト、プライベート IP/ホスト判定、defusedxml 利用など多層防御を実装
- .env 読み込み時に OS 環境変数を保護する設計（プロテクトセット）

### Notes / Implementation details
- API レート制限は固定間隔スロットリング（_RateLimiter）で実装、J-Quants の 120 req/min を想定
- _request のリトライポリシー:
  - 最大試行回数: 3
  - 指数バックオフ係数: 2.0（試行回ごとに 2^attempt 秒）
  - 429 の場合は Retry-After ヘッダを優先
  - 401 は allow_refresh=True の場合に1回だけトークン自動リフレッシュして再試行
- DuckDB へのデータ保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）で実装
- ニュース記事の ID は URL 正規化を起点に生成するため、トラッキングパラメータ差分による重複挿入を抑制
- bulk INSERT はチャンク（デフォルト 1000 件）に分割してパフォーマンスと SQL 長制限に配慮
- schema.init_schema は ":memory:" をサポートしつつ、ファイルパス指定時は親ディレクトリを自動作成

### Removed
- 該当なし（初回リリース）

### Changed
- 該当なし（初回リリース）

### Fixed
- 該当なし（初回リリース）

---

注意:
- 上記はコードベースから推測してまとめた変更・実装内容です。実際の運用やリリースノートではテスト状況、既知の制限、互換性注意事項（例: DuckDB のバージョン依存や設定ファイルの場所）を補足することを推奨します。