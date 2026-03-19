# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注: この CHANGELOG はソースコードの内容から推測して作成した初期リリースの記録です（バージョンは package の __version__ を参照）。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-19

最初の公開リリース。日本株自動売買システム「KabuSys」のコアライブラリを実装しました。以下は主な追加点、設計方針、既知の制限・注意点です。

### Added
- パッケージ基礎
  - パッケージ定義 (src/kabusys/__init__.py)
    - バージョン: 0.1.0
    - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定管理 (src/kabusys/config.py)
  - 環境変数の読み込み機能を実装（.env / .env.local をプロジェクトルートから自動ロード）。
  - プロジェクトルート判定: .git または pyproject.toml を基準に親ディレクトリを探索。
  - .env パース実装（コメント、export プレフィックス、シングル／ダブルクォート、エスケープ、インラインコメントの取り扱い）。
  - 自動ロードを無効化するフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを導入し、アプリケーション設定をプロパティ経由で提供:
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）
    - 任意設定とデフォルト: KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（検証）
    - is_live / is_paper / is_dev ヘルパー。

- Data 層: J-Quants クライアント (src/kabusys/data/jquants_client.py)
  - J-Quants API から日次株価、財務データ、マーケットカレンダーを取得するクライアントを実装。
  - レート制限管理: 固定間隔スロットリング（デフォルト 120 req/min）。
  - 再試行（リトライ）ロジック: 指数バックオフ、最大 3 回、408/429/5xx を対象。429 時は Retry-After ヘッダ優先。
  - 401 Unauthorized の自動トークンリフレッシュを 1 回試行（get_id_token による refresh）。
  - モジュールレベルの ID トークンキャッシュを実装（ページネーション間で共有）。
  - HTTP ユーティリティとページネーション対応の fetch_* 関数:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB へ冪等に保存するセーバー関数:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE（fetched_at を UTC ISO で記録）
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
  - ユーティリティ: 型変換ヘルパー _to_float / _to_int（安全な変換ロジックを提供）

- Data 層: ニュース収集 (src/kabusys/data/news_collector.py)
  - RSS フィードから記事を取得して raw_news に保存するための実装。
  - 安全設計:
    - defusedxml を使用して XML 攻撃を防ぐ
    - HTTP/HTTPS スキームのみ許可
    - 受信サイズに上限（MAX_RESPONSE_BYTES = 10MB）
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去、小文字化）
    - 記事IDは正規化 URL の SHA-256（先頭32文字）等を想定して冪等性を確保
    - バルク INSERT のチャンク処理
  - デフォルト RSS ソースに Yahoo Finance のカテゴリフィードを指定

- Research 層
  - ファクター計算 (src/kabusys/research/factor_research.py)
    - モメンタム: calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - ボラティリティ/流動性: calc_volatility（20日 ATR、atr_pct、avg_turnover、volume_ratio）
    - バリュー: calc_value（最新の raw_financials と株価を組合せて PER / ROE）
    - DuckDB を用いた SQL ベースの実装。prices_daily / raw_financials のみ参照。
  - 特徴量探索 (src/kabusys/research/feature_exploration.py)
    - 将来リターン計算: calc_forward_returns（複数ホライズン対応、範囲チェック）
    - IC（Information Coefficient）計算: calc_ic（Spearman の ρ、最小3サンプル要件）
    - 統計サマリー: factor_summary（count/mean/std/min/max/median）
    - ランク変換ユーティリティ: rank（同順位は平均ランク）
  - research パッケージ __all__ を整備

- Strategy 層
  - 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
    - build_features(conn, target_date):
      - research の calc_momentum/calc_volatility/calc_value を使用し、マージ、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）、Z スコア正規化（指定カラム）、±3 でクリップ、features テーブルへ日付単位で置換 (トランザクション)。
      - 正規化対象カラム: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev
      - 冪等性を保証（DELETE → INSERT のトランザクション）
  - シグナル生成 (src/kabusys/strategy/signal_generator.py)
    - generate_signals(conn, target_date, threshold=0.60, weights=None):
      - features / ai_scores / positions テーブルからデータを読み込み、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
      - final_score を重み付き合算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。weights は不正値を除外の上で自動正規化。
      - AI レジームスコアを集計して Bear 判定（サンプル数閾値あり）。Bear の場合は BUY シグナルを抑制。
      - BUY: final_score >= threshold（Bear で抑制）
      - SELL（エグジット）: _generate_sell_signals により判定
        - 実装済み条件:
          - ストップロス: pnl <= -8%（_STOP_LOSS_RATE = -0.08）
          - スコア低下: final_score < threshold
        - 未実装（TODO）: トレーリングストップ、時間決済（注記あり）
      - signals テーブルへ日付単位の置換（トランザクションで原子性を確保）
    - 生成されたロジックは execution 層や発注 API に依存しない設計（signals テーブルを通じて連携）

- strategy パッケージ __all__ を整備（build_features, generate_signals を公開）

- data.stats への参照（zscore_normalize を利用）を前提とした実装（モジュール間の分離）

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- news_collector で defusedxml を利用し XML 脆弱性を緩和
- news_collector と jquants_client で外部入力に対する取り扱いに注意（URL スキーム検証、受信サイズ制限、Retry-After の尊重等）

### Notes / Migration / 使用上の注意
- 環境変数（必須）
  - JQUANTS_REFRESH_TOKEN: J-Quants の refresh token（get_id_token で使用）
  - KABU_API_PASSWORD: kabu ステーション API のパスワード
  - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID: Slack 通知用
- .env 自動ロード
  - プロジェクトルート（.git または pyproject.toml）を基準に .env / .env.local を自動読み込みします。
  - .env.local は .env を上書き（override=True）。OS 環境変数は保護され上書きされません。
  - 自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト時など）。
- DB テーブル
  - 実装は DuckDB のテーブル（raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals 等）を前提として動作します。テーブルスキーマはコードから推測されますが、実行前に適切なスキーマ定義が必要です。
- 冪等性
  - データ保存系（save_*）および features / signals の書き込みは日付単位での置換や ON CONFLICT により冪等性を保つよう設計されています。
- 未実装 / TODO
  - signal_generator のエグジット条件においてトレーリングストップや時間決済は未実装（Positions テーブルに peak_price / entry_date 等の追加が必要）。
  - execution パッケージは初期状態では実装が含まれていない（発注ロジックは別途実装する必要あり）。
- ログレベルと検証
  - KABUSYS_ENV は development / paper_trading / live のいずれか、LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のいずれかでないと ValueError を送出します。

---

今後のリリースでは以下を予定（推奨）
- execution 層の実装（kabuステーションとの連携）
- monitoring / alerting 機能の追加（Slack 連携の実装）
- テストカバレッジ向上・例外ケースの詳細ログ改善
- パフォーマンス最適化（DuckDB クエリのチューニング、ニュース取得の並列化など）

（この CHANGELOG はソースコードからの推測に基づくため、実際の開発履歴と差異がある可能性があります。）