# Changelog

すべての重要な変更は Keep a Changelog のフォーマットに従って記載しています。  
慣例: すべての日付は yyyy-mm-dd 形式。

## [0.1.0] - 2026-03-16

初回リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。主な追加点は以下の通りです。

### 追加
- パッケージ基盤
  - パッケージ初期化: kabusys/__init__.py（バージョン 0.1.0、公開モジュール一覧）
- 環境設定 / 設定管理（src/kabusys/config.py）
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git / pyproject.toml から発見）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）
  - .env パーサーの実装: export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント処理に対応
  - 環境変数上書きルール: OS 環境変数を保護する protected セット（.env.local は override）
  - 必須環境変数取得ヘルパー _require()
  - 設定クラス Settings:
    - J-Quants / kabuAPI / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル検証
    - is_live / is_paper / is_dev のプロパティ
- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダーの取得機能
  - レート制限対応（固定間隔スロットリング、デフォルト 120 req/min）
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を対象）
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）と id_token キャッシュ（ページネーション間で共有）
  - ページネーション対応（pagination_key の追跡）
  - レスポンス JSON デコードエラーハンドリング
  - DuckDB への保存関数（冪等性を保つ ON CONFLICT DO UPDATE）
    - save_daily_quotes, save_financial_statements, save_market_calendar
  - データ型変換ユーティリティ _to_float / _to_int（安全な変換ルール）
  - fetched_at を UTC で記録し Look-ahead Bias を抑制
- DuckDB スキーマ定義と初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution 層をカバーする包括的な DDL を実装
  - raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_*,
    features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など
  - インデックス定義（典型的なクエリパターン用）
  - init_schema(db_path) によりディレクトリ作成 → テーブル・インデックス作成（冪等）
  - get_connection() により既存 DB へ接続
- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新ロジック: DB の最終取得日からの差分取得、バックフィル（日数指定で後出し修正を吸収）
  - 市場カレンダーの先読み（デフォルト 90 日）
  - run_prices_etl / run_financials_etl / run_calendar_etl（各ジョブの分離と独立したエラーハンドリング）
  - run_daily_etl: 日次 ETL の統合エントリポイント（カレンダー → 株価 → 財務 → 品質チェック）
  - ETLResult データクラス（実行結果・品質問題・エラー集約、辞書化メソッド）
  - trading_day への営業日調整ヘルパー（market_calendar に基づき過去方向へ補正）
  - id_token 注入可能でテスト容易性を確保
- 品質チェックモジュール（src/kabusys/data/quality.py）
  - QualityIssue データクラス（check_name, table, severity, detail, rows）
  - check_missing_data: raw_prices の OHLC 欠損検出（サンプル行・件数取得）
  - check_spike: 前日比スパイク検出（LAG ウィンドウ、閾値デフォルト 50%）
  - 各チェックは全件収集方針（Fail-Fast ではない）、DuckDB 上で SQL 実行
- 監査ログ（Audit）機能（src/kabusys/data/audit.py）
  - 監査テーブル: signal_events, order_requests, executions（監査トレーサビリティ階層の実装）
  - order_request_id を冪等キーとして設計、各種チェック制約（limit/stop/market の価格ルール）
  - executions テーブルは broker_execution_id をユニークに扱う（証券会社側の冪等性）
  - init_audit_schema(conn) / init_audit_db(db_path) によるスキーマ初期化（UTC タイムゾーン固定）
  - 監査用インデックス群（検索・JOIN を考慮）
- その他
  - モジュール分割: data, strategy, execution, monitoring のパッケージ準備（__init__ プレースホルダ）
  - ロギングを適切に配置（情報 / 警告 / エラーの出力）

### 変更
- 初版につき互換性変更はなし。

### 修正
- 初版につき既知のバグフィックス履歴なし。

### 既知の注意点 / 制限
- quality モジュールは主要チェック（欠損・スパイク等）を実装していますが、全チェック（重複・日付不整合等）の実装が部分的である可能性があります（コードコメント参照）。ETL 側では品質問題を収集し、呼び出し元が対処を判断する設計です。
- jquants_client は urllib を利用したシンプル実装のため、高度な HTTP 機能や接続プール・タイムアウト調整は将来的に改善余地があります。
- DuckDB スキーマの制約（CHECK / FOREIGN KEY 等）は初期設計に基づいており、将来的に運用要件で調整が必要となる場合があります。
- strategy / execution / monitoring パッケージはプレースホルダであり、戦略や実運用連携の実装は別途必要です。

---

（今後のリリースでは Unreleased セクションを用いて変更を逐次記載してください）