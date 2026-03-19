# CHANGELOG

すべての注目すべき変更を記録します。  
このプロジェクトは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に準拠しています。

## [0.1.0] - 2026-03-19

初回リリース。日本株自動売買システム「KabuSys」のベース実装を追加しました。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージトップレベルを追加 (`src/kabusys/__init__.py`)。バージョンは `0.1.0`、公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 設定・環境変数管理 (`src/kabusys/config.py`)
  - `.env` / `.env.local` ファイルまたは OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート探索ロジック `_find_project_root()`（`.git` または `pyproject.toml` を基準）を追加し、CWD に依存しない自動ロードを実現。
  - `.env` パーサー `_parse_env_line()` は以下に対応：
    - コメント行 / 空行の無視
    - `export KEY=val` 形式
    - シングル・ダブルクォート、バックスラッシュによるエスケープ処理
    - インラインコメント処理（クォートあり/なしの扱い差分）
  - オプション: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - 保護機能: OS 環境変数を上書きしない `protected` 処理（`.env.local` は override=True だが OS 環境変数は保護）。
  - 必須設定取得ユーティリティ `_require()` と、`Settings` クラスを提供。主要プロパティ：
    - `jquants_refresh_token`, `kabu_api_password`, `kabu_api_base_url`
    - `slack_bot_token`, `slack_channel_id`
    - `duckdb_path`, `sqlite_path`
    - `env`, `log_level`（バリデーション付き）、および `is_live` / `is_paper` / `is_dev` ユーティリティ。

- データ取得・保存（J-Quants クライアント） (`src/kabusys/data/jquants_client.py`)
  - J-Quants API クライアントを実装。
  - レート制限対応: 固定間隔スロットリング `_RateLimiter`（120 req/min の制約を満たす）。
  - リトライ・バックオフ: 指数バックオフ、最大リトライ回数 3、HTTP 408/429/5xx に対応。429 の場合は `Retry-After` を優先。
  - トークン管理: リフレッシュトークン -> ID トークン取得 (`get_id_token`)、401 発生時の自動リフレッシュ（1 回のみ）とキャッシュ共有。
  - ページネーション対応でのデータ取得を実装：
    - `fetch_daily_quotes`（日足 OHLCV、ページネーション対応）
    - `fetch_financial_statements`（四半期財務、ページネーション対応）
    - `fetch_market_calendar`（JPX カレンダー）
  - DuckDB への冪等保存関数を追加：
    - `save_daily_quotes` → `raw_prices`（ON CONFLICT DO UPDATE）
    - `save_financial_statements` → `raw_financials`（ON CONFLICT DO UPDATE）
    - `save_market_calendar` → `market_calendar`（ON CONFLICT DO UPDATE）
  - データ変換ユーティリティ `_to_float` / `_to_int`（安全なパース・不正値は None）。

- ニュース収集 (`src/kabusys/data/news_collector.py`)
  - RSS フィードからのニュース収集モジュールを追加（デフォルトソースに Yahoo Finance を指定）。
  - セキュリティ対策: `defusedxml` を使用して XML 関連の攻撃を低減。
  - 入力の安全化:
    - 最大レスポンスサイズ制限（`MAX_RESPONSE_BYTES` = 10 MB）
    - URL 正規化 `_normalize_url()`（スキーム/ホスト小文字化、トラッキングパラメータ除去、フラグメント削除、クエリキーソート）
    - 記事 ID は正規化後の URL の SHA-256（先頭 32 文字）で生成し冪等性を担保
    - HTTP/HTTPS スキーム検査、SSRF を考慮した処理（IP/ホストの検査を含む実装想定）
  - DB バルク挿入のチャンク化（`_INSERT_CHUNK_SIZE`）やトランザクションでの効率的保存を想定。

- 研究用モジュール（Research） (`src/kabusys/research/*`)
  - ファクター計算 (`src/kabusys/research/factor_research.py`)：
    - Momentum: `calc_momentum(conn, target_date)`（1M/3M/6M リターン、MA200 乖離）
    - Volatility: `calc_volatility(conn, target_date)`（20日 ATR、相対 ATR、平均売買代金、出来高比率）
    - Value: `calc_value(conn, target_date)`（PER、ROE。`raw_financials` の最新レコードを参照）
    - 実装上の配慮: 必要な過去データウィンドウのバッファ（カレンダー日ベースの余裕）・NULL 伝播制御等
  - 特徴量探索 (`src/kabusys/research/feature_exploration.py`)：
    - `calc_forward_returns(conn, target_date, horizons)`（複数ホライズンの将来リターンを一括取得）
    - `calc_ic(factor_records, forward_records, factor_col, return_col)`（Spearman IC をランク付けで計算）
    - `factor_summary(records, columns)`（count/mean/std/min/max/median の統計サマリー）
    - `rank(values)`（同順位は平均ランクにするランク関数。丸めで ties の検出漏れを防止）
  - Research パッケージの公開 API を `__init__` で整理。

- 特徴量エンジニアリング (`src/kabusys/strategy/feature_engineering.py`)
  - `build_features(conn, target_date)` を実装：
    - `research.factor_research` の出力（momentum/volatility/value）を取得してマージ
    - ユニバースフィルタを実装（最低株価 `_MIN_PRICE` = 300 円、20 日平均売買代金 `_MIN_TURNOVER` = 5 億円）
    - 正規化: `kabusys.data.stats.zscore_normalize` を用いた Z スコア正規化（対象カラムを指定）
    - Z スコアを ±3 (`_ZSCORE_CLIP`) でクリップ
    - 日付単位での置換（DELETE→INSERT をトランザクションで行い冪等性を確保）
    - レコード数を返却しログ出力

- シグナル生成 (`src/kabusys/strategy/signal_generator.py`)
  - `generate_signals(conn, target_date, threshold, weights)` を実装：
    - `features` と `ai_scores` を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - コンポーネントスコアの補完ルール: 欠損値は中立 0.5 で補完
    - 最終スコアの重み付け（デフォルト重み `_DEFAULT_WEIGHTS` を実装、ユーザー指定値は妥当性検査のうえ合成・再スケール）
    - シグナル生成ロジック:
      - BUY: `final_score >= threshold`（デフォルト閾値 `_DEFAULT_THRESHOLD` = 0.60）だが Bear レジーム時は BUY を抑制
      - Bear 判定: `ai_scores` の `regime_score` 平均が負で、サンプル数が閾値以上（`_BEAR_MIN_SAMPLES`）の場合に Bear と判定
      - SELL（エグジット判定）: ストップロス（損失率 <= `_STOP_LOSS_RATE` = -8%）およびスコア低下（final_score < threshold）
      - 保有ポジションは `positions` テーブルの最新行を参照。価格欠損時は SELL 判定をスキップして安全性を確保
    - BUY/SELL を日付単位で置換して `signals` テーブルへ保存（トランザクションで冪等）
    - ログ出力で結果サマリを返却

- Strategy パッケージ公開 (`src/kabusys/strategy/__init__.py`)
  - `build_features` / `generate_signals` を公開 API としてエクスポート。

### 改善/設計上の配慮 (Design)
- ルックアヘッドバイアス軽減: すべての計算で `target_date` 時点のデータのみを使用する方針を徹底（features/signal/factor 計算で明記）。
- 冪等性: DB への書き込みは可能な限り日付単位の置換や ON CONFLICT を用いて冪等に実装。
- 外部 API への安全なアクセス: トークン自動リフレッシュ、レート制御、リトライロジックを組み合わせて堅牢化。
- セキュリティ配慮: RSS の XML パースに `defusedxml`、HTTP レスポンスサイズ制限、URL 正規化によるトラッキング除去等を実装。

### 既知の未実装 / 制限 (Known limitations)
- `signal_generator._generate_sell_signals` の一部条件（トレーリングストップ、時間決済）は未実装（コメントで将来要件を記載）。これらは `positions` テーブルに `peak_price` / `entry_date` 等の追加情報が必要。
- `news_collector` の詳細なフェッチ実装（ネットワークタイムアウト制御や DOM の細部処理）は存在するが、本リリースでは外部 Feed の多様性・ブラックリスト等の追加強化が必要。
- 一部ユーティリティや DB スキーマはこのリリースで仮定されており、実運用に際してはスキーマ整合性の確認が必要。

### 削除 (Removed)
- なし

### 修正 (Fixed)
- なし

### セキュリティ (Security)
- `defusedxml` を用いた XML パースで RSS フィード関連の脆弱性に対処。
- RSS レスポンスサイズ上限を設定し、メモリ DoS のリスクを低減。

---

注: 上記はソースコードから推測した初回リリースの変更点・設計意図のまとめです。実際のリリースノート作成時にはビルド/テスト状況、マイグレーション手順、DB スキーマ定義ファイル、依存関係（例: duckdb, defusedxml 等）を併せて明記してください。