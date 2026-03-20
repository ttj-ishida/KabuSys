# Changelog

すべての変更は Keep a Changelog のフォーマットに準拠しています。  
現在のパッケージバージョン: 0.1.0

---

## [0.1.0] - 2026-03-20 (Initial release)

### Added
- パッケージ構成
  - 新規パッケージ `kabusys` を追加。サブモジュール: `data`, `research`, `strategy`, `execution`, `monitoring`（`execution` は現時点では空の初期化のみ）。
  - パッケージバージョンは `kabusys.__version__ = "0.1.0"`。

- 環境設定 / 設定管理 (`kabusys.config`)
  - プロジェクトルート検出: `.git` または `pyproject.toml` を基準に自モジュール位置からルートを探索する `_find_project_root()` を実装。パッケージ配布後も CWD に依存せず .env 自動読み込みが可能。
  - `.env` パーサを実装: コメントや `export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープに対応する `_parse_env_line()`。
  - .env 読み込みロジック `_load_env_file()`:
    - 読み込み時に OS 環境変数を保護できる `protected` 機能。
    - `.env` と `.env.local` の読み込み優先順位を実装（OS 環境 > .env.local > .env）。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用）。
  - `Settings` クラスを提供し、環境変数からアプリ設定を取得するプロパティを実装（J-Quants トークン、kabu API パスワード、Slack、DB パス、環境 / ログレベルの検証など）。不正な `KABUSYS_ENV` / `LOG_LEVEL` の値は明示的にエラーを出す。
  - 必須環境変数取得ユーティリティ `_require()` を実装し、未設定時に明確なエラーメッセージを出力。

- データ取得 & 永続化（J-Quants クライアント） (`kabusys.data.jquants_client`)
  - J-Quants API クライアントを実装。
  - 固定間隔スロットリング方式のレートリミッタ `_RateLimiter`（120 req/min に対応）を導入。
  - HTTP リクエスト共通処理 `_request()`：
    - JSON パースの失敗検出と明示的な例外化。
    - 指数バックオフによるリトライ（最大 3 回）、対象ステータスコード（408, 429, 5xx）への再試行。
    - 401 受信時の ID トークン自動リフレッシュを 1 回だけ行う仕組み（無限再帰防止）。
    - ページネーション対応。
  - 認証ユーティリティ `get_id_token()`（リフレッシュトークンから ID トークン取得）。
  - データ取得関数: `fetch_daily_quotes()`, `fetch_financial_statements()`, `fetch_market_calendar()`（ページネーション対応）。
  - DuckDB への保存関数: `save_daily_quotes()`, `save_financial_statements()`, `save_market_calendar()`：
    - 挿入は冪等（ON CONFLICT DO UPDATE／DO NOTHING）で実行。
    - PK 欠損行はスキップしログに警告を出力。
    - `fetched_at` を UTC ISO 形式で記録し、データ取得時点をトレース可能にする。
  - 型変換ユーティリティ `_to_float()` / `_to_int()` を実装し、入力データの堅牢な変換を行う。

- ニュース収集 (`kabusys.data.news_collector`)
  - RSS フィード収集の基礎実装（デフォルトに Yahoo ビジネス RSS を含む）。
  - URL 正規化 `_normalize_url()` を実装:
    - スキーム/ホストの小文字化、トラッキングパラメータ（utm_ 等）の除去、フラグメント削除、クエリパラメータソート等。
  - セキュリティ・堅牢化:
    - XML のパースに defusedxml を利用（XML Bomb 等対策）。
    - HTTP/HTTPS 以外のスキーム拒否による SSRF の低減（設計方針に明記）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）を設定しメモリ DoS を防止。
  - 記事 ID を正規化した URL の SHA-256 で生成する方針、DB へのバルク挿入はチャンク化して実行。

- リサーチ / ファクター計算 (`kabusys.research`)
  - ファクター計算群（`kabusys.research.factor_research`）を実装:
    - `calc_momentum(conn, target_date)`：mom_1m/mom_3m/mom_6m、200日移動平均乖離率（ma200_dev）。
    - `calc_volatility(conn, target_date)`：20日 ATR（atr_20）、相対ATR（atr_pct）、20日平均売買代金（avg_turnover）、出来高比率（volume_ratio）。
    - `calc_value(conn, target_date)`：価格 / EPS に基づく PER、ROE（raw_financials から最新財務を取得）。
    - 各関数は DuckDB の `prices_daily` / `raw_financials` のみ参照し、結果は (date, code) をキーとする dict リストで返す設計。
  - 特徴量探索 / 評価ユーティリティ（`kabusys.research.feature_exploration`）:
    - `calc_forward_returns(conn, target_date, horizons)`：複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - `calc_ic(factor_records, forward_records, factor_col, return_col)`：スピアマンのランク相関（IC）を実装。データ不足時は None を返す。
    - `rank(values)`：同順位は平均ランクとして扱うランク化ユーティリティ（丸め対策あり）。
    - `factor_summary(records, columns)`：count/mean/std/min/max/median を算出する統計サマリー。
  - 収集済み関数は `kabusys.research.__init__` でエクスポート。

- 戦略（feature engineering / signal generation） (`kabusys.strategy`)
  - `feature_engineering.build_features(conn, target_date)`：
    - `research` モジュールの生ファクターを取得し統合。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）し ±3 でクリップ。
    - DuckDB の `features` テーブルへ日付単位での置換（トランザクション＋バルク挿入）を行い冪等性を担保。
  - `signal_generator.generate_signals(conn, target_date, threshold, weights)`：
    - `features` と `ai_scores` を統合して銘柄ごとにコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換・欠損値は中立 0.5 で補完するロジック。
    - デフォルトウェイトはドキュメントに沿った比率で提供。ユーザー指定の weights は検証・補完・再スケールされる。
    - Bear レジーム検出（ai_scores の regime_score 平均が負の場合、かつサンプル数閾値満たす）で BUY シグナルを抑制。
    - BUY の閾値デフォルトは 0.60。SELL の判定ではストップロス（-8%）およびスコア低下を実装。
    - `signals` テーブルへ日付単位での置換（トランザクションで原子性確保）を実行。SELL 対象は BUY から除外する優先ポリシー。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Security
- XML パースに defusedxml を採用（news_collector）。
- RSS/URL 処理でトラッキングパラメータの除去・スキーム検査・受信サイズ制限などを実装し SSRF / DoS 対策を考慮。

### Known limitations / Notes
- execution サブパッケージは初期化のみで発注ロジックは含まれていません（将来的な実装予定）。
- signal_generator の SELL 判定に記載のうち「トレーリングストップ」「時間決済」は未実装（positions テーブルに peak_price / entry_date が必要）。
- news_collector の記事 ID 生成・銘柄紐付け（news_symbols）等の詳細実装は設計方針に記載されているが、実装の一部（ID 生成や紐付けロジックの実装詳細）は将来的な拡張を想定。
- research モジュールは外部依存（pandas 等）を使わない実装になっているため、大量データ処理での性能チューニングは今後の改善余地あり。
- J-Quants クライアントはリトライ・レート制限等を備えているが、実稼働ではさらに堅牢なエラーハンドリング（監視・メトリクス・アラート）を推奨。
- 環境変数自動読み込みはプロジェクトルート検出に依存する。配布後に期待通り動作しない場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定して手動ロードへ切り替え可能。

---

今後のリリースでは、execution 層の発注実装、news_collector の記事→銘柄マッチング強化、追加のリスク管理ルール（トレーリングストップ等）、パフォーマンス改善（大規模データ向けの最適化）を予定しています。