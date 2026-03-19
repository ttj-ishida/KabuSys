CHANGELOG
=========

すべての注目すべき変更はここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  
現在のパッケージバージョン: 0.1.0

Unreleased
----------

（なし）

0.1.0 - 2026-03-19
------------------

Added
- 初回リリース: KabuSys 日本株自動売買システムの基本コンポーネントを追加。
- パッケージ初期化
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定、公開モジュールを限定してエクスポート（data, strategy, execution, monitoring）。
- 設定 / 環境変数管理（src/kabusys/config.py）
  - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト時等に有用）。
  - .env パースは export 構文やクォート、インラインコメント、エスケープを考慮。
  - Settings クラスを提供し、必須環境変数の検査（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）・デフォルト値・値検証（KABUSYS_ENV, LOG_LEVEL）・ユーティリティプロパティ（is_live / is_paper / is_dev）を提供。
  - データベースパスの既定値（DUCKDB_PATH, SQLITE_PATH）を Path 型で扱う。
- データ取得・保存（src/kabusys/data/）
  - J-Quants API クライアント（src/kabusys/data/jquants_client.py）
    - レート制限 (120 req/min) を守る固定間隔スロットリング実装（_RateLimiter）。
    - HTTP リクエストラッパーで指数バックオフ付きリトライ（最大 3 回）、408/429/5xx に対応。
    - 401 受信時はリフレッシュトークンを使った ID トークン再取得を自動で行い 1 回リトライ。
    - ページネーション対応の fetch_* 関数 (fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar) を実装。
    - DuckDB への冪等保存関数（save_daily_quotes, save_financial_statements, save_market_calendar）を実装。ON CONFLICT を使った更新／挿入で重複を排除。
    - レスポンス parse/型変換ユーティリティ (_to_float/_to_int)、fetched_at を UTC で記録（Look-ahead bias を考慮）。
  - ニュース収集モジュール（src/kabusys/data/news_collector.py）
    - RSS フィードからの記事収集および前処理を想定した実装（URL 正規化、トラッキングパラメータ除去、content 前処理等）。
    - defusedxml を用いた XML パースで XML Bomb 等の対策を考慮。
    - レスポンスサイズ上限（10MB）や URL の安全性チェックなど DoS/SSRF 対策の設計方針を反映。
    - デフォルト RSS ソース（Yahoo Finance のビジネスカテゴリ）を設定。
- 研究用モジュール（src/kabusys/research/）
  - ファクター計算群（src/kabusys/research/factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離率を計算。データ不足時の扱いを明確化。
    - calc_volatility: 20 日 ATR（true range の取り扱い注意）、avg_turnover、volume_ratio を計算。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS=0 の扱いは None）。
    - DuckDB 上の prices_daily / raw_financials を前提とした SQL ベースの実装。
  - 探索・評価ユーティリティ（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）に対する将来リターンを一括取得する SQL 実装。
    - calc_ic: スピアマンのランク相関（IC）を計算。データ不足時（<3 件）は None を返す。
    - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量集計を提供。外部依存なし（pandas 等を使わない）。
  - research パッケージの __all__ に主要 API を登録。
- 戦略（src/kabusys/strategy/）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research モジュールの生ファクターを取り込み、ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップして外れ値影響を緩和。
    - features テーブルへの日付単位 UPSERT（DELETE + INSERT）の原子操作を実装（トランザクション使用、ROLLBACK 対応）。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換・重み付けで final_score を算出（デフォルト重みは StrategyModel.md に基づく）。
    - Bear レジーム検出ロジック（regime_score の平均が負かつサンプル数閾値以上で Bear と判定）により BUY を抑制。
    - BUY: final_score >= デフォルト閾値 0.60（閾値・重みは引数で上書き可能。重みは検証/正規化される）。
    - SELL（エグジット）: ストップロス（-8%）、スコア低下（threshold 未満）を実装。positions と prices_daily を参照し、保有ポジションに対する判定を行う。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）。
- 共通実装上の配慮
  - 可能な限り冪等性を確保（DB 保存やテーブル置換処理で DELETE+INSERT / ON CONFLICT を利用）。
  - ルックアヘッドバイアス回避（target_date 時点のデータのみを使用、fetched_at の記録）。
  - 外部 API（発注等）への直接依存を持たない設計（strategy 層は signals テーブルを書くだけ）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- news_collector で defusedxml を採用、RSS パースにおける XML 攻撃対策を明示。
- RSS 受信バイト上限や URL のスキーム検査等、外部入力に対する安全対策を設計に反映。

Deprecated / Removed
- （初回リリースのため該当なし）

Notes / Known limitations
- generate_signals のエグジット条件ではトレーリングストップ（peak_price が必要）や時間決済（保有日数）など一部ロジックは未実装（コード内に注記）。将来的な拡張が必要。
- execution パッケージは present だが発注実装（kabu API 経由の実行層）はこのリリースでは含まれていない。signals テーブルを経由して外部発注層で実行する想定。
- news_collector の実際の RSS フィード取得 / DB 保存処理の細部（チャンク処理・ハッシュ生成など）は設計方針を示しており、運用／微調整が必要な箇所がある。
- jquants_client の _request は urllib を用いた同期実装。大量並列化時のスループット制御や非同期対応は今後の検討対象。

Required environment variables (主なもの)
- JQUANTS_REFRESH_TOKEN (必須)
- KABU_API_PASSWORD (必須)
- SLACK_BOT_TOKEN (必須)
- SLACK_CHANNEL_ID (必須)
- KABUSYS_ENV (デフォルト: development; 有効値: development, paper_trading, live)
- LOG_LEVEL (デフォルト: INFO; 有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL)
- DUCKDB_PATH / SQLITE_PATH（デフォルトパスあり）

開発／運用メモ
- .env/.env.local の自動読み込みはプロジェクトルートを基準に行うため、パッケージ配布後でも CWD に依存せず動作する設計になっています。テスト等で自動読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB スキーマ（raw_prices, raw_financials, prices_daily, features, ai_scores, positions, signals, market_calendar など）の準備が前提です。スキーマ定義は別途ドキュメントで提供する想定です。

今後の予定（例）
- execution 層の実装（kabu ステーション API 経由での発注・約定管理）
- signals → 実際発注の統合テスト・安全ガードの追加
- ニュース紐付け（news_symbols）・AI スコア生成パイプラインの実装
- 非同期取得やバッチ並列化によるデータ収集の性能改善

--- 

この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やマイルストーンに合わせて調整してください。