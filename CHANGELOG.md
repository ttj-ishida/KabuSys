# Changelog

すべての非互換な変更はメジャーバージョンに記載しています。
このプロジェクトは Keep a Changelog の形式に準拠しています（日本語）。

[Unreleased]
- なし

[0.1.0] - 2026-03-20
Added
- パッケージ初期リリース。KabuSys: 日本株自動売買システムの基本機能群を実装。
- 公開モジュール・エントリポイント
  - パッケージバージョン: `kabusys.__version__ = "0.1.0"`
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring` を __all__ に設定（`execution` は空パッケージとして存在）。
- 環境設定管理 (`kabusys.config`)
  - .env の自動読み込み機構を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env（`.env.local` は override=True）。
  - 自動ロードの無効化フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサ: `export KEY=val` 形式、シングル/ダブルクォート内のエスケープ、インラインコメント処理等に対応する堅牢なパーサを実装。
  - `Settings` クラスを提供し、環境変数に対する型チェック・必須チェック（例: `JQUANTS_REFRESH_TOKEN`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`, `KABU_API_PASSWORD`）やデフォルト値（例: `KABUSYS_ENV`、`LOG_LEVEL`、`KABU_API_BASE_URL`、`DUCKDB_PATH`、`SQLITE_PATH`）を提供。
  - `KABUSYS_ENV` / `LOG_LEVEL` は許容値チェックを行い、不正値で例外を発生させる。
- データ取得・保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアント実装。
  - レート制御: 固定間隔スロットリングで 120 req/min を遵守する `_RateLimiter` 実装。
  - リトライ戦略: 指数バックオフ、最大 3 回、対象ステータス 408/429/5xx。429 の場合は `Retry-After` を優先して待機。
  - 401 Unauthorized を検知した場合、自動トークンリフレッシュ（1 回のみ）して再試行する仕組みを実装。トークン取得は `get_id_token()`。
  - ページネーション対応で `/prices/daily_quotes`、`/fins/statements`、`/markets/trading_calendar` を取得可能。
  - DuckDB への保存ユーティリティ（冪等操作）:
    - `save_daily_quotes` → `raw_prices` に `ON CONFLICT (date, code) DO UPDATE` を使用。
    - `save_financial_statements` → `raw_financials` に `ON CONFLICT (code, report_date, period_type) DO UPDATE` を使用。
    - `save_market_calendar` → `market_calendar` に `ON CONFLICT (date) DO UPDATE` を使用。
  - ペイロードからの型変換ヘルパー `_to_float`, `_to_int` を用意し、入力の堅牢化を実施。
  - モジュールレベルの ID トークンキャッシュを保持し、ページネーション間で共有。
- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード収集実装（デフォルトソース: Yahoo Finance のビジネスカテゴリ）。
  - セキュリティ対策:
    - defusedxml を用いた XML パースで XML-Bomb 等に対抗。
    - 受信サイズ制限（MAX_RESPONSE_BYTES = 10 MB）でメモリ DoS を軽減。
    - URL 正規化でトラッキングパラメータ（utm_*, fbclid 等）を除去し、記事 ID を正規化 URL の SHA-256（先頭 32 文字）で作成して冪等性を確保。
    - HTTP/HTTPS 以外のスキームの拒否等の基本検査（実装方針に沿っている）。
  - バルク INSERT をチャンク（_INSERT_CHUNK_SIZE）して DB オーバーヘッドを抑制。INSERT RETURNING による挿入件数取得を想定。
- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算群を実装・公開:
    - `calc_momentum`, `calc_volatility`, `calc_value`（`kabusys.research.factor_research`）
    - `zscore_normalize` は `kabusys.data.stats` から利用（実装ファイルは外部）。
  - 特徴量探索ツール群:
    - `calc_forward_returns`：指定ホライズン（デフォルト [1,5,21]）で将来リターン計算（1 クエリで取得、範囲限定の最適化あり）。
    - `calc_ic`：スピアマンのランク相関（Information Coefficient）計算（有効サンプル 3 未満は None を返す）。
    - `factor_summary`：基本統計量（count/mean/std/min/max/median）算出。
    - `rank`：同順位は平均ランクのランク付け（丸めで ties 検出を安定化）。
  - 実装方針: DuckDB の `prices_daily` / `raw_financials` テーブルのみを参照し、本番 API にアクセスしない。
- 特徴量生成（Feature Engineering） (`kabusys.strategy.feature_engineering`)
  - 研究モジュールから取得した raw factor を統合・正規化し、`features` テーブルへ UPSERT（対象日を一旦削除してから挿入する日付単位の置換）を行う `build_features(conn, target_date)` を実装。
  - ユニバースフィルタ:
    - 最低株価: 300 円。
    - 20 日平均売買代金: 5 億円。
  - Z スコア正規化（`zscore_normalize` を利用）と ±3 のクリップを実施して外れ値の影響を抑制。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）＋一括挿入で原子性を保証。
- シグナル生成（Signal Generator） (`kabusys.strategy.signal_generator`)
  - `generate_signals(conn, target_date, threshold=0.60, weights=None)` を実装。
  - フロー:
    - `features` / `ai_scores` / `positions` / `prices_daily` を参照して final_score を計算。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AIスコア）。
    - AI スコア未登録時は中立値 0.5 で補完。
    - weights の検証・補完・再スケール処理を実装（既知キーのみ受け付け、負値や非数値は無視）。
    - Bear レジーム判定: `ai_scores` の `regime_score` 平均が負かつサンプルが閾値（3）以上で BUY を抑制。
  - BUY シグナル生成:
    - final_score >= threshold の銘柄に BUY を割り当て（Bear の場合は抑制）。
    - SELL 判定がある銘柄は BUY から除外し、BUY のランクは再付与（SELL 優先ポリシー）。
  - SELL シグナル（エグジット判定）:
    - ストップロス: (close / avg_price - 1) < -8% → reason: "stop_loss"（最優先）。
    - スコア低下: final_score < threshold → reason: "score_drop"。
    - 価格欠損や avg_price 辺りの堅牢性チェックを実施。価格欠損時は SELL 判定をスキップし警告をログ出力。
  - 生成した BUY/SELL は `signals` テーブルへ日付単位で置換（トランザクション + bulk insert）。
- 設計方針・品質
  - ルックアヘッドバイアス防止: 各処理は target_date 時点で得られるデータのみを参照する方針で実装。
  - 本番発注層（execution）への直接依存を避け、各層は分離（strategy は execution に依存しない）。
  - DuckDB を主要な分析ストアとして利用し、SQL と Python の組合せで処理を記述。
  - 外部ライブラリ依存を最小化（research/feature_exploration では pandas 等に依存しない実装）。

Changed
- 初版につき該当なし。

Fixed
- 初版につき該当なし。

Security
- RSS パースに defusedxml、受信サイズ制限、URL 正規化等の対策を実装。
- J-Quants クライアントはトークンリフレッシュとレートリミット/リトライ処理を実装し、API 誤使用や過負荷を軽減。

Notes / Known limitations
- execution パッケージは空の状態（将来的な発注ロジックの実装を想定）。
- `positions` テーブルに peak_price / entry_date 等の拡張が必要な未実装のエグジット条件（トレーリングストップ、時間決済）がある旨をソースに注記。
- `kabusys.data.stats.zscore_normalize` 実装はファイルに含まれていないため、正規化関数は別ファイルで提供される前提。
- 一部警告/ログによる運用上の観測に依存している（例: 欠損データスキップ時のログ）。

Authors
- 初期実装: KabuSys 開発チーム（リポジトリ内の実装に基づく）

License
- リポジトリに従う（LICENSE ファイルを参照してください）。