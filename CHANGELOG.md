Keep a Changelog に準拠した CHANGELOG.md（日本語）
すべての注目すべき変更をこのファイルに記録します。
このプロジェクトはセマンティック バージョニングに従います。

[Unreleased]
- （現時点では未リリースの変更はありません）

[0.1.0] - 2026-03-18
Added
- 初回リリース。パッケージメタ情報:
  - パッケージバージョンを kabusys.__version__ = "0.1.0" として追加。
- 環境設定管理:
  - .env ファイルと OS 環境変数から設定を安全に読み込む仕組みを実装（src/kabusys/config.py）。
  - プロジェクトルートの自動検出（.git または pyproject.toml を基準）によりカレントディレクトリに依存しない自動ロードを実現。
  - .env, .env.local の優先順位制御、既存 OS 環境変数を保護する protected 機構、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
  - .env パーサで export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、インラインコメント等に対応。
  - Settings クラスにより必須環境変数の取得と値検証（KABUSYS_ENV と LOG_LEVEL のバリデーション、パスの Path 正規化など）を提供。
- Data 層（DuckDB）関連:
  - DuckDB 用スキーマ定義（Raw Layer のテーブル DDL の一部を実装）（src/kabusys/data/schema.py）。
  - raw_prices / raw_financials / raw_news 等の基本テーブル定義（Raw Layer）の追加（初期DDL実装）。
- J-Quants API クライアント:
  - J-Quants API からのデータ取得と DuckDB への保存を行うクライアントを実装（src/kabusys/data/jquants_client.py）。
  - レート制限遵守のための固定間隔スロットリング RateLimiter（120 req/min）を実装。
  - リトライロジック（指数バックオフ、最大3回；408, 429, 5xx 対応）を導入。
  - 401 受信時の自動トークンリフレッシュ（1 回のみ）とモジュールレベルの ID トークンキャッシュ実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes、fetch_financial_statements、fetch_market_calendar）を実装。
  - DuckDB に対する冪等保存関数（save_daily_quotes、save_financial_statements、save_market_calendar）を実装（ON CONFLICT DO UPDATE による重複排除）。
  - データ変換ユーティリティ（_to_float、_to_int）を実装し、不正値・空値を安全に扱う。
- ニュース収集（RSS）機能:
  - RSS から記事を取得して前処理し、raw_news / news_symbols に保存するニュースコレクタを実装（src/kabusys/data/news_collector.py）。
  - URL 正規化（トラッキングパラメータ除去、ソート、フラグメント削除）、正規化 URL からの記事ID（SHA-256 の先頭32文字）生成を実装。
  - defusedxml を利用した安全な XML パース（XML Bomb 等への耐性）、受信サイズ上限（10 MB）によるメモリ DoS 対策を導入。
  - SSRF 対策: リダイレクト時のスキーム検証・プライベートアドレス検査、初回ホスト検査、カスタムリダイレクトハンドラ実装。
  - gzip 圧縮対応／解凍時のサイズチェック（Gzip bomb 対策）、Content-Length による事前検査。
  - テキスト前処理（URL 除去・空白正規化）と記事保存の冪等性（INSERT ... ON CONFLICT DO NOTHING、INSERT ... RETURNING）を実装。チャンク挿入でパラメータ数・SQL 長の制御を行う。
  - 記事本文から4桁銘柄コード抽出用ユーティリティ（正規表現ベース）と、既知銘柄セットに基づく紐付けロジック（run_news_collection）を実装。
- Research（因子・特徴量）:
  - 特徴量探索モジュール（src/kabusys/research/feature_exploration.py）:
    - 将来リターン calc_forward_returns（複数ホライズン、営業日ベース、SQL 1 クエリ取得）。
    - スピアマンランク相関による IC 計算 calc_ic（欠損排除、最小サンプル数判定）。
    - 基本統計 summary（factor_summary）とランク変換ユーティリティ（rank）。
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）:
    - モメンタム calc_momentum（1M/3M/6M、MA200 乖離率）。
    - ボラティリティ・流動性 calc_volatility（20日 ATR、相対ATR、20日平均売買代金、出来高比）。
    - バリュー calc_value（raw_financials から最新財務を取得し PER/ROE を算出）。
  - research パッケージの __init__ で主要関数を公開（zscore_normalize は kabusys.data.stats からの外部ユーティリティとして参照）。
- パッケージ構成:
  - kabusys パッケージの __all__ に data, strategy, execution, monitoring を設定（将来のモジュール構成を明示）。
- ロギング:
  - 各モジュールにて適切な logger を取得し、情報・警告・例外時ログを追加。

Security
- ニュース収集で SSRF 対策、XML パース防御、受信サイズ制限など複数の安全対策を導入。
- J-Quants クライアントでのトークンリフレッシュ処理とリトライ/バックオフにより、誤った認証状態や過負荷への耐性を向上。

Known issues / Notes
- strategy/execution/monitoring パッケージは初期化ファイルのみで、実際の発注ロジックやモニタリング機能は未実装（プレースホルダ）。
- data.stats.zscore_normalize は参照されているが、本差分では実装ファイルの内容は含まれていないため、別途実装または提供が必要。
- DuckDB スキーマは Raw Layer の主要テーブル定義を含むが、Processed/Feature/Execution レイヤーの完全な DDL は追加実装が必要。
- 外部依存: duckdb、defusedxml を利用（実行環境にこれらのライブラリが必要）。

Future
- Execution 層（発注・約定・ポジション管理）の実装予定。
- Strategy 層で研究結果を用いたシグナル生成・バックテスト機能の追加予定。
- monitoring（Slack 通知等）や、より豊富なデータ前処理・特徴量群の拡充。

----- 
注: この CHANGELOG は、提示されたソースコードの内容から推測して作成しています。実際のコミット履歴や開発計画に基づく変更がある場合は適宜調整してください。