# CHANGELOG

すべての重要な変更を記録します。これは Keep a Changelog の形式に準拠しています。

全般的なルール:
- ここに記載されたリリースはパッケージの公開時点での機能・設計決定を示します。
- 影響範囲や設計上の注意点は各項目の説明を参照してください。

## [0.1.0] - 2026-03-18

Added
- パッケージ基盤を追加
  - パッケージ名: kabusys
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - public API 想定モジュール: data, strategy, execution, monitoring を __all__ に公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルまたは環境変数から設定をロードする Settings クラスを実装。
  - 自動 .env ロード機能:
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索（カレントワーキングディレクトリに依存しない）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサ: export プレフィックス、シングル/ダブルクォート、インラインコメント、エスケープを考慮。
    - protected 引数により OS 環境変数を上書きしない挙動を保持。
  - 設定プロパティ（必須チェックを行う _require 使用）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV（development / paper_trading / live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - is_live / is_paper / is_dev のヘルパープロパティ

- データ取得クライアント: J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - RateLimiter による固定間隔スロットリング実装（デフォルト 120 req/min 相当）。
  - HTTP レスポンスに対する堅牢なリトライロジック（指数バックオフ、最大 3 回、408/429/5xx を再試行対象）。
  - 401 Unauthorized を検知した場合の自動トークンリフレッシュ（1 回のみ）とリトライ。
  - ページネーション対応の取得関数:
    - fetch_daily_quotes: 日足（OHLCV）のページネーション取得。
    - fetch_financial_statements: 財務諸表のページネーション取得。
    - fetch_market_calendar: JPX マーケットカレンダー取得。
  - DuckDB への保存関数（冪等/Upsert 実装）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存。fetched_at を UTC ISO8601 で記録。
    - save_financial_statements: raw_financials へ冪等保存（ON CONFLICT DO UPDATE）。
    - save_market_calendar: market_calendar へ冪等保存（ON CONFLICT DO UPDATE）。
  - 入力変換ユーティリティ:
    - _to_float: None/空文字を None、変換失敗は None。
    - _to_int: "1.0" のような小数文字列は float 経由で検証、小数部がある場合は None を返す（意図しない切捨てを防止）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィードからニュースを安全に収集する機能を実装。
  - セキュリティ対策:
    - defusedxml を使用して XML Bomb 等を防止。
    - SSRF 対策: リダイレクトハンドラでスキーム検証およびプライベート/ループバック/リンクローカル/マルチキャストアドレスへの接続をブロック。
    - URL スキーム検証は http/https のみ許可。
    - ホストがプライベートアドレスかどうかを DNS 解決して検査（解決失敗時は安全側通過）。
    - レスポンスバイト数上限（MAX_RESPONSE_BYTES = 10 MB）と、gzip 解凍後のサイズチェック。
  - RSS パースと前処理:
    - title/description/content:encoded の正規化（URL 除去、空白正規化）。
    - pubDate の RFC2822 パース（失敗時は警告ログと現在時刻で代替）。
  - 記事 ID の生成:
    - 正規化 URL（トラッキングパラメータ除去・小文字化・ソートなど）から SHA-256 ハッシュの先頭32文字を記事IDとして使用（冪等性保証）。
  - DB 保存:
    - save_raw_news: INSERT ... RETURNING id を用い、実際に挿入された記事IDのみを返す。チャンク挿入・トランザクションで処理。
    - save_news_symbols / _save_news_symbols_bulk: news_symbols への記事と銘柄コードの紐付けをチャンク INSERT で保存、ON CONFLICT で重複除去。
  - 銘柄コード抽出:
    - 4桁数字パターンから known_codes に含まれるもののみ抽出、重複は除去。
  - run_news_collection: 複数 RSS ソースを順に処理し、新規保存数を返す。各ソースは独立してエラーハンドリング。

- 研究（Research）モジュール (src/kabusys/research/)
  - feature_exploration.py:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): DuckDB の prices_daily を参照し将来リターンを一度のクエリで取得（LEAD を使用）。ホライズンの検証（1..252）あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマン順位相関（ランク相関）を自前実装で計算。有効レコード < 3 なら None。
    - rank(values): 同順位は平均ランクとする実装（丸め誤差対策に round(..., 12) を使用）。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算するユーティリティ。
    - ログ出力によるデバッグ情報（銘柄数や日付）。
    - 標準ライブラリのみで実装し、Research 実行時に発注等の外部アクセスは行わない設計。
  - factor_research.py:
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m と ma200_dev を DuckDB のウィンドウ関数で計算（必要データ不足時は None）。
    - calc_volatility(conn, target_date): 20日 ATR（true range 計算に prev_close を利用して NULL 伝播制御）、相対 ATR (atr_pct)、avg_turnover、volume_ratio を計算。
    - calc_value(conn, target_date): raw_financials から最新の財務データを取得して per（EPS が 0/欠損なら None）と roe を計算。
    - 設計方針: prices_daily / raw_financials のみ参照。出力は (date, code) キーの辞書リスト。
  - research パッケージ __all__ に主要関数を公開（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- DuckDB スキーマ定義（初期テーブル DDL） (src/kabusys/data/schema.py)
  - Raw Layer テーブル定義を追加:
    - raw_prices（date, code を PK、数値チェック制約あり）
    - raw_financials（code, report_date, period_type を PK、財務カラム）
    - raw_news（id を PK、datetime NOT NULL、fetched_at あり）
    - raw_executions（途中まで定義。execution_id 等のカラムと制約があるスキーマを用意）
  - スキーマは DataSchema.md に基づく3層（Raw/Processed/Feature）構造を想定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集周りで以下のセキュリティ対策を実装:
  - defusedxml による XML パースの安全化。
  - SSRF 対策（リダイレクト時のスキーム検査、プライベート IP ブロック、最終 URL の再検証）。
  - レスポンスサイズ制限・gzip 解凍後サイズチェック（Gzip bomb 対策）。
  - URL スキーム制限（http/https のみ）。

Notes / Design decisions
- Research フェーズの関数は「DuckDB の prices_daily/raw_financials のみを参照」する設計で、実行/発注 API や外部通信を行わないように分離している（Look-ahead bias を防ぐため）。
- J-Quants client は rate limit / retry / token refresh / pagination / fetched_at 記録など実運用を意識した実装を持つ。
- DuckDB への保存は基本的に冪等（ON CONFLICT DO UPDATE / DO NOTHING）を採用。
- 一部モジュール（strategy, execution, monitoring）はパッケージに含まれているが、このリリースでは初期化ファイルのみ（空）で配置。今後の実装で発注ロジックやモニタリングを追加予定。

今後の TODO（抜粋）
- execution, strategy, monitoring の詳細実装（発注/ポジション管理、ストラテジー実行エンジン、Slack 等のアラート連携）。
- DuckDB の Processed / Feature レイヤーの DDL 完備とマイグレーション機能。
- 単体テスト・統合テストの追加（特にネットワーク依存部分のモックを整備）。
- パフォーマンス検証（大規模データセットでの DuckDB クエリ最適化、news_collector のチャンクサイズ最適化等）。

--- 

（注）この CHANGELOG は、提供されたコードベースの内容から推測して作成しています。実際のリポジトリ履歴やコミットメッセージが存在する場合は、それに沿って修正・補完してください。