# Changelog

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルはリポジトリ内の現行コードベースから推測して作成した初期リリースの変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-22

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys、バージョン 0.1.0

- 環境変数 / 設定管理
  - 環境変数を .env / .env.local から自動読込する機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
  - プロジェクトルート検出: __file__ を基点に .git または pyproject.toml を探索して自動ロードの基準に使用。
  - .env パーサ実装:
    - 空行・コメント行の無視
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ考慮
    - クォートなしの行におけるインラインコメント処理（直前がスペース/タブの場合に # をコメントとして扱う）
  - 環境変数読み込みの優先順位: OS 環境 > .env.local > .env
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）をプロパティ経由で取得。既定値・バリデーション付き:
    - KABUSYS_ENV の有効値: development / paper_trading / live
    - LOG_LEVEL の有効値: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - DB パスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"

- 戦略（strategy）モジュール
  - feature_engineering.build_features(conn, target_date)
    - research で計算済みの生ファクター（mom, vol, val）を取得して正規化（Z スコア）、±3 でクリップし、features テーブルへ日付単位で UPSERT（トランザクションで原子性保証）。
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
    - Z スコア正規化対象カラムを明示（mom_1m, mom_3m, atr_pct, volume_ratio, ma200_dev）。
  - signal_generator.generate_signals(conn, target_date, threshold=0.60, weights=None)
    - features と ai_scores を統合して各コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算。
    - コンポーネントの補完ポリシー: 欠損値は中立値 0.5 で補完。
    - final_score の重み付けとリスケール（デフォルト重みを採用しつつ、ユーザ指定の weights を検証・マージ）。
    - Bear レジーム検知（ai_scores の regime_score 平均 < 0 かつサンプル数 >= 3 の場合）により BUY シグナルを抑制。
    - BUY 閾値デフォルト 0.60。
    - SELL（エグジット）判定: ストップロス（-8%）優先、final_score が閾値未満なら SELL。
    - signals テーブルへ日付単位で置換挿入（トランザクションで原子性保証）。

- リサーチ（research）モジュール
  - factor_research:
    - calc_momentum(conn, target_date): mom_1m, mom_3m, mom_6m, ma200_dev を計算。
    - calc_volatility(conn, target_date): atr_20, atr_pct, avg_turnover, volume_ratio を計算。
    - calc_value(conn, target_date): target_date 以前の最新財務情報（raw_financials）と prices_daily を用いて PER, ROE を計算。
    - 各関数は prices_daily / raw_financials のみ参照し、本番 API にはアクセスしない方針。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 各銘柄の将来リターンを計算（LEAD を使用）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman ランク相関（IC）を計算。サンプルが 3 未満の場合は None を返す。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
    - rank(values): 同順位は平均ランクで処理（round で数値の丸めを行い ties を扱う）。
  - 研究モジュールは標準ライブラリのみで実装（pandas 等に依存しない）。

- データ / スキーマ連携（推定）
  - DuckDB を想定したテーブル参照/操作が随所にある（例: prices_daily, features, ai_scores, raw_financials, positions, signals, market_calendar, market_regime）。
  - zscore_normalize は kabusys.data.stats から利用。

- バックテスト（backtest）フレームワーク
  - engine.run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
    - 本番 DB から指定日付範囲のデータをインメモリ DuckDB にコピーしてバックテストを実行（signals / positions 等を汚染しない）。
    - 日次ループ: 前日シグナルを当日始値で約定 → positions テーブルへ書き戻し → 終値で時価評価 → generate_signals を実行 → 発注リスト組成。
    - positions テーブルはシミュレータの状態を書き戻すために使用（generate_signals の SELL 判定依存）。
  - simulator.PortfolioSimulator
    - 擬似約定ロジック（SELL を先に処理、SELL は保有全量をクローズ）。
    - スリッページ・手数料モデルと約定価格計算（BUY: entry_price = open * (1+slippage)、SELL: exit_price = open * (1 - slippage)）。
    - commission は約定金額 × commission_rate。
    - BUY 時に手数料込みで買えなくなった場合は株数を再計算。
    - mark_to_market で終値評価、終値欠損時は 0 と評価して WARNING ログ出力。
  - backtest.metrics.calc_metrics
    - CAGR、Sharpe、最大ドローダウン、勝率、ペイオフレシオ、総トレード数を計算するユーティリティを提供。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Deprecated
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 環境変数に関する注意:
  - 一部の重要パラメータ（API トークン等）は Settings で必須とされ、未設定時は ValueError を送出するため、デプロイ時に .env を適切に用意する必要があります。
  - .env ファイル読み込み時に OS 環境変数は保護され、.env.local の override が OS 環境変数を上書きしないよう設計されています。

### Known limitations / TODO（実装上の注記）
- signal_generator の売却条件について
  - トレーリングストップ（直近最高値から -10%）や時間決済（保有 60 営業日超）等は未実装。positions テーブルに peak_price / entry_date を保持する拡張が必要。
- feature_engineering / research はルックアヘッドバイアス回避のため target_date 時点のデータのみを用いる設計だが、入力テーブルの整合性（十分な過去データの有無）に依存。
- バックテスト用データのコピー時に一部テーブルのコピー失敗はログによりスキップする（堅牢性のため）。完全な再現性を得るには必要なテーブルが揃っていることを確認してください。
- 外部依存を最小限にする設計（pandas など未使用）であるため、大規模データセットでのパフォーマンス調整は今後の改善対象。

---

（注）本 CHANGELOG は与えられたソースコードから機能・設計意図を推測して作成しています。実際のリリース日や変更履歴の体裁はプロジェクト方針に合わせて適宜修正してください。