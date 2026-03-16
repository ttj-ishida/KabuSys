# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-16

初回公開リリース。

### 追加
- パッケージの基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0
  - エクスポート対象モジュール: data, strategy, execution, monitoring
  - ファイル: src/kabusys/__init__.py

- 環境設定管理
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
  - プロジェクトルートを .git または pyproject.toml を基準に自動検出し、そこから .env/.env.local を読み込む仕組みを提供。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサは以下をサポート:
    - 行頭のコメント（#）・空行の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内のバックスラッシュエスケープの取り扱い
    - クォート無し値におけるインラインコメント判定（# の前が空白/タブの場合のみ）
  - OS 環境変数を保護するための protected keys のサポート、.env.local は .env をオーバーライド可能
  - Settings クラスでアプリ設定をプロパティとして公開（J-Quants トークン、kabu API、Slack、DBパス、環境種別、ログレベル等）
  - 環境変数検証（KABUSYS_ENV の許容値: development/paper_trading/live、LOG_LEVEL の許容値）

  - ファイル: src/kabusys/config.py

- J-Quants API クライアント
  - 日足（OHLCV）、四半期財務、マーケットカレンダーを取得するクライアント実装。
  - レート制限（固定間隔スロットリング）を実装（デフォルト 120 req/min）。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。対象はネットワーク系エラーと HTTP 408/429/5xx。
  - 429 の場合は Retry-After ヘッダを優先して待機。
  - 401 受信時は ID トークンを自動リフレッシュして 1 回リトライ（無限再帰防止）。
  - ページネーション対応（pagination_key を使った取得ループ）。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias 防止のためトレース可能に。
  - ファイル: src/kabusys/data/jquants_client.py

- DuckDB スキーマ定義と初期化
  - DataPlatform の3層アーキテクチャを反映したスキーマを定義:
    - Raw layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature layer: features, ai_scores
    - Execution layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 各テーブルに適切な型チェック・制約（PRIMARY KEY, CHECK, FOREIGN KEY 等）を追加。
  - 頻用クエリ向けのインデックス定義を用意。
  - init_schema(db_path) でディレクトリ作成からテーブル作成までを冪等に実行。
  - get_connection(db_path) を提供（初期化は行わない）。
  - ファイル: src/kabusys/data/schema.py

- ETL パイプライン
  - 差分更新・バックフィル・品質チェックを含む日次 ETL 実装:
    - run_daily_etl(): 市場カレンダー取得 → 株価日足 ETL → 財務 ETL → 品質チェック の順で実行。
    - 日付調整: 非営業日は直近営業日に調整（market_calendar に基づく）。
    - 差分更新ロジック: DB の最終取得日を参照し、backfill_days（デフォルト 3 日）前から再取得して API 後出し修正を吸収。
    - カレンダー先読み（lookahead_days、デフォルト 90 日）により将来の営業日情報を事前取得。
    - ETL 結果を ETLResult データクラスで集約（取得数、保存数、品質問題、エラー一覧など）。
    - ETL の各ステップは独立してエラーハンドリング（1ステップ失敗でも他は継続）。
  - ファイル: src/kabusys/data/pipeline.py

- Data 保存（冪等）
  - DuckDB への保存は ON CONFLICT DO UPDATE を使い冪等に実行するヘルパーを提供:
    - save_daily_quotes(), save_financial_statements(), save_market_calendar()
  - PK 欠損行のスキップログ出力や saved レコード数のログ記録あり。
  - ファイル: src/kabusys/data/jquants_client.py

- 監査ログ（Audit / トレーサビリティ）
  - シグナル→発注要求→約定までを UUID 連鎖で完全にトレース可能な監査テーブルを定義:
    - signal_events, order_requests, executions
  - order_request_id を冪等キーとして扱い、二重発注防止を想定。
  - すべての TIMESTAMP は UTC で保存するように init_audit_schema() 内で SET TimeZone='UTC' を実行。
  - 状態遷移管理／インデックス定義を含む。
  - init_audit_db(db_path) による専用 DB 初期化も提供。
  - ファイル: src/kabusys/data/audit.py

- データ品質チェック
  - QualityIssue データクラスと品質チェック群を実装:
    - 欠損データ検出（raw_prices の OHLC 欄）
    - スパイク検出（前日比が閾値を超える変動）
    - 重複チェック、将来日付や営業日外データ検出（設計に記載）
  - 各チェックは問題をすべて収集して戻し、呼び出し元が重大度（error/warning）に応じて判断可能。
  - デフォルトのスパイク閾値は 50%（0.5）。
  - ファイル: src/kabusys/data/quality.py

- ユーティリティ関数
  - 型変換ユーティリティを実装:
    - _to_float(): 空値/変換失敗で None を返す
    - _to_int(): "1.0" のような浮動小数形式は float 経由で変換し、小数部が 0 以外の場合は None を返す（意図しない切り捨てを防止）
  - ファイル: src/kabusys/data/jquants_client.py

### 変更（設計上の決定）
- ETL の設計方針として:
  - Fail-Fast を採らず、各品質チェックは全件を収集して結果を返す方式を採用。
  - ETL の差分更新単位は「営業日」で、自動で最終取得日からの範囲計算とバックフィルを行う。
- jquants_client の HTTP リトライとレート制御はライブラリ内で完結する設計（外部ミドルウェア不要）。
- DuckDB スキーマは外部キー依存関係に配慮した順序で作成するよう定義。

### 修正（堅牢性・扱いの改善）
- .env パーサの強化（export プレフィックス、クォート・エスケープ、インラインコメント処理など）により実運用での耐性を向上。
- API 呼び出し時の JSON デコードエラー時に詳細メッセージを付与してデバッグしやすくした。
- トークンリフレッシュ失敗時の例外取り扱いを明示化してデバッグ性を向上。
- DuckDB 初期化時、ファイルパスが ":memory:" でない場合に親ディレクトリを自動作成することで初回セットアップを容易化。

### 既知の制限 / 注意点
- 現時点で strategy、execution、monitoring パッケージの具体的な実装は placeholder（__init__.py のみ）。戦略・発注実行の具体ロジックは別途実装が必要。
- quality モジュールは設計項目として重複チェックや日付不整合検出を想定しているが、個別の SQL 実装は今後拡張される可能性がある（現状主要なチェックは実装済み）。
- J-Quants API のレート上限や仕様変更により動作が影響を受ける可能性があるため、運用時はログ監視・エラーハンドリングの強化を推奨。

---

貢献・バグ報告や改善提案は Issue を通じて受け付けてください。