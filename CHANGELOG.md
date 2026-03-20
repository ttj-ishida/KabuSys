CHANGELOG
=========

すべての注目すべき変更点をこのファイルに記録します。
このプロジェクトは Keep a Changelog の慣例に従い、セマンティックバージョニングを採用します。

最新更新日: 2026-03-20

Unreleased
----------

（現在未リリースの変更はここに記載します）

0.1.0 - 2026-03-20
-----------------

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。

Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。バージョン番号は 0.1.0。
  - パッケージエクスポート: data, strategy, execution, monitoring を公開。

- 設定 / 環境読み込み (kabusys.config)
  - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）を導入し、CWD に依存しない自動ロードを実現。
  - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、インラインコメント等に対応）。
  - .env.local を .env より優先して上書きする挙動を実装。OS 環境変数は保護（上書き禁止）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、必須キー取得（_require）・値検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値等）を実装。
  - 環境変数プロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH 等。

- データ収集 / 保存（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング RateLimiter を実装。
  - 再試行（指数バックオフ、最大3回）と特定ステータス（408, 429, 5xx）でのリトライを実装。
  - 401 受信時にリフレッシュトークンから ID トークンを再取得して 1 回リトライするロジックを実装。
  - ページネーション対応の fetch_* 系関数（fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar）。
  - DuckDB への保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）は冪等（ON CONFLICT DO UPDATE / DO NOTHING）で保存。
  - データ整形ユーティリティ（_to_float, _to_int）を追加。
  - fetched_at を UTC ISO8601 で記録し、look-ahead バイアスのトレースを可能に。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードを収集して raw_news へ保存する仕組みを実装。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント削除、小文字化）を実装し、記事ID を正規化 URL の SHA-256 ハッシュ（先頭32文字）で生成して冪等性を担保。
  - defusedxml を利用して XML アンパック攻撃（XML Bomb 等）を防止。
  - HTTP レスポンスサイズ上限（MAX_RESPONSE_BYTES）や URL スキーム制限など SSRF / DoS を考慮した安全対策を実装。
  - bulk insert 用のチャンク処理を実装。

- 研究 / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（最新の報告日ベースで取得）。
    - SQL + ウィンドウ関数で効率的に計算し、データ不足時の None ハンドリングを実装。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装（有効レコード数が 3 未満の場合は None）。
    - rank / factor_summary: ランク変換（同順位は平均ランク）、各種統計量（count/mean/std/min/max/median）を提供。
  - research パッケージ初期エクスポートを提供。

- 戦略（kabusys.strategy）
  - feature_engineering.build_features:
    - research で計算した生ファクターをマージし、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、Zスコア正規化（zscore_normalize に依存）、±3 でクリップし features テーブルに日付単位で置換（トランザクション）して保存する。
    - 価格は target_date 以前の最新値を参照し、休場日対応。
    - 冪等性（DELETE + bulk INSERT をトランザクションで行い、ROLLBACK ハンドリング）を確保。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news の各コンポーネントスコアを計算して final_score を重み付き合算。
    - デフォルト重みと閾値（デフォルト threshold=0.60）を実装。ユーザ指定重みは検証・補正（無効値の除外、合計が 1 でない場合の再スケール）される。
    - Bear レジーム判定（ai_scores の regime_score 平均が負であり十分なサンプルがある場合は Bear と判断し BUY を抑制）。
    - BUY シグナル生成（score >= threshold かつ Bear でない場合）および SELL（ストップロス -8%／スコア低下）を実装。
    - positions / prices_daily から保有ポジションの最新情報を取得し、価格欠損や PK 欠損に対する安全な挙動（警告ログ・判定スキップ）を実装。
    - signals テーブルへ日付単位で置換（トランザクション）して保存。BUY 優先→SELL 優先のルール、ランク付け処理を実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- ニュース収集と XML パースで defusedxml を採用して潜在的な XML 攻撃を緩和。
- RSS/URL 正規化とレスポンスサイズ制限で SSRF/メモリDoS のリスクを低減。
- J-Quants クライアントでトークン自動リフレッシュと安全な再試行制御を実装。

Notes / Implementation details
- look-ahead バイアス対策:
  - データ取得時の fetched_at を UTC で記録し、feature/signal 計算は target_date 時点までのデータのみを用いる設計。
- 冪等性:
  - データ保存は ON CONFLICT / DELETE+INSERT を用いて日付単位で置換することで冪等性を担保。
- トランザクション:
  - features / signals の書き込みは BEGIN/COMMIT（例外時は ROLLBACK）で原子性を保証。ROLLBACK 失敗時は警告ログを出力。
- 研究コードは本番の発注機構や execution 層へ直接依存しないよう分離されている。
- 外部依存:
  - defusedxml を利用。
  - DuckDB をデータ処理のコアとして使用。
  - data.stats.zscore_normalize に依存する箇所あり（該当ユーティリティは別モジュールで提供される想定）。

Breaking Changes
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Roadmap / TODO（コード内コメントに基づく）
- signal_generator の SELL 条件: トレーリングストップ（peak_price 必要）や時間決済（60 営業日超）など未実装の項目があるため今後の実装予定。
- news_collector: RSS ソースの拡充やシンボル紐付け処理（news_symbols）などの強化。
- execution 層: 発注ロジック（kabu ステーション連携）については現時点で実装ファイルが空のため別途実装予定。

ライセンスやその他メタ情報はリポジトリのドキュメントを参照してください。