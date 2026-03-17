# Changelog

すべての変更は Keep a Changelog の形式に従います。  
新しい変更は常にトップに追加してください。  
リリースポリシー: 初期バージョン 0.1.0 をリリースします。

## [0.1.0] - 2026-03-17

初回リリース — 日本株自動売買システム「KabuSys」のコア機能を実装しました。

### Added
- パッケージメタ情報
  - src/kabusys/__init__.py にパッケージ名とバージョン（0.1.0）を定義。パブリック API として data, strategy, execution, monitoring をエクスポート。

- 環境変数・設定管理（src/kabusys/config.py）
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動的に読み込む機能を実装（プロジェクトルートは .git または pyproject.toml を基準に検出）。
  - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト目的）。
  - .env の行パーサ: export 形式、クォート対応、インラインコメント処理を含む堅牢なパーサを実装。
  - 必須設定の取得ヘルパー _require と Settings クラスを提供。
  - J-Quants / kabuステーション / Slack / DB パスなど主要な設定（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）をプロパティで公開。
  - デフォルト値: KABU_API_BASE_URL="http://localhost:18080/kabusapi", DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"。
  - env / log_level のバリデーション（許容値チェック）と環境判定ヘルパー（is_live, is_paper, is_dev）。

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants からの日足（OHLCV）、財務データ（四半期 BS/PL）、マーケットカレンダーの取得および DuckDB への保存関数を実装。
  - API レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を導入。
  - リトライロジック（指数バックオフ、最大 3 回）と HTTP ステータスごとの扱い（408/429/5xx を再試行）。
  - 401 Unauthorized を検出した際にリフレッシュトークンから id_token を自動取得して 1 回だけリトライする仕組みを実装（無限再帰回避のため allow_refresh フラグ有り）。
  - ページネーション対応（pagination_key による取得ループ）。
  - DuckDB への保存は冪等（ON CONFLICT DO UPDATE）で重複を排除。
  - 取得時刻（fetched_at）を UTC ISO 形式で保存し、Look-ahead Bias に配慮。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得と raw_news テーブルへの保存、記事と銘柄コードの紐付け（news_symbols）を実装。
  - セキュリティ対策:
    - defusedxml による XML パースで XML Bomb 等の防止。
    - HTTP リダイレクト時にスキームとホスト/IP を検証するカスタム RedirectHandler（SSRF 対策）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - ホストがプライベート/ループバック等であればアクセス拒否。
  - URL の正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と SHA-256 の先頭32文字を使用した記事ID生成により冪等性を確保。
  - テキスト前処理（URL除去、空白正規化）。
  - DuckDB へのバルク INSERT はチャンク化してトランザクション内で実行し、INSERT ... RETURNING により実際に挿入された件数を正確に返す。
  - デフォルト RSS ソースとして Yahoo Finance のビジネスカテゴリを登録。

- DuckDB スキーマ定義・初期化（src/kabusys/data/schema.py）
  - Raw / Processed / Feature / Execution の各レイヤーに対応するテーブル定義を多数実装（raw_prices, raw_financials, raw_news, raw_executions, prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance など）。
  - 適切な制約（PRIMARY KEY、CHECK、FOREIGN KEY）やインデックスを定義。
  - init_schema(db_path) により指定 DB を初期化して接続を返す（親ディレクトリ自動作成、冪等実行）。
  - get_connection(db_path) による既存 DB への接続取得。

- ETL パイプライン（src/kabusys/data/pipeline.py）
  - 差分更新、バックフィル、品質チェックのための基本フレームワークを実装。
  - ETLResult データクラスにより処理結果・品質問題・エラーメッセージを集約。
  - raw_* の最終取得日の取得ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）。
  - 市場カレンダーに基づく営業日調整ヘルパー（_adjust_to_trading_day）。
  - run_prices_etl: 差分更新ロジック（最終取得日 - backfill_days から再取得）、J-Quants client 経由で fetch & save を実行するジョブを実装。
  - 市場カレンダーの先読み日数・初回データ開始日の定数定義。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- news_collector:
  - defusedxml を使用した XML パースで XML 攻撃を緩和。
  - SSRF 対策としてリダイレクト先の検証、プライベートアドレスの拒否。
  - レスポンス上限・gzip 解凍後の上限チェックでメモリ DoS を防止。

### Known issues / Notes
- run_prices_etl の戻り値に関する不整合:
  - 現在の実装は最後の行で `return len(records),` とコンマのみになっており、意図した (fetched_count, saved_count) のタプルを返していません。テスト時や呼び出し元でタプルアンパックを行うと TypeError になる可能性があります。
  - 期待される修正: `return len(records), saved` のように第二要素として保存件数を返すこと。

- quality モジュールへの依存:
  - pipeline モジュールは品質検査結果の扱い（quality.QualityIssue）を想定していますが、今回のコードベースでは quality モジュールの実装詳細は含まれていません。品質チェック機能を利用する際は該当モジュールの実装・インターフェースを合わせて準備してください。

- テスト・モック用フック:
  - news_collector は _urlopen をモック可能な設計だが、外部統合テストを行う際はネットワーク依存部分のモックが必要です。

### Migration / Upgrade notes
- 初回導入時は .env.example を参照して以下の必須環境変数を設定してください:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードを無効化する場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト環境などで有用）。
- DuckDB の初期化は init_schema() を呼び出して行ってください（get_connection() は既存 DB 用）。

---

今後の予定（例）
- pipeline の残り ETL ジョブ（財務データ、マーケットカレンダー、news ETL の統合）を完成させる。
- quality モジュールの実装および品質チェック結果に基づく自動アクション機構。
- strategy / execution / monitoring 各層の実装と E2E テスト。