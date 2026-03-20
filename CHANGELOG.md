# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。  
このプロジェクトはセマンティックバージョニングを採用します。

## [0.1.0] - 2026-03-20

### Added
- パッケージ初期リリース。日本株自動売買システム「KabuSys」のコア機能を実装。
- パッケージメタ情報
  - `kabusys.__version__ = "0.1.0"`
  - 公開 API: `kabusys` の `__all__` に `data`, `strategy`, `execution`, `monitoring` を定義。

- 環境設定 / ロード機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む `Settings` クラスを実装。
  - 自動 .env ロード:
    - プロジェクトルートを `.git` または `pyproject.toml` を基準に検出（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能（テスト向け）。
    - OS 環境変数を保護する `protected` セットを導入し、.env.local の上書きを制御。
  - 高度な .env パーサ実装:
    - `export KEY=val` 形式対応、クォート文字列内でのバックスラッシュエスケープ対応、インラインコメント処理（クォート有無での扱い差分）など。
  - 必須キー読み取り用ヘルパ `_require()` と、設定検証:
    - `KABUSYS_ENV` は `development` / `paper_trading` / `live` のみ許容。
    - `LOG_LEVEL` は `DEBUG|INFO|WARNING|ERROR|CRITICAL` のみ許容。
  - Settings が提供するプロパティ（例）:
    - J-Quants 用: `jquants_refresh_token`
    - kabu API: `kabu_api_password`, `kabu_api_base_url`
    - Slack: `slack_bot_token`, `slack_channel_id`
    - DB パス: `duckdb_path`, `sqlite_path`
    - 環境判定: `is_live`, `is_paper`, `is_dev`

- データ取得・永続化（kabusys.data.jquants_client）
  - J-Quants API クライアントを実装:
    - レート制限 (120 req/min) を固定間隔スロットリングで実装（内部 RateLimiter）。
    - 冪等性を意識した DuckDB への保存関数（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）を実装。ON CONFLICT を用いた更新を行う。
    - ページネーション対応で全件取得。
    - リトライロジック（指数バックオフ、最大 3 回、対象ステータス: 408/429/5xx）。
    - 401 受信時は ID トークンを自動リフレッシュして再試行（1 回のみ）。モジュールレベルで ID トークンをキャッシュしページネーション間で共有。
    - JSON デコード失敗時の明確なエラー報告。
    - fetch 系 API:
      - `fetch_daily_quotes`, `fetch_financial_statements`, `fetch_market_calendar`
    - DuckDB 保存 API:
      - `save_daily_quotes` (raw_prices)
      - `save_financial_statements` (raw_financials)
      - `save_market_calendar` (market_calendar)
    - 入力変換ユーティリティ `_to_float`, `_to_int` を用意（安全な変換、空値・不正値は None）。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィードから記事を収集し `raw_news` 等に保存する処理を実装（Research / DataPlatform 指針に準拠）。
  - セキュリティと堅牢性:
    - defusedxml を用いた XML パースで XML-Bomb 等に対処。
    - HTTP/HTTPS 以外のスキーム拒否（SSRF 緩和）。
    - 受信サイズ上限 `MAX_RESPONSE_BYTES = 10MB` を設定しメモリ DoS を防止。
    - 記事 ID を URL 正規化後の SHA-256（先頭32文字）で生成し冪等性を確保。正規化ではトラッキングパラメータ（utm_*, fbclid 等）を削除、スキーム/ホストを小文字化、フラグメント削除、クエリをキーでソート。
    - バルク INSERT のチャンクサイズ `_INSERT_CHUNK_SIZE = 1000` を採用。
  - デフォルト RSS ソースを提供（例: Yahoo Finance）。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算群を実装（`factor_research.py`）:
    - Momentum（mom_1m / mom_3m / mom_6m、ma200_dev）
    - Volatility（atr_20, atr_pct、avg_turnover、volume_ratio）
    - Value（per、roe） — `raw_financials` と `prices_daily` を組合せて計算
    - DuckDB SQL を多用し、営業日欠損やウィンドウ未満の場合は None を返す設計。
  - 特徴量探索（`feature_exploration.py`）:
    - 将来リターン計算 `calc_forward_returns`（任意ホライズン、1/5/21 デフォルト、最大 252 日制約）。
    - IC（Spearman の ρ）計算 `calc_ic`、rank ユーティリティ（同順位は平均ランク）。
    - factor_summary（count/mean/std/min/max/median）を提供。
  - 研究向け API を `kabusys.research.__all__` で公開（`calc_momentum`, `calc_volatility`, `calc_value`, `zscore_normalize`, `calc_forward_returns`, `calc_ic`, `factor_summary`, `rank`）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究側で計算した raw ファクターを読み込み、ユニバースフィルタ・正規化・クリップを行い `features` テーブルへ UPSERT（置換/日付単位）する `build_features` を実装。
  - ユニバースフィルタ:
    - 最低株価 `_MIN_PRICE = 300` 円
    - 20日平均売買代金 `_MIN_TURNOVER = 5e8`（5 億円）
  - Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）、±3 でクリップして外れ値の影響を抑制。
  - 冪等性: まず該当 date のレコードを削除してからトランザクション内で挿入。

- シグナル生成（kabusys.strategy.signal_generator）
  - `generate_signals` を実装し、`features` と `ai_scores` を統合して各銘柄の final_score を算出、BUY/SELL シグナルを `signals` テーブルに日付単位で書き込む。
  - スコア計算:
    - momentum / value / volatility / liquidity / news の重み合成（デフォルト重みを実装、ユーザ指定は検証・再スケールされる）。
    - シグモイド変換、欠損コンポーネントは中立0.5で補完。
    - BUY 阈値デフォルト `_DEFAULT_THRESHOLD = 0.60`。
  - Bear レジーム判定:
    - `ai_scores` の `regime_score` 平均が負で、かつサンプル数が閾値以上（デフォルト 3）であれば Bear と判定し BUY を抑制。
  - エグジット判定（SELL）:
    - ストップロス: 終値 / avg_price - 1 < -8%（優先）
    - final_score が閾値未満
    - 保有銘柄に対する価格欠損時の判定スキップとログ出力
  - 冪等性: signals テーブルを日付単位で置換（DELETE してから INSERT）しトランザクションで原子性を保証。
  - 生成後に BUY と SELL の重複を排除（SELL 優先）、BUY はスコアでランク付けし直す。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- news_collector で defusedxml を使用して XML 攻撃を防止。
- news_collector で受信サイズ上限を設定し DoS に配慮。
- news_collector で URL 正規化を行いトラッキング除去と SSRF 緩和のためスキーム制限を想定。
- jquants_client で 401 時のトークンリフレッシュを安全に行い無限再帰を避ける設計（allow_refresh フラグ）。

### Known limitations / Notes
- signal_generator のエグジット条件について、コメントで以下が未実装であることを明示:
  - トレーリングストップ（peak_price に基づく）
  - 時間決済（保有 60 営業日超過）
  これらは positions テーブルに追加のカラム（peak_price / entry_date 等）が必要。
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリ + DuckDB SQL で実装しているため、大規模データ解析時の柔軟性は将来的に改善の余地あり。
- .env パーサは多くのケースをカバーするが、特殊なエッジケースでは期待どおりに動作しない可能性がある（要テスト）。

---

今後のリリースでは、実際の execution 層（kabu ステーション連携）やモニタリング機能、未実装のエグジット条件、より細かなエラー計測・メトリクス出力、単体/統合テストの追加を予定しています。