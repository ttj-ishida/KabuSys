# Changelog

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に従っています。  

なお以下は与えられたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-03-26

### 追加 (Added)
- パッケージ初期リリース。
- 基本的なパッケージ構成を追加：
  - kabusys（トップレベルパッケージ）
  - サブモジュール: data, strategy, execution, monitoring を __all__ で公開。
- 環境設定管理（kabusys.config）を実装：
  - .env / .env.local の自動読み込み（プロジェクトルート判定：.git または pyproject.toml を基準）。
  - .env 行パースの実装（コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ対応）。
  - 自動ロード無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）。
  - 必須環境変数取得ヘルパー _require()。
  - 設定値アクセス用 Settings クラス（J-Quants / kabu / Slack / DB パス / 環境 / ログレベル 等）。
  - env と log_level の検証（許容値チェック）。

- ポートフォリオ構築モジュール（kabusys.portfolio）を実装：
  - 候補選定 select_candidates（スコア降順・タイブレークロジック）。
  - 等金額配分 calc_equal_weights。
  - スコア加重配分 calc_score_weights（全スコア0時に等配分にフォールバック、WARN ログ）。
  - ポジションサイズ決定 calc_position_sizes（risk_based / equal / score の配分方式、lot_size、max_position_pct、max_utilization、cost_buffer を考慮した aggregate cap とスケーリング、単元調整）。
  - セクター集中制限 apply_sector_cap（既存保有をセクター別に集計し閾値超過セクターの新規候補を排除。unknown セクターは制限対象外）。
  - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をマップ、未知レジームはフォールバックで 1.0、WARN ログ）。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）を実装：
  - research 層の生ファクター（momentum/volatility/value）を取り込み、ユニバースフィルタ（最低株価・平均売買代金）適用。
  - 指定列の Z スコア正規化（zscore_normalize を使用）、±3 でクリップ。
  - 日付単位の冪等な features テーブルへの UPSERT（トランザクションで原子性保証）。
  - DuckDB を用いた prices_daily / raw_financials の参照。

- シグナル生成（kabusys.strategy.signal_generator）を実装：
  - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
  - シグモイド変換、欠損コンポーネントは中立値（0.5）で補完。
  - final_score に基づく BUY シグナル生成（閾値デフォルト 0.60）、Bear レジーム時は BUY を抑制。
  - エグジット判定（ストップロス -8% とスコア低下）に基づく SELL シグナル生成。SELL 優先ポリシー（SELL 対象は BUY から除外）。
  - signals テーブルへの日付単位置換（冪等）。
  - weights 引数のバリデーションと合計正規化ロジック。

- リサーチモジュール（kabusys.research）を実装：
  - ファクター計算 calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials に依存）。
  - 将来リターン calc_forward_returns（複数ホライズンに対応、単一クエリで取得）。
  - IC（スピアマンのρ）計算 calc_ic（rank を内部実装）。
  - factor_summary（count/mean/std/min/max/median）。
  - rank ユーティリティ（同順位は平均ランク、丸め処理で ties を安定化）。

- バックテスト（kabusys.backtest）を実装：
  - メトリクス計算（BacktestMetrics dataclass と calc_metrics）：
    - cagr, sharpe_ratio, max_drawdown, win_rate, payoff_ratio, total_trades。
  - PortfolioSimulator（擬似約定・ポートフォリオ状態管理）：
    - DailySnapshot / TradeRecord dataclass。
    - execute_orders により SELL→BUY の順で約定処理（スリッページ・手数料モデルを考慮）。SELL は保有全量クローズの実装方針。
    - 約定記録（TradeRecord）の保持と日次スナップショット履歴管理（基本的な状態更新ロジックを提供）。

### 変更 (Changed)
- 初回リリースのため、変更項目は無し（初期追加のみ）。内部でのログメッセージやデフォルトパラメータの選定は実装に記載の通り。

### 修正 (Fixed)
- 初回リリースのため、修正項目は無し。

### 既知の制限・注意点 (Known issues / Notes)
- Settings / env 自動ロード:
  - プロジェクトルートを __file__ の親ディレクトリから探索するため、配布形態やインストール方法によっては .env 自動検出が期待どおりに動作しない場合がある。KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能。

- .env パーサ:
  - 値のクォート処理でエスケープを処理するが、複雑なシェル展開等はサポートしない。

- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーを過少見積もる可能性があり、TODO として前日終値や取得原価のフォールバックを検討。

- calc_regime_multiplier:
  - Bear レジーム時に generate_signals 自体が BUY を生成しない設計になっているため、multiplier=0.3 は中間保険的な措置であり、Bear 相場下での BUY 生成は原則無い点に注意。

- signal_generator の未実装/将来拡張:
  - Trailing stop（最高値からのトレール）や時間決済（保有期間）判定のためには positions テーブルに peak_price / entry_date 等の追加情報が必要。現在は未実装。

- position_sizing:
  - lot_size は全銘柄共通パラメータとして扱っている。将来的には銘柄毎の lot_map をサポートする設計拡張を予定。
  - price が欠損の場合は当該銘柄をスキップ。

- backtest PortfolioSimulator:
  - 現在 SELL は保有全量をクローズする仕様（部分利確・部分損切りは未対応）。
  - execute_orders 実装はコード末尾で切れている可能性がある（与えられたコードの一部が未完の箇所あり）。実際の動作詳細は実装の続きに依存。

- research モジュール:
  - pandas 等外部ライブラリに依存せず標準ライブラリ + DuckDB で実装しているため、巨大データに対する最適化は今後の課題。

### 将来の計画 / TODO
- .env 読み込みのフォールバックロジック強化（配布後のパス問題対策）。
- position_sizing の lot_map（銘柄毎単元）対応。
- trailing stop や時間決済など、エグジットロジックの拡張（positions テーブルの拡張含む）。
- PortfolioSimulator の部分約定・部分利確対応、より詳細な手数料モデルの導入。
- execution 層の実装強化（kabu API / 実際の注文発行ロジック）。
- tests の追加と CI（自動化テスト）整備。

---

配布・利用時は README / StrategyModel.md / PortfolioConstruction.md 等の設計ドキュメントを参照してください。コード内に多くの設計注記（TODO / NOTE / Section リンク）が含まれており、今後の拡張ポイントが明記されています。