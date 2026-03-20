CHANGELOG
=========

すべての注目すべき変更はこのファイルに記載します。
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現在の作業中の変更はここに記載します）

0.1.0 - 2026-03-20
------------------

最初の公開リリース。以下の主要機能を含みます。

Added
- パッケージ基礎
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を設定。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に追加。

- 環境設定・読み込み（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行う（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
  - .env パーサーの強化:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理、クォートなしコメントの扱いを実装。
  - Settings クラスを提供:
    - 必須環境変数の取得（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID）。
    - DB パスのデフォルト（DUCKDB_PATH, SQLITE_PATH）や KABU_API_BASE_URL のデフォルトを提供。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の値検証。
    - is_live / is_paper / is_dev の便利プロパティ。

- データ取得・保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - 固定間隔レート制限（120 req/min）を実装する RateLimiter を導入。
    - リトライ戦略（指数バックオフ、最大 3 回、408/429/5xx でリトライ）。429 時は Retry-After を優先。
    - 401 受信時はリフレッシュトークンによる id_token 自動更新（1 回のみ）して再試行。
    - ページネーション対応の fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar を提供。
  - DuckDB への保存関数（冪等）を提供:
    - save_daily_quotes, save_financial_statements, save_market_calendar は ON CONFLICT DO UPDATE/DO NOTHING を用いて重複を排除。
    - 日時は UTC（ISO）で fetched_at を記録して Look-ahead バイアスをトレース可能に。
    - データ変換ユーティリティ _to_float / _to_int を実装（安全な変換と不正値除外）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集機能を実装（デフォルトに Yahoo Finance のビジネス RSS を含む）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、小文字化など）。
  - 記事 ID は正規化 URL の SHA-256（先頭32文字）を用い冪等性を確保。
  - defusedxml を使った XML パース（XML Bomb 等に対する防御）。
  - SSRF 対策、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）、バルク INSERT のチャンク化、トランザクション集約。
  - raw_news / news_symbols 等への保存を想定した実装方針。

- 研究用ファクター計算・探索（kabusys.research）
  - ファクター計算モジュール（kabusys.research.factor_research）:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日MA乖離）を計算。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio を計算（ATR は true_range を正しく扱う）。
    - calc_value: 最新財務データを用いて per / roe を計算（raw_financials と prices_daily を参照）。
    - 各関数は DuckDB の prices_daily / raw_financials テーブルのみを参照し、本番APIにはアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で計算。
    - calc_ic: factor と forward の Spearman ランク相関（IC）を計算（サンプル数 3 未満で None）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank ユーティリティ（同順位は平均ランク）。
  - 研究ユーティリティのエクスポート（zscore_normalize は kabusys.data.stats から）。

- 戦略レイヤ（kabusys.strategy）
  - 特徴量エンジニアリング（kabusys.strategy.feature_engineering）:
    - build_features: research で計算した生ファクターをマージし、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ、features テーブルへ日付単位で置換（トランザクションで原子性保証）。
    - ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）。
  - シグナル生成（kabusys.strategy.signal_generator）:
    - generate_signals: features と ai_scores を統合し、コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算して final_score を算出。
    - デフォルト重みを実装（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。外部から weights 指定可（バリデーションと正規化あり）。
    - Sigmoid 変換・欠損の中立補完（0.5）・Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつ十分なサンプル数）を実装。Bear の際は BUY シグナルを抑制。
    - BUY 閾値のデフォルトは 0.60。SELL のエグジット判定にストップロス（-8%）とスコア低下を実装。
    - signals テーブルへ日付単位で置換（トランザクション原子性）。

- ロギング・エラーハンドリング
  - 各所に logger を導入し、重要な警告や操作をログ出力。
  - DB トランザクションで例外時に ROLLBACK を試み、失敗時は警告出力。

Changed
- 初版のため "Changed" に該当する過去の変更はありません。

Fixed
- 初版のため既知のバグフィックス履歴はありません。

Removed
- 初版のため削除項目はありません。

Security
- news_collector は defusedxml を使用して XML 関連の脆弱性に対応。
- news_collector は受信サイズ上限と URL/スキーム検証（HTTP/HTTPS）によりメモリ DoS や SSRF を軽減する設計。
- J-Quants クライアントは認証トークンの自動リフレッシュを実装し、認証エラー時の安全な再取得を行う（無限再帰に注意した設計）。

Known Issues / Limitations
- signal_generator の SELL 条件について未実装の仕様がある:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに追加情報（peak_price / entry_date）が入手でき次第の実装を想定。
- news_collector の記事→銘柄紐付け（news_symbols）などの具体的なマッピングロジックの詳細は最小限の方針のみ記載されている。
- 一部ユーティリティ（例: kabusys.data.stats.zscore_normalize）の実装は本 CHANGELOG に含まれるソース一覧の外にあるが、research パッケージから利用されることを想定している。
- DuckDB のスキーマ（テーブル定義）はこのリリースノートには含まれないため、実行には所定のスキーマ準備が必要。

Migration Notes
- 初版リリースのため過去バージョンからの移行は存在しません。
- 今後のリリースで DB スキーマ変更が発生した場合はマイグレーション手順を別途提供予定。

Contributing
- バグ報告、機能提案、プルリクエストは歓迎します。テストや CI の整備が整い次第 CONTRIBUTING.md を整備予定です。

License
- 本リリースのライセンス情報はリポジトリの LICENSE ファイルを参照してください。