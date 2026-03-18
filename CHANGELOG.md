Keep a Changelog に準拠した形式で、このコードベースから推測される変更履歴を日本語で作成しました。

注意: 実際のコミット履歴ではなく、ソースコードの内容から推測してまとめた「初期リリース (0.1.0)」のリリースノートです。

CHANGELOG.md
=============

すべての変更はこのファイルに記録されます。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に従います。

[0.1.0] - 2026-03-18
--------------------

Added
- パッケージ基盤
  - kabusys パッケージの初期構成を追加。バージョンは 0.1.0。
  - パッケージの公開APIとして ["data", "strategy", "execution", "monitoring"] を __all__ に定義。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート探索: .git または pyproject.toml を基準に自動的にルートを検出（CWD 非依存）。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、行内コメント扱いなどを考慮して安全にパース。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - Settings クラスを提供し、以下の重要な設定をプロパティで取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL (デフォルト: http://localhost:18080/kabusapi)
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH (デフォルト: data/kabusys.duckdb), SQLITE_PATH (デフォルト: data/monitoring.db)
    - KABUSYS_ENV (development/paper_trading/live のバリデーション) および LOG_LEVEL のバリデーション
    - is_live / is_paper / is_dev ヘルパー

- データ収集クライアント (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
  - 特徴:
    - API レート制限制御（固定間隔スロットリング、デフォルト: 120 req/min）。
    - 再試行ロジック（指数バックオフ、最大3回、HTTP 408/429 および 5xx を再試行対象）。
    - 401 レスポンス時の自動トークンリフレッシュ（1 回のみ）、トークンキャッシュ共有。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes (日足 OHLCV)
      - fetch_financial_statements (四半期財務)
      - fetch_market_calendar (JPX マーケットカレンダー)
    - DuckDB への冪等な保存関数:
      - save_daily_quotes -> raw_prices テーブルに ON CONFLICT DO UPDATE
      - save_financial_statements -> raw_financials テーブルに ON CONFLICT DO UPDATE
      - save_market_calendar -> market_calendar テーブルに ON CONFLICT DO UPDATE
    - レスポンス JSON デコードエラーハンドリング、タイムアウト、ログ出力
    - 小さな変換ユーティリティ: _to_float / _to_int（不正値を安全に None に）

- ニュース収集モジュール (kabusys.data.news_collector)
  - RSS フィードを取得して raw_news / news_symbols に保存するフローを実装。
  - セキュリティ対策と堅牢性:
    - defusedxml を使った XML パース（XML Bomb 等の防御）。
    - SSRF 対策: URL スキーム検証（http/https のみ）、リダイレクト先の事前検証、ホストがプライベートアドレスか検査。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）および gzip 解凍後サイズチェック（Gzip bomb 対策）。
    - トラッキングパラメータ除去（utm_* 等）と URL 正規化、記事ID は正規化 URL の SHA-256（先頭32文字）で生成して冪等性を保証。
    - テキスト前処理（URL 除去、空白正規化）。
  - DB 保存:
    - save_raw_news: チャンク化して INSERT ... RETURNING により実際に挿入された記事IDを返す。トランザクション管理（まとめてコミット/ロールバック）。
    - save_news_symbols / _save_news_symbols_bulk: 記事と銘柄コードの紐付けをバルクで安全に保存。重複を排除してチャンク挿入。
  - 銘柄コード抽出: テキスト中の 4 桁数字を抽出し、known_codes に存在するものだけを返すユーティリティ。
  - デフォルト RSS ソースに Yahoo Finance のビジネス RSS を登録。

- DuckDB スキーマ定義 (kabusys.data.schema)
  - DataSchema に基づく初期 DDL を追加（Raw Layer のテーブル定義を含む）。
  - raw_prices, raw_financials, raw_news, raw_executions 等のテーブル DDL（NOT NULL / CHECK 制約、PRIMARY KEY）を定義。
  - スキーマ初期化用モジュールとして提供（DuckDB でのデータレイヤ管理を前提）。

- 研究（Research）モジュール (kabusys.research)
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト 1,5,21 営業日）の将来リターンを DuckDB の prices_daily を参照して一括取得。
    - calc_ic: ファクターと将来リターンのランク相関（Spearman ρ）を計算。欠損・定数分散時は None を返す。
    - factor_summary: 各ファクターカラムの count/mean/std/min/max/median を算出。
    - rank: 同順位は平均ランクとするランク付けユーティリティ（丸めで ties 判定を安定化）。
    - 設計方針: pandas 等の外部ライブラリに依存せず標準ライブラリ + duckdb で実装。
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev を prices_daily から計算（200 日 MA のデータ不足時は None）。
    - calc_volatility: atr_20 (20 日 ATR), atr_pct, avg_turnover, volume_ratio を計算（TR の NULL 伝播やカウントを正しく扱う）。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS が 0/欠損時は None）。prices_daily と組み合わせる。
    - 定数（ウィンドウ長等）はモジュール内で明示的に定義され、スキャン日数に余裕を持つ設計。

Changed
- 初版のため特に「変更」はありません。

Fixed
- 初版のため特に「修正」はありません。

Security
- news_collector: SSRF 対策、XML パースのハードニング、レスポンスサイズ制限、gzip 解凍後のサイズ検査により外部データ取り込みの安全性を高めています。
- jquants_client: トークンの自動リフレッシュとリトライ戦略により不正な認証状態や一時的な API 障害に対して堅牢性を確保。

Performance
- jquants_client: API レート制御（固定間隔）を実装、ページネーションを効率的に処理。
- news_collector: INSERT をチャンク化してまとめてトランザクションでコミット、RETURNING を使用して正確な新規件数を把握。
- feature_exploration / factor_research: DuckDB のウィンドウ関数を活用して集計を SQL 側で効率化。

Compatibility / Requirements
- DuckDB に依存するモジュールが多数（データ格納・集計は DuckDB を前提）。
- news_collector で defusedxml が必要（XML の安全なパースのため）。
- research モジュールは外部データ取得や本番口座 API へのアクセスを行わない設計（prices_daily / raw_financials のみ参照）。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意/デフォルト指定あり: KABUSYS_ENV (development|paper_trading|live)、LOG_LEVEL、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH
  - 自動 .env ロードを無効化したい場合: KABUSYS_DISABLE_AUTO_ENV_LOAD=1

Migration notes
- 初回導入時は kabusys.data.schema を使って DuckDB のスキーマ（raw_prices, raw_financials, raw_news, market_calendar など）を作成してください。
- J-Quants API を利用する場合は JQUANTS_REFRESH_TOKEN を設定し、必要に応じて DUCKDB_PATH を設定してください。
- RSS ニュース収集を利用する場合は defusedxml をインストールしてください。

Notes / Limitations
- research モジュールは pandas 等に依存しない純 Python 実装のため、大規模データ時のメモリ/速度特性は環境に依存します（DuckDB 側での事前フィルタリングが推奨）。
- jquants_client の再試行対象ステータスは 408, 429, >=500。429 の場合は Retry-After ヘッダを尊重。
- news_collector の URL 正規化は既知のトラッキングパラメータプレフィックスを削除する方式。未対応のパラメータがあれば識別の振る舞いに影響する可能性があります。

署名
- 初期リリース: 基本機能（データ取得、保存、リサーチ用ファクター計算、ニュース収集、設定管理）を一通り実装した初期バージョンです。今後、strategy / execution / monitoring 周りの実装強化、単体テスト追加、CI/配布設定、ドキュメント整備、性能最適化などを予定しています。