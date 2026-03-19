# Changelog

すべての注記は Keep a Changelog の形式に従います。  
このファイルは、コードベースから推測できる変更点・リリース内容をまとめたものです。

全般:
- パッケージバージョンは src/kabusys/__init__.py の __version__ に従い v0.1.0 を初期リリースとしています。
- 本リリースは自動取引システムのコアモジュール（データ収集・加工・研究・シグナル生成・設定管理）を含む初期実装です。

## [Unreleased]
（現在差分なし）

## [0.1.0] - 2026-03-19

### Added
- パッケージ基本構成を追加
  - モジュール構成: kabusys.data, kabusys.research, kabusys.strategy, kabusys.execution（空パッケージ含む）、kabusys.config 等を提供。

- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml により検出）。
  - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
  - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - Settings クラスで主要設定をプロパティとして公開（必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - デフォルト設定: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH、LOG_LEVEL バリデーション、KABUSYS_ENV（development / paper_trading / live）判定ユーティリティ（is_live / is_paper / is_dev）。

- データ取得クライアント（kabusys.data.jquants_client）
  - J-Quants API クライアント実装（認証トークン取得、自動リフレッシュ、ページネーション対応）。
  - レート制限（120 req/min）を固定間隔スロットリングで遵守する RateLimiter を実装。
  - 再試行ロジック（指数バックオフ、最大 3 回、408/429/5xx 等を対象）、429 の Retry-After を尊重。
  - レスポンスの JSON デコードエラーハンドリング。
  - データ保存用ユーティリティ:
    - fetch_daily_quotes / save_daily_quotes（raw_prices へ冪等保存）
    - fetch_financial_statements / save_financial_statements（raw_financials へ冪等保存）
    - fetch_market_calendar / save_market_calendar（market_calendar へ冪等保存）
  - データ変換ユーティリティ `_to_float`, `_to_int` を実装し、安全に型変換。

- ニュース収集（kabusys.data.news_collector）
  - RSS フィード収集のユーティリティを実装（デフォルトソースに Yahoo Finance を含む）。
  - URL 正規化（トラッキングパラメータ除去、クエリソート、フラグメント除去）を実装。
  - defusedxml を用いた XML の安全パース、受信サイズ上限（10MB）、SSRF 対策やトラッキング除去等を考慮。
  - バルク挿入のチャンク化、冪等性（記事ID は正規化 URL のハッシュ）を考慮した保存設計。

- 研究用ファクター計算（kabusys.research.factor_research）
  - Momentum（1/3/6ヶ月リターン、MA200乖離）、Volatility（20日ATR、相対ATR、出来高比率、平均売買代金）、Value（PER, ROE）を計算する関数を実装。
  - DuckDB の SQL ウィンドウ関数を活用して効率的に計算（営業日欠損・ウィンドウ不足時の None ハンドリング）。

- 特徴量探索・解析（kabusys.research.feature_exploration）
  - 将来リターン計算 calc_forward_returns（1/5/21 日等のホライズン対応、SQL による一括取得）。
  - Information Coefficient（Spearman ρ）計算 calc_ic、rank、factor_summary の実装。
  - 外部依存パッケージに頼らず標準ライブラリで統計処理を実施。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールで算出した生ファクターを統合・正規化して features テーブルへ保存する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）適用。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ、日付単位の置換（トランザクションで原子性確保）。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し最終スコア final_score を計算、BUY / SELL シグナルを生成して signals テーブルへ書き込む generate_signals を実装。
  - デフォルト重み（momentum/value/volatility/liquidity/news）と閾値（0.60）を持つ。ユーザー指定の weights は検証・正規化して採用。
  - AI のレジームスコア集計による Bear 判定機能（サンプル不足時は判定を行わない）。
  - SELL 条件: ストップロス（-8%）、スコア低下。トレーリングストップや時間決済は未実装（将来的な拡張点として注記）。
  - 保有ポジション（positions テーブル）参照時の価格欠損回避ロジック、SELL 優先のポリシーを適用。
  - signals への日付単位置換をトランザクションで実装（ROLLBACK 失敗時は警告ログ）。

- パブリック API のエクスポート
  - kabusys.strategy.__init__ で build_features, generate_signals を公開。
  - kabusys.research.__init__ で主要研究関数群を公開。

### Changed
- （初期リリースのため変更履歴なし）

### Fixed
- （初期リリースのため修正履歴なし）

### Security
- ニュース XML 解析に defusedxml を採用して XML Bomb 等の攻撃を軽減。
- ニュース収集で受信サイズ上限を導入しメモリ DoS を軽減。
- RSS/URL 正規化でトラッキングパラメータ削除・スキーム検証等を実装し SSRF やトラッキングの影響を低減。
- J-Quants クライアントは認証トークンを自動リフレッシュする際に無限再帰を防ぐ設計（allow_refresh フラグ）。

### Notes / Known limitations / TODO
- _generate_sell_signals ではトレーリングストップ（peak_price が必要）や時間決済（保有日数制限）は未実装。positions テーブルに peak_price / entry_date を持たせる必要あり。
- research モジュールは pandas 等に依存せず純粋 Python + DuckDB SQL で記述しているため、大規模データでの最適化やメモリ効率は今後の改善余地がある。
- news_collector は既知 RSS ソースのデフォルトを含むが、ソース管理やフェイルオーバーの強化は今後の課題。
- DB スキーマ（テーブル名: raw_prices, raw_financials, market_calendar, prices_daily, features, ai_scores, positions, signals, raw_news など）はコードから推定される前提で実装されているため、実運用前にスキーマ整備が必要。
- settings の必須環境変数未設定時は ValueError を発生させるため、デプロイ時に .env を適切に用意すること。

---

もしリリースノートをより詳細なファイル単位の変更一覧（各関数・SQL の変更点やサンプル挙動）として展開したい場合は、対象とするモジュールや受け取りたい詳細レベルを教えてください。