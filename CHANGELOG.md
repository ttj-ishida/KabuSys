# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

表記:
- Unreleased: 今後の変更（現時点では空）
- 各リリースはバージョン番号と日付を付与

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-03-16
初期リリース。以下の主要機能・設計を実装しました。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys/__init__.py）。
  - パッケージは data, strategy, execution, monitoring のサブパッケージを公開。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装。
    - プロジェクトルートを .git または pyproject.toml を起点に検出（cwd 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化対応（テスト用途）。
  - .env パーサは以下をサポート:
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの考慮（クォートなしの場合は '#' の直前が空白の場合にコメント認識）
  - Settings クラスを提供（settings インスタンス経由で利用可能）:
    - J-Quants / kabu API / Slack トークン等の必須設定を取得（未設定時は例外を発生）。
    - DB パス（duckdb/sqlite）取得（デフォルト path を提供、expanduser 対応）。
    - KABUSYS_ENV の許容値検査（development, paper_trading, live）。
    - LOG_LEVEL の許容値検査（DEBUG, INFO, WARNING, ERROR, CRITICAL）。
    - is_live / is_paper / is_dev のユーティリティプロパティ。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制御: 120 req/min（固定間隔スロットリングによる _RateLimiter）。
  - 再試行ロジック:
    - 指数バックオフ（最大 3 回）、対象: 408, 429, および 5xx。
    - 429 の場合 Retry-After ヘッダを優先して待機。
    - ネットワークエラー（URLError, OSError）に対してもリトライ。
  - 認証:
    - リフレッシュトークンから ID トークンを取得する get_id_token() を実装。
    - 401 を受けた場合はトークンを自動リフレッシュして 1 回だけリトライ（無限再帰防止の allow_refresh フラグ）。
    - モジュールレベルで ID トークンをキャッシュしてページネーション間で共有。
  - ページネーション対応 API 呼び出しを提供:
    - fetch_daily_quotes: 日足（OHLCV）をページネーション対応で取得。
    - fetch_financial_statements: 四半期財務データをページネーション対応で取得。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB への保存関数（冪等性を重視）:
    - save_daily_quotes / save_financial_statements / save_market_calendar を実装。
    - INSERT ... ON CONFLICT DO UPDATE による冪等処理。
    - PK 欠損行はスキップしてログ警告（サンプル数の集計とログ出力）。
  - データ変換ユーティリティ:
    - _to_float: 非数値や空値は None を返す。
    - _to_int: "1.0" のような整数表現は許容、"1.9" のように小数部がある場合は None を返す。

- DuckDB スキーマ定義・初期化（kabusys.data.schema）
  - Raw / Processed / Feature / Execution の多層スキーマ DDL を実装。
  - 主要テーブル（raw_prices, raw_financials, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）を定義。
  - 各テーブルに適切な型・CHECK 制約・PRIMARY KEY を付与。
  - よく使うクエリ向けにインデックスを定義（code/date 検索、status 検索等）。
  - テーブル作成順序を外部キー依存に配慮して整理。
  - init_schema(db_path) で DB ファイルの親ディレクトリ自動作成・全テーブル作成（冪等）し DuckDB 接続を返す。
  - get_connection(db_path) による既存 DB への接続取得。

- 監査ログ（トレーサビリティ）スキーマ（kabusys.data.audit）
  - signal_events（戦略が生成したシグナル） / order_requests（冪等キー付き発注要求） / executions（約定ログ）を実装。
  - order_request_id を冪等キーとし、再送による二重発注を防止する設計。
  - 実装方針に従い全ての TIMESTAMP は UTC で保存（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 外部キーは ON DELETE RESTRICT として監査ログは削除しない前提。
  - 監査用のインデックス群を定義（signal 日付検索、status キュー検索、broker_order_id 紐付けなど）。
  - init_audit_schema(conn) により既存接続へ監査テーブル追加。init_audit_db(db_path) で専用 DB の初期化も可能。

- データ品質チェック（kabusys.data.quality）
  - DataPlatform 設計に基づく品質チェックを実装。
  - チェック項目:
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欄の欠損を検出（volume は対象外）。
    - 重複チェック (check_duplicates): raw_prices の主キー重複検出（ON CONFLICT 対応していても念のため）。
    - 異常値（スパイク）検出 (check_spike): 前日比の変動率がデフォルト 50% を超えるレコードを検出（LAG を使用）。
    - 日付不整合チェック (check_date_consistency): 将来日付と market_calendar と矛盾する日（非営業日のデータ）を検出。
  - 各チェックは QualityIssue のリストを返す。QualityIssue は check_name, table, severity, detail, サンプル行（最大 10 件）を含むデータクラス。
  - run_all_checks(conn, ...) で全チェックを実行してまとめて返却（エラー・警告の集計ログあり）。
  - SQL はパラメータバインドを利用（インジェクションリスク低減）、DuckDB 接続経由で効率的に実行。

- その他
  - data サブパッケージの __init__ を追加してモジュール構成を確立。
  - strategy, execution, monitoring サブパッケージはプレースホルダの __init__ を配置（今後の拡張用）。

### 変更 (Changed)
- 初期リリースのため該当なし（すべて新規実装）。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### セキュリティ (Security)
- 認証トークンの取り扱いに注意:
  - J-Quants のリフレッシュトークンは Settings 経由で環境変数から取得（コード内にトークンをハードコードしないこと）。
  - 自動 .env ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### 注意事項 / 実装メモ
- DuckDB のスキーマやインデックスは設計段階での典型的クエリパターンを想定しており、実運用のクエリ特性に応じて調整が必要です。
- J-Quants API のレート制御は固定間隔スロットリングを採用しているため、非常に短期間にバースト要求があるケースではスループットに制約が出ます。用途に応じてトークンバケット等への変更を検討してください。
- save_* 関数は ON CONFLICT により冪等性を担保しますが、ETL 外から直接 DB に書き込まれたデータ等の影響を受ける可能性があります。品質チェックモジュールで定期検査を行ってください。
- 全てのタイムスタンプは UTC 基準での保存・ログ出力を想定しています。

---

発行: kabusys v0.1.0 — 初期実装（データ取得、スキーマ、監査、品質チェック、設定管理）