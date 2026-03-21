# Changelog

すべての注目すべき変更はこのファイルに記録します。本書式は「Keep a Changelog」に準拠しています。  
バージョン番号は semver に従います。

## [0.1.0] - 2026-03-21

初回公開リリース。

### Added
- パッケージのエントリポイント
  - `kabusys` パッケージを追加。公開 API: `data`, `strategy`, `execution`, `monitoring`（execution は空パッケージ）。
  - バージョン: `0.1.0`（`src/kabusys/__init__.py`）。

- 環境設定管理
  - `.env` / 環境変数を読み込む `kabusys.config` を追加。
    - プロジェクトルート検出は `.git` または `pyproject.toml` を基準に上位ディレクトリを探索（配布後の動作を考慮）。
    - 自動ロードの順序: OS 環境変数 > `.env.local` > `.env`。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` パーサーは `export KEY=val` 形式、シングル/ダブルクォート内のエスケープ、インラインコメントの扱いなどをサポート。
    - 必須環境変数取得時に未設定だと `ValueError` を送出するヘルパーを提供。
    - 設定値ラッパー `Settings` を提供（J-Quants トークン、kabu API、Slack、DB パス、実行環境、ログレベルなど）。`KABUSYS_ENV` と `LOG_LEVEL` の値検証を実装。

- データ収集・保存（J-Quants クライアント）
  - `kabusys.data.jquants_client` を追加。
    - J-Quants API 呼び出しユーティリティ（ページネーション対応、JSON パース、エラーハンドリング）。
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（内部 RateLimiter）。
    - 再試行ロジック（指数バックオフ、最大 3 回）と 401 時の自動トークン再取得（1 回のみリフレッシュして再試行）。
    - データ保存用ユーティリティ:
      - 日足: `fetch_daily_quotes` / `save_daily_quotes`（`raw_prices` に対して ON CONFLICT DO UPDATE、`fetched_at` を UTC で記録）。
      - 財務: `fetch_financial_statements` / `save_financial_statements`（`raw_financials` に対して ON CONFLICT DO UPDATE）。
      - マーケットカレンダー: `fetch_market_calendar` / `save_market_calendar`（`market_calendar` に対して ON CONFLICT DO UPDATE）。
    - 型変換ユーティリティ `_to_float` / `_to_int`（不正な値を安全に None に変換）。

- データ収集（ニュース）
  - `kabusys.data.news_collector` を追加。
    - RSS フィードからの記事収集・前処理と `raw_news` への冪等保存を想定。
    - URL 正規化（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリソート）。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字）などを利用して冪等性を確保する設計（仕様コメント）。
    - XML パースに `defusedxml` を使用し XML BOM 等の攻撃を防御。
    - 受信サイズ上限（MAX_RESPONSE_BYTES）や SSRF 対策の設計（コメント）。
    - バルク挿入のチャンクサイズ制御。

- リサーチ（ファクター計算・解析）
  - `kabusys.research.factor_research` を追加。
    - Momentum / Volatility / Value 等のファクター計算関数を提供:
      - `calc_momentum(conn, target_date)` : 1M/3M/6M リターン、MA200 乖離率（必要データ不足時は None）。
      - `calc_volatility(conn, target_date)` : ATR20、相対 ATR（atr_pct）、20 日平均売買代金、volume_ratio。
      - `calc_value(conn, target_date)` : PER（EPS が無効なら None）、ROE（raw_financials を参照）。
    - DuckDB SQL を中心に実装し、prices_daily / raw_financials テーブルのみを参照する設計。

  - `kabusys.research.feature_exploration` を追加。
    - 将来リターン計算: `calc_forward_returns(conn, target_date, horizons)`（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: `calc_ic(factor_records, forward_records, factor_col, return_col)`（Spearman の ρ、有効サンプル 3 未満で None）。
    - 基本統計サマリー: `factor_summary(records, columns)`。
    - ランク付けユーティリティ `rank(values)`（同順位は平均ランク）。

  - `kabusys.research.__init__` に主要関数をエクスポート。

- 戦略（特徴量エンジニアリング）
  - `kabusys.strategy.feature_engineering.build_features(conn, target_date)` を追加。
    - 研究環境の生ファクターを取得（research モジュールの calc_* を利用）、ユニバースフィルタ適用（最低株価 300 円、20 日平均売買代金 >= 5 億円）、Z スコア正規化（対象列: mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）、±3 にクリップ。
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT により原子性を確保）。
    - 冪等動作（同一 date の再実行で上書き）。

- 戦略（シグナル生成）
  - `kabusys.strategy.signal_generator.generate_signals(conn, target_date, threshold=0.60, weights=None)` を追加。
    - features と ai_scores を統合し、各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算して重み付き合算により final_score を算出（デフォルト重みは StrategyModel.md の設計に従う）。
    - 重みは外部から上書き可能だが、未知キー/不正値は無視し再スケールして合計 1.0 に正規化。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値以上で検知）時は BUY シグナル抑制。
    - BUY シグナル閾値のデフォルトは 0.60。SELL シグナルはストップロス（終値/avg_price -1 < -8%）およびスコア低下（threshold 未満）を判定。
    - positions テーブルの価格欠損時は SELL 判定をスキップ。保有銘柄が features に存在しない場合は final_score=0.0 として SELL 扱い。
    - signals テーブルへ日付単位で置換（冪等）。

### Changed
- コード設計/ドキュメントの明示化
  - 各モジュールに設計方針・処理フロー・未実装機能の注記を付与（ルックアヘッドバイアス回避、発注層依存の排除など）。
  - DuckDB 操作はトランザクションとバルク挿入で原子性とパフォーマンスを重視する方針を採用。

### Fixed
- 抜けやすいデータ型・欠損値への堅牢性向上
  - 各所で None/非有限値のチェックを徹底（math.isfinite 等を利用）し、欠損値が下流処理に悪影響を与えないように設計。
  - `save_*` 系で PK 欠損行をスキップし、その件数をログ警告するようにした。

### Notes / Migration
- 環境変数:
  - 自動 .env 読み込みを無効化したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト等で利用）。
  - 必須項目（例: JQUANTS_REFRESH_TOKEN, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, KABU_API_PASSWORD）は `Settings` 経由で取得され、未設定時は例外が発生します。

- DB スキーマ:
  - 本リリースでは `raw_prices`, `raw_financials`, `market_calendar`, `raw_news`, `raw_*`、`prices_daily`, `features`, `ai_scores`, `positions`, `signals` 等のテーブルを前提としています。実行前に必要テーブルの準備が必要です（スキーマはコード中のコメント/INSERT 句から参照してください）。

- 未実装 / TODO:
  - signal_generator のトレーリングストップや保有日数による時間決済など、一部エグジット条件は positions に peak 情報や entry_date を追加することで将来的に実装予定（コメントあり）。
  - news_collector の具体的な RSS フェッチ/パース・記事と銘柄の紐付け（news_symbols への挿入）は実装の補助が必要。

---

今後のリリースでは実運用での監視・実行（execution 層）、monitoring 用の DB メトリクス取り込み、より豊富な News→銘柄マッピング、テストおよび CI の追加などを予定しています。