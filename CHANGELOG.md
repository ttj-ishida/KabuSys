# Changelog

すべての変更は Keep a Changelog の慣習に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/

※ 本CHANGELOGはリポジトリ内のコード内容から実装済み機能・仕様・設計上の決定点を推測して作成しています。

## [Unreleased]

---

## [0.1.0] - 2026-03-20

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。  
設計上の方針として、ルックアヘッドバイアス回避、DB への冪等保存、トランザクションによる原子性、外部 API 呼び出しのレート制御・リトライ制御、安全な XML パース等を重視しています。

### Added
- パッケージ基盤
  - package version: `kabusys.__version__ = "0.1.0"`
  - パッケージ公開 API: `data`, `strategy`, `execution`, `monitoring`（`execution` はイニシャライズのみ）

- 設定 / 環境変数管理 (`kabusys.config`)
  - .env ファイル自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）
  - .env, .env.local の読み込み順序（OS 環境変数 > .env.local > .env）
  - 自動ロード無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD`
  - .env パーサーは `export KEY=val`, シングル/ダブルクォート、エスケープ、コメント処理に対応
  - 環境変数の必須チェック `_require` と型/値検証（`KABUSYS_ENV`, `LOG_LEVEL`）
  - Settings クラスにより以下の設定をプロパティで提供:
    - J-Quants / kabuステーション / Slack トークン等（必須項目は取得時にエラー）
    - DB パス（DuckDB / SQLite のデフォルトパス）
    - env 判定ヘルパー: `is_live`, `is_paper`, `is_dev`

- データ取得・保存（J-Quants） (`kabusys.data.jquants_client`)
  - J-Quants API クライアント実装（`get_id_token`, `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`）
  - ページネーション対応、モジュールレベルの ID トークンキャッシュ共有
  - レート制限制御（固定間隔スロットリング: 120 req/min 相当の _RateLimiter）
  - リトライロジック（指数バックオフ、最大 3 回、408/429/5xx を考慮）
  - 401 受信時はトークン自動リフレッシュを 1 回行ってリトライ
  - DuckDB への冪等保存関数（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）を実装（ON CONFLICT DO UPDATE）
  - CSV/外部値の安全なパースユーティリティ（`_to_float`, `_to_int`）
  - 取得時刻 `fetched_at` を UTC で記録（Look-ahead Bias をトレース可能）

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS から記事を収集・前処理して `raw_news` 等へ保存するモジュール基盤を実装
  - URL 正規化（tracking パラメータ除去、ソート、フラグメント除去、小文字化）
  - 記事 ID を正規化 URL の SHA-256（先頭32文字等）で生成し冪等性を保証する方針
  - XML の安全なパースに defusedxml を使用（XML Bomb 等の対策）
  - SSRF 対策（HTTP/HTTPS のみ許可、受信最大バイト数制限）
  - バルク INSERT のチャンク化、トランザクション化、挿入件数の正確な取得

- リサーチ用ファクター計算 (`kabusys.research.factor_research`)
  - Momentum（1M/3M/6M リターン、MA200乖離）、Volatility（20日ATR、相対ATR、平均売買代金、出来高比率）、Value（PER, ROE）等の計算を実装
  - DuckDB SQL とウィンドウ関数で効率的に算出（データ不足時は None を返す）
  - 休日や欠損に対応するためにスキャン範囲にバッファを設定

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - research モジュールから得た生ファクターを統合して `features` テーブルへ保存する処理を実装（`build_features`）
  - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5 億円）
  - 正規化: 指定カラムの Z スコア正規化 (`kabusys.data.stats.zscore_normalize` を利用)
  - Z スコアを ±3 でクリップ、日付単位で DELETE → INSERT（トランザクションで原子性を確保）
  - ルックアヘッド回避のため target_date 時点のデータのみ参照

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - `features`, `ai_scores`, `positions`, `prices_daily` を参照して売買シグナルを生成（`generate_signals`）
  - コンポーネントスコア: momentum / value / volatility / liquidity / news（シグモイド変換等）
  - final_score を重み付き合算（デフォルト重みを実装、ユーザ指定 weights を検証・正規化）
  - BUY シグナル閾値デフォルト 0.60、Bear レジーム検知で BUY を抑制（ai_scores の regime_score 平均 < 0 を Bear）
  - SELL シグナル（エグジット）: ストップロス（-8%）優先、スコア低下（threshold 未満）
  - SELL を優先して BUY から除外、signals テーブルへ日付単位の置換（トランザクションで原子性）
  - 欠損データに対する堅牢化（price 欠損時は SELL 判定スキップ、features 欠如銘柄は score=0 扱い等）

- リサーチ探索ユーティリティ (`kabusys.research.feature_exploration`)
  - 将来リターン計算（`calc_forward_returns`、複数ホライズン対応）
  - IC（Spearman の ρ）計算（`calc_ic`、結合とランク計算）
  - ファクター統計サマリー（count/mean/std/min/max/median）
  - 値のランク付けユーティリティ（`rank`）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- defusedxml を用いた安全な RSS/XML パース（XML 攻撃対策）
- news_collector における受信サイズ制限・スキーム検査で SSRF / メモリ DoS を低減
- .env 読み込み時に OS 環境変数を保護する機能（.env.local の override を制御）
- J-Quants クライアントでトークンリフレッシュ時の無限再帰を防止する制御（allow_refresh フラグ）

### Notes / Known limitations
- signal_generator 内でコメントとして明示している未実装機能:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有日数に基づく自動決済）
- execution 層はパッケージに含まれるが具体的な発注ロジック（kabu API 呼び出しなど）は実装されていないか空の初期ファイル
- 一部の設計決定（例: Z スコア ±3 クリップ、デフォルト重み・閾値）は今後の調整が想定される
- news_collector の記事 ID 生成やシンボル紐付け・NLU（AI スコア）側の実装は別途整備が必要

### Migration / Usage notes
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意: KABUSYS_ENV (development/paper_trading/live), LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH
- 自動 .env 読み込みを抑止したい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください
- DuckDB スキーマは本実装が想定するテーブル（prices_daily, raw_prices, raw_financials, market_calendar, features, ai_scores, positions, signals, raw_news 等）を事前に作成する必要があります

---

今後の予定（例）
- execution 層での kabu ステーション API 発注・監視機能の追加
- AI ニューススコア生成パイプライン（news -> AI -> ai_scores）の統合
- テストカバレッジ強化、CI の導入
- パフォーマンス改善（大銘柄数時の DuckDB クエリ最適化、news_collector の並列化）