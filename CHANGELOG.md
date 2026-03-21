# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。  
このリポジトリはセマンティックバージョニングを採用します。

## [Unreleased]

### Known limitations / TODO
- 売却条件の一部が未実装:
  - トレーリングストップ（peak_price の追跡が必要）
  - 時間決済（保有 60 営業日超過での強制決済）
- news_collector の一部の安全対策（例: 完全な SSRF 防止の IP/ホスト検証や受信ストリーム制御など）がドキュメントに記載されているが、実装箇所は今後の確認が必要。
- テストカバレッジ・エンドツーエンド検証は今後強化予定。

---

## [0.1.0] - 2026-03-21

### Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージメタ: src/kabusys/__init__.py に __version__ = "0.1.0"、主要サブパッケージを __all__ に宣言（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理モジュール（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定値を自動ロード（プロジェクトルートを .git または pyproject.toml で検出）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープを考慮したパース、コメント処理（クォート外の # は直前が空白/タブ時にコメントとみなす）などに対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等のプロパティを型付きで取得可能。環境変数の必須チェック・妥当性検証を実装（例: KABUSYS_ENV の許容値チェック、LOG_LEVEL の検査）。

- データ取得・永続化（src/kabusys/data/）
  - J-Quants クライアント（src/kabusys/data/jquants_client.py）
    - API 呼び出し共通処理:
      - 固定間隔ベースのレートリミッタ（120 req/min）を実装。
      - リトライロジック（指数バックオフ、最大 3 回、HTTP 408/429/5xx とネットワークエラーをリトライ対象）。
      - 401 受信時はトークン自動リフレッシュを 1 回行ってリトライ。
      - ページネーション対応（pagination_key によるループ）。
      - JSON デコード失敗時の明示的エラー。
    - 高レベル API:
      - get_id_token: リフレッシュトークンから ID トークン取得（POST）。
      - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar: J-Quants エンドポイントからデータ取得（ページネーション対応）。
    - DuckDB への保存関数（save_daily_quotes / save_financial_statements / save_market_calendar）:
      - fetched_at を UTC ISO8601 形式で保存し、取得時刻をトレース可能に。
      - INSERT ... ON CONFLICT DO UPDATE による冪等保存。
      - PK 欠損行のスキップとログ警告。
      - 型変換ユーティリティ (_to_float / _to_int) を実装。

  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードからの記事収集設計とユーティリティ実装（URL 正規化、トラッキングパラメータ除去、最大受信サイズ制限、XML の安全パースに defusedxml を使用）。
    - デフォルト RSS ソース定義（例: Yahoo のビジネスカテゴリ）。
    - 記事ID の生成方針（URL 正規化後の SHA-256 先頭など）に関する設計コメント。
    - DB 保存はバルクで行う設計（チャンクサイズ定義）。

- 研究用モジュール（src/kabusys/research/）
  - factor_research.py:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB (prices_daily / raw_financials) を用いて定量ファクターを計算（mom 1/3/6m、MA200 乖離、ATR20、相対 ATR、20日平均売買代金、出来高比率、PER/ROE 等）。
    - スキャン範囲や窓サイズに関するバッファ設計（カレンダー日数の余裕を取る等）。
  - feature_exploration.py:
    - calc_forward_returns: 与えたホライズン（デフォルト [1,5,21]）に基づく将来リターン計算を提供。
    - calc_ic: スピアマン順位相関（IC）を計算するユーティリティ（欠損・同順位を扱うランク付けを実装）。
    - factor_summary / rank: 基本統計量とランク関数の実装。外れ値や None の取り扱いを考慮。

  - research パッケージの __all__ を整備し、主要関数をエクスポート。

- 戦略モジュール（src/kabusys/strategy/）
  - feature_engineering.py:
    - 研究環境で計算した生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップし features テーブルへ日付単位で置換（トランザクションによる原子性）。
    - 価格取得は target_date 以前の最新価格を参照し、休場日や当日欠損に対応。
  - signal_generator.py:
    - features テーブルと ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換・欠損時の中立補完（0.5）を行い、重み付き合算で final_score を算出（デフォルト重みはコード内定義）。
    - Bear レジーム判定（ai_scores の regime_score の平均が負のとき）により BUY シグナルを抑制。
    - BUY 閾値（デフォルト 0.60）を超える銘柄に BUY シグナル出力。保有ポジションに対するエグジット判定（ストップロス -8% / スコア低下）により SELL シグナル生成。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入で原子性）。
    - weights の入力検証（未知キー・非数値・NaN/Inf・負値は無視）、合計が 1.0 でない場合は再スケールするロジック。

- DB トランザクション運用
  - features / signals / raw_* / market_calendar 等の書き込みは日付単位での置換を行い、BEGIN/COMMIT/ROLLBACK によって原子性を保証。ROLLBACK に失敗した場合は logger.warning を出力。

- ロギングと堅牢性
  - 各モジュールで logger を使用し、警告・情報・デバッグレベルのログメッセージを豊富に追加。
  - 入力欠損や非数値、取得失敗時の安全なスキップや明示的な警告を実装。

### Changed
- 新規パッケージのため、変更履歴は初版のみ。

### Fixed
- 新規パッケージのため、修正履歴はなし。

### Security
- news_collector は defusedxml を用いた安全な XML パースを使用し、外部入力に対する基本的な防御を考慮。
- J-Quants クライアントはトークンの自動リフレッシュ時の再帰を防止するフラグ（allow_refresh）を導入し、無限再帰を回避。

---

開発・運用者向けメモ
- 環境変数（主なもの）:
  - JQUANTS_REFRESH_TOKEN（必須）
  - KABU_API_PASSWORD（必須）
  - SLACK_BOT_TOKEN（必須）
  - SLACK_CHANNEL_ID（必須）
  - DUCKDB_PATH / SQLITE_PATH（デフォルト: data/kabusys.duckdb, data/monitoring.db）
  - KABUSYS_ENV（development/paper_trading/live、デフォルト development）
  - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL、デフォルト INFO）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で .env 自動ロードを無効化

- 未実装 / 将来追加予定:
  - signal_generator のトレーリングストップ / 時間決済ロジック（positions テーブルに peak_price / entry_date が必要）
  - より詳細なニュースの URL/ホスト検証（SSRF 防止）、受信ストリームの厳格化

もし CHANGELOG に含めたい追加の差分や日付、リリースノートのスタイル（例: 変更の粒度をさらに細かくするなど）があれば指示ください。