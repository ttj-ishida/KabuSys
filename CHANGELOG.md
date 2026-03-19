# CHANGELOG

すべての変更は Keep a Changelog に準拠して記載しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]

（特になし）

## [0.1.0] - 2026-03-19

初回公開リリース。日本株自動売買 / データ基盤の基礎機能をまとめて実装しました。

### Added
- パッケージ基盤
  - kabusys パッケージを追加。トップレベルで data, strategy, execution, monitoring モジュールを公開。
  - パッケージバージョン: 0.1.0

- 環境設定 / 設定管理（kabusys.config）
  - .env および .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env
  - 自動読み込みの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env ファイルの堅牢なパーサを実装（export プレフィックス対応、クォート内のエスケープ、インラインコメント処理等）。
  - Settings クラスを提供し、環境変数をラップして型・値チェックを行うプロパティを実装:
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DB パスデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
    - 環境タイプ検証: KABUSYS_ENV ∈ {"development", "paper_trading", "live"}
    - ログレベル検証: LOG_LEVEL ∈ {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
    - ヘルパープロパティ: is_live / is_paper / is_dev

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアント実装:
    - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大3回、対象: ネットワーク系/429/408/5xx）。
    - 401 (Unauthorized) 受信時はリフレッシュトークンで id_token を自動更新して1回リトライ。
    - ページネーション対応の fetch 関数:
      - fetch_daily_quotes
      - fetch_financial_statements
      - fetch_market_calendar
    - DuckDB へ冪等的に保存する save_* 関数:
      - save_daily_quotes → raw_prices テーブルへ ON CONFLICT DO UPDATE
      - save_financial_statements → raw_financials テーブルへ ON CONFLICT DO UPDATE
      - save_market_calendar → market_calendar テーブルへ ON CONFLICT DO UPDATE
    - 便利ユーティリティ: _to_float / _to_int（入力の堅牢な型変換）

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事収集し raw_news / news_symbols へ保存する機能を実装:
    - fetch_rss: RSS の取得とパース（defusedxml を用いた安全な XML パース）
    - 前処理: URL 除去、空白正規化（preprocess_text）
    - URL 正規化と追跡パラメータ除去（_normalize_url）
    - 記事 ID は正規化 URL の SHA-256 の先頭32文字で生成（冪等性）
    - SSRF 対策:
      - 取得前にホストがプライベート/ループバックかを検査（_is_private_host）
      - リダイレクト時にもスキームとホストを検査するカスタムハンドラ（_SSRFBlockRedirectHandler）
      - HTTP スキームのみ許可（http/https）
    - レスポンスサイズ制限（最大 10 MB）と gzip 解凍の安全チェック（Gzip bomb 対策）
    - DB への保存はチャンク化してトランザクション内で実行、INSERT ... RETURNING を用いて実際に挿入されたレコードを正確に把握
    - 銘柄コード抽出機能（extract_stock_codes）: テキスト中の 4 桁数字を known_codes と照合して抽出
    - 統合ジョブ run_news_collection を提供（複数ソースの収集、個別エラーハンドリング、銘柄紐付け）

- 研究用特徴量 / ファクター（kabusys.research）
  - feature_exploration:
    - calc_forward_returns: 指定日から各ホライズン（デフォルト [1,5,21]）の将来リターンを DuckDB の prices_daily から計算
    - calc_ic: Spearman ランク相関（Information Coefficient）を、ファクター結果と将来リターンをコードで結合して計算（有効レコードが3未満なら None）
    - factor_summary: カラムごとの count/mean/std/min/max/median を算出
    - rank: 同順位は平均ランクで処理（丸めにより ties 検出の安定化）
    - 設計方針: pandas 等に依存せず標準ライブラリ + duckdb で動作。実行時に発注 API 等にはアクセスしない。
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）を計算。十分な履歴がない場合は None を返す。
    - calc_volatility: 20日 ATR（atr_20、atr_pct）、20日平均売買代金（avg_turnover）、volume_ratio を計算。true_range の NULL 伝播を慎重に扱う実装。
    - calc_value: raw_financials から target_date 以前の最新財務を取得し PER（EPS ベース）と ROE を計算。EPS が 0/NULL の場合は PER を None とする。
    - データ参照は prices_daily / raw_financials のみ。計算は DuckDB の SQL ウィンドウ関数を利用。

- スキーマ定義（kabusys.data.schema）
  - DuckDB 用の DDL 定義を実装（Raw / Processed / Feature / Execution 層の方針に合わせた設計）
  - Raw レイヤーの DDL を含む（raw_prices, raw_financials, raw_news, raw_executions 等。型チェック・PRIMARY KEY 指定あり）

- エクスポート（kabusys.research.__init__）
  - 研究モジュールの主要ユーティリティをパッケージレベルで再エクスポート:
    - calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank

### Security
- RSS パーサに defusedxml を使用して XML ベースの攻撃（XML bomb 等）を抑制。
- ニュース収集においてリダイレクト先やホストのプライベート判定を行い SSRF を防止。
- HTTP スキームの検証およびレスポンスサイズ上限（10 MB）を導入し、外部からの悪意ある大容量レスポンスによる DoS を軽減。

### Notes / Migration
- 必須環境変数を設定してください（J-Quants API / kabuステーション / Slack など）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- デフォルトの DB 保存先:
  - DUCKDB_PATH: data/kabusys.duckdb
  - SQLITE_PATH: data/monitoring.db
- ログレベルや環境種別は設定値の検証があり、不正値を渡すと ValueError を発生します:
  - KABUSYS_ENV は "development" / "paper_trading" / "live" のいずれか
  - LOG_LEVEL は標準ログレベル名を使用
- .env 自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- news_collector の銘柄抽出は known_codes を渡すことで正確性が向上します（渡さない場合は紐付けをスキップ）。

### Known limitations / Future work
- Strategy / Execution / Monitoring の具体的な実装はこのバージョンでは未充足（パッケージ空ディレクトリ／初期プレースホルダ）。
- 一部テーブル定義や処理は今後の拡張で Processed / Feature 層の DDL を追加予定。
- 外部依存は最小化しているが（duckdb, defusedxml 等を使用）、更なるテストカバレッジと異常系テストを拡充予定。
- News の言語処理や自然言語処理系の拡張（形態素解析・固有表現抽出等）は未実装。

### Fixed
- 初回リリースのため該当なし。

### Changed
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

---

開発者向けの補足やバグ報告・提案は issue を立ててください。