# CHANGELOG

すべての変更は Keep a Changelog のフォーマットに従って記載しています。主要な追加・機能実装をコードベースから推測してまとめています。

## [Unreleased]

### Added
- ドキュメント文字列とモジュール構成を整理し、パッケージの公開 API を明示。
  - src/kabusys/__init__.py にてパッケージ版のエントリポイントとバージョン管理（__version__ = "0.1.0"）を追加。

- 環境変数／設定管理 (src/kabusys/config.py)
  - .env / .env.local をプロジェクトルート（.git または pyproject.toml を探索）から自動読み込みする仕組みを実装。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env のパースを厳密化：コメント行・export プレフィックス・クォートやエスケープ文字対応・インラインコメント処理などに対応するパーサを実装。
  - .env.local は .env の値を上書きでき、OS 環境変数は保護（protected）される。
  - 必須環境変数チェック（_require）と Settings クラスを実装し、J-Quants / kabu / Slack / DB パス等の設定プロパティを提供。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（許容値チェック）と is_live / is_paper / is_dev のユーティリティを追加。

- データ収集クライアント: J-Quants API クライアント (src/kabusys/data/jquants_client.py)
  - API 呼び出しユーティリティを実装。固定間隔のレートリミッタ（120 req/min）、指数バックオフによるリトライ、429 の Retry-After 考慮、ネットワークエラーの再試行などを実装。
  - 401 Unauthorized を検知した際のリフレッシュトークンを使ったトークン自動更新と 1 回の再試行ロジックを実装。
  - ページネーション対応の fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を実装。
  - DuckDB への保存用 save_daily_quotes / save_financial_statements / save_market_calendar を実装し、ON CONFLICT（冪等）で重複を排除する保存処理を提供。
  - 型変換ユーティリティ (_to_float, _to_int) を実装し、入力の堅牢性を高めた。

- ニュース収集モジュール (src/kabusys/data/news_collector.py)
  - RSS から記事を収集して raw_news に保存する処理を実装するためのユーティリティを追加。
  - URL 正規化（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）により記事 ID を安定化させ、SHA-256 ハッシュ（先頭 32 文字）で冪等な記事 ID を生成する設計を導入。
  - defusedxml を用いた XML パース・受信サイズ制限・HTTP スキーム検査・SSRF 対策など、セキュリティを考慮した設計方針を明記。
  - 一度に処理する INSERT チャンクサイズ制御を導入。

- リサーチ／ファクター計算 (src/kabusys/research/*.py)
  - ファクター計算モジュールを実装（calc_momentum, calc_volatility, calc_value）。
    - Momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日移動平均乖離率）を計算。データ不足時は None を返す。
    - Volatility: 20 日 ATR（atr_20）および相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算。
    - Value: raw_financials から最新の財務データを取得して PER / ROE を計算（EPS=0 や欠損時は None）。
  - 研究補助ユーティリティを実装（feature_exploration.py）。
    - 将来リターン計算（calc_forward_returns）: 複数ホライズン（デフォルト 1/5/21 営業日）をサポートし、1 クエリでまとめて取得。
    - IC（Information Coefficient）計算（calc_ic）: スピアマンのランク相関（ρ）を算出し、サンプル不足時や分散ゼロ時には None を返す。
    - ランク変換ユーティリティ（rank）やファクター統計サマリ（factor_summary）を追加。
  - 外部依存を最小化し、DuckDB のみ参照する設計（本番口座や発注 API にアクセスしない）を明記。

- 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールで計算された生ファクターを取りまとめ、ユニバースフィルタ（最低株価・最低平均売買代金）を適用、Z スコアで正規化（zscore_normalize を利用）および ±3 でクリップして features テーブルへ UPSERT する処理（build_features）を実装。
  - DuckDB トランザクションを使った日付単位の置換（DELETE + bulk INSERT）で処理の冪等性・原子性を確保。
  - ルックアヘッドバイアス回避方針を明示（target_date 時点のデータのみ使用）。

- シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して最終スコア final_score を算出し、BUY / SELL シグナルを生成して signals テーブルへ保存する処理（generate_signals）を実装。
  - コンポーネントスコア（momentum / value / volatility / liquidity / news）の計算ロジックを実装（シグモイド変換や PER に基づく変換など）。
  - 重み合成ではデフォルト値を用意し、ユーザー指定 weights を検証・補完・再スケールして扱う実装。
  - Bear レジーム判定（AI の regime_score の平均が負かつサンプル数条件）による BUY 抑制を実装。
  - 保有ポジションに対するエグジット判定（stop-loss と score 下落）を実装し、SELL シグナル生成ロジックを追加。
  - signals テーブルへの日付単位置換（トランザクション + bulk INSERT）で冪等性を確保。
  - SELL 優先ポリシー（SELL 対象を BUY から除外してランク付け）を採用。

- モジュールの公開 API を整備（src/kabusys/strategy/__init__.py、src/kabusys/research/__init__.py）
  - 主要関数を __all__ で明示的に公開。

### Changed
- なし（初期実装/追加のみと推測）。

### Fixed
- なし（初期実装/追加のみと推測）。

### Security
- news_collector: defusedxml の利用、受信サイズ上限、URL スキームチェック、追跡パラメータ除去等を採用して潜在的な攻撃ベクトル（XML Bomb / SSRF / DoS）へ対策。
- jquants_client: 認証トークンの安全なリフレッシュとキャッシュ管理、ネットワークや HTTP エラーに対する堅牢なリトライロジックを実装。

---

## [0.1.0] - 2026-03-20

初回公開リリース相当（コードベースの現状を基に推測）。上記 Unreleased の内容をベースに初期機能群を提供。

### Added
- パッケージ基本情報（バージョン）。
- 環境設定管理（.env 自動読み込み・Settings）。
- J-Quants API クライアント（取得／保存／リトライ／レート制御）。
- RSS ニュース収集ユーティリティ（正規化・セキュリティ対策）。
- DuckDB を用いたデータ保存・冪等処理。
- リサーチ用ファクター計算（Momentum / Volatility / Value）と探索ユーティリティ（forward returns / IC / summary）。
- 特徴量構築処理（Z スコア正規化・ユニバースフィルタ・features テーブル更新）。
- シグナル生成（final_score 計算、BUY/SELL 判定、signals テーブル更新）。
- 主要モジュールの公開 API を整理。

### Notes
- 多くの処理は DuckDB のテーブル（prices_daily / raw_financials / features / ai_scores / positions / signals / raw_prices / raw_financials / market_calendar / raw_news 等）を前提としているため、実行前にスキーマ整備が必要。
- 一部機能（例: positions テーブルに必要な peak_price / entry_date を用いるトレーリングストップや時間決済の自動処理）は未実装として記載あり（将来的な拡張対象）。
- settings から取得する必須環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。README/.env.example の整備が推奨される。

もし CHANGELOG に追記してほしい形式や、あるいは「リリース日を非公開にしたい」「Unreleased を消して 0.1.0 のみとしたい」といった希望があれば指示ください。