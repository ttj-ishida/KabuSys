# Changelog

すべての重要な変更点は Keep a Changelog の方針に従って記載しています。主にコードベースから推測できる機能追加・設計方針・既知の制限をまとめています。

フォーマット:
- 非互換な変更は Breaking Changes として明記します。
- 日付はリリース日を示します（推測または現時点の日付を使用）。

Unreleased
- (現時点で未リリースの変更はありません)

[0.1.0] - 2026-03-20
Added
- パッケージ初期リリースを追加（kabusys v0.1.0）。
  - パッケージ構成:
    - kabusys.config: .env / 環境変数読み込み・管理（自動読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）
      - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env
      - 高度な .env パーサ（export プレフィックス対応、クォートとエスケープ処理、インラインコメント処理）
      - Settings クラスで必須変数取得用の _require、env / log_level の検証（development / paper_trading / live、LOG_LEVEL の許容値検証）
      - 主要環境変数（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH）にアクセスするプロパティを提供
    - kabusys.data:
      - jquants_client:
        - J-Quants API クライアント（/token/auth_refresh、/prices/daily_quotes、/fins/statements、/markets/trading_calendar 等）
        - ページネーション対応、モジュールレベルの id_token キャッシュ共有
        - レート制限制御（固定間隔スロットリング、120 req/min を想定）
        - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx に対するリトライ）
        - 401 時にリフレッシュトークンで id_token を自動更新して再試行
        - DuckDB への保存ユーティリティ（save_daily_quotes, save_financial_statements, save_market_calendar）を実装（ON CONFLICT DO UPDATE で冪等化）
        - 型変換ユーティリティ (_to_float / _to_int)
      - news_collector:
        - RSS フィードからのニュース収集基盤
        - URL 正規化とトラッキングパラメータ除去（utm_*, fbclid 等）
        - defusedxml による XML パースで XML 攻撃を緩和
        - 受信サイズ制限（MAX_RESPONSE_BYTES = 10MB）、SSRF 緩和のためのスキームチェック等（コードに記載の設計方針に基づく）
        - raw_news への冪等保存（バルク挿入、チャンク処理）
    - kabusys.research:
      - factor_research:
        - モメンタム、ボラティリティ、バリューなどのファクター計算関数を実装（calc_momentum, calc_volatility, calc_value）
        - DuckDB prices_daily / raw_financials テーブルのみを参照する設計
        - 各ファクターは (date, code) ベースの dict リストを返す
      - feature_exploration:
        - 将来リターン計算（calc_forward_returns、複数ホライズン対応）
        - IC（Information Coefficient）計算（スピアマンの ρ をランクで計算する calc_ic）
        - ファクター統計サマリー（factor_summary）とランク付けユーティリティ（rank）
      - research パッケージで zscore_normalize を再公開
    - kabusys.strategy:
      - feature_engineering.build_features:
        - research の生ファクターを取り込み、ユニバースフィルタ（最低株価・最低平均売買代金）を適用
        - 指定カラムを Z スコア正規化し ±3 でクリップ
        - features テーブルへ日付単位の置換（DELETE→INSERT をトランザクションで実行し原子性を担保）
        - ユニバース条件: 株価 >= 300 円、20日平均売買代金 >= 5 億円
      - signal_generator.generate_signals:
        - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
        - 最終スコア final_score を重み付け合算（デフォルト重みあり）し BUY/SELL シグナルを生成
        - Bear レジーム判定（ai_scores の regime_score の平均が負の場合、ただしサンプル数閾値あり）
        - BUY シグナルは threshold（デフォルト 0.60）を超える銘柄を採用（Bear 時は BUY 抑制）
        - SELL シグナルはストップロス（-8%）とスコア低下で判定
        - signals テーブルへ日付単位の置換（トランザクション + バルク挿入）
        - 重みの入力検証と再スケーリング（未知キーや不正値は無視）
        - features が空の場合は BUY を生成せず SELL 判定のみ実行
    - その他:
      - パッケージエントリポイントに __version__ = "0.1.0" を追加

Changed
- N/A（初回リリースのため過去からの変更はなし）

Fixed
- N/A（初回リリースのため過去の不具合修正履歴はなし）

Security
- news_collector で defusedxml を利用して XML ベースの攻撃を緩和
- RSS / HTTP レスポンスの最大受信サイズを設定してメモリ DoS を軽減
- jquants_client でトークンリフレッシュを安全に行う（allow_refresh フラグで無限再帰を防止）
- .env パーサで export プレフィックス・エスケープ・クォート処理を行い、不正な値解釈を低減

Known limitations / TODO
- signal_generator の一部エグジット条件（トレーリングストップや時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）
- news_collector の実装では SSRF や外部接続の厳密なホワイトリストチェックなど追加の堅牢化が想定されているが、実装詳細は今後拡充可能
- jquants_client のレート制御は固定間隔スロットリング（_RateLimiter）で簡易実装。より高精度なトークンバケット等に改善可能
- DuckDB スキーマ前提（raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news など）が存在する想定。スキーマ作成処理は含まれていないため、導入時に事前準備が必要

Notes for operators / integrators
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- ローカルでのテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定すると自動 .env 読み込みを無効化できます。
- DuckDB/SQLite のパスは DUCKDB_PATH / SQLITE_PATH で制御可能（デフォルト: data/kabusys.duckdb, data/monitoring.db）
- settings.env, settings.log_level により動作モードとログレベルの検証を行うため、不正な値を渡すと起動時に例外が発生します。

クレジット
- 本リリースはコードベース（src/kabusys 以下）から推測して作成された CHANGELOG です。実際のコミット履歴・リリースノートと差異がある可能性があります。必要に応じて実際のコミットや issue を反映して更新してください。