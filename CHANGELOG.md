# CHANGELOG

すべての変更は Keep a Changelog 規約に準拠しています。  
注: 以下はリポジトリ内のコードから推測して作成した初回リリースの変更履歴です。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買システムのコア基盤を提供します。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。
  - モジュール構成: data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサ実装: export プレフィクス対応、シングル/ダブルクォート内のエスケープ、行内コメント認識などの堅牢なパース処理。
  - Settings クラスを提供し、アプリ設定（J-Quants トークン、kabu API、Slack、DB パス、環境モード、ログレベル等）をプロパティ経由で取得。
  - env / log_level の値検証（許容値チェック）と is_live / is_paper / is_dev ヘルパー。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー取得関数を実装。
  - API レート制限対応: 固定間隔スロットリング（120 req/min）を内部的に適用する RateLimiter。
  - リトライ戦略: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象。429 の場合は Retry-After ヘッダを優先。
  - 401 応答時の自動トークンリフレッシュ（1 回限定）とリトライ処理を実装。
  - ページネーション対応（pagination_key を利用）およびモジュールレベルの ID トークンキャッシュでページ間トークン共有を実装。
  - 取得データに対して fetched_at を UTC で付与する運用方針。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）実装。ON CONFLICT DO UPDATE による冪等性（重複更新の置換）を確保。
  - データ変換ユーティリティ _to_float / _to_int（空値や不正値に対して安全に None を返すロジック、"1.0" のような文字列→int 変換の扱い等）。

- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - 3層構造（Raw / Processed / Feature）+ Execution レイヤーを想定したテーブル定義を追加。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 頻出クエリに備えたインデックス定義。
  - init_schema(db_path) によりディレクトリ作成から全テーブル・インデックス作成を冪等に行う関数を提供。get_connection による既存 DB 接続取得も提供。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新（差分取得）、保存、品質チェックを組み合わせた日次 ETL 実装。
  - run_prices_etl / run_financials_etl / run_calendar_etl による個別ジョブ。
  - run_daily_etl により以下を順次実行:
    1. 市場カレンダー ETL（先読み lookahead）
    2. 株価日足 ETL（差分 + backfill）
    3. 財務データ ETL（差分 + backfill）
    4. 品質チェック（任意）
  - 差分判定ロジック: DB の最終取得日を基に date_from を自動決定。backfill_days による過去再取得で API の後出し修正を吸収。
  - ETLResult データクラスにより、取得数／保存数／品質問題／エラー一覧を構造化して返却。品質チェックの重大度フラグ（has_quality_errors）を提供。
  - 市場カレンダーが取得済みであれば対象日を直近営業日へ調整する _adjust_to_trading_day 実装。

- 品質チェック（src/kabusys/data/quality.py）
  - 欠損データ検出（OHLC 欠損）、スパイク検出（前日比 > threshold）、重複チェック、日付不整合検出を行う方針を実装。
  - QualityIssue データクラスを用い、チェック毎に (check_name, table, severity, detail, sample rows) を返す。Fail-Fast ではなく全件収集の方針。
  - SQL による効率的なチェック実装（パラメータバインドを使用しインジェクションを回避）。
  - デフォルトのスパイク閾値は 50%（_SPIKE_THRESHOLD = 0.5）。

- 監査ログ（Audit）モジュール（src/kabusys/data/audit.py）
  - シグナル -> 発注要求 -> 約定 のトレーサビリティを確保する監査テーブル群を追加:
    - signal_events（戦略が生成したシグナルの記録）
    - order_requests（発注要求。order_request_id を冪等キーとして採用）
    - executions（証券会社からの約定ログ。broker_execution_id を外部からの冪等キーに）
  - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
  - 状態遷移や注文件件の CHECK 制約、外部キー制約を設計に組み込み。
  - init_audit_schema(conn) による既存 DB への監査スキーマ追加と、init_audit_db(db_path) による監査専用 DB 初期化を提供。
  - 監査向けのインデックスを作成し、検索／ジョイン性能を考慮。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- 機密情報（トークン等）は Settings 経由で環境変数から読み込む設計。自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Implementation details
- API クライアントは urllib を低レイヤで利用しており、JSON デコード失敗時や HTTP エラー時の詳細ログが出力される設計。
- DuckDB をデフォルトのデータストアとして使用（ファイル or :memory: をサポート）。
- ETL の各ステップは独立してエラーハンドリングされ、1 ステップ失敗でも他ステップを継続する設計（呼び出し元が最終的な停止判断を行う）。
- 保存処理は基本的に冪等であり、同一主キーの更新は置換（ON CONFLICT DO UPDATE）されるため再実行に安全。
- .env パーサは実運用でよくあるパターン（export プレフィクスやクォートとエスケープ、行内コメントなど）に対応。

### Known issues / Limitations
- 現在、Slack 連携や実際の kabu ステーション API を叩く実装（execution 層の外部ブローカー連携・実際の注文送信ロジック）は本コードベースには含まれていません（execution・strategy パッケージの実装予定箇所あり）。
- J-Quants API 呼び出しに urllib を使用しているため、将来的に requests 等への移行で利便性向上の余地あり。
- 一部の入力検証やエラーメッセージは簡潔化されているため、運用時にさらなるロギングやメトリクス（リクエスト数・失敗率等）の追加が想定されます。

---

もしリリースノートの粒度（ファイル別、関数別、あるいはより簡潔な要約）や日付の調整、既知のバグ追記などの要望があれば教えてください。必要に応じて英語版やリリースハイライト版も作成します。