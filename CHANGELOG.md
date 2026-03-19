CHANGELOG
=========
すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングに従います。

0.1.0 - 2026-03-19
-----------------

Added
- 初回公開リリース。
- パッケージのエントリポイント:
  - パッケージバージョン __version__ = "0.1.0"
  - パブリックモジュール: data, strategy, execution, monitoring

- 環境変数 / 設定管理 (kabusys.config)
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml 基準）から自動読み込みする機能を追加。読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env 行パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント、トラッキングコメントの取り扱いをサポート。
  - Settings クラスを提供し、環境変数経由で設定を取得:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（既定: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（既定: data/kabusys.duckdb）
    - SQLITE_PATH（既定: data/monitoring.db）
    - KABUSYS_ENV（development / paper_trading / live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のヘルパー

- データ取得 / 永続化 (kabusys.data.jquants_client)
  - J-Quants API クライアントを実装:
    - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar
    - 固定間隔レートリミッタ（120 req/min）を実装（内部クラス _RateLimiter）
    - 再試行（指数バックオフ、最大 3 回）・429 の Retry-After 優先処理・408/429/5xx を再試行対象にするロジック
    - 401 受信時はリフレッシュトークンで自動的に id_token を更新して 1 回リトライ
    - ページネーション中での id_token キャッシュ共有
  - DuckDB へ保存するユーティリティを追加:
    - save_daily_quotes -> raw_prices テーブルへ（ON CONFLICT DO UPDATE による冪等）
    - save_financial_statements -> raw_financials テーブルへ（同上）
    - save_market_calendar -> market_calendar テーブルへ（同上）
    - データ正規化ユーティリティ _to_float / _to_int を実装し、型安全に変換。PK 欠損行はスキップしログ警告を出力。
  - 取得時の fetched_at は UTC ISO8601 で記録（Look-ahead bias を抑止するための設計）

- ニュース収集 (kabusys.data.news_collector)
  - RSS 取得と raw_news への冪等保存を想定したモジュールを追加:
    - デフォルト RSS ソースに Yahoo Finance を設定
    - トラッキングパラメータ（utm_*, fbclid 等）を除去して URL 正規化
    - 記事 ID は正規化 URL の SHA-256（先頭 32 文字）で生成して冪等性を確保
    - defusedxml を用いた XML パース、受信サイズ上限（10MB）、HTTP スキームチェックなどの安全対策
    - バルク INSERT のチャンク処理（チャンクサイズ 1000）
    - raw_news に保存する際のトランザクション集約、INSERT の実際に挿入された数の追跡を想定

- 研究（Research）機能 (kabusys.research)
  - ファクター計算 / 調査用ユーティリティを追加:
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを算出
    - zscore_normalize を外部（kabusys.data.stats）から利用
    - calc_forward_returns: 指定ホライズン（デフォルト 1,5,21 営業日）の将来リターンを計算。horizons の検証（正の整数かつ <=252）
    - calc_ic: Spearman のランク相関（IC）を計算する実装（同順位は平均ランクで処理）
    - factor_summary / rank: 基本統計量とランク付けユーティリティ

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date) を実装:
    - research の calc_* 結果を統合
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    - 指定カラムを Z スコア正規化（_NORM_COLS）して ±3 でクリップ
    - features テーブルへ日付単位で置換（DELETE->INSERT をトランザクションで実行し原子性を確保）
    - 欠損やトランザクションエラー時の ROLLBACK とログ警告

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.6, weights=None) を実装:
    - features / ai_scores / positions を参照し、各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - 各コンポーネントは None を中立値 0.5 で補完して最終スコア final_score を作成
    - weights はデフォルト値から安全にマージ・検証・再スケール（負値・NaN/Inf・未知キーは無視）
    - Bear レジーム判定（AI の regime_score の平均が負のとき。ただしサンプル数が閾値未満なら Bear としない）
    - BUY は final_score >= threshold（Bear 時は BUY を抑制）、SELL はストップロス（-8%）やスコア低下等で判定
    - SELL 優先ポリシー: SELL 対象は BUY から除外し、ランクを再付与
    - signals テーブルへ日付単位で置換（トランザクションで原子性保護）
    - トランザクション失敗時の ROLLBACK ログ

- パッケージ API エクスポート (kabusys.strategy.__init__, kabusys.research.__init__)
  - build_features / generate_signals / 各 research API を __all__ 経由で公開

Documentation / Design Notes (コード内コメントに記載)
- Look-ahead bias 回避方針（target_date 時点のデータのみを使用、fetched_at の記録）
- 冪等性の重視（DB への ON CONFLICT、日付別 DELETE->INSERT）
- 外部依存を最小化（research モジュールは pandas 等に依存しない実装）
- セキュリティ考慮（defusedxml、受信サイズ制限、SSRF を想定した URL 検証）
- 未実装 / 将来実装予定の項目（コード内に TODO として記載）:
  - positions テーブルに peak_price / entry_date を付与してトレーリングストップや時間決済を実装する予定（signal_generator のエグジット条件に記載）

Known limitations
- execution / monitoring パッケージは公開されているが、このスナップショットでは実装の詳細が含まれていない（execution/__init__.py は空）。発注ロジック（kabu API 経由など）は別モジュールで実装予定。
- 一部の集計は DuckDB の window 関数に依存しており、DuckDB のスキーマ（prices_daily, raw_prices, raw_financials, features, ai_scores, positions, signals, market_calendar, raw_news 等）を前提としている。実行前にスキーマを準備する必要あり。
- jquants_client は urllib を直接使用する実装のため、環境ごとのプロキシ設定や TLS 設定に注意が必要。

Migration / Usage notes
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- ローカル開発時はプロジェクトルートに .env/.env.local を配置すると自動で読み込まれる。自動読み込みを無効化する場合は KABUSYS_ASSUME_AUTO_ENV_LOAD=1 ではなく KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。
- DuckDB/SQLite の既定パスは Settings.duckdb_path / sqlite_path を参照。必要に応じて環境変数で上書き可能。

Contributors
- コードベースに記載された設計コメント・実装に基づく最初の公開リリース。

（今後のリリースでは execution 層の実装、モニタリング機能、テスト追加、ドキュメントの拡充、細かなハンドリング改善を予定）