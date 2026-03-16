Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードベースから推測できる変更点・初期リリース内容をまとめています。

注意: 日付は本ファイル生成日（2026-03-16）を使用しています。必要に応じて調整してください。

---------------------------------------------------------------------
CHANGELOG.md
---------------------------------------------------------------------

全般
======
このプロジェクトは Keep a Changelog の形式に従って変更履歴を管理します。

フォーマット:
- Added: 新規機能
- Changed: 既存機能の変更
- Fixed: バグ修正
- Deprecated: 非推奨
- Removed: 削除
- Security: セキュリティ関連

[Unreleased]
-----------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-03-16
-------------------
Added
- 初期リリース: KabuSys 日本株自動売買システムの基盤となるモジュール群を追加。
- パッケージエントリポイント
  - src/kabusys/__init__.py によるバージョン管理（__version__ = "0.1.0"）および主要サブパッケージの公開（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py を追加。
  - .env / .env.local 自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env 行パーサ（export 形式、クォート付き文字列のエスケープ、インラインコメント処理をサポート）。
  - Settings クラスによる型付きアクセス（必須キーチェックと ValueError によるバリデーション）。
  - 設定例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等を取得。
  - 環境値の検証（KABUSYS_ENV と LOG_LEVEL に対する許容値チェック）。
- J-Quants API クライアント
  - src/kabusys/data/jquants_client.py を追加。
  - 提供データ: 株価日足（OHLCV）、四半期財務データ（BS/PL）、JPX マーケットカレンダー取得関数を実装。
  - レート制限管理: 固定間隔スロットリング（120 req/min, _RateLimiter）。
  - リトライ実装: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx。429 の場合は Retry-After を尊重。
  - 認証トークン処理: get_id_token() によるリフレッシュ、モジュールレベルのトークンキャッシュ、401 受信時の自動リフレッシュ（1回のみ再試行）。
  - ページネーション対応の fetch_* 関数（pagination_key を利用）。
  - DuckDB 向けの保存関数 save_*（raw_prices, raw_financials, market_calendar）：ON CONFLICT DO UPDATE による冪等保存、PK 欠損行のスキップ、fetched_at を UTC タイムスタンプで記録。
  - ユーティリティ: 型変換ヘルパー _to_float, _to_int（不正値や小数混入を厳密に扱う）。
- DuckDB スキーマ定義・初期化
  - src/kabusys/data/schema.py を追加。
  - 3 層データモデルを定義: Raw / Processed / Feature / Execution 層。
  - raw_prices, raw_financials, raw_news, raw_executions など Raw レイヤー。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols など Processed レイヤー。
  - features, ai_scores など Feature レイヤー。
  - signals, signal_queue, orders, trades, positions, portfolio_performance など Execution レイヤー。
  - 各種インデックス定義（典型的なクエリパターンに最適化）。
  - init_schema(db_path) によりディレクトリ自動作成とテーブル作成（冪等）。
  - get_connection(db_path) で既存 DB へ接続。
- ETL パイプライン
  - src/kabusys/data/pipeline.py を追加。
  - 日次 ETL (run_daily_etl): 市場カレンダー取得、株価・財務データの差分取得と保存、品質チェックの一連処理を実行。
  - 差分更新ロジック: DB の最終取得日を基に date_from を自動算出。デフォルトのバックフィル日数は 3 日（後出し修正吸収用）。
  - カレンダーの先読み（デフォルト 90 日）をサポート。
  - ページネーション・id_token 注入によるテスト容易性を考慮。
  - ETLResult dataclass により実行結果を集約（取得数・保存数・品質問題・エラー一覧を保持）。
  - ステップ間の独立したエラーハンドリング（1 ステップ失敗でも他を継続し、結果にエラーを蓄積）。
- 監査ログ（トレーサビリティ）
  - src/kabusys/data/audit.py を追加。
  - シグナル → 発注要求 → 約定 のトレーサビリティを担保するテーブル群（signal_events, order_requests, executions）。
  - order_request_id を冪等キーとして扱う設計（重複再送の防止）。
  - すべての TIMESTAMP は UTC 保存を前提（init_audit_schema で SET TimeZone='UTC' を実行）。
  - init_audit_schema(conn) / init_audit_db(db_path) による冪等初期化。
  - インデックス: ステータス検索や broker_order_id による結び付けなど実用的な検索性を考慮。
- データ品質チェック
  - src/kabusys/data/quality.py を追加。
  - 実装済みチェック:
    - check_missing_data: raw_prices の OHLC 欄の欠損検出（重大度: error）。
    - check_spike: 前日比のスパイク検出（LAG ウィンドウ使用、既定閾値 50%）。
    - （重複・日付不整合チェック等は設計ドキュメントに準じて拡張可能な構成）
  - QualityIssue dataclass によりチェック結果を構造化（check_name, table, severity, detail, sample rows）。
  - DuckDB 上の SQL を利用、パラメータバインド（?）で安全に実行。
- その他
  - src/kabusys/data/__init__.py, src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py を追加（パッケージ化のため）。
  - ロギング（logger を各モジュールで取得）により ETL や API 呼び出しの実行ログ/警告を出力。
  - 設計原則やドキュメント注釈（Look-ahead bias 回避、冪等性、監査やUTCタイムスタンプなど）をコード内 docstring に反映。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 認証トークンの扱い:
  - J-Quants のリフレッシュトークン（JQUANTS_REFRESH_TOKEN）は Settings 経由で必須取得。ID トークン取得・更新ロジックを実装し、401 時に自動リフレッシュを試行する（無限再帰防止のため allow_refresh フラグを使用）。
  - トークン・機密情報は環境変数で管理する想定（.env 自動読み込みは無効化可能）。
- SQL 実行はパラメータバインドを基本にしており、SQL インジェクションリスクを低減。

Known limitations / 注意事項
- jquants_client は標準ライブラリの urllib を使用しており、HTTP クライアントや接続周りの挙動は環境に依存する可能性がある。必要に応じて requests 等に置き換え可能。
- DuckDB のスキーマは初期化時にディレクトリを自動作成するが、ファイルパスの権限などは利用環境に依存。
- quality モジュールには設計上のチェック項目が並んでいるが、現状で実装済みなのは主に欠損・スパイク検出（将来的に重複・日付不整合などを追加予定）。
- run_calendar_etl の fetch_market_calendar では holiday_division フィルタを受け付ける設計だが、pipeline 側の呼び出しではデフォルト（全件）で取得される。
- 一部の API 呼び出しや保存処理は例外をキャッチして ETLResult.errors に文字列を追加する設計（Fail-Fast ではない）。呼び出し側で適切にハンドリングしてください。

---------------------------------------------------------------------
（終わり）