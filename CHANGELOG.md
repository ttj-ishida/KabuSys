# Changelog

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

注意: 日付は本コードベース解析時のものです。

## [Unreleased]

- （現在なし）

## [0.1.0] - 2026-03-22

### Added
- パッケージ初期リリース。
- 基本パッケージ構成:
  - kabusys.__version__ = "0.1.0"
  - エクスポート: data, strategy, execution, monitoring（パッケージ入口を定義）
- 環境設定管理（kabusys.config）
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml で探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能
  - .env パースの堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォートの有無で挙動調整）
  - ファイル読み込み時の警告報告（読み込み失敗時に warnings.warn）
  - 環境変数取得ユーティリティ _require と Settings クラスを提供
  - 設定項目（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパス）
    - KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL の検証ロジック
    - is_live / is_paper / is_dev ヘルパー

- 戦略モジュール（kabusys.strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research 側で計算された生ファクターを取得（calc_momentum, calc_volatility, calc_value）
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）
    - 指定列の Z スコア正規化（zscore_normalize を使用）、±3 でクリップ
    - features テーブルへの日付単位置換（トランザクションで原子性保証）
    - 欠損・非数値への堅牢な取り扱い
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して final_score を計算
    - momentum、value、volatility、liquidity、news の重み付け（デフォルトを定義）
    - スコアのシグモイド変換、欠損コンポーネントは中立値 0.5 で補完
    - Bear レジーム検出（ai_scores の regime_score 平均が負である場合。ただしサンプル数閾値あり）
    - BUY（閾値デフォルト 0.60）/SELL（ストップロス -8% 等）の生成
    - SELL 優先ポリシー（SELL の銘柄は BUY から除外）
    - signals テーブルへの日付単位置換（トランザクションで原子性保証）
    - 重み辞書の検証と再スケーリング挙動（不正値はスキップ）

- Research モジュール（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum: mom_1m, mom_3m, mom_6m, ma200_dev（200 日データ不足時は None）
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（20 日窓、NULL 伝播を考慮）
    - calc_value: per（price/EPS）, roe（raw_financials から最新レコードを取得）
    - DuckDB のウィンドウ関数を活用した効率的実装
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算
    - calc_ic: スピアマン順位相関（IC）計算（有効サンプル 3 未満は None）
    - factor_summary: 各ファクターの count/mean/std/min/max/median
    - rank: 同順位は平均ランクにするランク付け（round を用いて浮動小数丸めの ties を防止）
  - research パッケージは本番 API へアクセスせず prices_daily / raw_financials のみ参照する設計

- バックテストフレームワーク（kabusys.backtest）
  - シミュレータ（simulator.PortfolioSimulator）
    - BUY/SELL の擬似約定（SELL を先に処理、SELL は全量クローズ）
    - スリッページ・手数料モデル（引数で調整可能）
    - 平均取得単価管理（cost_basis）、trade レコード記録（TradeRecord）
    - mark_to_market による日次スナップショット記録（終値欠損時は 0 で評価し WARNING）
  - メトリクス（metrics.calc_metrics）
    - CAGR、Sharpe、最大ドローダウン、勝率、Payoff Ratio、トレード数を計算
    - 各指標の実装と境界ケース（データ不足時の 0.0 フォールバック）
  - エンジン（engine.run_backtest）
    - 本番 DB からインメモリ DuckDB へ必要データをコピーしてバックテストを実行
    - get_trading_days を使用したループ、日次での約定→positions 書き戻し→時価評価→シグナル生成→発注の流れを実装
    - データコピー時に date 範囲フィルタを適用（prices_daily, features, ai_scores, market_regime, market_calendar）
    - positions テーブルへシミュレータ保有状態を冪等に書き戻すユーティリティを提供
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20

- ロギングとエラーハンドリング
  - 多数の関数で logger を使用した情報 / 警告 / デバッグ出力を追加
  - トランザクション中の例外時に ROLLBACK を試み、失敗時に警告をログ出力する実装

### Changed
- （初回リリースにつき履歴なし）

### Fixed
- （初回リリースにつき履歴なし）

### Removed
- （初回リリースにつき履歴なし）

### Security
- （特記事項なし）

### Known limitations / TODO
- _generate_sell_signals 内でコメントとして記載されている条件はいくつか未実装:
  - トレーリングストップ（peak_price / entry_date を positions に保持する必要あり）
  - 時間決済（保有 60 営業日超過等）
- research モジュールは外部ライブラリ（pandas 等）を使わず標準ライブラリのみで実装しているため、大規模データでの速度は調整の余地あり。
- features / signals など DB スキーマの存在を前提としている（init_schema 等のスキーマ初期化ロジックに依存）。
- AI スコア（ai_scores）が未登録の場合は中立扱いに補完する設計のため、AI データの欠落がシグナルに影響しにくい。

---

翻訳や表現の調整、リリースノートの細分化（例: 修正・改善の分離）等が必要であれば指示してください。