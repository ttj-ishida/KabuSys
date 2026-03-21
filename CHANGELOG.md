# CHANGELOG

すべての変更は Keep a Changelog の仕様に従って記載しています。  
このプロジェクトではセマンティックバージョニングを採用しています。

## [Unreleased]

## [0.1.0] - 2026-03-21
初回リリース。日本株自動売買システムの基礎機能を実装。

### Added
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）およびバージョン "0.1.0" を追加。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
    - 自動読み込みの優先順位: OS 環境変数 > .env.local > .env
    - 自動読み込みを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
    - プロジェクトルートは .git または pyproject.toml を起点に探索（CWD 非依存）。
  - .env パーサを独自実装（コメント・export プレフィックス・クォート・エスケープに対応）。
  - 環境値取得用 Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / システム設定など）。
    - 必須環境変数チェックを行い未設定時は ValueError を送出。
    - 有効な環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）の検証を実装。
    - デフォルト DB パス（DuckDB/SQLite）の返却（Path 型）。

- データ取得 & 永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装。
    - API レート制限（120 req/min）を守る固定間隔スロットリング実装（RateLimiter）。
    - リトライロジック（指数バックオフ、最大 3 回）を実装。対象ステータスコードに対応（408/429/5xx）。
    - 401 応答時はリフレッシュトークンから自動で ID トークンを再取得して 1 回リトライ。
    - ページネーション対応の fetch_* 関数（fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar）。
    - DuckDB へ冪等に保存する save_* 関数（raw_prices / raw_financials / market_calendar）。ON CONFLICT を用いた更新処理。
    - 値変換ユーティリティ（_to_float / _to_int）。
    - レスポンスの取得時刻（fetched_at）を UTC ISO8601 形式で記録し、Look-ahead バイアスのトレーサビリティを確保。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードからの記事収集と raw_news への冪等保存の基盤を実装。
    - デフォルト RSS ソースを定義（例: Yahoo Finance）。
    - 記事 ID は URL 正規化後の SHA-256（頭 32 字）等で冪等性を確保する方針。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングクエリ除去、フラグメント除去、クエリソート）を実装。
    - defusedxml を使用して XML 攻撃（XML Bomb 等）に対する耐性を考慮。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）等の DoS 防御設計を採用。
    - DB 保存はチャンク・トランザクションで実行する設計（INSERT チャンクサイズの設定）。

- リサーチ機能（kabusys.research）
  - 研究用途のファクター計算・解析モジュール群を実装。
    - calc_momentum / calc_volatility / calc_value（kabusys.research.factor_research）
      - prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを算出。
      - MA200・ATR20・出来高移動平均・PER/ROE 等を算出し、データ不足時は None を返す設計。
    - calc_forward_returns / calc_ic / factor_summary / rank（kabusys.research.feature_exploration）
      - 将来リターン（複数ホライズン）を一度のクエリで取得するロジック。
      - スピアマンの情報係数（IC）をランク相関で算出（同順位は平均ランク）。
      - ファクターの統計サマリー（count/mean/std/min/max/median）を計算。
    - zscore_normalize はデータ層（kabusys.data.stats）経由で利用可能に公開。

  - 設計方針:
    - DuckDB 接続を引数に取り、prices_daily のみ参照（本番環境の実行・発注 API へはアクセスしない、外部ライブラリ非依存で純粋 Python/SQL 実装）。

- 戦略ロジック（kabusys.strategy）
  - 特徴量作成（kabusys.strategy.feature_engineering）
    - 研究環境から得た生ファクターを統合し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - Z スコア正規化（外れ値 ±3 でクリップ）、features テーブルへ日付単位で置換保存（冪等、トランザクションで原子性確保）。
    - ユニバース閾値: 最低株価 300 円、最低 20 日平均売買代金 5 億円。
  - シグナル生成（kabusys.strategy.signal_generator）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントを重み付けして final_score を算出（デフォルト重みは momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。
    - BUY 閾値のデフォルトは 0.60。重みはユーザ指定で上書き可（検証・正規化ロジックあり）。
    - Bear レジーム判定（ai_scores の regime_score 平均が負の場合、十分なサンプル数がある時のみ Bear と判定し BUY を抑制）。
    - 保有ポジションのエグジット判定（ストップロス -8%、スコア低下）を実装。SELL は BUY より優先して排除。
    - signals テーブルへ日付単位の置換保存（トランザクションで原子性確保）。
    - 設計方針として発注層（execution）には依存しない（signals テーブルを通じて分離）。

- その他
  - kabaseys.research と strategy の __all__ を整備し公開 API を明示。
  - duckdb を主要な分析用 DB として使用する設計に整合。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を利用し XML 関連攻撃の軽減を図る旨を明記。
- J-Quants クライアントでトークンリフレッシュやリトライの挙動を厳密に制御し、エラー時の過剰試行や情報漏洩を抑制。

### Notes / Ops
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 未設定の場合、Settings プロパティ呼び出しで ValueError が発生します。
- .env 自動読み込み:
  - プロジェクトルートを基準に .env → .env.local の順で読み込み（.env.local は上書き）。
  - OS 環境変数は保護され、.env による上書きを防止（ただし override=True の扱いで .env.local は上書き可）。
- DuckDB / SQLite のデフォルトファイルパス:
  - DUCKDB_PATH (デフォルト: data/kabusys.duckdb)
  - SQLITE_PATH (デフォルト: data/monitoring.db)
- トランザクション処理:
  - features / signals などの日付単位の置換は BEGIN/COMMIT/ROLLBACK を用いて原子性を保つ実装。
- 研究モジュールは外部ライブラリ（pandas 等）に依存せず純粋 Python + SQL（DuckDB）での実行を想定。

---

今後の予定（例）
- execution 層の発注・注文管理の実装（kabu ステーション連携）
- モニタリング/アラート機能（Slack 通知等）の充実
- ニュースの銘柄紐付け（news_symbols）と自然言語処理によるニューススコアの導入
- 単体テスト・統合テストの追加と CI パイプライン整備

[Unreleased]: #unreleased