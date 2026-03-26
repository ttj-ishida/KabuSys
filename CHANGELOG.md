# Changelog

すべての重要な変更点はこのファイルに記録します。本ファイルは「Keep a Changelog」準拠の形式で記載しています。  

現在のパッケージバージョン: 0.1.0

## [Unreleased]

### 追加予定 / TODO / 既知の制限
- position_sizing: 銘柄別の単元（lot_size）を銘柄マスタから取得する拡張を検討中（現状はグローバル lot_size のみ）。
- risk_adjustment.apply_sector_cap: 価格欠損時にエクスポージャーが過少評価される問題へのフォールバック（前日終値や取得原価など）の実装検討。
- strategy.signal_generator: トレーリングストップや時間決済（保有期間による決済）の判定は未実装。positions テーブルに peak_price / entry_date 等を追加して実装予定。
- execution パッケージはスケルトン（実装不足）: 実運用向けの発注・API連携ロジックの追加が必要。
- 部分約定・手数料・スリッページの実運用チューニングとユニットテスト強化。

---

## [0.1.0] - 2026-03-26

### 追加 (Added)
- パッケージ初期リリース。日本株自動売買システムのコア機能群を提供。
- パッケージメタ
  - src/kabusys/__init__.py にて __version__="0.1.0" を設定。公開 API の __all__ を定義（data, strategy, execution, monitoring）。
- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して判定）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
    - .env パーサは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメント等に対応。
    - OS 環境変数の保護（.env の上書きを制御）機構を実装。
    - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベル等の取得と簡易バリデーションをサポート。
- ポートフォリオ構築関連
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルをスコア降順、同点は signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコアに基づく配分。合計スコアが 0 の場合は等金額配分にフォールバック（警告出力）。
  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: 既存保有のセクター別時価を計算し、1セクター上限（max_sector_pct）を超える場合は当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは警告と共に 1.0 にフォールバック）。
  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した発注株数計算。リスクベース計算、ポジション上限、単元（lot_size）丸め、aggregate cap（available_cash を超えた場合のスケールダウン）や cost_buffer（手数料・スリッページ見積）に対応。
- ストラテジー（研究→実装）
  - src/kabusys/strategy/feature_engineering.py
    - build_features: research モジュール（calc_momentum / calc_volatility / calc_value）から因子を取得し、ユニバースフィルタ（最低株価・最低平均売買代金）、Z スコア正規化（±3 でクリップ）を行い、features テーブルへ日付単位の置換（トランザクションで原子性保証）で保存。
    - ユニバース条件: 株価 >= 300 円、20日平均売買代金 >= 5億円。
  - src/kabusys/strategy/signal_generator.py
    - generate_signals: features と ai_scores を統合し、モメンタム／バリュー／ボラティリティ／流動性／ニュースの重み付けにより final_score を計算。Bear レジーム時の BUY 抑制、閾値超過で BUY、エグジット条件で SELL（ストップロス -8% 等）を生成。signals テーブルへ日付単位の置換で保存。
    - 各種スコア計算ユーティリティ実装（シグモイド変換、欠損値処理、重みの正規化・検証）。
- リサーチ（分析）機能
  - src/kabusys/research/factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials を参照）。200日移動平均やATR/平均売買代金等を計算し、データ不足時は None を返す設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定ホライズン（デフォルト 1/5/21 営業日）で将来リターンを計算。
    - calc_ic: スピアマンのランク相関（IC）計算を実装（結合・欠損除外・最小サンプル検査）。
    - factor_summary, rank: 基本統計量とランク変換ユーティリティを提供。
- データ処理ユーティリティ
  - src/kabusys/data/stats.py（参照されるユーティリティ）：Z スコア正規化を利用（実装ファイルはこのスニペット外だが参照を統一）。
- バックテスト関連
  - src/kabusys/backtest/metrics.py
    - BacktestMetrics dataclass と評価指標計算（CAGR, Sharpe, Max Drawdown, 勝率, Payoff Ratio, 総取引数）実装。
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator, DailySnapshot, TradeRecord を実装。execute_orders による SELL 先行 → BUY 後処理、スリッページ・手数料の考慮、約定記録の生成など基礎的なシミュレータ機能を提供。

### 変更 (Changed)
- （初版のため該当なし）

### 修正 (Fixed)
- （初版のため該当なし）

### 注意点 / 設計上の判断
- DB 書き込み処理（features / signals 等）は日付単位で既存レコードを削除して再挿入する設計により冪等性を確保。
- strategy の重み（weights）は入力検証を行い、不正値・未知キーはスキップ、合計が 1.0 でない場合は正規化して使用。
- generate_signals は AI レジームスコアのサンプル数が不足する場合は Bear 判定を行わない設計（誤判定防止）。

### 既知の制約 / 警告ログ出力
- features もしくは価格が欠損する銘柄に対しては適切に None を扱い、必要に応じて警告ログを出力して処理をスキップまたは中立値で補完する実装。
- calc_score_weights はスコア合計が 0 の場合に等配分へフォールバックし、警告ログを出力。
- apply_sector_cap は "unknown" セクター（マップ未登録銘柄）にセクターキャップを適用しない（例外的扱い）。

### セキュリティ (Security)
- （初版リリース時に報告されたセキュリティ修正点なし）

---

メンテナンス / 貢献について:
- 実運用化にあたっては execution 層の実装、単体テスト・統合テスト、監視・アラート（monitoring）統合、ドキュメント整備が推奨されます。ソース中に TODO コメントや警告ログが残っている箇所は優先的に対応してください。