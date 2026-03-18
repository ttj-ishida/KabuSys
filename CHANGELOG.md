# CHANGELOG

すべての重要な変更をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

なお、本 CHANGELOG は提示されたコードベースの内容から推測して作成しています（実装上の意図や設計方針も併記）。

## [Unreleased]

- なし

## [0.1.0] - 2026-03-18

初回リリース。日本株自動売買システム「KabuSys」の基本機能群を実装。

### 追加 (Added)

- パッケージ基盤
  - パッケージ定義とバージョン: kabusys v0.1.0 を追加（src/kabusys/__init__.py）。
  - モジュール公開: data, strategy, execution, monitoring をパッケージ外部に公開。

- 設定管理
  - 環境変数 / .env 自動読み込み機能を実装（src/kabusys/config.py）。
    - プロジェクトルート判定は .git または pyproject.toml を基準に実施。CWD に依存しない検索。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
    - .env 解析は export プレフィックス、クォート、インラインコメント等に対応。
  - Settings クラスを提供し、主要な必須設定をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルト値あり）
    - KABUSYS_ENV（development/paper_trading/live のバリデーション）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のバリデーション）
    - is_live / is_paper / is_dev のヘルパープロパティ

- データ層（DuckDB）
  - スキーマ定義モジュールを追加（src/kabusys/data/schema.py）。
    - raw_prices, raw_financials, raw_news, raw_executions（等）の DDL を定義。
    - DataLayer / Raw/Processed/Feature/Execution の3層構成に基づく設計（ドキュメントに準拠）。

- J-Quants クライアント
  - J-Quants API クライアントを実装（src/kabusys/data/jquants_client.py）。
    - rate limiting（120 req/min）を固定間隔スロットリングで実装（RateLimiter）。
    - 自動リトライ（最大 3 回、指数バックオフ）と 408/429/5xx に対する再試行。
    - 401 受信時はリフレッシュトークンで ID トークンを自動更新して 1 回だけリトライ。
    - ページネーション対応の fetch_* 関数:
      - fetch_daily_quotes（株価日足）
      - fetch_financial_statements（財務データ）
      - fetch_market_calendar（取引カレンダー）
    - DuckDB への冪等保存（ON CONFLICT DO UPDATE）関数を実装:
      - save_daily_quotes, save_financial_statements, save_market_calendar
    - データ取得時に fetched_at を UTC ISO8601 で記録（Look-ahead Bias 対策）
    - HTTP ユーティリティは urllib を利用（JSON デコードエラー検知）

- ニュース収集（RSS）
  - RSS ニュース収集モジュールを実装（src/kabusys/data/news_collector.py）。
    - RSS フィード取得（fetch_rss）、前処理、記事ID生成、抽出、DB 保存までを提供。
    - 記事ID は URL 正規化（トラッキングパラメータ除去）後の SHA-256（先頭32文字）で生成して冪等性を保証。
    - XML パースに defusedxml を使用し XML-bomb 脅威を軽減。
    - SSRF 対策:
      - URL スキームは http/https のみ許可。
      - 初回ホスト検査とリダイレクト時のホスト検査を実装（プライベート/ループバックなどを拒否）。
      - 専用のリダイレクトハンドラでリダイレクト先の検証を実施。
    - レスポンスサイズ制限（MAX_RESPONSE_BYTES = 10MB）と gzip 解凍後のサイズ再チェック（Gzip-bomb 対策）。
    - content:encoded 優先、description フォールバックの実装。
    - raw_news テーブルへの冪等保存（INSERT ... ON CONFLICT DO NOTHING + RETURNING）をチャンク単位で実行（トランザクション管理）。
    - news_symbols（記事と銘柄の紐付け）を一括登録する内部ユーティリティを提供。
    - 銘柄コード抽出ユーティリティ（4桁数字、known_codes によるフィルタ）を実装。

- リサーチ（特徴量・ファクター）
  - feature_exploration モジュール（src/kabusys/research/feature_exploration.py）を追加:
    - calc_forward_returns（将来リターン計算）: DuckDB の prices_daily を参照し、複数ホライズンを一度のクエリで取得。
    - calc_ic（Spearman の ρ ＝ ランク相関）: ties の平均ランク処理と丸めによる ties 検出安定化。
    - rank（同順位は平均ランク）および factor_summary（count/mean/std/min/max/median）を提供。
    - 外部ライブラリに依存せず標準ライブラリのみで実装（研究環境向け）。
  - factor_research モジュール（src/kabusys/research/factor_research.py）を追加:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離率）
    - calc_volatility（20日 ATR、相対ATR、20日平均売買代金、出来高比率）
    - calc_value（PER、ROE を原データに基づき計算）
    - 各関数は prices_daily / raw_financials のみを参照。本番 API へアクセスしない。
    - データ不足時は None を返す（ウィンドウサイズ未満など）。
  - research パッケージの __init__ に主要関数をエクスポート（zscore_normalize を kabusys.data.stats から参照）。

### 修正 (Fixed)

- データ保存の堅牢性向上
  - raw データ保存時に PK 欠損行をスキップして警告を出力（save_* 関数群）。
  - save_raw_news / save_news_symbols はトランザクション内でチャンク処理・エラー時ロールバックを行う。

- 型変換の堅牢化
  - _to_float / _to_int ユーティリティで不正値を None に変換し、意図しない切捨てを防止（例: "1.9" は int 変換で None を返す）。

### セキュリティ (Security)

- RSS/HTTP 関連の強化
  - defusedxml による XML パースで XML bomb を防止。
  - SSRF 対策（スキーム検証、IP/ホストのプライベート判定、リダイレクト検査）。
  - レスポンスのサイズ制限と gzip 解凍後チェック（DoS 対策）。
  - 許可されない URL スキームをログ・スキップ。

- API クライアントの耐障害性
  - レート制限とリトライ、トークン自動更新を実装して誤った再試行や無限リトライを防止。

### 変更 (Changed)

- 設計方針として、research モジュールは外部 API にアクセスしない、DuckDB のテーブルのみを参照する方針を明記。
- .env ライブラリ相当の軽量実装を採用し、自動ロードの挙動をプロジェクトルート探索に依存させた（配布後の安定動作を考慮）。

### 既知の注意点 / TODO

- strategy と execution パッケージは __init__ のみ（プレースホルダ）となっており、戦略の学習・発注ロジックは未実装／未公開。
- research/__init__.py は kabusys.data.stats.zscore_normalize を参照しているが、当該ファイルはこのスナップショットに含まれていません。実稼働では kabusys.data.stats モジュールの提供が必要です。
- DuckDB のスキーマ定義は一部ファイルの途中で切れている（raw_executions の DDL が途中）。実際の DDL 全体は DataSchema.md に沿って完成させる必要あり。
- J-Quants API のベース URL/_BASE_URL や実際の API 仕様依存の挙動は将来的な変更で影響を受ける可能性あり。

---

この CHANGELOG はコードベースから推測して作成しました。実際のリリースノートではコミット履歴やタスク管理の内容に基づき調整してください。