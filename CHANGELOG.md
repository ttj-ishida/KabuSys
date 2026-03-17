# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
このファイルはコードベースの現状から推測して自動生成した変更履歴です。

## [Unreleased]

### Added
- 開発中の ETL / データ収集パイプライン、ニュース収集、J-Quants クライアント等の基礎実装を追加（詳細は 0.1.0 を参照）。
- ドキュメントや実装の追加予定:
  - ETL の追加ジョブ（財務データ・カレンダーを含む差分ETLの完全化）
  - 戦略 (strategy) / 実行 (execution) モジュールの具現化
  - 単体テストの整備、例外ケースのカバレッジ強化

### Fixed / Changed
- なし（初期リリースベースの追加と設計メモが中心）。

### Known issues / TODO
- ETL パイプラインの一部処理（ファイル末尾に見られる run_prices_etl の戻り値取り扱い等）が未完成または途中で終端しているように見えるため、実運用前に追加の実装・レビューが必要。
- execution と strategy パッケージは __init__ のプレースホルダのみで具体実装がない。

---

## [0.1.0] - 2026-03-17

初回リリース相当（コードベースから読み取れる初期実装群）。

### Added
- パッケージ初期化
  - kabusys.__version__ = "0.1.0"
  - パッケージ公開 API: data, strategy, execution, monitoring（strategy/execution は未実装のまま空のパッケージ）

- 設定（kabusys.config）
  - .env ファイルまたは環境変数からの設定値自動読み込み機能を実装
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml が存在するディレクトリ）を探索して行う
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
  - .env 解析の強化
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、インラインコメント処理（クォートの有無に応じた挙動）
    - override オプションおよび protected キー（OS 環境変数保護）をサポート
  - Settings クラス（settings インスタンス）を提供
    - J-Quants / kabu API / Slack / DB パス等のプロパティ
    - KABUSYS_ENV / LOG_LEVEL 等の値検証（ホワイトリスト）と便利プロパティ（is_live / is_paper / is_dev）

- J-Quants クライアント（kabusys.data.jquants_client）
  - API クライアントを実装
    - レート制限（120 req/min）を守る _RateLimiter（固定間隔スロットリング）
    - リトライロジック（指数バックオフ、最大 3 回。対象: 408/429/5xx、429 の Retry-After を優先）
    - 401 受信時の ID トークン自動リフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ
    - ページネーション対応
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar の実装
  - DuckDB への冪等保存関数
    - save_daily_quotes, save_financial_statements, save_market_calendar：ON CONFLICT ベースで重複を排除・更新する設計
  - データ変換ユーティリティ
    - _to_float / _to_int（空・不正値ハンドリング）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集と DuckDB への保存機能を実装
    - fetch_rss: RSS 取得、XML パース（defusedxml 使用）、gzip 対応、レスポンスサイズ上限チェック（デフォルト 10MB）
    - セキュリティ対策: SSRF 対応（リダイレクト検査ハンドラ、ホストがプライベートアドレスかの検査）、http/https スキームのみ許可
    - URL 正規化（トラッキングパラメータ除去・クエリソート・フラグメント削除）
    - 記事ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を保証
    - テキスト前処理（URL除去、空白正規化）
    - save_raw_news: チャンク化とトランザクションでの INSERT ... RETURNING により挿入された ID を返す実装
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをチャンク化して保存（ON CONFLICT DO NOTHING）
    - extract_stock_codes: 4桁数字パターンにより既知銘柄コードから抽出
    - run_news_collection: 複数 RSS ソースからの収集を行い、失敗ソースを個別に扱う（known_codes による銘柄紐付けを含む）
  - その他
    - RSS の pubDate を UTC naive datetime にパース（パース失敗時は警告ログを出して現在時刻で代替）

- スキーマ定義（kabusys.data.schema）
  - DuckDB のテーブル定義を一元化（Raw / Processed / Feature / Execution 層）
    - raw_prices, raw_financials, raw_news, raw_executions 等（主キー・制約付）
    - prices_daily, market_calendar, fundamentals, news_articles, news_symbols（Processed 層）
    - features, ai_scores（Feature 層）
    - signals, signal_queue, orders, trades, positions, portfolio_performance（Execution 層）
  - インデックス定義（頻出クエリパターン向け）
  - init_schema(db_path): ディレクトリ自動作成を含むスキーマ初期化関数
  - get_connection(db_path): 既存 DB への接続取得

- ETL パイプライン（kabusys.data.pipeline）
  - ETLResult dataclass による ETL 実行結果の構造化（品質問題・エラーの収集、dict 変換）
  - テーブル存在確認・最大日付取得などのユーティリティ
  - 市場カレンダーを考慮したトレーディングデイ調整関数 (_adjust_to_trading_day)
  - 差分更新向けのヘルパー関数:
    - get_last_price_date / get_last_financial_date / get_last_calendar_date
  - run_prices_etl の骨格:
    - 最終取得日の backfill（デフォルト 3 日）による差分取得ロジック
    - jquants_client.fetch_daily_quotes と save_daily_quotes を組み合わせた取得→保存処理
    - 取得件数と保存件数のログ出力

### Security
- RSS パースに defusedxml を採用し XML ベースの攻撃（XML bomb 等）に対策
- SSRF 対策:
  - リダイレクト時のスキーム/ホスト検査（内部アドレス拒否）
  - 初回リクエスト前のホストプライベートアドレス検査
- .env ロード時に OS 環境変数を保護するための protected キー概念を導入

### Changed
- 初期リリースのため、既存の外部仕様変更はなし（新規追加のみ）。

### Removed
- なし

### Fixed
- なし

### Known issues / Limitations (重要)
- run_prices_etl の戻り値や ETL フローの一部がソース末尾で途切れているように見える（コードレビュー要）。実運用前に該当部分の完成と単体テストを推奨。
- strategy / execution パッケージは実装がない（プレースホルダ）。
- RateLimiter は固定間隔スロットリングの単純実装（短時間のバースト制御やより高度な Token Bucket 等は未実装）。
- DuckDB に依存した INSERT ... RETURNING を多用しているため、DB 実装上の挙動（ロック / 同時実行）については運用テストが必要。
- 単体テスト・統合テストの実装は含まれていないため CI 設定・テストケースの追加が必要。

---

## 参考 / 開発方針メモ
- 設計上の指針はコード内コメントに詳細に記載されている（レート制御、リトライ、冪等性、Look-ahead Bias 回避、セキュリティ対策等）。
- 次のイテレーションでの優先タスク（推奨）
  - run_prices_etl の完了および他 ETL ジョブ（財務データ・カレンダー）の pipeline 統合
  - strategy / execution 実装とエンドツーエンドのテスト（モックによる API 切替を含む）
  - CI 流水線、ユニットテスト、負荷テスト（RSS 大量取得時のメモリ/IO 挙動確認）
  - ドキュメント整備（DataPlatform.md / API 使い方 / 運用手順）

--- 

（この CHANGELOG はコードの現状から推測して作成しています。実際の変更履歴やリリース日付はリポジトリのコミットログ・タグに基づき適宜更新してください。）