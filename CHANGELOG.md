# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
このプロジェクトは "Keep a Changelog" の慣例に従い、意味のあるリリースノートを残します。  

フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]

## [0.1.0] - 2026-03-17
初回リリース。

### Added
- パッケージ基底
  - kabusys パッケージを追加。公開 API は data, strategy, execution, monitoring を想定。
  - __version__ = 0.1.0 を設定。

- 設定管理
  - kabusys.config モジュールを追加。
  - .env ファイル（.env, .env.local）および OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
  - 自動環境変数ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` を追加。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / データベースパス等をプロパティで安全に取得。
  - 環境変数の検証（KABUSYS_ENV や LOG_LEVEL の許容値チェック）と必須項目取得時のエラー通知を実装。

- J-Quants データクライアント
  - kabusys.data.jquants_client を追加。
  - API レート制御（120 req/min）を固定間隔スロットリングで実装（_RateLimiter）。
  - 冪等性を考慮した DuckDB への保存（ON CONFLICT DO UPDATE）関数を実装:
    - fetch_daily_quotes / save_daily_quotes（株価日足）
    - fetch_financial_statements / save_financial_statements（四半期財務データ）
    - fetch_market_calendar / save_market_calendar（JPX マーケットカレンダー）
  - リトライ戦略（指数バックオフ、最大3回）を実装。408/429/5xx を再試行対象とし、429 の場合は Retry-After を尊重。
  - 401 受信時はリフレッシュトークンから id_token を自動更新して1回リトライするロジックを実装。
  - 取得時刻（fetched_at）を UTC で記録し、Look-ahead Bias の追跡を容易にする設計。

- ニュース収集モジュール
  - kabusys.data.news_collector を追加。
  - RSS フィード取得・パース・前処理・DB保存のパイプラインを実装（raw_news / news_symbols への保存）。
  - セキュリティ／堅牢化:
    - defusedxml を用いた XML パース（XML Bomb 等への対策）。
    - HTTP リダイレクト時にスキームとリダイレクト先のホストを検査する SSRF 対策ハンドラを実装。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンス最大バイト数制限（MAX_RESPONSE_BYTES=10MB）と gzip 解凍後の再チェック（Gzip bomb 対策）。
    - トラッキングパラメータ（utm_*, fbclid, gclid 等）除去と URL 正規化。
  - 冪等性:
    - 記事IDを正規化URLの SHA-256（先頭32文字）で作成し一意性を保証。
    - INSERT ... ON CONFLICT DO NOTHING と INSERT ... RETURNING を利用して新規挿入分のみを返す実装。
    - バルク挿入のチャンク化（デフォルトチャンク 1000 件）で SQL 長の問題を回避。
  - 銘柄コード抽出ユーティリティ（4桁数字、known_codes によるフィルタリング）を実装。
  - run_news_collection により複数 RSS ソースからの収集を統合し、各ソースは独立してエラーハンドリングする設計。

- スキーマ定義
  - kabusys.data.schema に DuckDB 用のスキーマ定義を追加。
  - Raw / Processed / Feature / Execution の多層構造テーブルを定義（raw_prices, raw_financials, raw_news, market_calendar, features, ai_scores, signals, orders, trades, positions 等）。
  - 関連インデックスを作成して典型的クエリの検索性能を改善。
  - init_schema(db_path) でディレクトリ作成とテーブル初期化を行うユーティリティを提供。get_connection も用意。

- ETL パイプライン
  - kabusys.data.pipeline を追加。
  - 差分更新ロジック（最終取得日からの差分取得、自動バックフィル）を実装。
  - ETL の結果を表現する ETLResult データクラスを提供（品質問題とエラーの集約）。
  - run_prices_etl（株価日足差分ETL）等の個別 ETL ジョブ用ユーティリティを追加（差分計算・_adjust_to_trading_day など）。
  - 品質チェックフック（quality モジュールとの連携を想定）を組み込む設計。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- news_collector:
  - defusedxml の採用、SSRF 対策、レスポンスサイズ制限、gzip 解凍後の検査により外部からの攻撃ベクトルを低減。
- jquants_client:
  - タイムアウト・リトライ・トークン自動リフレッシュにより誤動作や認証に起因する障害を縮小。

### Notes / Design decisions
- 環境変数自動ロードはプロジェクトルートの検出に依存するため、パッケージ配布後も挙動が一致するように __file__ を基点に親ディレクトリを探索する実装にしています。
- DuckDB に対する保存は可能な限り冪等に設計（ON CONFLICT DO UPDATE / DO NOTHING）。これにより再実行や部分的なリトライが安全になることを意図しています。
- API レート制御はシンプルな固定間隔スロットリングを採用（120 req/min）。将来的にトークンバケット等に変更する余地があることを想定。
- ニュース記事 ID は URL 正規化に基づく SHA-256 を先頭32文字切り出しで生成。トラッキングパラメータ除去により同一記事の多重登録を抑止します。
- ETL は Fail-Fast にせず、品質チェックで問題が検出されても可能な限り処理を継続し、呼び出し元が対応を判断できるようにしています。

### Known issues / TODO
- strategy, execution, monitoring パッケージは初期構成のみ（__init__.py が存在）で、実装は今後拡張予定。
- quality モジュールは pipeline から参照される想定だが、このリリースには含まれていない（外部モジュールとして提供予定）。
- DuckDB 接続周りのトランザクション・並列性/ロックに関する運用検証は必要。
- 単体テスト・統合テストのカバレッジは今後強化予定（現行コードは設計ドキュメントに基づく実装）。

---

貢献: 初期実装チーム（実装・設計に基づく自動生成注釈を含む）。