Keep a Changelog
すべての注目すべき変更をバージョンごとに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。

[Unreleased]

[0.1.0] - 2026-03-21
--------------------

Added
- 初回リリース: kabusys パッケージ v0.1.0
  - パッケージエントリポイントとバージョン情報を追加（src/kabusys/__init__.py）。
- 環境設定 / ロード機能（src/kabusys/config.py）
  - .env ファイル自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - .env/.env.local の優先順位と OS 環境変数保護（protected set）に基づく上書き制御を実装。
  - .env 行パーサを実装:
    - export プレフィックス対応、クォート（シングル/ダブル）内のバックスラッシュエスケープ処理、インラインコメント処理の挙動を考慮。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを追加し、J-Quants / kabu API / Slack / DB パス / システム設定（KABUSYS_ENV, LOG_LEVEL）等のプロパティを提供。値検証（許容値チェック）を実施。
- J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - API 呼び出しのための汎用 HTTP ラッパーを実装（_request）。
  - レート制限（120 req/min）用の固定間隔スロットリング RateLimiter を追加。
  - 再試行（指数バックオフ、最大 3 回）・Retry-After 処理・HTTP 401 時の自動トークンリフレッシュ（1 回）を実装。
  - id_token キャッシュと get_id_token 実装（settings からリフレッシュトークン取得）。
  - ページネーション対応のデータ取得関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar（pagination_key を使用）。
  - DuckDB への冪等保存関数を実装:
    - save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT DO UPDATE を利用）。
  - データ型変換ユーティリティ _to_float / _to_int を追加（不正値を None にする安全変換）。
- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事収集する基礎機能を実装（デフォルトソースに Yahoo Finance）。
  - defusedxml を用いた安全な XML パース、受信サイズ上限（10 MB）、トラッキングパラメータ除去による URL 正規化、SHA-256 による記事 ID の生成など冪等性を考慮した設計。
  - バルク INSERT のチャンク化、SQL トランザクションでの保存を想定。
- 研究用ファクター計算（src/kabusys/research/*）
  - factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装（prices_daily / raw_financials を参照）。
    - 移動平均、ATR、出来高比、PER/ROE 等を計算。
  - feature_exploration.py:
    - calc_forward_returns（複数ホライズン対応）
    - calc_ic（スピアマンのランク相関）
    - factor_summary（基本統計量）、rank（同順位を平均ランクにするランク関数）
  - research パッケージの __init__ で主要関数をエクスポート。
- 戦略（src/kabusys/strategy/*）
  - feature_engineering.build_features:
    - research モジュールの生ファクターを取得、ユニバースフィルタ（最低株価・平均売買代金）、Z スコア正規化（外部 zscore_normalize を利用）、±3 でクリップ、features テーブルへ日付単位で置換（トランザクションによる原子性）を実装。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算、重み付けで final_score を算出。
    - weights の入力検証・補完・再スケール機構を実装。
    - Bear レジーム判定（AI の regime_score 平均 < 0 かつサンプル数閾値）を実装し、Bear 時は BUY を抑制。
    - BUY（閾値超）/SELL（ストップロス・スコア低下）シグナルを生成し、signals テーブルへ日付単位で置換。
    - 保有ポジションに関するエグジット判定（stop_loss, score_drop）を実装（positions / prices_daily を参照）。
- その他
  - strategy/__init__.py で主要 API を再エクスポート（build_features, generate_signals）。
  - 各所にログ出力を追加し運用時の可観測性を向上。

Changed
- 初回リリースのため該当なし。

Fixed
- API レスポンスの JSON デコード失敗時の明確なエラーメッセージを追加（_request）。
- DuckDB への保存で主キー欠損行をスキップしログ警告を出すことで不正データによる例外を回避。

Security
- XML のパースに defusedxml を使用して XML 関連の攻撃（XML Bomb 等）対策を実施（news_collector）。
- RSS の URL 正規化でトラッキングパラメータを除去し、ID 生起を安定化。
- HTTP リクエストのタイムアウトと受信サイズ上限を設定してリソース枯渇攻撃を緩和。
- .env 自動読み込み時に OS 環境変数を保護する設計（protected set）。

Performance
- DuckDB クエリにおいてスキャン範囲をバッファ付きで限定（パフォーマンス配慮）。
- save_* 系で executemany を使用したバルク挿入、トランザクションをまとめることでオーバーヘッドを削減。
- API 呼び出しで固定間隔のスロットリングによりサービス側レート制限に適合。

Known issues / Limitations
- execution パッケージは空で、発注の実装（kabu-station との実際の発注インターフェイス）は本リリースに含まれていません。
- signal_generator 内の一部エグジット条件（トレーリングストップ、保有期間による時間決済）は positions テーブルに peak_price / entry_date 等の追加が必要であり未実装。該当箇所にコメントで明示。
- news_collector の一部ユーティリティ（例: URL/SSRF 検査や外部ネットワークリクエストの細部制御）は実装済だが、利用環境に応じた追加の検証・ハードニングが必要。
- research モジュールは外部ライブラリ（pandas 等）に依存せず実装しているため、大規模データに対するメモリ/パフォーマンス検証が今後必要。

Migration / Usage notes
- 環境変数名:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（任意）, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか。有効値でない場合は起動時に ValueError を投げます。
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テストで便利）。
- デフォルトの DuckDB パスは data/kabusys.duckdb、SQLite の監視 DB は data/monitoring.db。

Contributors
- 初期実装（コア機能群とドキュメント化）を実装。

ライセンス
- 本リリースではライセンス情報はソースに含まれていません。配布時は適切なライセンスを付与してください。

（注）本 CHANGELOG は、提供されたソースコード内容から推測してまとめたものであり、実運用環境での追加要件や変更は別途記録してください。