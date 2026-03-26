# Changelog

すべての重大な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠しています。

最新の安定版: 0.1.0

## [Unreleased]

### Added
- 設定
  - .env/.env.local 読み込みやパース機能の改善（詳細は config モジュールに実装済みの挙動を参照）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動環境変数読み込み抑止フラグ（テスト用途）。

### Changed / Planned
- position sizing の拡張：
  - 銘柄毎の lot_size（単元）対応（現状は全銘柄共通の lot_size）。
  - 価格フォールバック（前日終値や取得原価）を用いた sector exposure の改善。
- strategy の exit 戦略拡張：
  - トレーリングストップ、時間決済（保有期間によるクローズ）等の追加実装。
- 実行層（execution）や監視（monitoring）モジュールの実装・統合（現状はパッケージエクスポートのみ）。

### Fixed / Planned
- edge-case のログ出力・エラーハンドリング明確化（価格欠損時の挙動や weights の検証は既に安全策あり）。

---

## [0.1.0] - 2026-03-26

初期リリース。以下の主要機能を実装しました。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン 0.1.0
  - エントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）

- 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - .env パーサ: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープに対応。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護（protected）され上書きされない。
  - 必須環境変数取得用ヘルパ（_require）と Settings クラス:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須として取得。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH のデフォルト設定。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
    - is_live / is_paper / is_dev のプロパティ。

- ポートフォリオ構築（src/kabusys/portfolio/）
  - portfolio_builder:
    - select_candidates: BUY シグナルのスコア順ソートと上位抽出（同点タイブレークは signal_rank）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率配分。全スコアが 0 の場合は等金額へフォールバック（WARNING ログ）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中の上限チェック（max_sector_pct）。当日売却対象は除外可能。unknown セクターは上限対象外。
    - calc_regime_multiplier: 市場レジームに応じた乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 でフォールバック（WARNING ログ）。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づく発注株数計算。
    - per-stock 上限（max_position_pct）や aggregate cap（available_cash）を考慮、lot_size による丸め、cost_buffer を踏まえた保守的見積もり。
    - aggregate cap 超過時はスケールダウンし、端数は fractional remainder の大きい順に lot_size 単位で追加配分する実装。

- 戦略（src/kabusys/strategy/）
  - feature_engineering.build_features:
    - research モジュールから取得した生ファクターを結合、ユニバース（最低株価・最低売買代金）フィルタを適用。
    - 指定列を Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ。
    - DuckDB を用いて features テーブルに日付単位で置換（トランザクションで冪等に挿入）。
  - signal_generator.generate_signals:
    - features / ai_scores / positions テーブルを参照して各構成スコア（momentum, value, volatility, liquidity, news）を計算。
    - シグモイド変換と重み付け（デフォルト重みは code 内に定義）で final_score を算出。weights の検証・正規化ロジックあり。
    - Bear レジーム検知時は BUY シグナルを抑制（AI レジームスコアに基づく判定）。
    - BUY シグナル閾値はデフォルト 0.60。
    - SELL シグナル生成（ストップロス、スコア低下）。features 欠損や価格欠損時は警告ログを出し保守的な挙動。
    - signals テーブルへ日付単位の置換（トランザクションで冪等）。

- リサーチ（src/kabusys/research/）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率。
    - calc_value: 最新財務データ（raw_financials）と当日株価から PER, ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21] 営業日）での将来リターン計算。
    - calc_ic: ファクターと将来リターンのスピアマン ρ（ランク相関）を計算。サンプル不足時は None。
    - factor_summary / rank: 基本統計量・ランク計算ユーティリティ。
  - 研究向け実装方針として外部ライブラリ（pandas 等）に依存せず、DuckDB のみで完結する設計。

- バックテスト（src/kabusys/backtest/）
  - simulator:
    - PortfolioSimulator: メモリ上での現金・ポジション・平均取得単価管理、約定シミュレーション（SELL を先に処理、SELL は全量クローズ）。
    - TradeRecord / DailySnapshot データ構造。
    - スリッページ（BUY:+、SELL:-）と手数料モデル、lot_size の扱い。
  - metrics:
    - calc_metrics: CAGR, Sharpe Ratio（無リスク金利=0）, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティ。

### Changed / Notes
- DB 操作は DuckDB を前提とした SQL 実装（features, ai_scores, positions, prices_daily, raw_financials 等を使用）。
- 多くの処理で「データ欠損時は保守的スキップ or フォールバック」を採用（価格欠損時の SELL 判定スキップ、スコア欠損時は中立値 0.5 補完など）。
- ロギングを多用して異常やフォールバックの発生箇所を記録。

### Known limitations / Unimplemented
- position_sizing: 銘柄別単元（lot_size）をマスタで持つ設計への拡張未実装（現状は関数引数で共通 lot_size）。
- risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性あり（コード内で TODO コメントあり）。
- signal_generator のエグジット条件:
  - トレーリングストップや時間決済（保有日数ベース）は未実装。positions テーブルに追加情報（peak_price, entry_date 等）が必要。
  - SELL は現状保有全量をクローズ（部分利確・部分損切りに非対応）。
- research.calc_value: PBR・配当利回り等のバリューファクターは未実装。
- execution / monitoring サブパッケージは骨組みのみ（詳細な API 実装は今後）。

### Security
- 環境変数パースと自動ロードに注意: .env を扱うため、配布・運用時は秘匿情報の管理を厳格に行ってください。

---

（注）この CHANGELOG は提供されたコードベースの内容から推測して作成した要約です。実際のリリースノートや運用ドキュメントとして利用する場合は、変更履歴やコミットログと照合のうえ適宜修正してください。