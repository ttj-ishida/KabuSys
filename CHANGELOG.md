# Changelog

すべての注目すべき変更はこのファイルに記載します。
フォーマットは Keep a Changelog に準拠します。
このプロジェクトはセマンティックバージョニングに従います。

## [Unreleased]

（現時点では未リリースの修正・追加はありません）

## [0.1.0] - 2026-03-19

初回公開リリース。主要な機能はデータ収集・保存、ファクター計算、特徴量生成、シグナル生成、環境設定まわりのユーティリティを含みます。

### Added
- パッケージ基盤
  - パッケージ名 kabusys とバージョン 0.1.0 を設定（src/kabusys/__init__.py）。
  - 公開 API を整理（strategy.build_features, strategy.generate_signals 等を __all__ にエクスポート）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動ロードする機構を追加。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - プロジェクトルート検出は .git または pyproject.toml を基準に実装（CWD 非依存）。
  - .env 行パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート、エスケープ対応）。
  - 環境変数の必須チェック _require と Settings クラスを提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等のプロパティを追加。
    - DUCKDB_PATH / SQLITE_PATH の既定値と Path 返却。
    - KABUSYS_ENV / LOG_LEVEL の検証（許可値セット・例外処理）。
    - is_live / is_paper / is_dev の便利プロパティ。

- データ取得・保存：J-Quants クライアント（src/kabusys/data/jquants_client.py）
  - J-Quants API クライアントを実装（ページネーション対応）。
  - 固定間隔スロットリングによるレート制御（120 req/min）を実装する RateLimiter。
  - リトライロジック（指数バックオフ、最大 3 回）と HTTP ステータスに基づく再試行ポリシーを実装（408, 429, 5xx 等）。
  - 401 受信時にトークンを自動リフレッシュして 1 回リトライする仕組みを実装。
  - fetch_daily_quotes / fetch_financial_statements / fetch_market_calendar を提供。
  - DuckDB への冪等保存ユーティリティを提供（save_daily_quotes, save_financial_statements, save_market_calendar）。
    - INSERT ... ON CONFLICT DO UPDATE を用いた重複排除（冪等性）。
  - データ整形ヘルパー _to_float / _to_int を実装。
  - 取得時刻（fetched_at）は UTC ISO8601 で記録し、Look-ahead バイアス可視化を支援。

- ニュース収集（src/kabusys/data/news_collector.py）
  - RSS フィードからニュース記事を収集する機能（デフォルトソースに Yahoo Finance を設定）。
  - URL 正規化ユーティリティを追加（トラッキングパラメータ除去、スキーム/ホスト小文字化、フラグメント削除、クエリソート）。
  - セキュリティ対策の実装：
    - defusedxml を用いた XML パース（XML Bomb 等の防御）。
    - 受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）によるメモリ DoS 対策。
    - トラッキングパラメータ除去、記事ID の SHA-256 ハッシュ化（先頭32文字）による冪等化設計。
    - バルク INSERT のチャンク処理で SQL 長・パラメータ数を抑制。
  - raw_news / news_symbols へ保存する際の設計方針を記載（冪等保存、URL 正規化等）。

- リサーチ用ユーティリティ（src/kabusys/research）
  - ファクター計算（factor_research.py）
    - calc_momentum: 1M/3M/6M リターン・MA200 乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: target_date 以前の最新財務データから PER / ROE を計算（EPS が 0 の場合を考慮）。
    - 各関数は prices_daily / raw_financials のみを参照し、本番 API へのアクセスは行わない設計。
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）を実装。サンプル不足時に None を返す。
    - rank / factor_summary: ランク付けと基本統計量（count/mean/std/min/max/median）を算出。
    - 外部依存（pandas 等）に依存しない純粋 Python + DuckDB 実装。

- 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date) を実装。
    - research モジュールの calc_momentum / calc_volatility / calc_value を利用して生ファクターを取得。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で置換（DELETE + バルク INSERT、トランザクション）により冪等性を担保。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみを利用する方針を明記。

- シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装。
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - Z スコアを sigmoid で [0,1] に変換、欠損コンポーネントは中立値 0.5 で補完。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を提供し、ユーザ指定は検証・正規化して合計を 1 に再スケール。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY を抑制。
    - SELL 条件（ストップロス -8%、score が閾値未満）を実装。トレーリングストップ・時間決済は未実装（コメントで記載）。
    - signals テーブルへ日付単位置換で書き込み（トランザクション、冪等性）。
    - price 欠損時の SELL 判定スキップや features 未登録保有銘柄の扱い（score=0.0 と見なす）を明示。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- news_collector で defusedxml を使用して XML パースを安全化。
- RSS 取得時の受信バイト数制限や URL 正規化、HTTP スキーム制限等により SSRF / DoS リスクを低減。

---

注記:
- DuckDB への INSERT は可能な限り冪等（ON CONFLICT / DELETE+INSERT）を採用し、再実行性を重視しています。
- 多くのモジュールで「ルックアヘッドバイアス」を防ぐ方針を採用しており、target_date 時点のデータのみ参照する設計になっています。
- 本リリースでは外部発注 API（kabu/station への実際の注文発行）は実装層と分離され、strategy 層は発注層に依存しないことを前提としています。