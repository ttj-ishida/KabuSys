# CHANGELOG

All notable changes to this project will be documented in this file.

遵守: Keep a Changelog の形式、セマンティックバージョニングに準拠。

---

## [0.1.0] - 2026-03-26

初回リリース — 日本株向け自動売買フレームワークの基礎機能を実装しました。以下はコードベースから推測される主要な追加点・挙動・設計上の注意点です。

### Added
- パッケージ情報
  - パッケージルート: kabusys、バージョン `0.1.0` を設定。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - 自動ロードを無効化する環境変数: `KABUSYS_DISABLE_AUTO_ENV_LOAD`。
  - .env パーサー: export プレフィックス、シングル/ダブル引用符、バックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - .env 読み込み時の上書き制御（override / protected）をサポート。OS 環境変数を保護。
  - 必須環境変数取得用ヘルパー `_require` と Settings クラスを提供。
  - Settings が提供する主要プロパティ:
    - J-Quants / kabu API / Slack トークン類（必須チェック）
    - DB パス（DuckDB / SQLite）のデフォルト
    - 実行環境（development / paper_trading / live）の検証
    - ログレベル検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ヘルパー

- ポートフォリオ構築関連 (kabusys.portfolio)
  - 候補選定 / 重み計算（portfolio_builder）
    - select_candidates: スコア降順、同点時に signal_rank 昇順で上位 N 件を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等配分へフォールバックし警告を出力。
  - リスク調整（risk_adjustment）
    - apply_sector_cap: セクター集中を検出し、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下資金乗数を返す（既定: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして警告。
  - 株数決定・ポジションサイジング（position_sizing）
    - allocation_method に応じた計算: "risk_based" / "equal" / "score" をサポート。
    - risk_based: 許容リスク率 (risk_pct) と stop_loss_pct に基づくベース株数算出。
    - equal/score: ウェイトに基づく投資額算出、lot_size（単元）で丸め。
    - per-stock 上限 (max_position_pct)、全体の資金利用上限（max_utilization）を考慮。
    - cost_buffer を用いた手数料・スリッページの保守的見積り、available_cash を超過する場合のスケーリング処理（端数処理・lot 単位での再配分）を実装。
    - 価格欠損時のスキップや各種ログ出力を備える。

- 戦略（feature engineering / signal generation）
  - 特徴量エンジニアリング（strategy.feature_engineering）
    - research モジュールから生ファクターを取得（momentum / volatility / value）。
    - ユニバースフィルタ（最低株価、20日平均売買代金）適用。
    - 指定カラムの Z スコア正規化（kabusys.data.stats の zscore_normalize を利用）、±3 でクリップ。
    - DuckDB を使い features テーブルへ日付単位で置換（トランザクションで冪等性保証）。
    - 欠損やトランザクション失敗時のロールバック処理とログを実装。
  - シグナル生成（strategy.signal_generator）
    - features と ai_scores を組み合わせて各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - sigmoid, 平均化、欠損補完（None は中立 0.5）等のロジックを実装。
    - デフォルト重みを持ち、ユーザー指定の weights の検証と正規化を行う。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0、サンプル数閾値あり）で BUY シグナル抑制。
    - BUY シグナル閾値 (default 0.60) 以上の銘柄を BUY、保有銘柄に対して SELL 条件（ストップロス／スコア低下）を判定。
    - SELL 優先ポリシー（SELL 銘柄は BUY から除外）と、signals テーブルへ日付単位で置換して保存するトランザクション処理を実装。
    - 価格未取得や features 非存在時の警告ログ出力。

- リサーチ / ファクター計算（kabusys.research）
  - ファクター計算モジュール（research.factor_research）
    - モメンタム: mom_1m/mom_3m/mom_6m、ma200_dev（200 日 MA）を計算。データ不足時は None。
    - ボラティリティ/流動性: ATR(20)、atr_pct、avg_turnover、volume_ratio を計算。true_range 計算は高値/安値/前日終値の欠損を考慮。
    - バリュー: raw_financials から最新財務を取得して PER/ROE を計算（EPS 欠損時は PER=None）。
  - 特徴量探索ユーティリティ（research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）: 複数ホライズンを一度に取得する効率的クエリ実装。horizons の検証あり。
    - IC（calc_ic）: ランク相関（Spearman）の実装。データ不足・等分散のケースをハンドリング。
    - factor_summary / rank: 基本統計量、ランク付け（同順位は平均ランク）を提供。標準ライブラリのみで実装。

- バックテスト（kabusys.backtest）
  - シミュレータ（backtest.simulator）
    - DailySnapshot / TradeRecord のデータ構造を定義。
    - PortfolioSimulator: メモリ内でポジション・コスト基準・履歴・約定記録を管理。
    - execute_orders: SELL を先に処理してから BUY（資金確保のため）。SELL は全量クローズ（部分決済は未対応）。
    - スリッページ（BUY:+、SELL:-）および手数料率を適用して約定価格・コミッションを計算（詳細はコード内の実装に依存）。
  - メトリクス（backtest.metrics）
    - CAGR、シャープレシオ（無リスク金利 = 0）、最大ドローダウン、勝率、ペイオフレシオ、総トレード数を算出するユーティリティを実装。
    - 履歴不足やゼロ除算に対する安全策あり（値を 0.0 にフォールバック）。

- パッケージエクスポート
  - strategy, portfolio, research, backtest など主要 API を __init__ で公開。公開関数一覧が各サブパッケージの __all__ に整備されている。

### Changed
- 初回リリースのため変更履歴はなし（新規実装）。

### Fixed
- 初回リリースのため修正履歴はなし。

### Notes / Known limitations（コード内注釈に基づく）
- 一部機能は将来拡張を想定:
  - position_sizing の lot_size は現状はグローバル固定。将来的な銘柄別 lot_map の導入が想定されている。
  - apply_sector_cap の価格欠損（0.0）の扱いで過少見積りとなる懸念がある（前日終値や取得原価によるフォールバック検討）。
  - signal_generator のトレーリングストップや時間決済は positions テーブルに peak_price / entry_date 情報が必要で現状未実装。
- strategy.feature_engineering / signal_generator / research モジュールは DuckDB のスキーマ（prices_daily、raw_financials、features、ai_scores、positions、signals 等）に依存します。実行前に適切なテーブルが存在することを確認してください。
- execution パッケージは __init__ のみ（現状実装ファイルは未提示）。実際のリアル注文送信ロジックは別実装が必要。

---

今後のリリースでは以下が想定されます（参考）
- 実運用向けの execution 層（kabu API 統合、注文管理）
- モニタリング（Slack 通知など）の実装
- 銘柄別単元・手数料モデルの拡張
- テストカバレッジとエンドツーエンドの CI

もし CHANGELOG に追記してほしい特定の実装詳細や日付/貢献者情報があれば教えてください。