# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはコードベース（バージョン 0.1.0 相当）の実装内容から推測して作成しています。

## [0.1.0] - 2026-03-20

### 追加 (Added)
- パッケージ基盤
  - 初期パッケージ `kabusys` を追加。公開 API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。
  - バージョンを `0.1.0` として定義。

- 環境設定 / ロード機構 (`kabusys.config`)
  - .env ファイルまたは環境変数から設定値を読み込む自動ローダーを実装。
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準にルートを探索（__file__ 起点、CWD に依存しない実装）。
  - 読み込み優先順位: OS 環境変数 ＞ `.env.local` ＞ `.env`。`.env.local` は `.env` を上書き可能。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` による自動ロード無効化対応（テスト用途）。
  - .env パース実装の強化:
    - `export KEY=val` 形式に対応。
    - シングル／ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなしではインラインコメント判定を「直前が空白/タブ」の場合にのみ行う（# を含む値を誤解釈しないように）。
  - OS 環境変数を保護するための上書き制御（protected set）。
  - `Settings` クラスを提供し、各種必須設定値（J-Quants トークン、kabu ステーション API パスワード、Slack トークン/チャネル等）をプロパティ経由で取得可能。
  - 設定値検証:
    - `KABUSYS_ENV` は `development|paper_trading|live` のみ許容。
    - `LOG_LEVEL` は `DEBUG/INFO/WARNING/ERROR/CRITICAL` のみ許容。
  - データベースパスプロパティ（DuckDB / SQLite）の展開を実装。

- データ取得/保存（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。
  - レート制限: 固定間隔スロットリングで 120 req/min を順守する `_RateLimiter` を追加。
  - リトライロジック: 指定したステータス（408, 429）や 5xx を対象に指数バックオフで最大 3 回リトライ。
  - 401 Unauthorized に対する自動トークンリフレッシュ（1 回のみ）を実装。モジュールレベルの ID トークンキャッシュを導入してページネーション間で共有。
  - ページネーション対応の取得関数を実装:
    - `fetch_daily_quotes`（株価日足）
    - `fetch_financial_statements`（財務データ）
    - `fetch_market_calendar`（マーケットカレンダー）
  - DuckDB への冪等保存関数を実装（ON CONFLICT ... DO UPDATE を利用）:
    - `save_daily_quotes` → `raw_prices`（取得時刻 `fetched_at` を UTC ISO8601 で記録）
    - `save_financial_statements` → `raw_financials`
    - `save_market_calendar` → `market_calendar`
  - 入力データに主キー（PK）が欠損している場合は行をスキップしログ出力。

- データ前処理 / ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィードからニュース記事を収集・正規化するモジュールを追加。
  - セキュリティ指向の実装:
    - defusedxml を利用して XML 関連攻撃を緩和。
    - 受信最大サイズ制限（MAX_RESPONSE_BYTES=10MB）によりメモリ DoS を軽減。
    - トラッキングパラメータ（utm_* 等）の除去、URL 正規化を実装。
    - 記事 ID は正規化 URL の SHA-256 ハッシュ（先頭 32 文字等）を利用する方針。
  - バルク INSERT のチャンク化（_INSERT_CHUNK_SIZE）や DB トランザクションの利用で効率的な保存を想定。
  - デフォルト RSS ソースを定義（例: Yahoo Finance のビジネス RSS）。

- 研究用ファクター計算（research） (`kabusys.research`)
  - ファクター計算ユーティリティ群を提供:
    - `calc_momentum`（1M/3M/6M リターン、MA200 乖離）
    - `calc_volatility`（20日 ATR、相対 ATR、20日平均売買代金、出来高比率）
    - `calc_value`（PER、ROE。raw_financials から最新財務データを取得）
  - 特徴量解析補助:
    - `calc_forward_returns`（将来リターン計算、複数ホライズン対応）
    - `calc_ic`（Spearman ランク相関 / IC 計算）
    - `factor_summary`（count/mean/std/min/max/median の統計サマリー）
    - `rank`（同順位は平均ランクを採用）
  - 設計方針として prices_daily / raw_financials のみ参照し、本番発注 API にはアクセスしない点を明記。

- 特徴量エンジニアリング (`kabusys.strategy.feature_engineering`)
  - 研究側で計算した生ファクターを正規化・合成して `features` テーブルへ保存する `build_features` を実装。
  - フロー:
    1. research の `calc_momentum` / `calc_volatility` / `calc_value` を呼び出しファクターを取得
    2. ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用
    3. 数値ファクターを Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）、±3 でクリップ
    4. 日付単位で DELETE → INSERT の置換（トランザクションで原子性を保証）
  - ルックアヘッドバイアスを避けるため target_date 時点のデータのみ使用。

- シグナル生成 (`kabusys.strategy.signal_generator`)
  - 正規化済み `features` と `ai_scores` を統合して `final_score` を計算し、BUY / SELL シグナルを生成する `generate_signals` を実装。
  - 特長:
    - 各コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算し、重み付き合算で `final_score` を算出（デフォルト重みはコードに定義）。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完する実装（欠損銘柄の不当な降格防止）。
    - Bear レジーム検知（AI の `regime_score` 平均が負）により BUY を抑制するロジックを実装。
    - SELL（エグジット）判定:
      - ストップロス: 終値/avg_price - 1 < -8%（優先）
      - final_score が threshold 未満
    - positions / prices_daily / ai_scores / features を参照し、日付単位で signals テーブルを置換（トランザクションで原子性保証）。
    - ユーザ提供の weights は検証・再スケーリングされる（未知キーや負値・非数値は無視）。

- ユーティリティ
  - データ変換ユーティリティ `_to_float`, `_to_int` を実装（空値や不正な文字列を None に変換するなどの安全な変換ロジック）。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 既知の制限・未実装 (Notes / Known limitations)
- signal_generator 内でコメント化されている一部エグジット条件は未実装:
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超過 の実装には追加の positions 情報が必要）
- calc_value は PBR・配当利回りなど一部バリューメトリクスをまだ実装していない旨を注記。
- news_collector の実装は設計に基づいた安全性や効率化の処理を含むが、DB への最終的な保存ロジック（INSERT RETURNING 等の挙動）や銘柄紐付け（news_symbols）については追加の実装/テストが想定される。
- research モジュールは外部ライブラリ（pandas 等）に依存せず純粋に SQL + 標準ライブラリで実装しているため、大規模データでのメモリ・性能特性は実運用で評価が必要。

### セキュリティ (Security)
- XML パーシングに defusedxml を採用（news_collector）。
- 外部 URL 正規化・トラッキングパラメータ除去・受信サイズ制限を実装し、SSRF やメモリ DoS のリスク軽減を図っている。
- J-Quants API 呼び出しではトークン管理・自動リフレッシュ・レート制御・再試行を組み合わせて予期せぬ失敗時のオペレーションリスクを低減。

---

注: 本 CHANGELOG はリポジトリ内のソースコードから実装内容を要約して作成しています。実際のリリースノート作成時はコミット履歴・Issue/Ticket 等と照合のうえ必要に応じて改訂してください。