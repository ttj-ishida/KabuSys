# CHANGELOG

すべての注目すべき変更を記録します。本ファイルは「Keep a Changelog」形式に準拠します。  

注: この CHANGELOG は提供されたコードベースから推察して作成しています。

## [Unreleased]

## [0.1.0] - 2026-03-26

初回リリース — 基本的な自動売買・研究・バックテスト基盤を実装。

### 追加 (Added)
- パッケージ化
  - kabusys パッケージの初期公開。バージョン 0.1.0 を src/kabusys/__init__.py に定義。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いに対応。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / システム設定等の環境変数をプロパティとして取得。値検証（KABUSYS_ENV, LOG_LEVEL 等）を実施。

- ポートフォリオ構築 (kabusys.portfolio)
  - candidate 選定: select_candidates（スコア降順、タイブレーク方針を実装）。
  - 重み計算: calc_equal_weights（等分配）, calc_score_weights（スコア加重。スコア合計が0の際は等分配へフォールバック）。
  - ポジションサイズ計算: calc_position_sizes を実装。以下をサポート:
    - allocation_method: "risk_based", "equal", "score"
    - 単元（lot）丸め、銘柄毎の max_per_stock、max_utilization、aggregate cap によるスケール調整
    - cost_buffer を考慮した保守的見積りと残差処理（lot 単位での再配分）
  - リスク調整: apply_sector_cap（セクター集中制限を適用）と calc_regime_multiplier（市場レジームに応じた投下資金乗数）を実装。

- 戦略（特徴量・シグナル） (kabusys.strategy)
  - 特徴量作成: build_features（research モジュールの生ファクターをマージして正規化・Z スコアクリップし、features テーブルへ UPSERT）。
  - シグナル生成: generate_signals（features と ai_scores を統合して final_score を計算、BUY/SELL シグナルを生成し signals テーブルへ書き込み）。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）と重み合成実装。
    - Bear レジーム判定による BUY 抑制。
    - SELL のエグジット判定（ストップロス、スコア低下）を実装。
    - weights の検証・補完・正規化ロジックを実装。

- 研究ユーティリティ (kabusys.research)
  - ファクター計算: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照して各種ファクターを算出）。
  - 特徴量探索: calc_forward_returns（任意ホライズンの将来リターン算出）, calc_ic（Spearman のランク相関で IC 計算）, factor_summary（基本統計量算出）, rank（平均ランク付け）を実装。
  - zscore_normalize をデータ統計ユーティリティから利用可能にエクスポート。

- バックテスト (kabusys.backtest)
  - メトリクス: calc_metrics と BacktestMetrics（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades）。
  - シミュレータ: PortfolioSimulator（メモリ内のポートフォリオ状態管理、擬似約定ロジック、スリッページ・手数料モデル、SELL 優先処理、TradeRecord/DailySnapshot データクラス）。

### 変更 (Changed)
- なし（初回リリースのため）。

### 修正 (Fixed)
- 環境変数パーサの堅牢化:
  - クォート内でのバックスラッシュエスケープ処理や export 形式対応、コメントの扱い（クォート外での # の扱い条件）を実装して .env 読み込みの互換性を向上。

### 注意事項 / 既知の制約 (Notes / Known issues)
- apply_sector_cap:
  - sector_map に存在しないコードは "unknown" とみなしてセクター上限の適用対象外となる。
  - price_map で価格が欠損（0.0）の場合、エクスポージャーが過少見積もられる可能性があり、将来的に前日終値や取得原価をフォールバックする案が示されている（TODO）。
- calc_position_sizes:
  - 現状 lot_size は単一値（全銘柄共通）を想定。将来的に銘柄別 lot_map 受け取りへの拡張予定（TODO）。
- シグナル生成 / エグジット条件:
  - 現在実装されている SELL 条件はストップロスとスコア低下のみ。トレーリングストップや時間決済（保有期間ベース）は未実装（positions テーブルに peak_price / entry_date が必要）。
- データ依存性:
  - 多くの処理は prices_daily / raw_financials / features / ai_scores / positions 等の DB テーブルに依存。該当データが欠損すると当該銘柄はスキップまたは中立値で補完される仕様（警告ログ出力あり）。
- トランザクション処理:
  - DuckDB への書き込みは日付単位で DELETE → INSERT を行い原子性を確保するためトランザクションを使用。例外時は ROLLBACK を試行するが、ROLLBACK 自体の失敗は警告ログに記録される。
- 互換性 / 安全性:
  - KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト等で自動 .env ロードを抑止可能。

### セキュリティ (Security)
- なし。

---

今後の改善案（コード内 TODO より抜粋）
- price_map のフォールバック戦略（前日終値や取得原価）を導入して exposure 計算精度を向上。
- 銘柄別単元（lot_size）管理の導入。
- SELL のトレーリングストップ・時間決済ロジック実装。
- より詳細な手数料・スリッページモデルの追加・チューニング。

---

作成: 自動生成（コードベースのコメント・実装から推測）