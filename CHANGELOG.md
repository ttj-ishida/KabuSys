# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に従います。  
安定版リリース、機能追加、バグ修正、既知の制約や将来の TODO などをコードベースから推測して日本語でまとめています。

注: バージョン番号はパッケージの __version__（src/kabusys/__init__.py）に基づきます。

## [Unreleased]

- 今後のリリースでの検討点（コード内コメント・TODOより抜粋）
  - 銘柄ごとの単元情報（lot_size）の外部マスタ化と position_sizing へ反映する設計拡張
  - position_sizing の price フォールバック（前日終値や取得原価）を実装して価格欠損時の過小見積りを改善
  - signal_generator / _generate_sell_signals におけるトレーリングストップや時間決済（positions テーブルの peak_price / entry_date を利用）を実装
  - execution 層（発注 API 統合）および monitoring 層の実装・強化
  - テストカバレッジの追加（特に DB 結合クエリやスケーリングロジック）

---

## [0.1.0] - 2026-03-26

初版リリース。バックテスト・リサーチ・シグナル生成から発注用計算までのコアライブラリ群を提供します。主な内容は以下の通りです。

### 追加 (Added)
- パッケージ構成
  - kabusys パッケージの基本構造を提供（data, strategy, execution, monitoring をエクスポート）。
  - バージョン: 0.1.0

- 環境設定・自動 .env ロード機能（kabusys.config）
  - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（CWD 非依存）。
  - .env / .env.local の自動読み込み（OS 環境変数優先）を実装。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサを実装（export フォーマット、クォート文字列のエスケープ、行末コメントの扱いなど）。

- ポートフォリオ構築（kabusys.portfolio）
  - select_candidates: BUY シグナルから上位候補をスコア順で選定（タイブレークに signal_rank）。
  - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分の重み計算（スコア全てが 0 の場合は等分にフォールバック）。
  - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて発注単位（株数）を算出。最大ポジション上限・aggregate cap・単元丸め・コストバッファ考慮を実装。
  - apply_sector_cap: セクター集中の制限を実装（既存保有のセクター比率が上限を越える場合、新規候補を除外）。
  - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull/neutral/bear）を提供。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research モジュールの生ファクターを統合し、ユニバースフィルタ（最低株価/平均売買代金）を適用。
  - 数値ファクターの Z スコア正規化（±3 でクリップ）を行い、DuckDB の features テーブルへ日付単位での置換（冪等）挿入を実装。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して最終スコア（final_score）を算出。
  - momentum/value/volatility/liquidity/news を重み付け合算（デフォルト重みを実装）。
  - Bear レジーム検知による BUY シグナル抑制（ai_scores の regime_score を集計）。
  - BUY / SELL シグナルの生成ロジック（スコア閾値、ストップロス、SELL 優先ルール）と signals テーブルへの冪等書き込みを実装。
  - weights の入力検証とフォールバック・再スケーリングを実装。

- リサーチ（kabusys.research）
  - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算。
  - calc_forward_returns: 複数ホライズン（デフォルト: 1,5,21 営業日）で将来リターンを算出。
  - calc_ic: Spearman のランク相関（Information Coefficient）を実装。
  - factor_summary / rank / zscore_normalize の公開（統計・正規化ユーティリティ）。

- バックテスト（kabusys.backtest）
  - PortfolioSimulator: 擬似約定（スリッページ・手数料モデル）とポートフォリオ状態管理（DailySnapshot, TradeRecord）を実装。SELL を先行処理し BUY を後処理する挙動などを備える。
  - metrics: バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）を計算。

### 修正 (Changed)
- N/A（初版のため既存コードの「変更」はなし。ただし内部ロジックは複数の設計判断・フォールバックを含む実装あり）
  - 環境変数や重みの不正入力に対する防御的実装（警告ログ出力とフォールバック）を盛り込んでいる。

### 既知の制約 / 注意点 (Known issues / Notes)
- position_sizing
  - 銘柄毎の単元 (lot_size) は現状グローバル指定のみ。将来的に銘柄マスタと連携して銘柄別単元対応を検討する必要あり（コード内に TODO）。
  - open_prices の欠損（price が None または <= 0）の場合、その銘柄はスキップする実装。price 0 の扱いでエクスポージャーが過少見積りされる可能性がある（コメントでフォールバック案を記載）。

- signal_generator / _generate_sell_signals
  - トレーリングストップや時間ベースの決済判定は未実装（positions テーブルに peak_price / entry_date 等の追加が必要）。
  - features に存在しない保有銘柄は final_score=0.0 扱いで SELL 判定対象になるため、features の更新欠落に注意。

- .env パーサ
  - 基本的な shell 形式（export 句、クォート、行末コメント）に対応するが、極端に複雑なシェル式や特殊なエスケープケースは未保証。

- テスト・カバレッジ
  - DB クエリや数値アルゴリズムに対するユニットテストの記述は今後の課題。

### セキュリティ (Security)
- 環境変数読み込み時に OS 環境変数を保護する機構（protected set）を導入し、.env.local による上書きを制御可能にしている。機密値の取り扱いには引き続き注意。

---

（補足）本 CHANGELOG は現行のソースコードコメント・実装から推測して作成しています。実際のリリースノートとして用いる場合は、実際に行った変更やリリース履歴に合わせて編集してください。