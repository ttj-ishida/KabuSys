# Changelog

すべての重要な変更点を記載します。本ドキュメントは Keep a Changelog の形式に準拠しています。

フォーマット:
- Unreleased: 未リリースの変更（現在はなし）
- 各リリースには日付（YYYY-MM-DD）を付記

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-19

Added
- パッケージ初期リリース。
- パッケージルート: `kabusys`（`__version__ = "0.1.0"`）。
- 環境設定管理:
  - `kabusys.config` モジュールを追加。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に自動検出する実装を追加（CWD非依存）。
  - `.env` / `.env.local` の自動読み込み（優先順位: OS 環境変数 > .env.local > .env）。自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサーは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応。
  - 既存 OS 環境変数を保護するための上書き制御（protected set）を実装。
  - `Settings` クラスを提供し、必須環境変数取得 (`_require`) と検証（`KABUSYS_ENV` の許容値検査、`LOG_LEVEL` の検査）、パス(duckdb/sqlite)の正規化を提供。
  - 必須設定例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`。

- Data 層（J-Quants）:
  - `kabusys.data.jquants_client` を実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング `_RateLimiter` を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回）を実装。HTTP 408/429/5xx を対象。429 の場合は `Retry-After` ヘッダを優先。
  - 401 受信時にリフレッシュトークンから自動的に ID トークンを再取得し 1 回リトライする仕組みを実装（無限再帰を防止）。
  - ページネーション対応で `fetch_daily_quotes` / `fetch_financial_statements` を実装。
  - DuckDB への保存関数（冪等）を提供:
    - `save_daily_quotes`：`raw_prices` へ INSERT .. ON CONFLICT DO UPDATE。
    - `save_financial_statements`：`raw_financials` へ INSERT .. ON CONFLICT DO UPDATE。
    - `save_market_calendar`：`market_calendar` へ INSERT .. ON CONFLICT DO UPDATE。
  - データ変換ユーティリティ `_to_float`, `_to_int` を実装（変換ポリシーを明示）。

- Data 層（ニュース収集）:
  - `kabusys.data.news_collector` を実装（RSS ベース）。
  - デフォルト RSS ソース（Yahoo Finance）を提供。
  - 記事 ID は URL 正規化後の SHA-256 ハッシュ（先頭 32 文字）で生成し冪等性を担保する方針を採用。
  - URL 正規化実装: スキーム/ホスト小文字化、既知トラッキングパラメータ（utm_*, fbclid, gclid 等）の除去、フラグメント削除、クエリパラメータのソート。
  - 受信サイズ上限（MAX_RESPONSE_BYTES=10MiB）を設定しメモリ DoS を軽減。
  - XML パースに `defusedxml` を使用し XML Bomb 等の攻撃を防止。
  - SSRF を意識し HTTP/HTTPS 以外のスキームは拒否（設計方針）。
  - DB 保存はバルク挿入（チャンク化）し、トランザクションでまとめる方針。

- Research 層:
  - `kabusys.research.factor_research` を実装。
    - Momentum: 1M/3M/6M リターン（営業日ベース）と 200 日移動平均乖離（ma200_dev）を SQL ウィンドウで算出（データ不足時は None）。
    - Volatility: 20 日 ATR を計算し相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を算出。
    - Value: raw_financials から直近財務データを取得し PER/ROE を計算（EPS が 0/欠損なら PER=None）。
    - 各ファクターはいずれも `prices_daily` / `raw_financials` のみを参照する設計。
  - `kabusys.research.feature_exploration` を実装。
    - 将来リターン計算 (`calc_forward_returns`)：複数ホライズン（デフォルト [1,5,21]）に対応、最大ホライズンに応じてクエリ範囲を制限。
    - IC（Spearman の ρ）計算 (`calc_ic`)、ランク付けユーティリティ `rank`（同順位は平均ランク）を実装。
    - `factor_summary` で基本統計量（count/mean/std/min/max/median）を計算。
    - 外部ライブラリに依存せず標準ライブラリ + DuckDB で実装。

- Strategy 層:
  - `kabusys.strategy.feature_engineering` を実装。
    - 研究環境の生ファクターを取得（`calc_momentum` / `calc_volatility` / `calc_value`）し、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 正規化: `kabusys.data.stats.zscore_normalize` を利用して指定列を Z スコア正規化し ±3 にクリップ（外れ値抑制）。
    - DuckDB の `features` テーブルへ日付単位で削除→挿入の置換（トランザクション + バルク挿入）で冪等性・原子性を保証。
  - `kabusys.strategy.signal_generator` を実装。
    - `features` と `ai_scores` を統合してコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完するポリシーを採用。
    - デフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）を用い、ユーザ指定重みは検証のうえマージ・再スケーリングする実装。
    - Bear レジーム検知（AI レジームスコア平均が負で充分なサンプルがある場合）では BUY シグナルを抑制するロジックを実装。
    - BUY 閾値デフォルト 0.60、STOP-LOSS は -8%（エグジット条件）を導入。
    - 保有ポジションのエグジット判定は価格欠損時に判定をスキップする保護ロジックを追加（誤クローズ防止）。
    - `signals` テーブルへ日付単位の置換（トランザクション + バルク挿入）で冪等性・原子性を保証。

- パッケージ公開用のモジュール束ね:
  - `kabusys.research.__init__` / `kabusys.strategy.__init__` で主要 API をエクスポート。

Changed
- （初版リリースのため該当なし）

Fixed
- （初版リリースのため該当なし）

Security
- RSS パースに `defusedxml` を採用し XML 関連攻撃を緩和。
- ニュース収集で受信サイズを制限することでメモリ DoS を軽減。
- 外部 HTTP リクエストでスキーム検証（HTTP/HTTPS のみ）等による SSRF 対策を想定した設計。

Notes / 補足
- 多くの DB 操作は DuckDB を想定しており、SQL 内でウィンドウ関数／ROW_NUMBER 等を利用しているため DuckDB の互換性に依存します。
- J-Quants API 周りは認証トークンの自動リフレッシュやページネーション処理、レート制限守備が実装されているため、実運用での API 接続に配慮した設計となっています。
- 一部のエグジット条件（トレーリングストップ、時間決済など）は `positions` テーブルに追加情報（peak_price / entry_date 等）が必要で、現バージョンでは未実装であることがソース上の注釈に記載されています。
- `kabusys.execution` と `kabusys.monitoring` はパッケージの公開対象に含まれているが、今回のコードベースでは実装が含まれていません（プレースホルダ）。

以上。