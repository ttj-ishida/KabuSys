Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。

履歴
----

## [Unreleased]

## [0.1.0] - 2026-03-18

初期リリース。本リリースでは日本株自動売買システム「KabuSys」のコアライブラリの基盤機能を実装しています。

### 追加 (Added)
- パッケージ初期化
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` として設定。
  - パッケージ公開 API: `["data", "strategy", "execution", "monitoring"]`（モジュールのエントリポイントを定義）。

- 環境設定管理 (`kabusys.config`)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート探索は `.git` または `pyproject.toml` を基準に実行）。
  - `.env` / `.env.local` の読み込み優先順位を実装（OS 環境変数 > .env.local > .env）。`.env.local` は上書き (`override=True`)。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - `.env` ファイルパーサを実装:
    - `export KEY=val` 形式に対応
    - シングル/ダブルクォート中のエスケープ処理、インラインコメントの扱い、クォート無しのコメント判定などを実装
  - 設定取得用 `Settings` クラスを提供（必須変数チェック `_require`、型変換・デフォルト値、検証済み列挙値: `KABUSYS_ENV`, `LOG_LEVEL` など）。
  - DB パス用プロパティ (`duckdb_path`, `sqlite_path`) や Slack / Kabu API / J-Quants の設定プロパティを実装。

- データ取得・保存基盤 (`kabusys.data`)
  - J-Quants API クライアント (`kabusys.data.jquants_client`)
    - レート制御（120 req/min）を固定間隔スロットリングで実装（内部 `_RateLimiter`）。
    - 再試行（指数バックオフ、最大3回）、特定ステータスコードでのリトライロジック（408/429/5xx）、429 の `Retry-After` 優先処理。
    - 401 受信時の自動トークンリフレッシュ（1回のみ）とトークンキャッシュ共有 `_ID_TOKEN_CACHE`。
    - ページネーション対応のデータ取得 (`fetch_daily_quotes`, `fetch_financial_statements`)。
    - JPX カレンダー取得 (`fetch_market_calendar`)。
    - DuckDB へ冪等的に保存するユーティリティ（`save_daily_quotes`, `save_financial_statements`, `save_market_calendar`）を提供。INSERT は ON CONFLICT DO UPDATE を使用。
    - レコード整形ユーティリティ `_to_float`, `_to_int`（安全な変換ルールを実装）。
  - ニュース収集モジュール (`kabusys.data.news_collector`)
    - RSS フィード収集・前処理・DB 保存ワークフローを実装。
    - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）と記事ID生成（正規化 URL の SHA-256 の先頭32文字）を実装し、冪等性を担保。
    - SSRF 対策: リダイレクト時のスキーム検査、ホストがプライベート/ループバック/リンクローカルでないことの検証（DNS 解決と IP 判定）、許可スキームは http/https のみ。
    - レスポンスサイズ上限チェック（デフォルト 10 MB）、gzip 解凍後もサイズ検査。XML は defusedxml で安全にパースし、パース失敗は回避。
    - テキスト前処理（URL 除去・空白正規化）と銘柄コード抽出（4桁数値パターン + known_codes フィルタ）。
    - DB 保存はチャンク化と1トランザクションまとめ挿入、INSERT ... RETURNING を使用して実際に挿入された件数/IDを正確に取得。
    - 統合ジョブ `run_news_collection` を提供（複数ソースの個別エラーハンドリング、銘柄紐付け処理含む）。

- DuckDB スキーマ定義 (`kabusys.data.schema`)
  - Raw / Processed / Feature / Execution 層のスキーマ方針に基づくDDLを実装。
  - Raw 層の主要テーブル DDL を定義:
    - `raw_prices`（日足データ、主キー (date, code)、数値チェック制約付き）
    - `raw_financials`（四半期財務、主キー (code, report_date, period_type)）
    - `raw_news`（記事保存テーブル）
    - `raw_executions`（約定テーブル定義の一部実装）
  - スキーマを用いた初期化を想定したモジュール。

- 研究（Research）モジュール (`kabusys.research`)
  - ファクター計算と特徴量探索を提供する研究向けユーティリティ群を実装。
  - Feature exploration (`kabusys.research.feature_exploration`)
    - 将来リターン計算 `calc_forward_returns`（複数ホライズン対応、SQL による一括取得）
    - IC（Information Coefficient）計算 `calc_ic`（スピアマンρ、ランク変換の実装を含む）
    - ファクター統計サマリー `factor_summary`、ランク付け `rank`
    - 標準ライブラリのみでの実装（pandas 等に依存しない設計）
  - Factor research (`kabusys.research.factor_research`)
    - Momentum / Volatility / Value 等の代表的ファクター計算関数を実装:
      - `calc_momentum`（mom_1m, mom_3m, mom_6m, ma200_dev）
      - `calc_volatility`（atr_20, atr_pct, avg_turnover, volume_ratio）
      - `calc_value`（per, roe、raw_financials から最新報告を結合）
    - DuckDB 上の `prices_daily` / `raw_financials` テーブルのみ参照する設計（本番 API へアクセスしない）。
  - 研究モジュールの公開 API を `kabusys.research.__all__` で整理（`zscore_normalize` はデータ統計ユーティリティより利用）。

- 基本的なモジュールスキャフォールド
  - `kabusys.execution.__init__` および `kabusys.strategy.__init__` をプレースホルダとして追加（後続の発注・戦略実装のためのエントリポイント）。

### 変更 (Changed)
- 初期リリースのため該当なし。

### 修正 (Fixed)
- 初期リリースのため該当なし。

### パフォーマンス (Performance)
- J-Quants の API 呼び出しに固定間隔レートリミッタを導入して API レート上限を遵守。
- ニュース保存・銘柄紐付けはチャンク化・単一トランザクションで実行し、DB オーバーヘッドを削減。
- 将来リターン計算等は複数ホライズンを一度の SQL で取得することでクエリ回数を削減。

### 信頼性・安全性 (Security & Reliability)
- RSS パーサは defusedxml を利用して XML 攻撃を軽減。
- RSS フェッチ時に SSRF 対策（スキーム検査、プライベートアドレス排除、リダイレクト先検証）を実装。
- API クライアントはリトライ・トークン自動リフレッシュを備え、ネットワーク/一時的エラーに強い設計。
- DB 保存は冪等性を考慮した UPSERT（ON CONFLICT DO UPDATE / DO NOTHING）を採用。

### 既知の制限 (Known limitations)
- 研究モジュールは外部ライブラリ（例: pandas）に依存しない純粋 Python 実装であるため、大規模データ処理の面で最適化余地がある。
- `kabusys.execution` / `kabusys.strategy` は初期スキャフォールドのみで、発注ロジックや売買戦略の実実装は今後のリリースで追加予定。
- 一部のスキーマ/DDL（例: raw_executions の定義）はコード断片で提示されており、追加カラムや制約の最終調整が必要。

注記
----
- このCHANGELOGはリポジトリの現在のコード内容から推測して作成しています。将来的な変更に応じて適宜更新してください。