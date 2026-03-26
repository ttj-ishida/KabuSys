# Changelog

すべての変更は Keep a Changelog の原則に従い、重要度の高い変更をセクションごとに記載しています。日付はリリース日です。

## [0.1.0] - 2026-03-26

初回公開リリース。日本株自動売買システムのコアライブラリを提供します。主な機能群は設定管理、ポートフォリオ構築、戦略（特徴量生成・シグナル生成）、リサーチ用ファクター計算、バックテストシミュレータ／メトリクスです。

### Added
- パッケージ初期化
  - kabusys パッケージの __version__ を "0.1.0" として公開。主要サブパッケージ（data, strategy, execution, monitoring）を __all__ でエクスポート。

- 環境設定管理（kabusys.config）
  - .env/.env.local 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - 自動ロードを無効化するための環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを実装: コメント行対応、export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱いなどをサポート。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能。J-Quants / kabu API / Slack / DB パス等の設定プロパティを持つ。
  - 設定値検証:
    - KABUSYS_ENV は "development" / "paper_trading" / "live" のみ許可（不正値は ValueError）。
    - LOG_LEVEL は "DEBUG","INFO","WARNING","ERROR","CRITICAL" のみ許可（不正値は ValueError）。
  - 必須環境変数取得用の _require() を実装（未設定時は明示的なエラーメッセージを投げる）。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定:
    - select_candidates: BUY シグナルをスコア降順にソートし、同点タイブレークは signal_rank の昇順で上位 N を返す。
  - 重み計算:
    - calc_equal_weights: 等金額配分を返す。
    - calc_score_weights: スコア比率により配分。全スコアが 0 の場合は等配分にフォールバック（WARNING を出力）。
  - リスク調整:
    - apply_sector_cap: セクター別エクスポージャーを計算し、指定比率（デフォルト 30%）超過セクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（"bull":1.0, "neutral":0.7, "bear":0.3）。未知のレジームは 1.0 にフォールバック（WARNING）。
  - 株数決定:
    - calc_position_sizes: allocation_method に応じて発注株数を計算。
      - risk_based: 許容リスク（risk_pct）と stop_loss_pct から株数算出（単元調整あり）。
      - equal / score: 重み情報から各銘柄の目標投資額を算出し単元丸め、per-position と per-portfolio 上限、aggregate cap（available_cash）を考慮してスケールダウン。cost_buffer による保守的見積りに対応。
      - lot_size（単元）サポート、将来の銘柄別 lot_map への拡張点をコメントとして記載。

- 戦略（kabusys.strategy）
  - 特徴量エンジニアリング:
    - build_features: research モジュールの calc_momentum / calc_volatility / calc_value を用いて生ファクターを取得、ユニバースフィルタ（最低株価・平均売買代金）を適用、数値ファクターを Z スコア正規化して ±3 でクリップし、features テーブルへ日付単位で UPSERT（トランザクション）を実行。DuckDB を使用。ルックアヘッドバイアス回避のため target_date 時点のデータのみ利用。
  - シグナル生成:
    - generate_signals: features と ai_scores を統合して各銘柄の final_score を計算し、BUY / SELL シグナルを生成・signals テーブルへ日付単位で置換（トランザクション）。
      - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算。SIGMOID 等の変換関数を実装。
      - AI スコアが無い銘柄は中立（0.5）で補完。欠損コンポーネントも中立補完により不当な降格を防止。
      - weights をデフォルト値とマージし、合計が 1.0 でない場合は正規化。無効値は警告して無視。
      - Bear レジーム検知: ai_scores の regime_score の平均が負（かつサンプル数が閾値以上）なら BUY シグナルを抑制。
      - SELL シグナル生成: ストップロス（終値が平均取得単価比で -8% 以下）および final_score が閾値未満で SELL。価格欠損時の判定スキップとログ出力、features に存在しない保有銘柄は score=0 として SELL 扱い（警告ログ）。
      - SELL 優先ポリシー: SELL 対象は BUY から除外しランクを再付与。

- リサーチ（kabusys.research）
  - ファクター計算:
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA の乖離）を計算。データ不足時は None。
    - calc_volatility: 20 日 ATR / atr_pct（ATR / close） / avg_turnover（20 日平均売買代金）/ volume_ratio（当日出来高比率）を計算。true_range の NULL 伝播を明確に制御。
    - calc_value: raw_financials から最新財務（target_date 以前）を取得して PER / ROE を計算。EPS が 0/欠損 の場合は PER を None に。
  - 特徴量探索:
    - calc_forward_returns: 指定 horizon（デフォルト [1,5,21]）に対する将来リターンを一度のクエリで取得。horizons の妥当性チェックあり。
    - calc_ic: Spearman のランク相関（Information Coefficient）を計算。有効レコードが 3 未満の場合は None。
    - factor_summary: count/mean/std/min/max/median を列ごとに計算するユーティリティ。
    - rank: 同順位は平均ランクで扱うランク関数。浮動小数丸めによる ties 検出漏れ対策を実装。

- バックテスト（kabusys.backtest）
  - シミュレータ:
    - PortfolioSimulator: メモリ内でポートフォリオ状態を管理し、SELL を先に、BUY を後に処理する約定ロジックを実装。SELL は保有全量クローズ（部分利確未対応）。スリッページ（BUY:+, SELL:-）・手数料率を適用。TradeRecord / DailySnapshot のデータモデルを提供。
  - メトリクス:
    - calc_metrics: DailySnapshot と TradeRecord から BacktestMetrics を算出（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 各種内部計算: CAGR（暦日ベース）、Sharpe（年次化：252 日）、最大ドローダウン、勝率、ペイオフレシオの計算実装。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Notes / Known limitations / TODO
- apply_sector_cap:
  - price_map に価格欠損（0.0）があるとエクスポージャーが過少見積りされ、ブロックが外れる可能性がある。将来的に前日終値や取得原価などのフォールバック価格を検討。
- position_sizing:
  - 現状 lot_size は全銘柄共通の引数で扱う。将来的には銘柄別 lot_map を受ける拡張を想定（TODO コメントあり）。
- signal_generator:
  - トレーリングストップや時間決済（保有期間によるクローズ）などは未実装。positions テーブルに peak_price / entry_date 等の情報が必要。
- build_features / generate_signals:
  - DuckDB を前提に設計。外部 API（発注層）への依存は持たないため、本番実行時は engine/execution 層との組み合わせが必要。
- 一部関数は入力データの欠損（価格・財務・AI スコア等）に対して中立補完やスキップ等の保守的振る舞いを採用しており、設計文書（PortfolioConstruction.md, StrategyModel.md 等）に準拠しています。

もし CHANGELOG に追記したい差分（例えばリリース日や既知のバグ修正、API の変更点など）があれば教えてください。