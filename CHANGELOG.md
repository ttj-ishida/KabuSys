KEEP A CHANGELOG
すべての重要な変更を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [0.1.0] - 2026-03-19
初回リリース。本リポジトリに含まれる主要機能を実装しました。

### 追加 (Added)
- パッケージ基盤
  - kabusys パッケージを追加。__version__ = 0.1.0、公開モジュールとして data, strategy, execution, monitoring を定義。
  - strategy/、execution/ フォルダの __init__.py を配置してパッケージ構成を確立（現時点ではプレースホルダ）。

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード停止オプションを提供。
  - .env のパースを堅牢化：
    - export KEY=val 形式対応、シングル/ダブルクォート内のエスケープ処理、インラインコメントの扱い、空行/コメント行スキップ等。
  - Settings クラスを実装し、環境変数から各種設定を取得するプロパティを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH の Path 返却（デフォルトパス設定）
    - KABUSYS_ENV / LOG_LEVEL の妥当性検査（有効値集合を定義）、is_live/is_paper/is_dev ユーティリティ。

- J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API クライアント実装（/token/auth_refresh, /prices/daily_quotes, /fins/statements, /markets/trading_calendar 等）。
  - レート制御: 固定間隔スロットリング _RateLimiter（デフォルト 120 req/min）。
  - リトライ/バックオフ: 最大3回、429/408/5xx を対象に指数バックオフ。429 の場合は Retry-After を優先。
  - 401 時に自動トークンリフレッシュ（1 回のみ）して再試行する仕組みを実装。
  - ページネーション対応の fetch_* 関数（fetch_daily_quotes, fetch_financial_statements）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装し、ON CONFLICT DO UPDATE による冪等性を担保。
  - データ整形ユーティリティ _to_float / _to_int を実装（不正値に対する安全な変換）。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS フィード取得パイプラインを実装（fetch_rss, save_raw_news, save_news_symbols, run_news_collection）。
  - セキュリティ／堅牢性:
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - リダイレクト時や事前にホストがプライベートアドレスでないかをチェックして SSRF を防止（_is_private_host, _SSRFBlockRedirectHandler）。
    - URL スキーム検証（http/https のみ許可）。
    - レスポンスサイズ上限チェック（MAX_RESPONSE_BYTES=10MB）と gzip 解凍時のサイズチェック（Gzip bomb 対策）。
    - トラッキングパラメータ除去・URL 正規化（_normalize_url）、正規化 URL の SHA-256 先頭32文字を記事IDに利用。
  - テキスト前処理（URL 除去、空白正規化）と銘柄コード抽出（4桁数字パターン、known_codes に基づくフィルタ）。
  - DB 保存はチャンク化＆トランザクションで実施。INSERT ... RETURNING を用いて実際に挿入された ID/件数を取得。

- 研究（Research）モジュール (src/kabusys/research/)
  - 特徴量探索 (feature_exploration.py)
    - calc_forward_returns: 指定日から複数ホライズンの将来リターンを一括で取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算（不足レコード時は None）。
    - rank: 同順位は平均ランクにするランク化ユーティリティ（丸めによる ties 検出問題に対処）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ。
  - ファクター計算 (factor_research.py)
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。
    - calc_volatility: atr_20 / atr_pct、avg_turnover、volume_ratio を計算（ATR・出来高窓を考慮）。
    - calc_value: raw_financials と prices_daily を組み合わせて PER (close/eps)・ROE を計算（最新財務レコードを採用）。
  - research パッケージの __init__ で主要関数をエクスポート（zscore_normalize を data.stats から再エクスポート）。

- DuckDB スキーマ (src/kabusys/data/schema.py)
  - Raw レイヤの DDL を定義：raw_prices, raw_financials, raw_news, raw_executions（テーブル定義とチェック制約を含む）。
  - DataSchema.md に基づく多層（Raw / Processed / Feature / Execution）構造を想定した初期スキーマ設計。

### 修正 (Fixed)
- .env パーサーのコメント/クォート処理を強化し、実運用の .env フォーマット差異に耐性を向上。
- DuckDB への保存処理で主キー欠損行をスキップすることで例外/不整合の発生を軽減（save_* のログでスキップ件数を警告）。

### 内部 (Internal)
- ロギング（各モジュールで logger を使用）を一貫して導入し、処理状況や警告を記録。
- 一部処理は標準ライブラリのみで実装（research モジュールは外部依存を避ける設計）。

### セキュリティ (Security)
- RSS パーシングで defusedxml を採用、SSRF 対策、リダイレクト検査、レスポンスサイズ制限、URL スキーム検証を実装。
- J-Quants クライアントは認証トークンの自動リフレッシュ時に無限ループを起こさないよう設計（allow_refresh フラグ等）。

---

注記
- 本チェンジログはソースコードの内容から推測して作成しました。実際のリリースノートや仕様とは差異があり得ます。必要であれば、差異を埋めるための追加情報（実際のリリース日、既知のバグや互換性情報など）を提供してください。