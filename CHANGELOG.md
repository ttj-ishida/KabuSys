CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠し、安定版リリースごとに主要な変更点を記載します。

Unreleased
----------

（現在未リリースの変更はありません）

0.1.0 - 2026-03-22
------------------

Added
- 初回リリース。日本株自動売買フレームワーク「KabuSys」を公開。
- パッケージのエントリポイント
  - src/kabusys/__init__.py にてバージョン情報と公開モジュールを定義（__version__ = "0.1.0"）。
- 環境設定管理
  - src/kabusys/config.py
    - .env/.env.local ファイルまたは OS 環境変数から設定を自動読み込み（プロジェクトルートは .git / pyproject.toml を基準に検索）。
    - .env のパースは export プレフィックス、クォート（シングル/ダブル）、バックスラッシュエスケープ、インラインコメントの扱いに対応。
    - 自動ロードを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - 認証や運用設定の required getters を提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
    - DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL のデフォルトやバリデーション（env 値の検証、ログレベル検証、is_live/is_paper/is_dev ヘルパー）。
- データ処理 / 研究モジュール
  - src/kabusys/research/factor_research.py
    - モメンタム（1M/3M/6M/MA200乖離）、ボラティリティ（ATR20, atr_pct）、流動性（20日平均出来高、出来高比率）、バリュー（PER/ROE）を DuckDB 上で計算する関数を実装。
    - 欠損データや窓サイズ不足時の安全な None 処理。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン（指定ホライズンの forward returns）計算。
    - IC（Spearman のランク相関）計算、rank ユーティリティ、factor_summary（count/mean/std/min/max/median）を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB で実行可能。
  - src/kabusys/research/__init__.py で研究系 API を再公開。
- 戦略（特徴量作成・シグナル生成）
  - src/kabusys/strategy/feature_engineering.py
    - 研究で算出した生ファクターを正規化（zscore_normalize を利用）し、±3 にクリップして features テーブルへUPSERT（指定日で日付単位の置換を行い冪等性を維持）。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
    - DuckDB の prices_daily / raw_financials を参照。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネント毎の計算ロジック（シグモイド変換、PER の扱い、欠損時の中立補完など）。
    - デフォルト重み（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）をサポート。外部から渡された重みは検証・正規化して合計が 1.0 に調整。
    - Bear レジーム判定（AI の regime_score 平均が負かつサンプル数閾値以上で BUY を抑制）を実装。
    - BUY シグナル閾値デフォルト 0.60、SELL ロジック（ストップロス -8% とスコア低下）を実装。
    - signals テーブルへ日付単位の置換で書き込み（トランザクション + バルク挿入）。
- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator: BUY/SELL の擬似約定、平均取得単価管理、スリッページ/手数料の適用、終値での時価評価（DailySnapshot）記録、TradeRecord の出力を実装。
    - SELL は保有全量クローズ、BUY は割当金額から取得可能株数を計算（手数料込みで再調整）。
    - 適切なログ出力（始値/終値欠損時の警告など）。
  - src/kabusys/backtest/metrics.py
    - バックテスト評価指標計算（CAGR, Sharpe Ratio（無リスク=0）, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
  - src/kabusys/backtest/engine.py
    - run_backtest() を実装（本番 DB から必要テーブルを日付範囲でコピーしてインメモリ DuckDB を構築し、日次ループでシミュレーションを実行）。
    - テーブルのコピー処理（prices_daily, features, ai_scores, market_regime, market_calendar）と失敗時の警告。
    - 日次のフロー: 前日シグナル約定 → positions テーブル書き戻し → 終値で時価評価 → generate_signals（当日） → ポジションサイジング → 次日約定。デフォルトパラメータ: initial_cash=10,000,000 / slippage_rate=0.001 / commission_rate=0.00055 / max_position_pct=0.20。
  - src/kabusys/backtest/__init__.py で Backtest API を公開（run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics）。
- パッケージ公開
  - src/kabusys/strategy/__init__.py で build_features / generate_signals を公開。
  - src/kabusys/research と backtest の __all__ による公開。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / Implementation Details
- DB テーブル
  - 多くの機能は DuckDB のテーブルを前提とする: prices_daily, features, ai_scores, raw_financials, positions, signals, market_calendar, market_regime 等。
- 安全性 / 冪等性
  - features / signals / positions への書き込みは「日付単位で DELETE → INSERT（トランザクション）」により冪等性とアトミック性を担保。
- 欠落している（未実装）点（ドキュメント内に TODO）
  - signal_generator の SELL 条件の一部（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の追加が必要で未実装。
- ロギングと警告
  - データ欠損（価格欠如、財務データ欠如など）時は警告ログを出力して処理をスキップまたは中立で補完する実装方針。
- 設計方針
  - ルックアヘッドバイアス回避のため、各処理は target_date 時点の利用可能データのみを参照するよう設計。
  - 研究モジュールは本番 API/発注層に依存しない（純粋な分析ロジック）。
  - 外部依存を最小限にする設計（研究モジュールは pandas 等に依存しない）。

既知の問題
- positions に peak_price / entry_date 等が存在しないため、将来的に実装予定のトレーリングストップ等は現状では動作しない。
- .env ファイル読み込みはプロジェクトルート検出に依存するため、パッケージ配布後や特殊な配置では自動検出が失敗する可能性がある（その場合は自動ロードをスキップ）。
- run_backtest のテーブルコピーでスキーマ差異や不整合があると警告を出してコピーをスキップするため、完全なデータセットがないと想定通りに動作しない可能性あり。

Upgrade Notes
- 初回リリースのため、既存リリースからのマイグレーションは不要。

Contributing
- バグ報告、改善提案、プルリクエストは歓迎します。ドキュメント（StrategyModel.md, BacktestFramework.md 等）に基づいて変更をお願いします。