# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティック バージョニング（MAJOR.MINOR.PATCH）を採用します。

## [Unreleased]


## [0.1.0] - 2026-03-20
初期リリース。日本株自動売買システムのコア機能群を実装しました。主にデータ取得・保存、リサーチ用ファクター計算、特徴量エンジニアリング、シグナル生成、環境設定ユーティリティ、ニュース収集に関する機能を提供します。

### Added
- パッケージ初期化
  - kabusys パッケージのエクスポートを定義（data, strategy, execution, monitoring）。
  - strategy サブパッケージから build_features / generate_signals を公開。

- 環境設定管理（kabusys.config）
  - .env ファイル（.env, .env.local）及び OS 環境変数から設定を自動読み込み（プロジェクトルート検出：.git または pyproject.toml）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - export KEY=val 形式、コメント、シングル/ダブルクォート、エスケープ処理などに対応した .env パーサー実装。
  - 環境変数必須取得ヘルパー _require と Settings クラスを実装。主要な設定プロパティを提供：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV 検証（development / paper_trading / live）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。ページネーション対応の fetch_* 系関数を提供：
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（財務データ）
    - fetch_market_calendar（マーケットカレンダー）
  - レート制限管理（120 req/min）を行う固定間隔スロットリング RateLimiter を実装。
  - リトライ（指数バックオフ、最大3回、408/429/5xxを対象）、429 の Retry-After 優先、401 受信時のトークン自動リフレッシュ処理を実装。
  - DuckDB へ冪等に保存する save_* 関数を実装（ON CONFLICT DO UPDATE を利用）：
    - save_daily_quotes（raw_prices）
    - save_financial_statements（raw_financials）
    - save_market_calendar（market_calendar）
  - 入力変換ユーティリティ _to_float / _to_int を提供し、不正データを安全に扱う。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集して raw_news／news_symbols 等へ保存するためのユーティリティを実装。
  - URL 正規化（トラッキングパラメータ除去・ソート・小文字化・フラグメント除去）で記事IDを生成（SHA-256 ハッシュの先頭 32 文字）。
  - defusedxml による XML パースで XML Bomb 対策、受信サイズ制限（10 MB）などの安全対策を実装。
  - INSERT のチャンク化、トランザクション最適化、ON CONFLICT DO NOTHING による冪等性確保。

- リサーチ（kabusys.research）
  - ファクター計算と探索用ユーティリティを実装・公開：
    - factor_research: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を使用）
    - feature_exploration: calc_forward_returns（複数ホライズン対応）、calc_ic（Spearman の ρ）、factor_summary（count/mean/std/min/max/median）、rank（平均ランク方式）
    - zscore_normalize を data.stats から再エクスポート（パッケージ API に統合）

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features 実装：
    - research モジュールの生ファクターを取得しマージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）を適用。
    - 指定カラム群に対する Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（DELETE -> bulk INSERT、トランザクションで原子性確保）。
    - 処理はルックアヘッドバイアス防止のため target_date 時点で完結。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals 実装：
    - features / ai_scores / positions / prices_daily を参照して最終スコア final_score を計算。
    - コンポーネントスコア：momentum / value / volatility / liquidity / news（AIスコア）を計算するユーティリティ実装（シグモイド・平均補完など）。
    - weights の検証・補完・正規化（デフォルト重みを定義、ユーザ指定は検証して再スケール）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつ十分なサンプル数）により BUY シグナルを抑制。
    - BUY は閾値（デフォルト 0.60）に基づいて生成、SELL はエグジット条件（ストップロス -8%／スコア低下）で生成。
    - 保有銘柄の SELL を BUY から除外する優先ポリシーを適用。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性確保）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Security
- news_collector: defusedxml を使用した XML パース、レスポンスサイズ制限、URL 正規化とスキーム検査により外部からの攻撃（XML Bomb / SSRF / メモリ DoS）に配慮。
- jquants_client: トークン自動リフレッシュの際の再帰防止（allow_refresh フラグ）やタイムアウト設定等で堅牢性を考慮。

### Notes / Implementation details
- DuckDB をデータレイヤに採用し、SQL ウィンドウ関数を活用した高効率のファクター計算（移動平均・ラグ・LEAD/LAG）を実装。
- 多くの DB 書き込み処理は冪等性を担保（ON CONFLICT / 日付単位のDELETE->INSERT）しており、再実行可能な ETL フローを想定。
- ルックアヘッドバイアス回避方針をドキュメント化しており、計算・シグナル生成は target_date 時点の情報のみを使用する設計。
- execution / monitoring パッケージはエクスポートされるが、今回リリースのコードでは発注処理等の実装は含まれていません（今後の拡張を想定）。

--- 

今後のリリースでは、以下を想定しています（未実装機能・改善候補）
- execution 層の実装（Kabu API 経由の発注・注文管理）
- monitoring 層（アラート・Slack 通知等）の充実
- feature_engineering / signal_generator のユニットテスト追加とパフォーマンス改善
- news_collector の記事→銘柄紐付けアルゴリズム強化（NLP/ルールベース）
- 高可用性・マルチスレッド/プロセスでのレートリミット調整や実運用向けのバックオフ戦略調整

--- 

著者注: 本 CHANGELOG は提示されたコードベースの内容と docstring / 実装から推測して作成しています。具体的な運用手順や外部仕様（DB スキーマ、テーブル定義、外部サービスの接続設定など）は別途ドキュメントを参照してください。