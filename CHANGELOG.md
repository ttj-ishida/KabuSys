# CHANGELOG

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティック バージョニングを採用します。

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買プラットフォーム「KabuSys」の基盤機能を実装しました。

### 追加 (Added)
- パッケージ初期化
  - パッケージ名: kabusys。バージョンを `__version__ = "0.1.0"` に設定。
  - パッケージ公開モジュール: data, strategy, execution, monitoring を __all__ に定義。

- 設定管理 (kabusys.config)
  - .env ファイルと環境変数から設定を読み込む Settings クラスを実装。
  - プロジェクトルート検出: __file__ を基準に親ディレクトリから `.git` または `pyproject.toml` を探索して自動で .env を読み込む機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応）。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの取り扱いをサポート。
  - 必須設定取得時のエラー報告 (`_require`) と値検証（KABUSYS_ENV, LOG_LEVEL 等）。

- J-Quants クライアント (kabusys.data.jquants_client)
  - J-Quants API との通信実装（token 取得、株価日足、財務データ、マーケットカレンダー取得）。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライ戦略: 指数バックオフによる最大 3 回のリトライ（HTTP 408/429/5xx、ネットワークエラー）を実装。
  - 401 Unauthorized 受信時の自動 ID トークンリフレッシュ（1 回のみ）とトークンキャッシュ機構。
  - ページネーション対応（pagination_key を利用）。
  - DuckDB へ保存する冪等性の高い保存関数を実装（ON CONFLICT DO UPDATE）:
    - save_daily_quotes: raw_prices への保存（fetched_at を UTC で記録）。
    - save_financial_statements: raw_financials への保存。
    - save_market_calendar: market_calendar への保存（取引日/半日/SQ 日フラグ変換）。
  - 型変換ユーティリティ: _to_float, _to_int（安全な変換と空値処理）。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからニュース記事を収集し raw_news と news_symbols に保存する一連の機能を実装。
  - セキュリティ対策:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: リダイレクト毎にスキーム/ホスト検証を行うカスタムリダイレクトハンドラ、プライベートアドレス検出（IP と DNS 解決の両方）。
    - URL スキーム検証（http/https のみ）。
    - レスポンス最大サイズ制限（MAX_RESPONSE_BYTES = 10 MB）と gzip 解凍後の検査。
  - URL 正規化とトラッキングパラメータ除去（utm_* 等）、SHA-256（先頭32文字）に基づく記事 ID 生成で冪等性を確保。
  - テキスト前処理（URL 除去、空白正規化）。
  - DuckDB への保存はトランザクション単位でまとめ、チャンク化して INSERT ... RETURNING を利用：
    - save_raw_news: 新規挿入された記事IDのリストを返す。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括保存し、実際に挿入された件数を返す。
  - 銘柄コード抽出ロジック（4桁数字を候補とし、既知のコードセットに基づくフィルタリング）。

- DuckDB スキーマ (kabusys.data.schema)
  - DataPlatform 設計に基づく包括的な DuckDB スキーマを実装（Raw / Processed / Feature / Execution 層）。
  - 主要テーブル: raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など。
  - インデックス定義（頻出クエリに備えた index を複数作成）。
  - init_schema(db_path): ディレクトリ自動作成 + 全 DDL を実行して接続を返す冪等な初期化関数を提供。
  - get_connection(db_path): 既存 DB への接続取得（初期化は行わない）。

- ETL パイプライン (kabusys.data.pipeline)
  - ETL の設計方針と差分取得ロジックを実装:
    - 差分取得のための最終日取得ヘルパー (get_last_price_date, get_last_financial_date, get_last_calendar_date)。
    - 取引日調整ヘルパー (_adjust_to_trading_day)。
    - run_prices_etl: 差分更新の算出（backfill_days を用いた再取得）、J-Quants からの取得と DuckDB への保存を行う関数（取得/保存件数を返す）。
  - ETL 結果を表す ETLResult データクラス（品質チェック結果・エラー集約・シリアライズ用）。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### セキュリティ (Security)
- RSS パーサで defusedxml を利用し、外部エンティティ攻撃や XML Bomb を低減。
- RSS フェッチでスキーム確認・プライベートアドレスチェック・リダイレクト検査を実施して SSRF リスクを低減。
- ネットワークおよび API 呼び出しでタイムアウト/レスポンスサイズを明示し、メモリ DoS を緩和。

### 既知の制限 / 注意点 (Notes)
- 環境変数の自動ロードはプロジェクトルート検出に依存します。パッケージ配布やテスト時に自動ロードを無効にするには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマの初期化は init_schema() を呼び出すことで行ってください。get_connection() はスキーマを作成しません。
- run_news_collection 等の収集処理は個々のソースで独立してエラーハンドリングされます（1 ソースの失敗が他へ影響しない設計）。
- J-Quants API 呼び出しは rate limiting を内部で行いますが、外部の長時間バッチや並列処理を組み合わせると上限に達する可能性があります。
- SQL 実行にはパラメータバインディングを用いて値を渡していますが、大きなチャンクサイズや長いクエリは DB 実装や環境に依存して調整が必要になる場合があります。
- 本リリースは初期版です。運用に当たってはログ・監視・リトライの挙動確認を推奨します。

### 互換性 (Compatibility)
- まだ初期リリースのため、破壊的変更はこれまで存在しません。今後のバージョンで API（関数シグネチャやテーブルスキーマ）に変更を加える可能性があります。マイナー/メジャーアップデート時は CHANGELOG と移行ガイドを提供します。

---

今後のリリースでは以下のような改善を予定しています（例）:
- ETL の品質チェック (quality モジュール) の統合、検出結果に基づく自動アクション。
- strategy / execution / monitoring モジュールの実装（バックテスト・発注連携・監視/アラート）。
- テストスイートの充実と CI ワークフローの整備。