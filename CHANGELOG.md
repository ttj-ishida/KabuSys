CHANGELOG
=========

All notable changes to this project will be documented in this file.
このプロジェクトの重要な変更点はすべて本 CHANGELOG に記載します。

フォーマットは "Keep a Changelog" に準拠します。

0.1.0 - 2026-03-19
------------------

Added
- 初回リリース。パッケージ名: kabusys, バージョン: 0.1.0。
- パッケージ公開インターフェースを定義:
  - src/kabusys/__init__.py による __version__ と主要サブパッケージのエクスポート (data, strategy, execution, monitoring)。
- 環境設定 / 自動 .env ロード:
  - src/kabusys/config.py を追加。プロジェクトルート (.git または pyproject.toml) を起点に .env/.env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可）。
  - .env パースの堅牢化: export 形式対応、クォート内のエスケープ対応、インラインコメント処理の改善。
  - 環境変数取得ヘルパ (Settings) を実装。必須変数チェック、デフォルト値、KABUSYS_ENV / LOG_LEVEL のバリデーション、パス（DUCKDB_PATH / SQLITE_PATH）取得ユーティリティを提供。
- データ取得・格納 (J-Quants):
  - src/kabusys/data/jquants_client.py を実装。J-Quants API から日足・財務・マーケットカレンダーを取得するクライアントを提供。
  - レート制限対応 (固定間隔スロットリング、デフォルト 120 req/min) とリトライ（指数バックオフ、最大3回、408/429/5xx 対象）を実装。
  - 401 Unauthorized 受信時にリフレッシュトークンで ID トークンを自動更新して 1 回リトライする仕組みを実装。
  - ページネーション対応とモジュールレベルの ID トークンキャッシュを追加。
  - DuckDB への保存関数 (save_daily_quotes, save_financial_statements, save_market_calendar) を実装し、ON CONFLICT を用いた冪等保存をサポート。
  - 型変換ユーティリティ (_to_float, _to_int) を追加し、不正値に対して安全に None を返す。
- ニュース収集:
  - src/kabusys/data/news_collector.py を実装。RSS から記事を収集して raw_news / news_symbols に保存する一連のユーティリティを提供。
  - 特徴:
    - URL 正規化とトラッキングパラメータ除去（_normalize_url）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成し冪等性を確保。
    - defusedxml を用いた XML パース（XML Bomb 対策）。
    - SSRF 対策: リクエスト前のホスト検査、リダイレクト時の検証を行うカスタム RedirectHandler を導入し、プライベート/ループバック/リンクローカルアドレスへの到達を拒否。
    - レスポンス最大サイズ制限 (MAX_RESPONSE_BYTES = 10MB) と gzip 解凍後サイズ検査（Gzip bomb 対策）。
    - テキスト前処理（URL 除去・空白正規化）、銘柄コード抽出（4桁数字、known_codes によるフィルタ）を提供。
    - DB 書き込みはチャンク化＋トランザクションで行い、INSERT ... ON CONFLICT DO NOTHING RETURNING を使って実際に挿入された件数を正確に取得。
    - run_news_collection により複数ソースを独立して処理（1 ソース失敗でも続行）可能。
- リサーチ / ファクター計算:
  - src/kabusys/research/factor_research.py を追加。prices_daily / raw_financials を参照して以下のファクターを計算:
    - Momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日移動平均乖離）。
    - Volatility / Liquidity: atr_20, atr_pct, avg_turnover, volume_ratio（ATR は true range を NULL 伝播で正しく扱う）。
    - Value: per, roe（raw_financials と price を組み合わせて最新財務データを取得）。
  - src/kabusys/research/feature_exploration.py を追加。将来リターン計算 calc_forward_returns、IC（スピアマンρ）計算 calc_ic、ランキング関数 rank、統計サマリー factor_summary を実装。rank は丸め (round(v, 12)) により ties 検出の安定化を図る。
  - src/kabusys/research/__init__.py で公開 API をまとめてエクスポート。
- DuckDB スキーマ初期化:
  - src/kabusys/data/schema.py に Raw 層の DDL を定義 (raw_prices, raw_financials, raw_news, raw_executions 等のテーブル定義を含む)。プロジェクトの DataSchema に基づく初期化用モジュール。

Changed
- 初期設計として、すべてのデータ取得／計算関数は本番発注 API にアクセスしない方針を明確化（研究 / バックテスト用途の分離）。
- DuckDB への書き込みは可能な限り冪等（ON CONFLICT）を採用し再取得時の整合性を向上。
- .env の上書きルール:
  - OS 環境変数を protected として .env/.env.local 読み込み時の上書きを防止（.env.local は override=True だが protected によって OS 環境を保持）。

Fixed
- .env のパースでのコメント・クォート処理を改善し、引用符内の = やエスケープを正しく扱うように修正。
- ニュース収集における URL / リダイレクトの検査を強化し、SSRF 脆弱性の発生を抑制。
- J-Quants クライアントの HTTP エラー処理を改善し、429 の Retry-After ヘッダを優先して待機するようにした。

Security
- defusedxml を利用した XML パースにより XML 関連の攻撃（XML bomb 等）を緩和。
- RSS フェッチに対する SSRF 対策:
  - リクエスト前のホストがプライベートアドレスかを検査しブロック。
  - リダイレクト先も事前検証してプライベートリダイレクトを拒否。
- 外部から取り込むコンテンツサイズに上限（10MB）を設け、メモリ DoS / Gzip bomb を防止。

Performance
- calc_forward_returns は複数ホライズンをまとめて単一クエリで取得することで DB スキャン回数を削減。
- ニュースの DB 書き込みはチャンク（デフォルト 1000 件）でバルク INSERT を行いオーバーヘッドを削減。
- J-Quants API のレートリミッタは固定間隔スロットリングを用い、API レートに合わせた安定した呼び出しを保証。

Notes / Migration
- 自動 .env ロード動作:
  - デフォルトでプロジェクトルートの .env（次に .env.local）を読み込みます。テスト等で自動ロードを無効化する場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings 経由で必須チェックが入り、未設定時は ValueError を送出します。
- KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれかのみ許容。
- LOG_LEVEL は "DEBUG"/"INFO"/"WARNING"/"ERROR"/"CRITICAL" のみ許容。

Acknowledgements / Future
- 初版では Strategy / Execution / Monitoring の実装はパッケージ構成上用意されていますが、具体的な発注ロジックや監視機能は今後のリリースで拡張予定です。
- DataLayer（DuckDB）や Research の関数群は今後ユニットテスト・統合テストを追加して品質を強化予定です。

-----