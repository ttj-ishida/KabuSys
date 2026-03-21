# Changelog

すべての注記は Keep a Changelog の形式に従い、慣習的に重要な変更点を記載します。  
このファイルはパッケージのソースコードから推測した変更点・機能一覧を基に作成しています。

全てのバージョン: https://github.com/your-repo/kabusys (実際のリポジトリ URL に置換してください)

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 2026-03-21

初回リリース。日本株自動売買システムのコアモジュール群を実装しています。主な追加点・仕様は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ名: kabusys（version 0.1.0）
  - エクスポート: data, strategy, execution, monitoring を公開（src/kabusys/__init__.py）

- 設定管理（src/kabusys/config.py）
  - .env ファイルと環境変数からの自動ロード機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env ファイルのパーサ実装（export KEY=val、シングル/ダブルクォート、インラインコメント、エスケープ対応）。
  - .env 読み込み時の protected キー概念（OS 環境変数を上書きしない挙動）をサポート。
  - Settings クラスでアプリ設定をプロパティとして提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須値として取得する _require()。
    - KABU_API_BASE_URL, DB パス（DUCKDB_PATH, SQLITE_PATH）のデフォルト値。
    - 環境（KABUSYS_ENV）のバリデーション（development, paper_trading, live）。
    - LOG_LEVEL のバリデーション（DEBUG, INFO, WARNING, ERROR, CRITICAL）と is_live/is_paper/is_dev 判定プロパティ。

- データ取得・永続化（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装。
  - レート制限（120 req/min）を守る固定間隔スロットリング実装（内部 RateLimiter）。
  - HTTP リトライ（指数バックオフ、最大3回）・429/408/5xx のリトライ対応。
  - 401 受信時にリフレッシュトークンから ID トークンを自動取得して 1 回リトライするロジック。
  - ページネーション対応の fetch_* API:
    - fetch_daily_quotes（株価日足）
    - fetch_financial_statements（四半期財務）
    - fetch_market_calendar（JPX カレンダー）
  - DuckDB への保存関数（冪等）:
    - save_daily_quotes（raw_prices テーブル、ON CONFLICT DO UPDATE）
    - save_financial_statements（raw_financials テーブル、ON CONFLICT DO UPDATE）
    - save_market_calendar（market_calendar テーブル、ON CONFLICT DO UPDATE）
  - データ型変換ユーティリティ: 安全な _to_float / _to_int 実装（空値・不正値は None）

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードから記事を収集し raw_news に保存する処理の骨格。
  - セキュリティ設計:
    - defusedxml を用いた XML パース（XML Bomb 等対策）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10 MB）。
    - URL の正規化（トラッキングパラメータ除去、スキーム/ホストの小文字化、フラグメント除去）。
    - 記事 ID を正規化 URL の SHA-256（先頭32文字）で生成して冪等性を確保。
    - SSRF 対策やトラッキングパラメータプレフィックス除去の方針が明記。
  - デフォルト RSS ソース（例: Yahoo Finance）とバルク挿入チャンク制御。

- 研究・ファクター計算（src/kabusys/research/*.py）
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、200日 MA 乖離、データ不足時は None）
    - calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比）
    - calc_value（PER, ROE：raw_financials を参照、最新財務データを取得）
    - DuckDB の SQL + ウィンドウ関数を用いた実装
  - feature_exploration:
    - calc_forward_returns（デフォルト horizons=[1,5,21]、まとめて 1 クエリで取得）
    - calc_ic（Spearman ランク相関（Information Coefficient））
    - rank（同順位は平均ランク、丸め対策で round(v, 12) を使用）
    - factor_summary（count/mean/std/min/max/median の統計サマリー）
  - research パッケージの __all__ を整備し、zscore_normalize（data.stats 由来）等を公開

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date): research モジュールから得た生ファクターを結合・ユニバースフィルタ・Z スコア正規化し features テーブルへ UPSERT（日付単位で置換）する処理を実装。
  - ユニバースフィルタ:
    - 最低株価: 300 円
    - 20日平均売買代金 >= 5 億円
  - 正規化: 指定カラムを zscore_normalize で正規化し ±3 でクリップ（外れ値抑制）
  - 原子性: トランザクション開始→DELETE（date）→バルク INSERT→COMMIT（例外時は ROLLBACK）

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - スコア変換: Z スコアにシグモイド変換を適用し、None は中立 0.5 で補完。
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10。weights 引数は検証・正規化（合計が 1 に調整）される。
    - Bear レジーム判定: ai_scores の regime_score 平均が負（かつサンプル >= 3）なら BUY シグナル抑制。
    - BUY シグナル: final_score >= threshold（Bear 時は抑制）。
    - SELL シグナル（エグジット判定）:
      - ストップロス: 終値/avg_price - 1 < -8%（最優先）
      - スコア低下: final_score < threshold
      - 未実装だが設計書にトレーリングストップ・時間決済の記載あり（positions に peak_price/entry_date が必要）
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）

### Changed
- （初回リリースのため変更履歴はありません）

### Fixed
- （初回リリースのため修正履歴はありません）

### Security
- ニュース収集で defusedxml を採用、受信サイズ制限、URL 正規化など SSRF/DoS/XML 攻撃への対策を明記。
- J-Quants クライアントはリフレッシュトークン処理時に無限再帰を回避するため allow_refresh フラグを導入。

### Known limitations / Notes
- 一部機能は「設計書に記載されているが未実装（TODO）」として明記されています:
  - signal_generator のトレーリングストップ・時間決済（positions に peak_price / entry_date が必要）
  - ニュースと銘柄の紐付け処理（news_symbols 等） の具象的実装はソースに示唆があるが、この抜粋では未完。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装を目指している（標準ライブラリ + DuckDB のみ）。
- J-Quants API の最大レートやリトライポリシーはコード内定数で調整可能（_RATE_LIMIT_PER_MIN, _MAX_RETRIES 等）。

---

作者: kabusys コードベース（ソース解析に基づく CHANGELOG）  
注: 実際のコミット履歴やリリース日、リリースノートは開発リポジトリの履歴に基づいて調整してください。