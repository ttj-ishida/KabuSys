# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-26

初回リリース。日本株自動売買フレームワークのコア機能群を実装しました。以下の主要機能・モジュールを含みます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期化（__version__ = 0.1.0、主要サブパッケージを公開）。
- 環境設定管理（kabusys.config）
  - .env/.env.local の自動読み込み（プロジェクトルート検出は .git または pyproject.toml を基準、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサーは export 構文、シングル/ダブルクォート、エスケープ、コメント扱い（スペース前の # をコメントとみなす）に対応。
  - Settings クラスを提供（必須環境変数取得用の _require、J-Quants/Slack/Kabu 設定、DB パスの既定値、環境・ログレベル検証、 is_live/is_paper/is_dev プロパティ等）。
  - 環境値検証（KABUSYS_ENV, LOG_LEVEL）のバリデーションとエラー発生。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: スコア降順、同点は signal_rank 昇順で上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率で配分（合計スコアが0なら等分にフォールバック、警告ログ）。
  - risk_adjustment
    - apply_sector_cap: 既存保有のセクターエクスポージャーを算出し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームは警告と共に 1.0 にフォールバック）。
  - position_sizing
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく株数計算、単元（lot_size）丸め、1銘柄上限・aggregate cap のスケーリング、cost_buffer（手数料・スリッページ見積り）を反映した保守的な計算、価格欠損時スキップ。
    - aggregate cap スケールダウン時の余剰割当ては、fractional remainder を用いて lot_size 単位で再配分（再現性を考慮して安定ソート）。

- 戦略（kabusys.strategy）
  - feature_engineering
    - build_features: research モジュール（calc_momentum/calc_volatility/calc_value）から生ファクターを取得し、ユニバースフィルタ（最低株価・最低平均売買代金）、Z スコア正規化（zscore_normalize 利用）、±3 クリップ、features テーブルへの日付単位 UPSERT（トランザクションで原子性保証）を実装。
  - signal_generator
    - generate_signals: features / ai_scores / positions を読み込み、モメンタム・バリュー・ボラティリティ・流動性・ニュースのコンポーネントを計算し final_score を算出。
    - デフォルト重みのマージと検証（無効値はスキップ、合計が 1.0 でなければ再正規化）。
    - AI レジームスコアに基づく Bear 判定で BUY を抑制。
    - BUY シグナル閾値（デフォルト 0.60）超過で BUY を生成、SELL はストップロス（-8%）とスコア低下で判定。
    - signals テーブルへ日付単位の置換（トランザクションで原子性保証）。
    - 欠損データ時のフォールバック処理（AI スコア未登録は中立、features にない保有銘柄は score=0 として SELL 判定など）とログ出力。

- 研究用モジュール（kabusys.research）
  - factor_research
    - calc_momentum / calc_volatility / calc_value を SQL ベースで実装（prices_daily, raw_financials を参照）。
    - 各ファクターは欠損処理を行い、必要なデータが不足する場合は None を返す設計。
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: スピアマンのランク相関（IC）計算（結合・None 除外・最小サンプル数チェック）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位は平均ランク処理（round による安定化）。

- バックテスト（kabusys.backtest）
  - metrics
    - 多数の評価指標を実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 実装は DailySnapshot / TradeRecord のリストのみを利用（DB 参照なし）。
  - simulator
    - PortfolioSimulator クラス: メモリ内でポートフォリオ状態を管理し、約定ロジックを提供。
    - DailySnapshot / TradeRecord dataclass を定義。
    - execute_orders: SELL を先に処理してから BUY（SELL は保有全量クローズ）、スリッページ（BUY:+, SELL:-）・手数料モデルを適用。lot_size を受け取り丸めを行う。
    - ログ出力や入力検査（価格欠損、shares<=0 のスキップ）を含む。

- 汎用ユーティリティ
  - data.stats.zscore_normalize を再公開（research/__init__.py でエクスポート）。
  - 各モジュールで適切なログ出力を組み込み、例外発生時にトランザクションをロールバックする処理を実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Notes / Known issues / TODO
- 一部未実装機能・拡張余地:
  - position_sizing: 銘柄ごとの lot_size をサポートするための設計拡張（現状は全銘柄共通 lot_size を想定）。
  - risk_adjustment.apply_sector_cap: price_map に 0.0 が含まれるとエクスポージャーが過少評価される可能性あり（将来的に前日終値や取得原価でフォールバックする検討）。
  - signal_generator._generate_sell_signals: トレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date のフィールドが必要）。
  - feature_engineering は zscore_normalize に依存。zscore_normalize の実装品質に依存する。
- トランザクション処理: DuckDB を用いた INSERT/DELETE はトランザクションで原子性を保証するよう実装しているが、周辺の DB スキーマ・インデックス設計や並行実行を考慮する必要あり。
- テストとエラーハンドリング: 価格欠損・データ不足時はスキップやフォールバックで安全側に動作するよう設計されている。実運用前に十分なテストを推奨。

---

今後のリリースでは、運用監視・execution 層の具体的な API 統合、銘柄個別の単元対応、追加のリスク制御（トレーリングストップ等）、およびドキュメントの充実を予定しています。