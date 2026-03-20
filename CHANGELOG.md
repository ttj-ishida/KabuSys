CHANGELOG
=========

すべての注目に値する変更点をこのファイルに記載します。
この変更履歴は Keep a Changelog のガイドラインに準拠します。

フォーマット:
- 反復的にリリースされるバージョンごとに日付とカテゴリ（Added, Changed, Fixed, Security, Deprecated, Removed）で記載します。

Unreleased
----------
（現在のリポジトリ状態に対する未リリースの変更点はありません）

0.1.0 - 2026-03-20
-----------------

Added
- パッケージ初期リリース: kabusys (日本株自動売買システム) を提供。
  - パッケージ公開 API: kabusys.__all__ に data, strategy, execution, monitoring を定義。
  - バージョン: 0.1.0

- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数からの自動読み込み機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を起点に探索（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサを実装:
    - export 句対応、クォート文字内のエスケープ処理、インラインコメント処理、キー/値のトリム処理をサポート。
  - .env 読込時の上書き制御（override, protected）をサポートし、OS 環境変数の保護を実現。
  - Settings クラスを実装し、主要設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL など。
  - 設定値の検証:
    - KABUSYS_ENV は development / paper_trading / live のいずれかのみ許容。
    - LOG_LEVEL は標準的なログレベルのみ許容。

- データ取得・保存 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装。
    - 固定間隔のレートリミッタ（120 req/min）を実装。
    - 再試行ロジック（指数バックオフ、最大 3 回）と HTTP ステータスに基づく挙動（408/429/5xx）。
    - 401 受信時の自動トークンリフレッシュを実装（リフレッシュは 1 回まで）。
    - ページネーション対応の fetch_* 関数: fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar。
    - DuckDB への冪等保存関数: save_daily_quotes, save_financial_statements, save_market_calendar（ON CONFLICT 更新 を使用）。
    - 入力変換ユーティリティ: _to_float, _to_int。
  - 取得時の fetched_at を UTC ISO8601 で記録し、look-ahead バイアスのトレースを可能に。

- ニュース収集 (kabusys.data.news_collector)
  - RSS フィードからの記事収集機能を実装（DEFAULT_RSS_SOURCES に既定のソースを定義）。
  - URL 正規化（トラッキングパラメータ削除、クエリソート、フラグメント除去、小文字化）を実装。
  - 記事 ID を正規化 URL の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を確保。
  - XML パーシングに defusedxml を使用し XML Bomb 等の攻撃対策を実施。
  - 受信サイズ上限（MAX_RESPONSE_BYTES、デフォルト 10MB）を設けメモリ DoS を防止。
  - SSRF 対策やスキームチェックなどのセーフガードを設計書に明記（実装方針として明文化）。
  - DB 挿入はチャンク化してバルク挿入（_INSERT_CHUNK_SIZE）を行う。

- 研究用モジュール (kabusys.research)
  - ファクター計算 (kabusys.research.factor_research):
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照して各種ファクター（mom_1m/3m/6m、ma200_dev、atr_20/atr_pct、avg_turnover、volume_ratio、per、roe など）を算出。
    - 各メソッドはデータ不足時に None を返す安全な設計。
  - 特徴量探索 (kabusys.research.feature_exploration):
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）での将来リターンを計算。
    - calc_ic: スピアマンランク相関（Information Coefficient）を計算。
    - factor_summary: 各ファクター列の統計サマリー（count/mean/std/min/max/median）を提供。
    - rank: 同順位は平均ランクで扱うランク変換を実装（丸めによる ties 判定の安定化あり）。
  - research パッケージは上記主要関数を __all__ で公開。

- 戦略モジュール (kabusys.strategy)
  - 特徴量エンジニアリング (feature_engineering.build_features):
    - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価、最低売買代金）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（トランザクションで原子性を保証）。
  - シグナル生成 (signal_generator.generate_signals):
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - final_score を重み付きで計算（デフォルト重みを定義）、ユーザ指定 weights の検証・正規化を実装。
    - Bear レジーム判定（AI の regime_score 平均が負の場合、最小サンプル閾値あり）に基づく BUY 抑制。
    - BUY 閾値、ストップロス（-8%）等のエグジット条件を実装。保有銘柄に対する SELL 判定を実装（優先）。
    - signals テーブルへ日付単位の置換（トランザクションで原子性を保証）。
  - strategy パッケージは build_features / generate_signals を公開。

Security
- news_collector で defusedxml を使用し XML の脆弱性に対処。
- RSS の URL 正規化・スキーム検査・受信サイズ制限などにより SSRF とメモリ DoS を低減する設計を採用。
- jquants_client でのトークン自動リフレッシュでは無限再帰を防ぐため allow_refresh フラグを導入。

Known limitations / Notes
- トレーリングストップや時間決済など一部のエグジット条件は未実装（signal_generator 内に TODO コメントあり; positions テーブルの拡張が必要）。
- news_collector の実際のネットワーク取得ロジック（HTTP レスポンスの検証やホスト検査等）の詳細実装は設計指針に基づき実装されているが、環境に依存する追加検査が必要な場合がある。
- DuckDB スキーマ（tables: raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar 等）は本変更履歴に含まれないため、初期セットアップ手順（DDL）を別途整備する必要あり。

Deprecated
- なし

Removed
- なし

以上

---