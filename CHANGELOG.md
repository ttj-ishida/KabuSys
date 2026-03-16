# Changelog

すべての重要な変更をこのファイルに記録します。本ファイルは「Keep a Changelog」形式に準拠しています。  
バージョン番号はセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-16

初期リリース。日本株自動売買プラットフォームのコア基盤を実装しました。主な追加点、設計方針、および既知の注意点を以下にまとめます。

### 追加 (Added)
- パッケージ基盤
  - パッケージ名: kabusys
  - 公開モジュール: data, strategy, execution, monitoring（空の __init__ により名前空間を用意）

- 設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装
  - プロジェクトルート探索機能を導入（.git または pyproject.toml を起点に探索）
  - .env/.env.local の読み込み順序と OS 環境変数の保護機能（protected keys）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能（テスト用途を想定）
  - Env パーサー: export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント対応
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 環境モード / ログレベル 等）
  - 環境変数の必須チェックで未設定時に ValueError を発生

- J-Quants クライアント (kabusys.data.jquants_client)
  - API ベースクライアントを実装（取得対象: 日足（OHLCV）、財務（四半期 BS/PL）、JPX マーケットカレンダー）
  - レート制御: 固定間隔スロットリングで 120 req/min を保証（_RateLimiter）
  - リトライロジック: 指数バックオフ、最大 3 回、408/429/5xx をリトライ対象
  - 401 受信時はリフレッシュトークンを使った自動リフレッシュを 1 回実施してリトライ
  - id_token のモジュールレベルキャッシュを導入（ページネーション間で共有）
  - ページネーション対応の fetch_* 系メソッド（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）
  - 取得データを DuckDB に冪等的に保存する save_* 関数（ON CONFLICT DO UPDATE）
  - 取得時刻（fetched_at）を UTC ISO8601 形式で記録
  - 型変換ユーティリティ (_to_float / _to_int) を実装（安全変換）

- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform に基づく多層スキーマ定義を実装
    - Raw Layer: raw_prices, raw_financials, raw_news, raw_executions
    - Processed Layer: prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - Feature Layer: features, ai_scores
    - Execution Layer: signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適用しやすい初期化 API: init_schema(db_path) と既存接続取得用 get_connection(db_path)
  - 頻出クエリ向けインデックス定義を追加
  - テーブル作成順を外部キー依存に配慮して順序化（冪等）

- ETL パイプライン (kabusys.data.pipeline)
  - 日次 ETL エントリーポイント run_daily_etl を実装
  - 個別 ETL ジョブ: run_calendar_etl, run_prices_etl, run_financials_etl（差分取得 + backfill 対応）
  - 差分更新ロジック: DB の最終取得日から backfill_days（デフォルト3日）遡って再取得
  - 市場カレンダーは先読み（デフォルト 90 日）して営業日判定に利用
  - ETL 実行結果を格納する ETLResult データクラス（品質問題・エラーの一覧を保持）
  - 各ステップは個別にエラーハンドリングされ、1ステップ失敗でも他ステップを継続（Fail-Fast ではない設計）
  - テストしやすさのため id_token の注入をサポート

- 監査ログ (kabusys.data.audit)
  - シグナル→発注→約定のトレーサビリティを保持する監査用テーブル群を実装
    - signal_events, order_requests (冪等キー: order_request_id), executions
  - UTC タイムゾーンを固定して保存（init_audit_schema で SET TimeZone='UTC'）
  - 発注種別チェック、limit/stop 矛盾チェック等の整合性制約を導入
  - 監査向けインデックスを多数追加（検索・結合性能向上）

- 品質チェック (kabusys.data.quality)
  - 品質チェック基盤と項目を実装
    - 欠損データ検出 (check_missing_data): raw_prices の OHLC 欠損を検出（重大度: error）
    - 異常値検出 (check_spike): 前日比のスパイク検出（デフォルト閾値 50%）
    - QualityIssue データクラスでチェック名・テーブル・重大度・サンプル行を返却
  - DuckDB 上での効率的な SQL 実行、パラメータバインドを採用

### 改善 (Changed)
- エラー・ログ出力の充実
  - ETL 各ステップや J-Quants リクエストで適切に logger を利用して状態・警告を出力
- 環境変数読み込みの安全性向上
  - OS 環境変数を protected set として優先保護
  - override ロジックで .env.local を使って上書き可能に

### 修正 (Fixed)
- .env パーサーで以下に対応
  - export KEY=val 形式のサポート
  - シングル/ダブルクォート中のバックスラッシュエスケープの処理
  - コメント (#) の取り扱い（クォート外かつ直前がスペース/タブの場合をコメントとみなす）

### 既知の問題 / 注意点 (Known issues / Notes)
- API シグネチャの不整合の可能性
  - pipeline.run_calendar_etl は jq.fetch_market_calendar を date_from / date_to 付きで呼び出していますが、現行の jquants_client.fetch_market_calendar のシグネチャは (id_token, holiday_division) となっており date_from/date_to を受け取らない実装になっています。この点は実際の J-Quants API 要求仕様に合わせて修正が必要です（pipeline 側か client 側のいずれかを調整）。
- fetch_* 系のページネーションは pagination_key に依存しており、API の挙動変更があった場合は影響を受けます。
- _to_int の float→int 変換ルール
  - "1.0" のような表記は int に変換されますが、小数部が 0 以外の値（例: "1.9"）の場合は None を返す設計です。外部データにより想定外の表記が来ると None が入る可能性があるため、上位での取り扱いに注意してください。
- DuckDB のタイムゾーンは audit 初期化時に UTC に設定しますが、それ以外の接続や既存 DB に対しては注意が必要です。

### 互換性に関する注記 (Breaking Changes)
- 初期リリースのため、後方互換性の破壊となる変更はありません。ただし、上記の「既知の問題」で指摘した API シグネチャ不整合は実運用前に解消する必要があります。

### セキュリティ (Security)
- 秘密情報（J-Quants リフレッシュトークン、SLACK_BOT_TOKEN など）は Settings 経由で必須チェックが入り、未設定時に明確なエラーを出力します。環境変数の取り扱いは .env ファイルと OS 環境変数を分けて扱い、意図しない上書きを防止しています。

---

今後の予定（例）
- pipeline と client の API 不整合解消
- 追加の品質チェック（重複チェック・日付不整合検出の実装完了と統合）
- strategy / execution / monitoring モジュールの実装（現在は名前空間のみ）
- 単体テスト・統合テストの追加と CI 組み込み

もし CHANGELOG の表現や記載内容（公開 API の列挙、既知の問題の扱いなど）で特に強調したい点があれば教えてください。必要に応じて日付やフォーマットを調整します。