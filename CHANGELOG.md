# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングに従います。

なお、この CHANGELOG は提供されたコードベースから実装内容を推測して作成しています。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-20
初期リリース。以下の主要機能・モジュールを追加。

### Added
- パッケージ初期化
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。__all__ に主要サブパッケージを公開（data, strategy, execution, monitoring）。

- 環境設定 / config
  - Settings クラスを追加し、アプリケーション設定を環境変数から取得する API を提供。
  - 必須設定をチェックする _require() を実装（未設定時は ValueError を送出）。
  - .env 自動読み込み機能を実装:
    - プロジェクトルートを .git または pyproject.toml から探索（CWD 非依存）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサを実装し、export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント（スペース前の `#`）等に対応。
  - 設定項目（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを Path として返す）
    - KABUSYS_ENV 検証（development / paper_trading / live のみ許容）
    - LOG_LEVEL 検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - settings インスタンスをモジュールレベルで公開

- Data 層: J-Quants クライアント（data/jquants_client.py）
  - J-Quants API から株価・財務・マーケットカレンダーを取得するクライアントを実装。
  - レート制限ガード（固定間隔スロットリング）を実装（120 req/min）。
  - リトライロジック（指数バックオフ、最大試行回数、408/429/5xx 対応）を実装。
  - 401 受信時はリフレッシュトークンから ID トークンを再取得して再試行する仕組みを実装（無限再帰を防止）。
  - ページネーション対応（pagination_key を利用して取得継続）。
  - fetch_… 系関数を実装:
    - fetch_daily_quotes, fetch_financial_statements, fetch_market_calendar
  - DuckDB への保存用ユーティリティを実装（冪等性を考慮）:
    - save_daily_quotes: raw_prices テーブルへ ON CONFLICT DO UPDATE で保存
    - save_financial_statements: raw_financials テーブルへ ON CONFLICT DO UPDATE
    - save_market_calendar: market_calendar テーブルへ ON CONFLICT DO UPDATE
  - データ変換ユーティリティ:
    - _to_float, _to_int（安全に None を返す）

- Data 層: ニュース収集（data/news_collector.py）
  - RSS フィードから記事を収集して raw_news に保存するための基盤を追加（設計に基づく実装）。
  - URL 正規化関数を実装（トラッキングパラメータ削除、スキーム/ホスト小文字化、クエリソート、フラグメント削除）。
  - defusedxml を用いた XML パース方針、HTTP(S) スキーム検査、受信サイズ上限（MAX_RESPONSE_BYTES = 10MB）などの安全対策を明示。
  - RSS ソースのデフォルト（Yahoo Finance ビジネス）を定義。
  - バルク INSERT のチャンク処理や ID の一意化（docstring に SHA-256 ハッシュでの記事ID生成が記載）など冪等保存の方針を記述。

- Research 層
  - ファクター計算（research/factor_research.py）を実装:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）
    - calc_volatility: 20 日 ATR（atr_20 / atr_pct）、20 日平均売買代金、volume_ratio
    - calc_value: PER / ROE（raw_financials と prices_daily の組み合わせ）
    - カレンダーバッファを取り営業日欠損に耐える設計
  - 特徴量探索ユーティリティ（research/feature_exploration.py）を実装:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得
    - calc_ic: スピアマンのランク相関（Information Coefficient）を計算
    - rank: 同順位は平均ランクとするランク変換（丸めで ties を安定化）
    - factor_summary: 各ファクターの基本統計量（count/mean/std/min/max/median）
  - research パッケージの public API を exports に追加（calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。

- Strategy 層
  - 特徴量エンジニアリング（strategy/feature_engineering.py）を実装:
    - research で計算された生ファクターを統合して features テーブルに保存する build_features(conn, target_date)
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用
    - 正規化（zscore_normalize を利用）、±3 でクリップ、日付単位の置換（DELETE + INSERT）で冪等性を担保
    - DuckDB トランザクションによる原子性の確保、ROLLBACK の失敗はログ警告
  - シグナル生成（strategy/signal_generator.py）を実装:
    - features と ai_scores を統合し final_score を算出、BUY/SELL シグナルを生成して signals テーブルへ保存（generate_signals）
    - スコア成分: momentum/value/volatility/liquidity/news（デフォルト重みを持つ）
    - Z スコアをシグモイド変換し [0,1] にマッピング、欠損値は中立 0.5 で補完
    - 重みの入力検証と正規化（合計が 1 になるよう再スケール）
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）による BUY 抑制
    - SELL 条件（実装済み）:
      - ストップロス: 終値/avg_price - 1 < -8%
      - スコア低下: final_score が threshold 未満
      - （未実装）トレーリングストップ / 時間決済は将来対応予定と注記
    - signals テーブルへの日付単位置換をトランザクションで実行（冪等）
    - ロギング（INFO/DEBUG/警告）による動作可視化

- 共通ユーティリティ
  - zscore_normalize（kabusys.data.stats から利用）を前提にしたワークフロー統合（research <-> strategy）。
  - DuckDB を主要なデータストアとして使用し、SQL ウィンドウ関数等を活用した実装。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Security
- ニュース XML のパースに defusedxml を利用する方針を明記し、RSS パースにおける XML 攻撃対策を行っている（実装済みのユーティリティや docstring により確認可能）。
- API クライアントでのトークン取り扱いやネットワークリトライで適切に例外処理を行い、無限ループや暴発を回避する設計。

### Notes / Known limitations
- execution パッケージは空の __init__.py のみで、実際の注文発注ロジック（kabu API への発注）は含まれていない（分離された execution 層での実装が想定される）。
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は未実装であり、positions テーブルに peak_price / entry_date 等の追加カラムが必要。
- news_collector の docstring は詳細な設計（SHA-256 による記事ID生成等）を示しているが、提供コード断片では一部関数（RSS フェッチ本体や DB への INSERT の詳細）が省略されている可能性があるため、完全実装は別モジュール/箇所で行われる想定。
- J-Quants クライアントはネットワーク I/O に urllib を直接使用する実装で、ユーザーはタイムアウトや例外の取り扱いに注意すること。

---

If you need a translated/English version of this changelog, release notes for a specific module, or a more granular changelog per file,教えてください。