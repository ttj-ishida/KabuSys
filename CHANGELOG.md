Keep a Changelog 準拠の CHANGELOG.md（日本語）

すべての変更は SemVer（パッケージ __version__ = 0.1.0）に従います。

履歴
----

Unreleased
----------
（なし）

0.1.0 - 2026-03-18
-----------------
Added
- パッケージ初期リリース: kabusys（__version__ = 0.1.0）
  - パッケージ公開用 __init__ にて主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。
- 環境設定管理（kabusys.config）
  - .env/.env.local 自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索して検出）。
  - .env パースの詳細実装（export 形式、クォート・エスケープ、コメント扱いの厳密処理をサポート）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - Settings クラスを提供し、必須環境変数取得（_require）やバリデーション（KABUSYS_ENV, LOG_LEVEL）を実装。
  - デフォルト DB パス（DUCKDB_PATH, SQLITE_PATH）や Slack / kabu API / J-Quants トークン等の設定プロパティを提供。
- Data モジュール（kabusys.data）
  - J-Quants クライアント（kabusys.data.jquants_client）
    - API 呼び出しユーティリティ (_request) を実装。JSON デコードエラーハンドリング、タイムアウト、ページネーション対応。
    - レート制限（120 req/min）を固定間隔スロットリングで制御する RateLimiter 実装。
    - 再試行ロジック（指数バックオフ、最大 3 回）および 401 受信時の自動トークンリフレッシュ処理を実装。
    - データ取得関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（ページネーション対応）。
    - DuckDB への保存関数（冪等）: save_daily_quotes, save_financial_statements, save_market_calendar。ON CONFLICT を用いた上書き処理、PK 欠損のスキップ、fetched_at の記録。
    - ユーティリティ: 型変換ヘルパー _to_float, _to_int（堅牢な変換ロジック）。
  - ニュース収集（kabusys.data.news_collector）
    - RSS フェッチ実装（fetch_rss）: defusedxml を用いた安全な XML パース、gzip 解凍、Content-Length/受信サイズ上限（10MB）による防御、リダイレクト時のスキーム/ホスト検査。
    - SSRF 対策: リダイレクトハンドラと事前ホスト検査でプライベートアドレスや非 http(s) スキームを拒否。
    - URL 正規化（utm などのトラッキングパラメータ削除）と記事 ID 生成（正規化 URL の SHA-256 の先頭 32 文字）。
    - テキスト前処理（URL 除去・空白正規化）と pubDate パースの堅牢化（フォールバック）。
    - DB 保存: save_raw_news（チャンク挿入、トランザクション、INSERT ... RETURNING による実際に挿入された記事 ID の取得）および news_symbols 関連（単体/バルク保存）を実装。重複排除・トランザクションロールバック処理あり。
    - 銘柄抽出ユーティリティ extract_stock_codes（4 桁コード検出と known_codes フィルタ）。
    - 統合ジョブ run_news_collection: 複数ソース処理、各ソースの独立エラーハンドリング、新規挿入記事に対する銘柄紐付けの一括保存。
  - DuckDB スキーマ定義（kabusys.data.schema）
    - Raw レイヤーの主要テーブル DDL（raw_prices, raw_financials, raw_news, raw_executions など）の定義を提供（CREATE TABLE IF NOT EXISTS）。
    - DataSchema に基づく多層構造（Raw / Processed / Feature / Execution）の方針を示すドキュメント文字列。
- Research モジュール（kabusys.research）
  - factor_research モジュール
    - モメンタム、ボラティリティ、バリュー等のファクター計算関数を実装:
      - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200 日 MA 乖離）計算。データ不足時は None を返す仕様。
      - calc_volatility: ATR（20 日平均 true range）、atr_pct、avg_turnover、volume_ratio の計算。真のレンジ計算で NULL 伝播を制御。
      - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS 不在や 0 の場合は None）。
    - データスキャン範囲のバッファ設計（カレンダー日での余裕）を導入。
  - feature_exploration モジュール
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得する実装（LEAD を利用）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。必要件数未満の場合は None。
    - rank / factor_summary: 同順位の平均ランクや各カラムの count/mean/std/min/max/median を計算するユーティリティ。
  - research パッケージの __all__ で主要関数を公開。
- ドキュメント・設計注釈
  - 各モジュールに設計方針・使用上の注意・安全対策（Look-ahead bias 対策の fetched_at 記録、SSRF 対策、XML 安全化など）を詳細な docstring として含める。

Security
- defusedxml を使用して XML 関連の脆弱性（XML Bomb 等）に対処。
- RSS フェッチでの SSRF 対策を実装（リダイレクト検査、非公開 IP 拒否、スキーム制限）。
- レスポンスサイズ上限と gzip 解凍後の検査でメモリ DoS を緩和。
- J-Quants API クライアントでの再試行・トークン自動更新により認証失敗時の暴露・無限再帰を回避する設計。

Notes / Upgrade and Usage
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings により必須とされる（未設定で ValueError）。
- 環境変数の自動ロード:
  - プロジェクトルート（.git または pyproject.toml を含む親ディレクトリ）を検出して .env → .env.local の順に読み込む（OS 環境変数を保護）。テスト時に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB の初期化:
  - schema モジュールの DDL を使用して raw_* テーブル等を作成してください（CREATE TABLE IF NOT EXISTS を使用）。
- J-Quants API:
  - API レート制限を守るため内部で固定間隔のスロットリングを行います。大量取得や高速並列化時は呼び出し間隔に注意してください。
- ニュース収集:
  - fetch_rss は外部ネットワークアクセスを行います。内部ネットワークや非 http/https スキームを拒否するため、社内プロキシ設定やホワイトリスト利用時は挙動確認をお願いします。
- 冪等性:
  - データ保存関数は ON CONFLICT を用いた冪等処理を行いますが、スキーマの主キー・制約が実際の DB と一致していることを確認してください。

今後の予定（含める可能性）
- Feature / Processed レイヤの追加 DDL と ETL ユーティリティ
- Strategy / Execution の具体的な発注ロジックとシミュレーション機能
- 追加のニュースソースやスクレイピング機能（要セキュリティ評価）
- ユニットテストや統合テストを含む CI 設定の整備

補足:
- ここに記載した機能・挙動はコードベースから推測してまとめたものであり、実際の運用・設定や環境によって注意点が変わる場合があります。README や個別のモジュール docstring を参照のうえ、運用時には必ずテスト環境で動作確認してください。