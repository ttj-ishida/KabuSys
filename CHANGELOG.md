# Changelog

すべての変更は Keep a Changelog の形式に準拠しています。  
このファイルはリポジトリ内のコード実装（src/kabusys 以下）から推測して作成しています。

## [0.1.0] - 2026-03-26

初回リリース相当。日本株自動売買システムのコアライブラリを提供します。主な追加点は以下の通りです。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを定義（kabusys.__init__）。
  - バージョン: 0.1.0

- 環境設定 / ロード機能（kabusys.config）
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込み。
  - 読み込み優先度: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサーを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、コメント処理）。
  - ファイル読み込み失敗時に警告を出す処理を追加。
  - Settings クラスを追加し、環境変数から各種設定（J-Quants / kabu API / Slack / DB パス / システムモード / ログレベル）を取得・バリデーション。
  - 必須変数未設定時は明示的に ValueError を送出する _require() を用意。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定:
    - select_candidates(): スコア降順、同点は signal_rank でタイブレークして上位 N を選択。
  - 配分重み:
    - calc_equal_weights(): 等配分（1/N）。
    - calc_score_weights(): スコア加重（スコア総和が 0 の場合は等配分にフォールバック）。
  - ポジションサイズ決定:
    - calc_position_sizes(): risk_based / equal / score の allocation_method をサポート。
      - risk_based: 許容リスク率、損切り率に基づく株数算出。
      - equal/score: ウェイトに基づく配分、per-position/max_utilization/aggregate cap を考慮。
      - 単元（lot_size）丸め、単元単位での端数再配分（残余キャッシュを用いた補正）を実装。
      - cost_buffer により手数料・スリッページを保守的に見積もる。
  - リスク調整:
    - apply_sector_cap(): 同一セクターの既存エクスポージャが閾値（デフォルト 30%）を超える場合、新規候補を除外。売却予定銘柄（sell_codes）をエクスポージャ計算から除外可能。sector_map にない銘柄は "unknown" として扱い、セクター上限は適用しない。
    - calc_regime_multiplier(): 市場レジーム（bull/neutral/bear）に応じたレバレッジ乗数（1.0 / 0.7 / 0.3）。未知レジームは 1.0 にフォールバックし警告を出す。

- 戦略（kabusys.strategy）
  - 特徴量生成:
    - build_features(conn, target_date): research で計算した原ファクターをマージ・ユニバースフィルタ適用・Z スコア正規化（クリッピング ±3）して features テーブルへ日単位で置換（冪等）。ユニバース条件: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
  - シグナル生成:
    - generate_signals(conn, target_date, threshold=0.6, weights=None): features と ai_scores を統合して final_score を算出し、BUY/SELL シグナルを生成して signals テーブルへ日単位で置換（冪等）。
      - デフォルト重みを定義し、ユーザ指定重みは検証・マージ・再スケーリング。
      - AI スコア未登録銘柄は中立扱い（news = 0.5）で補完。
      - Bear レジーム検知時は BUY シグナルを抑制（レジーム判定には ai_scores の regime_score を使用。サンプル数が少ない場合は誤判定防止のため Bear とみなさない）。
      - SELL シグナル（エグジット）判定を実装（ストップロス -8% / final_score が閾値未満）。
      - features に存在しない保有銘柄は final_score = 0.0 と見なして SELL 対象にする。
      - SQL トランザクションで signals の置換を行い、失敗時にロールバック。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を用いてモメンタム・ボラティリティ・バリュー系ファクターを算出。各関数はデータ不足時に None を返す設計。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 将来リターンを一括 SQL で取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンの ρ（ランク相関）を計算。サンプル不足（<3）や分散ゼロ時には None を返す。
    - factor_summary(records, columns): 各ファクターの count/mean/std/min/max/median を計算。
    - rank(values): 同順位は平均ランクを返す安定したランク関数（丸め対策あり）。

- バックテスト（kabusys.backtest）
  - metrics:
    - BacktestMetrics dataclass を定義（cagr, sharpe_ratio, max_drawdown, win_rate, payoff_ratio, total_trades）。
    - calc_metrics(history, trades) を提供。CAGR/Sharpe/MaxDD/勝率/PayoffRatio を計算。
  - simulator:
    - DailySnapshot / TradeRecord dataclass を定義。
    - PortfolioSimulator: メモリ内でポートフォリオ状態を管理（cash, positions, cost_basis, history, trades）。
      - execute_orders(signals, open_prices, slippage_rate, commission_rate, trading_day=None, lot_size=1) を実装。
      - SELL を先に処理、保有全量クローズ（部分利確未対応）。
      - スリッページと手数料を考慮した約定モデル、トレードレコードへ反映。
      - （実装途中でファイル末尾が切れているが、主要なインタフェースと基本動作を定義）。

- モジュールエクスポート整理
  - portfolio/research/strategy モジュールの __all__ で主要 API を整理して公開。

### 変更 (Changed)
- （初回リリースのため該当なし。実装上のフォールバック/保護的な挙動は設計上の仕様として導入）
  - 例: score 加重で合計スコアが 0 の場合は等配分にフォールバック（警告ログ）。
  - features が空の場合は BUY シグナルをスキップし、SELL 判定のみ実施。

### 修正 (Fixed)
- env ファイル読み込みの安全性向上:
  - ファイルオープン失敗時に warnings.warn を出すようにして例外でプロセスが止まらないように保護。
- データ欠損時の保護:
  - 価格欠損時は SELL 判定やポジションサイズ計算をスキップして誤処理を防止（警告ログを出力）。
  - トランザクションのロールバック失敗時に警告を出力する保守的な処理を追加。

### 注意点 / 既知の制限 (Known issues / Limitations)
- position_sizing の lot_size は現在グローバル一律。将来的に銘柄別 lot_map に拡張する予定。
- apply_sector_cap のエクスポージャ算出は price_map の欠損（price=0.0）で過少見積りされ得るため、将来的に前日終値や取得原価を用いたフォールバック検討が必要。
- signal_generator の一部トレーリングストップや時間決済（保有 60 営業日超過）は未実装（実装要件はコメントで記載）。
- simulator の BUY 約定ロジックの一部（ファイル末尾）が切れているため、細部の挙動は完全実装を要確認。

---

今後のリリースでは以下を想定:
- 戦略の追加パラメータや AI スコア連携強化
- 単元/取引コスト周りの拡張（銘柄別 lot/手数料モデル）
- トレーリングストップや時間決済などエグジット条件の追加
- テストカバレッジと CI ワークフローの整備

（この CHANGELOG はコードベースからの推測に基づいて作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴 / リリースノートを参照してください。）