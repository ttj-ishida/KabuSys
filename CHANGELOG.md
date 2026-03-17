# Changelog

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の方針に従って管理されています。

フォーマット: [Unreleased] と各リリース（例: [0.1.0] - YYYY-MM-DD）

## [Unreleased]

- Known issues / TODO
  - run_prices_etl の実装に不整合が見られます（関数末尾の return が 1 要素しか返さないように見えるため、呼び出し側で期待される (fetched, saved) のタプルになっていない可能性があります）。ユニットテストの追加と戻り値の修正を推奨します。

---

## [0.1.0] - 2026-03-17

初回リリース。日本株自動売買システムのコアライブラリを追加しました。主な追加点は以下の通りです。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（__version__ = 0.1.0）。
  - サブパッケージの公開: data, strategy, execution, monitoring（空 __init__.py を含む構成）。

- 設定/環境変数管理（kabusys.config）
  - .env ファイルや OS 環境変数からの自動読み込み機能を実装。
  - プロジェクトルート探索ロジック（.git または pyproject.toml を基準に親ディレクトリを検索）により CWD に依存しない自動読み込み。
  - .env 構文のパーサ実装（コメント、export 句、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの処理対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。
  - 環境変数保護機能（protected set）を導入し、override オプションで OS 環境変数を上書きしない挙動を提供。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス / 環境種別（development/paper_trading/live）等のプロパティを提供。値検証（有効な env 値・ログレベルの検証）と is_live/is_paper/is_dev ヘルパーを提供。
  - 必須変数未設定時には ValueError を投げる _require ユーティリティ。

- J-Quants API クライアント（kabusys.data.jquants_client）
  - J-Quants API からのデータ取得機能を実装（株価日足・四半期財務・JPX カレンダー）。
  - API レート制限対応: 固定間隔スロットリングで 120 req/min を遵守する RateLimiter を実装。
  - リトライ戦略: 指数バックオフ（最大 3 回）、対象ステータス（408, 429, 5xx）でリトライ。429 の場合は Retry-After を優先。
  - 401 Unauthorized 受信時にリフレッシュトークンを使って id_token を自動リフレッシュし 1 回だけ再試行する仕組みを実装（allow_refresh フラグで無限再帰を防止）。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）を実装。pagination_key を追跡して重複ページを防止。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。挿入は冪等（ON CONFLICT DO UPDATE）で重複を排除。fetched_at を UTC ISO 形式で記録して Look-ahead バイアスを防止。
  - 型変換ヘルパー（_to_float / _to_int）を用意し、不正値や空値を安全に変換。
  - id_token キャッシュ（モジュールレベル）を導入してページネーション間や短時間の呼び出しでの再発行を抑制。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからのニュース収集機能を実装（デフォルトに Yahoo Finance カテゴリを含む）。
  - セキュリティ重視の設計:
    - defusedxml を利用した XML パース（XML Bomb 防止）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、プライベート/ループバック/リンクローカル/マルチキャスト IP を検出してアクセス拒否、リダイレクト時の検証を行うカスタム HTTPRedirectHandler を導入。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES = 10MB）を設け、受信バイト数と解凍後のサイズ両方をチェックして DoS 対策。
  - URL 正規化: トラッキングパラメータ（utm_*, fbclid, gclid, ref_, _ga 等）を削除しフラグメントを除去、クエリをソートして一意化。
  - 記事 ID は正規化後 URL の SHA-256 の先頭32文字で生成して冪等性を確保。
  - テキスト前処理: URL 除去、空白正規化（連続空白→単一スペース）。
  - extract_stock_codes 関数でテキスト中の 4 桁銘柄コードを抽出し、既知コードセットでフィルタ。
  - DB 保存: save_raw_news でチャンク挿入（INSERT ... RETURNING id）およびトランザクション管理（失敗時はロールバック）。save_news_symbols と _save_news_symbols_bulk により記事と銘柄の紐付けを一括で安全に保存。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用のスキーマ定義を追加（Raw / Processed / Feature / Execution の多層構造）。
  - raw_prices, raw_financials, raw_news, raw_executions をはじめ、prices_daily, market_calendar, fundamentals, news_articles, news_symbols, features, ai_scores, signals, signal_queue, portfolio_targets, orders, trades, positions, portfolio_performance 等のテーブル定義と制約（PRIMARY KEY / CHECK / FOREIGN KEY）を実装。
  - よく使うクエリ向けのインデックス定義を追加。
  - init_schema(db_path) により DB ファイルの親ディレクトリ自動作成とテーブル/インデックスの冪等作成を提供。get_connection は既存 DB への接続を返すヘルパー。

- ETL パイプライン（kabusys.data.pipeline）
  - ETL の設計方針と差分更新ロジックを実装（最終取得日に基づく差分取得、バックフィル設定）。
  - ETLResult dataclass により ETL 実行結果・品質検査結果・エラーを集約（to_dict により品質問題をシリアライズ可能）。
  - 市場カレンダーの調整ヘルパー（非営業日は直近営業日に調整）など便利関数を実装。
  - 差分判定ヘルパー（get_last_price_date, get_last_financial_date, get_last_calendar_date）を実装。
  - run_prices_etl の骨子を実装（差分計算、fetch_daily_quotes 呼び出し、save_daily_quotes 保存）。※（注）関数末尾の戻り値に注意（Unreleased に記載の既知問題参照）。

### Security
- news_collector において SSRF 対策・受信サイズ制限・defusedxml の採用により外部入力を扱う際の堅牢性を強化。
- config の .env パースは明示的にエスケープやクォートの扱いを安全に行う設計。

### Notes
- 多くの部分で「冪等性（ON CONFLICT）」「トランザクション」「EXPLICIT ロギング」を重視した実装になっており、再実行耐性・監査可能性を意識しています。
- run_news_collection はソース毎に個別にエラーハンドリングし、1 ソース失敗でも他ソースは継続します。
- 将来的な改善点としてユニットテストの拡充（特にネットワーク周りのモックテスト・ETL 結果検証）と、pipeline 内の戻り値整合性チェックを推奨します。

---

メンテナンス履歴は今後のコミットで随時更新してください。