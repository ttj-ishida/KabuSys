# CHANGELOG

すべての変更は Keep a Changelog の仕様に準拠しています。  
バージョン番号はパッケージの __version__ に合わせています。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム KabuSys のコア基盤を提供します。

### Added
- パッケージ基盤
  - パッケージエントリポイント `kabusys.__init__` を追加（__version__ = 0.1.0、モジュール公開一覧を定義）。
- 設定・環境変数管理
  - `.env` / `.env.local` 自動ロード機能（プロジェクトルート判定：.git または pyproject.toml を基準）。
  - カスタム .env パーサ（export 形式・引用符・インラインコメント・エスケープ処理に対応）。
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境 / ログレベルなどをプロパティ経由で取得・バリデーション。
- J-Quants データクライアント（kabusys.data.jquants_client）
  - 株価日足（OHLCV）、財務データ（四半期 BS/PL）、JPX マーケットカレンダー取得 API を実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング（RateLimiter）。
  - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx を対象）。429 の場合は Retry-After ヘッダを優先。
  - 401 レスポンス時はリフレッシュトークンで自動再取得・1 回のみリトライ。
  - ページネーション対応（pagination_key の取り扱い）。
  - DuckDB へ保存する冪等な save_* 関数（ON CONFLICT DO UPDATE を利用）。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead バイアスを抑止。
  - 型変換ユーティリティ（_to_float / _to_int）を実装し、不整合値を安全に扱う。
- RSS ニュース収集（kabusys.data.news_collector）
  - RSS フィード取得・パース・前処理・DuckDB への保存ワークフローを実装。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）。
  - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を担保。
  - defusedxml を利用して XML 関連の安全対策（XML Bomb 等）を実装。
  - SSRF 対策：
    - URL スキーム制限（http/https のみ許可）。
    - リダイレクトハンドラでリダイレクト先スキームおよびプライベートアドレス判定を実施。
    - ホスト名を DNS 解決してプライベート/ループバック/リンクローカルを検出。
  - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、受信超過や Gzip 解凍後のサイズ超過を検出して拒否。
  - 投稿本文の前処理（URL 除去、空白正規化）。
  - DB へのバルク挿入はチャンク化（_INSERT_CHUNK_SIZE）してトランザクションで実行。INSERT ... RETURNING を使い実際に挿入された件数を返す。
  - 記事と銘柄コードの紐付け処理（news_symbols 保存、重複除去）。
  - デフォルト RSS ソースに Yahoo Finance ビジネスカテゴリを設定。
- DuckDB スキーマ（kabusys.data.schema）
  - DataPlatform に基づくスキーマ定義を提供（Raw / Processed / Feature / Execution 層）。
  - raw_prices, raw_financials, raw_news, raw_executions 等の Raw テーブル。
  - prices_daily, market_calendar, fundamentals, news_articles, news_symbols 等の Processed テーブル。
  - features, ai_scores 等の Feature テーブル。
  - signal_queue, orders, trades, positions, portfolio_performance 等の Execution テーブル。
  - 各種制約（PK/チェック制約/外部キー）およびクエリ最適化用インデックスを定義。
  - init_schema(db_path) によりディレクトリ作成含めて初期化を行い、接続を返す。get_connection() で既存 DB に接続。
- ETL パイプライン（kabusys.data.pipeline）
  - 差分更新（差分取得・バックフィルを考慮）、保存、品質チェックを行う ETL 設計。
  - ETLResult データクラスで ETL 実行結果・品質問題・エラーを集約・シリアライズ可能に実装。
  - テーブル存在チェック、最大日付取得ユーティリティ、営業日調整ロジックを提供。
  - run_prices_etl の差分取得ロジック（DB 最終取得日に基づく date_from 自動算出、backfill_days の考慮）を実装。
- ロギング
  - 各モジュールで意図的に情報・警告・例外ログを出力し、障害時のトレースを容易にする。

### Security
- ニュース収集での SSRF 対策（スキーム検証・ホストプライベート判定・リダイレクト時の検査）。
- defusedxml の利用により XML ベース攻撃（XML Bomb 等）に対処。
- .env 読み込み時のファイルアクセスエラーを warnings.warn で通知し、安全にフォールバック。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known issues / 注意点
- run_prices_etl の実装は差分取得ロジックを備えていますが、配布されたコード片では最後の戻り値行が途中で切れているように見えます（"return len(records), " で終了）。実際の利用時には関数が (fetched_count, saved_count) のタプルを返す想定であるため、必要に応じて実装を確認・修正してください。
- news_collector の DNS 解決失敗時は「安全側」として非プライベート扱いで通過させる実装です。極めて厳格に内部アドレスを排除したい場合は追加のポリシー（明示的許可リスト等）を検討してください。
- J-Quants クライアントは urllib を使った同期実装であり、大量の並列フェッチなど高スループット用途には設計されていません。必要であれば非同期化やコネクションプーリングの導入を検討してください。

---

（今後のリリースでは各機能の安定化、追加の ETL ジョブ、戦略・実行モジュールの実装、テストカバレッジ強化、非同期処理や監視機能の拡張を予定）