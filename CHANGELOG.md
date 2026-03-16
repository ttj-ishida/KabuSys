KEEP A CHANGELOGの形式に従い、コードベースから推測できる変更履歴（日本語）を作成しました。

CHANGELOG.md
=============

すべての注目に値する変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

- (なし)

[0.1.0] - 2026-03-16
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本モジュールを追加。
  - パッケージ公開情報
    - src/kabusys/__init__.py に __version__ = "0.1.0" と主要サブパッケージの公開（data, strategy, execution, monitoring）。
  - 設定管理 (kabusys.config)
    - .env ファイルおよび環境変数の自動ロード機能を実装。プロジェクトルート検出（.git または pyproject.toml に基づく）によりカレントワーキングディレクトリに依存しない読み込みを実現。
    - 柔軟な .env パーサを実装（コメント、export 形式、シングル/ダブルクォート、エスケープ処理、インラインコメントの扱い）。
    - .env と .env.local の優先順位制御、既存 OS 環境変数の保護（protected set）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - Settings クラスを提供し、J-Quants / kabustation / Slack / DB パス / 環境名 / ログレベル等のプロパティを取得。必須環境変数未設定時に明確なエラーを送出。
    - KABUSYS_ENV と LOG_LEVEL の許容値チェック。

  - データ取得クライアント (kabusys.data.jquants_client)
    - J-Quants API クライアントを実装。
    - レート制限制御: 固定間隔スロットリングで 120 req/min（_RateLimiter）。
    - 再試行ロジック: 指数バックオフ + 最大 3 回リトライ、408/429/5xx を対象。429 の場合は Retry-After を考慮。
    - 401 ハンドリング: トークン自動リフレッシュを 1 回行いリトライ（無限再帰防止）。
    - ページネーション対応の fetch_* 関数を実装:
      - fetch_daily_quotes（株価日足 OHLCV）
      - fetch_financial_statements（四半期財務データ）
      - fetch_market_calendar（JPX マーケットカレンダー）
    - Look-ahead bias の抑止のため取得時刻（fetched_at）を UTC で記録する設計指針を反映。
    - DuckDB への永続化関数（save_*）を実装し、ON CONFLICT DO UPDATE による冪等性を確保:
      - save_daily_quotes -> raw_prices
      - save_financial_statements -> raw_financials
      - save_market_calendar -> market_calendar
    - 型変換ユーティリティ（_to_float, _to_int）を実装し、不正値を安全に扱う。

  - DuckDB スキーマ定義・初期化 (kabusys.data.schema)
    - Raw / Processed / Feature / Execution の 3 層＋監査・実行レイヤを含む豊富なテーブル定義を追加。
    - 主なテーブル:
      - Raw: raw_prices, raw_financials, raw_news, raw_executions
      - Processed: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
      - Feature: features, ai_scores
      - Execution: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
    - 各テーブルにチェック制約（NOT NULL, CHECK, PRIMARY KEY 等）を付与。
    - 頻出クエリに対するインデックスを複数定義。
    - init_schema(db_path) によりディレクトリ自動作成と DDL 実行（冪等）を実現。get_connection を提供。

  - ETL パイプライン (kabusys.data.pipeline)
    - 日次 ETL のフローを実装（差分更新、バックフィル、カレンダー先読み、品質チェック）。
    - 差分更新のデフォルト: 最終取得日から backfill_days（デフォルト 3）分を遡って再取得し API の後出し修正を吸収。
    - 市場カレンダーは lookahead（デフォルト 90 日）分を先読みして営業日調整に利用。
    - run_prices_etl / run_financials_etl / run_calendar_etl を個別に実行可能。
    - run_daily_etl により
      1) calendar ETL
      2) prices ETL
      3) financials ETL
      4) 品質チェック（オプション）
      を順次実行し、各ステップは独立してエラーハンドリング（1 ステップ失敗でも継続）する設計。
    - ETLResult データクラスを導入し、取得件数・保存件数・品質問題・エラー一覧を返却。品質問題はシリアライズ可能な形で出力。

  - データ品質チェック (kabusys.data.quality)
    - 欠損データ検出（OHLC 欠損）: check_missing_data。
    - スパイク検出（前日比の絶対変動率）: check_spike（デフォルト閾値 50%）。
    - QualityIssue データクラスで問題の種類、重大度（error|warning）、サンプル行を返す。
    - 全チェックはフェイルファストではなく全件収集し、呼び出し側が重大度に応じて判断できる設計。

  - 監査ログ (kabusys.data.audit)
    - シグナルから約定に至るトレーサビリティ用テーブル群を追加:
      - signal_events（シグナル生成ログ）
      - order_requests（発注要求、冪等キー order_request_id）
      - executions（証券会社からの約定ログ）
    - すべての TIMESTAMP を UTC で保存する方針（init_audit_schema は SET TimeZone='UTC' を実行）。
    - ステータス遷移や制約（チェック制約、外部キー、UNIQUE）を反映。
    - init_audit_schema(conn) / init_audit_db(db_path) を提供。

  - その他
    - サブパッケージのプレースホルダ __init__ を作成（kabusys.execution, kabusys.strategy, kabusys.data パッケージ初期化）。
    - ロギング箇所を多く設け、処理状況・警告・エラーを記録。

Changed
- 該当なし（初回リリースのため変更履歴なし）。

Fixed
- 該当なし（初回リリースのため修正履歴なし）。

Security
- 該当なし（公開版では認証トークンの自動リフレッシュ等、秘匿情報の取り扱いに配慮した実装を含む）。

Notes / 開発者向け補足
- J-Quants API のトークン情報は Settings を経由して取得。テスト時や CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を有効にして自動ロードを抑制してください。
- DuckDB 初期化は init_schema を一度実行することを推奨。監査ログは別途 init_audit_schema を呼ぶことで追加可能。
- ETL は外部 API と DB 操作が含まれるため、実行環境のネットワーク・ファイル書き込み権限に注意してください。
- 将来的な追加: strategy / execution 層の実装、モニタリング（Slack 通知など）およびより詳細な品質チェック（重複チェック・日付不整合検出の具体的実装）を想定。

ライセンスやパッケージ配布に関する記載はこの CHANGELOG に含めていません。必要に応じて README や pyproject.toml に追記してください。