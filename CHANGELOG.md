# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
このファイルはコードベース（現行バージョン: 0.1.0）から推測して作成した初期の変更履歴です。

フォーマット: [Unreleased] とリリース済みバージョンの一覧を含みます。

## [Unreleased]
（現時点で未リリースの変更はありません）

## [0.1.0] - 2026-03-17
初回リリース。日本株自動売買システム "KabuSys" のコア基盤を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - パッケージ名: kabusys。バージョンを `__version__ = "0.1.0"` として設定。
  - public API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定読み込みを自動化（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化オプション: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサ実装: export プレフィックス、クォート、エスケープ、インラインコメント対応。
  - 環境変数保護: OS の既存環境変数を保護する機構（protected set）。
  - Settings クラス: 型化されたプロパティを提供（J-Quants / kabuステーション / Slack / DB パス / 環境種別 / ログレベル 等）。
  - 入力検証: `KABUSYS_ENV` や `LOG_LEVEL` の許容値チェック、必須変数未設定時は明示的なエラー（ValueError）。

- J-Quants API クライアント (`kabusys.data.jquants_client`)
  - API 呼び出しユーティリティを実装: JSON パース、タイムアウト、クエリパラメータの組立て。
  - レート制御: 固定間隔スロットリング（120 req/min）を実装する内部 RateLimiter。
  - リトライ/バックオフ: 指数バックオフ（最大3回）、408/429/5xx に対する再試行処理、429 の場合は Retry-After を尊重。
  - トークン管理: リフレッシュトークンから ID トークンを取得する get_id_token、モジュールレベルのトークンキャッシュと自動リフレッシュ（401 検知時に1回のみリフレッシュして再試行）。
  - ページネーション対応の取得関数: fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar。
  - DuckDB への冪等保存関数: save_daily_quotes、save_financial_statements、save_market_calendar（ON CONFLICT DO UPDATE を利用）。
  - データ品質に配慮した変換ユーティリティ: _to_float, _to_int（空値や不正値の安全ハンドリング）。
  - 取得時刻 (fetched_at) を UTC で記録し、Look-ahead bias 対策のためいつデータを取得したかを追跡可能に。

- ニュース収集モジュール (`kabusys.data.news_collector`)
  - RSS フィード取得と前処理: fetch_rss、preprocess_text。
  - セキュリティ対策:
    - defusedxml を使った XML パース（XML Bomb 等に耐性）。
    - リダイレクト時の事前検査やホストの私的IP判定による SSRF 防止（_SSRFBlockRedirectHandler、_is_private_host）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンス長の上限チェック（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後の再検査（Gzip bomb 対策）。
  - URL 正規化: トラッキングパラメータ（utm_* 等）除去、スキーム/ホストの小文字化、フラグメント削除、クエリソート。
  - 記事 ID の生成: 正規化 URL の SHA-256（先頭32文字）を記事IDとして使用し冪等性を担保。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用いたチャンク単位の冪等保存（トランザクション）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けを一括挿入（ON CONFLICT DO NOTHING、INSERT ... RETURNING）。
  - 銘柄コード抽出: テキストから 4 桁数字候補を抽出し、known_codes に基づくフィルタリング（extract_stock_codes）。
  - デフォルト RSS ソースとして Yahoo Finance のカテゴリフィードを登録（DEFAULT_RSS_SOURCES）。

- DuckDB スキーマ管理 (`kabusys.data.schema`)
  - DataPlatform 指針に基づくスキーマを実装:
    - Raw, Processed, Feature, Execution 層のテーブル定義（raw_prices, raw_financials, raw_news, market_calendar, prices_daily, fundamentals, features, ai_scores, signals, signal_queue, orders, trades, positions, portfolio_performance など）。
    - 制約（PRIMARY KEY, CHECK, FOREIGN KEY）および型指定。
    - 索引定義（頻出クエリ向けのインデックス）。
  - init_schema(db_path) による初期化機能（親ディレクトリ自動作成、冪等なテーブル作成）。
  - get_connection(db_path) による既存 DB への接続取得。

- ETL パイプライン基盤 (`kabusys.data.pipeline`)
  - ETL の設計概要に沿った基礎実装。
  - ETLResult データクラス: 実行結果・品質問題・エラーを表現。
  - 差分更新ヘルパー: テーブル存在判定、最大日付取得、取引日調整（_adjust_to_trading_day）。
  - 最終取得日計算ヘルパー: get_last_price_date、get_last_financial_date、get_last_calendar_date。
  - run_prices_etl の骨子実装（差分取得ロジック、backfill_days による再取得、J-Quants からの fetch と保存の呼び出し）。
  - 設計方針コメント: 品質チェックは Fail-Fast ではなく呼び出し元で判断すること、テスト容易性のため id_token 注入可能。

- モジュール骨組み
  - 空のパッケージ初期化ファイルを配置: `kabusys.data.__init__`, `kabusys.strategy.__init__`, `kabusys.execution.__init__`（将来的な拡張箇所）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- RSS パーサや HTTP クライアント周りに複数のセキュリティ対策を導入:
  - defusedxml の利用による XML 攻撃緩和。
  - SSRF 対策: URL スキームのホワイトリスト化、リダイレクト先の検査、プライベート IP 判定。
  - レスポンスサイズ制限・gzip 解凍後チェックによりメモリ DoS 対策。
  - 環境変数読み込み時に OS 環境変数の保護機構を用意。

### Performance
- API レート制御（RateLimiter）で J-Quants のレート制限順守を容易に。
- DB 書き込みはチャンク分割・トランザクション・ON CONFLICT を利用して効率と冪等性を確保。
- 取得処理のページネーション対応（pagination_key 共有）で大容量取得に対応。

### Notes / Known limitations / TODO
- pipeline モジュールは ETL の基盤と一部ジョブ（run_prices_etl の骨子）を実装していますが、完全なフロー（calendar / financials の ETL、品質チェックの実行とハンドリング）は今後の実装が想定されます。quality モジュールは参照されていますが、この差分だけからは内容の全実装が確認できません。
- strategy / execution / monitoring の各パッケージはエントリポイントを用意していますが、具体的な戦略ロジックや発注連携処理はまだ追加実装が必要です。
- DEFAULT_RSS_SOURCES は最小構成（Yahoo Finance）で、実運用では追加のソース設定が推奨されます。
- エラーハンドリング方針として「1ソース失敗でも他ソースは継続する」等の記述があるため、運用時はログ・監視の整備が推奨されます。

---

メジャーな追加・設計方針やセキュリティ・性能面の考慮点を中心に記載しました。必要であれば、各モジュール（jquants_client / news_collector / schema / pipeline）ごとにより詳細な変更点や設計コメントを追記できます。どの粒度で追記するか指示してください。