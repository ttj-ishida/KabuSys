CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。
このファイルは「Keep a Changelog」形式に従います。

フォーマット:
- 変更はセマンティックバージョニング（MAJOR.MINOR.PATCH）に従います。
- できるだけ各エントリに短い説明と理由を付記します。

Unreleased
----------

（現在の時点で未リリースの変更はありません）

[0.1.0] - 2026-03-18
--------------------

初回公開リリース。KabuSys のコア機能とデータ取得・前処理・リサーチ用ユーティリティを実装しました。

Added
- パッケージ基盤
  - パッケージ version を src/kabusys/__init__.py にて設定（__version__ = "0.1.0"）。
  - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を自動読み込み（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理等）。
  - Settings クラスを提供し、以下の必須/任意設定を取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（任意、デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（任意、デフォルトパスを提供）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（値検証）

- J-Quants API クライアント（src/kabusys/data/jquants_client.py）
  - 日足、財務データ、マーケットカレンダー取得用 API クライアント実装。
  - 固定間隔スロットリング（120 req/min）によるレート制限制御（内部 RateLimiter）。
  - リトライロジック（指数バックオフ、最大 3 回）を実装。408/429/5xx を再試行対象に。
  - 401 応答時にリフレッシュトークンで自動的にトークン更新して 1 回だけリトライする仕組み。
  - ページネーション対応（pagination_key を用いた全ページ取得）。
  - データ保存ユーティリティ:
    - save_daily_quotes/save_financial_statements/save_market_calendar：DuckDB へ冪等に保存（ON CONFLICT DO UPDATE）。
    - fetched_at を UTC で記録し、Look-ahead bias のトレースを可能に。
  - 型変換ヘルパー（_to_float / _to_int）で入力不正値や空文字を適切に None 処理。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィード取得と raw_news/raw_symbols への保存処理を実装。
  - セキュリティ・堅牢化:
    - defusedxml を使用して XML 攻撃を緩和。
    - SSRF 対策としてリダイレクト時のスキーム/ホスト検査、プライベートアドレス検出を導入（カスタム RedirectHandler）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限（MAX_RESPONSE_BYTES=10MB）を導入し大容量レスポンスを防御。
    - gzip 解凍後もサイズ検査を実施（Gzip bomb 対策）。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）を使って冪等性を保証。正規化時に utm_* 等のトラッキングパラメータを除去。
  - テキスト前処理（URL 除去・空白正規化）ユーティリティを提供。
  - raw_news へのチャンク化・トランザクション付き INSERT（ON CONFLICT DO NOTHING + RETURNING）で新規挿入 ID を正確に取得。
  - news_symbols のバルク保存（重複除去・チャンク INSERT・トランザクション）を実装。
  - 銘柄抽出ロジック（4桁数字パターン）を実装し、known_codes でフィルタリング。

- DuckDB スキーマ初期化（src/kabusys/data/schema.py）
  - Raw Layer のテーブル定義を実装（raw_prices, raw_financials, raw_news, raw_executions 等の DDL）。
  - DataLayer / FeatureLayer / ExecutionLayer のスキーマ設計方針に基づく定義（Raw Layer が実装済み、他レイヤーの拡張を想定）。

- リサーチ / ファクター計算（src/kabusys/research/）
  - feature_exploration.py:
    - calc_forward_returns：指定日に対する複数ホライズン（デフォルト 1,5,21）の将来リターンを DuckDB の prices_daily から取得して計算。
    - calc_ic：Spearman のランク相関（Information Coefficient）を実装（欠損値フィルタ・最小サンプル数チェック）。
    - factor_summary：各ファクターの基本統計量（count/mean/std/min/max/median）を計算。
    - rank：同順位は平均ランクを返すランク関数（浮動小数丸めで ties 検出）。
  - factor_research.py:
    - calc_momentum：mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility：20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算（true range の NULL 伝播を制御）。
    - calc_value：raw_financials から最新の財務を結合して PER/ROE を計算。
  - research パッケージ __init__ で主要ユーティリティをエクスポート（calc_momentum/volatility/value, calc_forward_returns, calc_ic, factor_summary, rank, zscore_normalize など）。

- モジュール構造
  - strategy と execution のパッケージ初期化ファイルを配置（将来の戦略・発注ロジック用のプレースホルダ）。

Security
- ニュース取得に関する SSRF 対策と XML パース安全化（defusedxml）を追加。
- RSS のレスポンス最大サイズを制限し DoS リスクを軽減。
- URL 正規化でトラッキングパラメータを削除し ID 生成を安定化。

Performance / Reliability
- J-Quants API 呼び出しに対してレート制限・リトライ・トークン自動リフレッシュを実装し信頼性を向上。
- DuckDB への保存処理は冪等設計（ON CONFLICT）とチャンク化/トランザクションにより効率化。
- RSS 保存はチャンク INSERT と INSERT … RETURNING を使用して実際に挿入された ID を正確に把握。

Changed / Improved
- .env のパースは export プレフィックス、クォート内のエスケープ、インラインコメント処理など現実的なケースに対応するよう強化。
- _to_int/_to_float の変換挙動を明確化し、不正フォーマットは None を返す（意図しない切り捨て防止）。
- DuckDB 向けクエリは集約ウィンドウ関数を多用して一回のクエリで必要値を取得することにより I/O を削減。

Fixed
- データ不足や同値列（ties）等の境界条件を安全に扱うためのガード処理を追加（例: IC 計算での最小レコードチェック、ma200 のカウントチェック、ATR の true_range NULL 伝播制御）。

Known limitations / TODO
- PBR・配当利回りなど一部バリューファクターは未実装（calc_value に注記あり）。
- Execution / Strategy 本体ロジックはまだ未実装（パッケージプレースホルダのみ）。
- Research は標準ライブラリのみで実装しており、大規模データ処理における最適化（pandas 等）は将来検討予定。

注記
- 初回リリースでは API トークン等の必須環境変数が存在しないと例外を投げます。開発時は .env をプロジェクトルートに配置してください（.env.example を参照することを想定）。
- DuckDB/SQLite のデフォルトパスは data/ 以下に設定されています。運用環境では適切に上書きしてください（環境変数 DUCKDB_PATH / SQLITE_PATH）。

-- END --