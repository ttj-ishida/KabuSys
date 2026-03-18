# Changelog

すべての重要な変更は Keep a Changelog の規約に従って記載します。  
リリースはセマンティックバージョニングに従います。

- 当ドキュメントはコードベース（初期実装）から推測して作成しています。
- 不明点や追加情報があれば反映して更新します。

## [Unreleased]

*（現時点の開発中変更は未記載）*

---

## [0.1.0] - 2026-03-18

初回公開リリース。日本株自動売買プラットフォームの基盤機能を実装しました。主要な追加点を以下にまとめます。

### Added
- パッケージ構成
  - kabusys パッケージの骨子を追加（src/kabusys/__init__.py）。
  - サブパッケージプレースホルダ: data, strategy, execution, monitoring（将来的な機能拡張用）。

- 設定・環境管理（src/kabusys/config.py）
  - .env ファイル及び環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート判定は .git または pyproject.toml を探索して行う（__file__ 基準、CWD 非依存）。
    - 読み込み順: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
    - .env パーサは export プレフィックス、クォート内のエスケープ、インラインコメント判定（クォートなしでの '#' の扱い）等に対応。
    - ファイル読み込み失敗時は警告を出力して続行。
  - Settings クラスを公開（settings インスタンス）。
    - J-Quants / kabu ステーション / Slack / DB パス 等の必須/既定値設定をプロパティで提供。
    - KABUSYS_ENV・LOG_LEVEL の検証（許容値チェック）。
    - is_live / is_paper / is_dev といった環境判定ユーティリティ。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーを取得する fetch_* 関数を実装。
  - HTTP リクエスト共通処理:
    - API レート制御（120 req/min）を固定間隔スロットリングで遵守する RateLimiter 実装。
    - 再試行ロジック（指数バックオフ、最大 3 回）。408/429/5xx をリトライ対象。429 の場合は Retry-After を考慮。
    - 401 受信時はリフレッシュトークンから id_token を自動更新して 1 回だけリトライ。
    - ページネーション対応（pagination_key の追跡で重複ループ回避）。
    - JSON デコードエラー時は明示的なエラーを送出。
  - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）を実装。
    - 挿入は冪等性を保つため ON CONFLICT DO UPDATE を使用。
    - fetched_at を UTC タイムスタンプで記録（Look-ahead Bias のトレースに対応）。
    - 不正なレコード（PK 欠損）をスキップして警告出力。
  - 型変換ユーティリティ _to_float / _to_int を追加（空値・不正値に対する安全な変換、"1.0" 文字列への対応など）。

- ニュース収集モジュール（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news, news_symbols に保存する一連処理を実装。
  - セキュリティ・堅牢性対応:
    - defusedxml を用いた XML パース（XML Bomb 等の緩和）。
    - SSRF 対策: リダイレクト時のスキーム検査、ホストのプライベート/ループバック判定（DNS 解決して A/AAAA を検査）を実施。
    - URL スキームは http/https のみ許可。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後のサイズチェック（Gzip bomb 対策）。
    - リダイレクト用カスタムハンドラで事前検証を行う設計。
  - 記事 ID は URL を正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント除去、クエリソート）した上で SHA-256 ハッシュ先頭32文字を使用し冪等性を保証。
  - テキスト前処理（URL 除去、空白正規化）ユーティリティを提供。
  - DB 保存:
    - save_raw_news: INSERT ... ON CONFLICT DO NOTHING RETURNING id を用いて新規挿入 ID を正確に算出。チャンク単位挿入と 1 トランザクションでのコミット/ロールバック対応。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への紐付けをチャンクで一括挿入、INSERT ... RETURNING を利用して実際に挿入された件数を返す。
  - 銘柄コード抽出機能 extract_stock_codes を実装（4桁数字パターン、既知コードセットでフィルタ、重複排除）。

- DuckDB スキーマ（src/kabusys/data/schema.py）
  - DataSchema.md 想定に基づく多層スキーマを定義（Raw / Processed / Feature / Execution 層）。
  - 主なテーブル:
    - raw_prices, raw_financials, raw_news, raw_executions
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols
    - features, ai_scores
    - signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance
  - 適切な CHECK 制約、PRIMARY KEY、FOREIGN KEY を定義。
  - 頻出クエリに対するインデックスを作成（コード×日付スキャンやステータス検索向け）。
  - init_schema(db_path) を実装し、ディレクトリ作成→DDL実行→インデックス作成→DuckDB 接続を返す。
  - get_connection(db_path) を提供（初期化を行わない既存接続取得）。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - ETL の設計方針に基づく差分更新パイプラインの基礎実装。
  - ETLResult データクラスを追加（結果集約、品質問題リスト、エラー一覧、ヘルパー property）。
  - テーブル存在チェック、最大日付取得ユーティリティ（_table_exists, _get_max_date）。
  - 市場カレンダーを使った営業日調整（_adjust_to_trading_day）。
  - 差分取得用ヘルパー: get_last_price_date / get_last_financial_date / get_last_calendar_date。
  - run_prices_etl の骨組みを実装（差分算出、backfill_days を考慮した date_from の自動算出、J-Quants からの取得→保存ロジック呼び出し、ログ出力）。
  - 品質チェックモジュール（quality）との連携想定（実装は別モジュール）。

### Security
- ニュース収集での SSRF 対策や defusedxml による XML の安全なパースを導入。
- .env 読み込みでは既存 OS 環境変数を保護する protected セットを採用。

### Notes / Implementation details
- J-Quants API 呼び出しはモジュールレベルの id_token キャッシュを共有し、ページネーション間で再利用して効率化。
- データ保存は可能な限り冪等に設計（ON CONFLICT...DO UPDATE / DO NOTHING）。これにより再実行やバックフィル時の一貫性を確保。
- news_collector は受信時の各種検証（サイズ・スキーム・プライベートホスト等）を行い、最大限失敗をローカライズする設計（1 ソース失敗でも他ソース継続）。
- pipeline.run_prices_etl は差分更新ロジックを備えるが、追加の ETL ジョブ（財務データ・カレンダー・品質チェックのフルパイプライン統合）は今後の実装フェーズ。

### Deprecated
- なし（初回リリースのため該当なし）。

### Breaking Changes
- なし（初回リリースのため該当なし）。

---

今後の想定タスク（次回以降に実装検討）
- pipeline の完全実装（財務データ・カレンダーETL、品質チェックの実行とレポート、監査ログ出力）。
- strategy / execution / monitoring サブパッケージの具現化（シグナル生成、注文送信、取引監視、Slack 通知等）。
- 単体テスト、統合テストの追加（外部 API モック、ネットワークエラー/再試行のシナリオ）。
- CI による schema 初期化テストや DB マイグレーション対応。
- ドキュメント（DataPlatform.md / DataSchema.md / API 使用例）の整備。