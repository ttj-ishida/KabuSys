# CHANGELOG

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

最新: Unreleased → 次回リリース前の変更はここに記載します。

## [Unreleased]
- ドキュメント・リファクタなどの作業があればここに記載してください。

## [0.1.0] - 2026-03-15
初回リリース。日本株自動売買システム「KabuSys」の基本モジュール群を追加しました。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを 0.1.0 に設定（src/kabusys/__init__.py）。
  - パッケージ公開対象モジュール: data, strategy, execution, monitoring。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート自動検出（.git または pyproject.toml を探索）により、CWD に依存しない.env読み込みを実現。
  - .env の詳細なパース実装:
    - コメント行・export プレフィックス対応
    - シングル／ダブルクォートとバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォート有無での差異）
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト用途等）。
  - Settings クラスでアプリケーション設定を公開:
    - J-Quants トークン、kabu API パスワード・ベース URL、Slack トークン／チャンネル、
      DB パス（DuckDB / SQLite）、環境（development/paper_trading/live）、
      ログレベル等を取得。
  - 必須項目未設定時は ValueError を送出する _require 実装。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装（JSON デコード、エラーハンドリング）。
  - レートリミッタ実装（固定間隔スロットリング、120 req/min を遵守）。
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx 対象）。
  - 401 レスポンス検出時の自動トークンリフレッシュ（1 回まで）と id_token キャッシュ。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes（株価日足 OHLCV）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX マーケットカレンダー）
  - DuckDB への保存関数（冪等化）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存。fetched_at を UTC ISO にて付与。
    - save_financial_statements: raw_financials へ保存（PK 欠損行はスキップ）。
    - save_market_calendar: market_calendar へ保存（取引日/半日/SQ 日フラグの型安全変換を含む）。
  - 型変換ユーティリティ:
    - _to_float および _to_int（float 文字列を経由した int 変換ルールを含む）。

- DuckDB スキーマ定義・初期化 (src/kabusys/data/schema.py)
  - DataSchema.md に準拠した多層スキーマ（Raw / Processed / Feature / Execution）を定義。
  - Raw レイヤーのテーブル: raw_prices, raw_financials, raw_news, raw_executions。
  - Processed レイヤーのテーブル: prices_daily, market_calendar, fundamentals, news_articles, news_symbols。
  - Feature レイヤーのテーブル: features, ai_scores。
  - Execution レイヤーのテーブル: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance。
  - 各テーブルに適切な CHECK 制約・PRIMARY KEY を付与し、データ整合性を確保。
  - 頻出クエリ向けのインデックス定義を追加（銘柄×日付スキャンやステータス検索等）。
  - init_schema(db_path) により DB 作成・DDL 実行・インデックス作成を行い、接続を返す（冪等）。
  - get_connection(db_path) で既存 DB への接続を提供。

- 監査ログ（トレーサビリティ） (src/kabusys/data/audit.py)
  - シグナルから約定に至る監査チェーンを追跡するテーブル群を追加:
    - signal_events（戦略が生成したシグナルを記録、棄却やエラーも保存）
    - order_requests（冪等キー order_request_id を持つ発注要求ログ、注文種別ごとのチェック制約）
    - executions（実際の約定ログ、broker_execution_id をユニーク冪等キーとして扱う）
  - すべての TIMESTAMP を UTC で保存する方針を採用。init_audit_schema で SET TimeZone='UTC' を実行。
  - 監査用インデックス群を追加（signal_id, strategy_id, status 等の検索を高速化）。
  - init_audit_schema(conn) と init_audit_db(db_path) を提供（既存接続への追加や専用 DB 初期化が可能）。

- 空モジュール（将来拡張のためのプレースホルダ）
  - src/kabusys/execution/__init__.py, src/kabusys/strategy/__init__.py, src/kabusys/data/__init__.py, src/kabusys/monitoring/__init__.py を追加（現状は空）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 削除 (Removed)
- （初版のため該当なし）

### 注意事項 / 設計上の重要ポイント
- レート制限: J-Quants API は 120 req/min を想定。_RateLimiter により固定間隔スロットリングを実装していますが、複数プロセスでの同時実行時はシステム全体のレートに注意してください。
- トークン管理: id_token はモジュールレベルでキャッシュされ、401 発生時に自動リフレッシュを 1 回試みます。get_id_token は allow_refresh=False で呼び出されるため無限再帰は発生しません。
- ページネーション: fetch_* 関数は pagination_key を用いたページネーションをサポートし、重複防止のため seen_keys を保持します。
- 冪等性: DuckDB への保存は ON CONFLICT DO UPDATE を利用しており、再実行可能です。ただし PK 欠損行はスキップされログ出力されます。
- 時刻管理: 取得時刻（fetched_at / created_at 等）は UTC で保存されます（ISO 文字列または TIMESTAMP）。
- スキーマ制約: 多数の CHECK 制約や FOREIGN KEY が設定されています。既存データや外部ソースの値によっては挿入時に制約エラーとなる場合があるため、入力データの検証を推奨します。
- 環境変数自動読み込み: プロジェクトルートが検出できない場合、自動ロードはスキップされます。CI やテスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定して自動ロードを抑制できます。

### 既知の制限 / 今後の予定
- strategy / execution / monitoring パッケージは現時点では空のプレースホルダで、戦略実装・発注処理・監視ロジックは今後実装予定。
- ロギングやメトリクスの整備（詳細ログ、監視用メトリクスのエクスポート）は今後の改善項目。
- マルチプロセス／分散実行におけるレートリミット共有・トークン共有機構の追加検討。

---

この CHANGELOG はコードベースから推測して作成しています。実際の開発履歴やコミットメッセージがある場合は、それに合わせて修正してください。