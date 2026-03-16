CHANGELOG
=========

すべての変更は「Keep a Changelog」規約に準拠して記載しています。

なお、本CHANGELOGは与えられたコードベースの内容から推測して作成した初期リリース記録です（バージョンはパッケージ内 __version__ に基づく）。

Unreleased
----------

- なし

[0.1.0] - 2026-03-16
--------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムのコアモジュール群を追加。
- パッケージ公開:
  - パッケージルート: kabusys（__version__ = 0.1.0、public API として data, strategy, execution, monitoring をエクスポート）
- 環境設定管理:
  - kabusys.config:
    - .env / .env.local の自動読み込み実装（プロジェクトルートを .git または pyproject.toml から解決）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション。
    - .env パーサーは export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメント等に対応。
    - 上書きルール: OS 環境変数を保護しつつ .env/.env.local を読み込む（.env.local は上書き、.env は新規のみ）。
    - Settings クラスに主要設定をプロパティとして提供（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル検証等）。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値の列挙および不正値時の ValueError）。
- データ取得クライアント:
  - kabusys.data.jquants_client:
    - J-Quants API クライアントを実装（価格日足、財務データ、JPX カレンダーを取得）。
    - レート制御: 固定間隔スロットリング（120 req/min、min interval 設定）。
    - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。
    - 401 Unauthorized での自動トークンリフレッシュを 1 回のみ実行（再帰防止）。
    - ページネーション対応（pagination_key を利用して全ページ取得）。
    - ID トークンのモジュールレベルキャッシュを保持（ページネーション間で共有）。
    - JSON デコードエラー・ネットワークエラー時に分かりやすい例外／ログ出力。
    - DuckDB へ保存する save_* 関数を提供。ON CONFLICT DO UPDATE による冪等保存を実現。
    - 保存時に fetched_at を UTC ISO 形式で記録。
    - 型変換ユーティリティ (_to_float / _to_int) を備え、空値・不正値を安全に扱う。
- データベーススキーマ:
  - kabusys.data.schema:
    - DuckDB 用スキーマ定義と初期化関数 init_schema を実装。
    - Raw / Processed / Feature / Execution 層を包含するテーブル群を定義（raw_prices, raw_financials, market_calendar, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance 等）。
    - 各テーブルに制約（PRIMARY KEY, CHECK 等）を付与しデータ整合性を強化。
    - 頻出クエリのためのインデックスを作成（例: code×date、status 検索等）。
    - get_connection による既存 DB への接続獲得 API を提供。
- ETL パイプライン:
  - kabusys.data.pipeline:
    - 日次 ETL の主要エントリポイント run_daily_etl を実装（市場カレンダー → 株価 → 財務 → 品質チェックの順）。
    - 差分更新ロジック: DB の最終取得日を確認し、新規分のみを取得。デフォルトのバックフィル日数（backfill_days=3）で後出し修正を吸収。
    - カレンダー先読み（lookahead_days=90）を実装し営業日判定に使う。
    - 個別ジョブ: run_prices_etl, run_financials_etl, run_calendar_etl を提供。
    - ETLResult dataclass により実行結果（取得件数、保存件数、品質問題、エラー一覧）を集約。品質問題はシリアライズ可能に変換可能。
    - 各ステップは独立して例外処理され、1 ステップ失敗でも他のステップを継続（Fail-Fast しない設計）。
    - logging と warning を適切に出力（例: PK 欠損でのスキップ警告など）。
- 品質チェック:
  - kabusys.data.quality:
    - データ品質チェックフレームワークを実装（QualityIssue dataclass を定義）。
    - チェック実装（まずは）:
      - 欠損データ検出 (missing_data): raw_prices の OHLC 欄の NULL 検出（サンプル行を最大 10 件返す）。
      - スパイク検出 (spike): 前日比が閾値（デフォルト 50%）を超える急騰・急落の検出（LAG ウィンドウ使用）。
    - 各チェックは問題を全て収集して返し、呼び出し元が重大度に応じて判断できる設計。
    - DuckDB 上で SQL による効率的なチェックを行う。SQL にはパラメータバインドを使用し安全性を確保。
- 監査ログ（トレーサビリティ）:
  - kabusys.data.audit:
    - シグナルから約定に至る監査トレーサビリティのためのテーブル定義を追加（signal_events, order_requests, executions）。
    - order_request_id を冪等キーとすることで二重発注防止を想定。
    - すべての TIMESTAMP を UTC で保存する設定を強制（init_audit_schema は SET TimeZone='UTC' を発行）。
    - 監査テーブルの初期化関数 init_audit_schema / init_audit_db を提供。
    - 各種制約（CHECK、FOREIGN KEY）とインデックス（status 検索、signal_id 結合、broker_order_id 等）を定義。
- その他:
  - 各モジュールに docstring と設計方針を詳細に記載（Rate limit、冪等性、Look-ahead Bias 回避、ETL の非 Fail-Fast 方針等）。
  - ロギングを広く採用し、問題発生時に stacktrace や警告を出力する設計。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Removed
- なし（初回リリース）

Security
- なし（初回リリース）

Notes / Known limitations
- kabusys.strategy と kabusys.execution のパッケージは __init__.py のみで中身は実装されておらず、戦略ロジックやブローカ接続ロジックは今後の実装項目です（プレースホルダ）。
- テストコードは提供されていないため、実運用前にユニットテスト／統合テストの追加を推奨します。
- J-Quants/API や証券会社 API の具体的なエンドポイント仕様変更に対する互換性保証は未検証です。運用開始前に実際の API 応答を用いた検証を行ってください。
- DuckDB の UNIQUE/NULL の挙動や外部キー制約は導入環境に依存するため、マイグレーションや運用上の注意が必要です。

今後の改善案（想定）
- execution 層で実際のブローカー接続（kabuステーション等）の実装と発注ワークフローの組込。
- strategy 層に戦略のバージョン管理／パラメータ永続化を実装。
- 品質チェックの追加（重複チェック、未来日付検出、ニュース整合性チェック等）。
- モニタリング／アラート（Slack 通知等）を settings の Slack 設定を使って実装。
- 単体テスト、CI 実装、ドキュメント生成パイプラインの整備。

--- 

（この CHANGELOG はコード内容から推定して作成したものであり、実際のコミット履歴やリリースノートとは差異がある可能性があります。）