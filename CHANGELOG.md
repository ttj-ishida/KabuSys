# Changelog

すべての重要な変更はこのファイルに記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
リリースはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-26
初回公開リリース

### Added
- パッケージ基盤
  - kabusys パッケージを追加。バージョンは 0.1.0。
  - パッケージエクスポート: data, strategy, execution, monitoring を __all__ として公開。

- 設定 / 環境変数管理 (kabusys.config)
  - .env ファイルまたは OS 環境から設定を自動ロードする仕組みを実装。
    - プロジェクトルートの検出は __file__ の親ディレクトリを辿り `.git` または `pyproject.toml` を基準とするため、CWD に依存しない。
    - 読み込み優先順位: OS 環境 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサを実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、行末コメントの取り扱いに対応。
  - Settings クラスを実装し、典型的な設定項目（J-Quants トークン、kabu API、Slack、DB パス、実行環境、ログレベルなど）をプロパティとして提供。
    - 必須環境変数が未設定の場合は ValueError を送出する `_require` を提供。
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェックを実装（許容値を限定）。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder
    - select_candidates: BUY シグナルのソートと上位 N 抽出（スコア降順、同点は signal_rank でタイブレーク）。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分（全スコア 0 の場合は等配分にフォールバックし WARNING を出力）。
  - risk_adjustment
    - apply_sector_cap: セクターごとの既存エクスポージャを計算し、指定比率を超えているセクターからの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックし警告を出力。
  - position_sizing
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じた発注株数計算を実装。
      - risk_based: 許容リスク率（risk_pct）と stop_loss_pct に基づくポジションサイズ計算。
      - equal/score: weight に基づくポジション計算。
      - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、全体投下上限（max_utilization）、cost_buffer を用いた保守的見積り、aggregate cap によるスケールダウン（残差処理で lot_size 単位の追加配分）を実装。
      - 価格欠損時は該当銘柄をスキップしログを出力。

- 戦略（Strategy） (kabusys.strategy)
  - feature_engineering
    - build_features: research モジュールから取得した生ファクターをマージし、ユニバースフィルタ（最低株価、20日平均売買代金）を適用、数値カラムを Z スコア正規化 → ±3 にクリップし、features テーブルへ日付単位で置換（トランザクションで原子性確保）。
    - 正規化対象列やフィルタ閾値は定数化（例: _MIN_PRICE=300 円, _MIN_TURNOVER=5e8 円）。
  - signal_generator
    - generate_signals: features と ai_scores を統合して最終スコア（final_score）を算出し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で置換。
      - ファクター重みのマージ・検証・再スケール処理を実装（無効なユーザー指定はスキップして警告）。
      - コンポーネントスコア計算（momentum/value/volatility/liquidity/news）。
      - AI スコア未登録時は中立 0.5 で補完。
      - Bear レジーム検知時は BUY を抑止（regime 判定は ai_scores の regime_score 平均 < 0 かつサンプル数閾値を満たす場合）。
      - SELL シグナルはストップロス（-8%）および final_score が閾値未満の場合に判定。価格欠損や features 未登録時の扱い（警告・デフォルト処理）を明確化。
      - DB 操作はトランザクションで原子性を保証。

- 研究（Research） (kabusys.research)
  - factor_research
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を参照して各種ファクター（mom_1m/3m/6m、ma200_dev、atr_pct、avg_turnover、volume_ratio、per/roe）を計算。
    - SQL ベースの実装で欠損処理・ウィンドウ集計を適切に扱う。
  - feature_exploration
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21] 営業日）先までの将来リターンを一度に取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効サンプル数が 3 未満なら None）。
    - factor_summary / rank: ファクター列の基本統計量とランク変換ユーティリティを実装。
  - zscore_normalize を含めたライブラリ的エクスポートを提供。

- バックテスト (kabusys.backtest)
  - metrics
    - BacktestMetrics データクラスと calc_metrics API を実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades を算出）。
    - 各内部関数で数値検査やエッジケース（データ不足、ゼロ分散など）をハンドリング。
  - simulator
    - PortfolioSimulator: メモリ内の現金・保有・平均取得単価を管理し、売買約定の擬似処理を実装。
      - execute_orders は SELL を先に、BUY を後に処理（SELL は保有全量クローズ）。
      - スリッページ（BUY は +、SELL は -）、手数料、lot_size の取り扱いを実装。
      - TradeRecord / DailySnapshot データクラスを提供。

### Changed
- 初回リリースにつき変更履歴はなし（初期実装）。

### Fixed
- 初回リリースにつき修正履歴はなし。

### Known issues / TODO
- apply_sector_cap:
  - price_map に価格が無い場合 0.0 と扱い、エクスポージャが過少見積りされてブロックが外れる可能性がある（将来的に前日終値や取得原価などのフォールバックを検討）。
- position_sizing:
  - lot_size は全銘柄共通（現状固定）。将来的に銘柄別 lot_map を受け取り拡張する予定あり（TODO コメントあり）。
- signal_generator:
  - トレーリングストップや時間決済（保有 60 営業日超過）は未実装。positions テーブルに peak_price / entry_date 情報が必要。
- feature_engineering:
  - features テーブルへ挿入するカラムや命名は現行設計に基づく。将来的な拡張に伴い互換性に注意が必要。
- .env パーサ:
  - 複雑な corner case（ネストしたクォートや無効なエスケープシーケンス等）では未検証。基本的な .env 書式に対して互換性を持たせているが、さらに厳密な仕様が必要な場合は調整予定。

### Security
- 本リリースには特段のセキュリティ修正は含まれません。機密情報（トークン・パスワード等）は環境変数で管理する設計を採用しています。Settings._require により必須変数の不足は明示的に検出されます。

---

今後のリリースでは、実運用向けの堅牢化（詳細なエラー監視・リトライ、銘柄別単元対応、トレーリングストップ等）や execution 層（kabu API 連携）、monitoring 機能の充実を予定しています。