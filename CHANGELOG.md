Keep a Changelog 準拠の CHANGELOG.md（日本語）

すべての変更は semver に従います。初版リリースを以下に記録します。

[Unreleased]

# 0.1.0 - 2026-03-26
初回公開リリース。日本株自動売買フレームワークのコア機能を実装しました。主な追加点は以下のとおりです。

Added
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン 0.1.0、公開 API の __all__ に data/strategy/execution/monitoring を登録）。
- 環境設定管理
  - kabusys.config モジュールを追加。
    - .env / .env.local 自動ロード（プロジェクトルートを .git または pyproject.toml で検出）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化。
    - .env の柔軟なパース実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント判定など）。
    - Settings クラスを追加し、J-Quants / kabu ステーション API / Slack / DB パス / 環境（development/paper_trading/live）/ログレベル等のプロパティを提供。必須環境変数未設定時は ValueError を投げる。
    - 環境値バリデーション（KABUSYS_ENV, LOG_LEVEL）。
- ポートフォリオ構築
  - ポートフォリオ関連関数群（純粋関数）を実装。
    - select_candidates: BUY シグナルをスコア降順で選抜（タイブレークは signal_rank）。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（スコア全0 の場合は等金額へフォールバック、警告ログ出力）。
    - calc_position_sizes: 株数（発注量）算出ロジックを実装。
      - allocation_method による振る舞い（"risk_based" / "equal" / "score"）。
      - risk_pct / stop_loss_pct / max_position_pct / max_utilization / lot_size / cost_buffer をサポート。
      - per-pos / aggregate 上限処理、コストバッファを考慮した保守的見積もり、スケールダウンと lot_size 単位での残差配分ロジック。
- リスク制御
  - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、セクター集中が max_sector_pct を超える場合に同セクターの新規候補を除外。
    - sell_codes 引数で当日売却予定銘柄をエクスポージャー計算から除外可能。
    - "unknown" セクターは上限適用対象外（除外しない）。
    - 価格欠損時の注意（将来的にフォールバック価格導入予定。ログに TODO を記載）。
  - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を返す（既知でないレジームは警告を出力して 1.0 にフォールバック）。
- 特徴量エンジニアリング（strategy）
  - build_features(conn, target_date): research モジュールの生ファクターを取得し、ユニバースフィルタ（株価・売買代金）、Z スコア正規化（指定列）、±3 でのクリップ、features テーブルへ日付単位置換（トランザクションで原子性）を実行。DuckDB 接続を使用。
  - ユニバースフィルタ条件: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
- シグナル生成（strategy）
  - generate_signals(conn, target_date, threshold, weights): features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成して signals テーブルへ日付単位で書き込む。
    - momentum/value/volatility/liquidity/news のコンポーネントスコア計算（シグモイド・Zスコア処理・PER の変換など）。
    - AI ニューススコア補完（未登録は中立補完）。weights の入力検証と正規化（既定重みはデフォルト実装）。
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）で BUY シグナルを抑制。
    - SELL 条件実装（ストップロス、スコア低下）。SELL は BUY より優先して処理し、BUY からは除外。
    - トランザクション処理（BEGIN/COMMIT/ROLLBACK）で原子性を保証。
    - 未実装のエグジット（トレーリングストップ、時間決済）はコード内で明示。
- リサーチ（research）
  - ファクター計算モジュールを実装（DuckDB ベース、外部依存なし）。
    - calc_momentum: mom_1m/3m/6m、ma200_dev（データ不足時は None）。
    - calc_volatility: atr_20, atr_pct, avg_turnover, volume_ratio（true_range の NULL 伝播制御）。
    - calc_value: target_date 以前の最新 raw_financials を参照して PER / ROE を計算（EPS が 0/欠損なら PER=None）。
  - 解析ユーティリティ
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（SQL による高速取得）。horizons の検証。
    - calc_ic: スピアマンのランク相関（IC）を計算（有効サンプル数が 3 未満なら None）。
    - factor_summary / rank: 基本統計量集計、ランク計算（同順位は平均ランク）。
- バックテスト（backtest）
  - PortfolioSimulator と関連データクラスを実装。
    - DailySnapshot / TradeRecord / PortfolioSimulator（メモリ内状態管理、DB 非依存）。
    - execute_orders: SELL を先に全量クローズ、その後 BUY を処理。open_prices, slippage_rate, commission_rate を反映した約定処理。lot_size パラメータ対応（デフォルト 1、通常は 100 を渡す想定）。
    - 部分約定・部分利確は未対応（全量クローズのみ）。
  - バックテスト指標計算
    - calc_metrics(history, trades) と内部実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 時系列・統計計算は明示的に実装（営業日252日での年次化等）。
- パッケージエクスポート
  - kabusys.portfolio, kabusys.strategy, kabusys.research が主要 API を __all__ で公開。

Security
- 特になし。

Known Issues / Notes / TODO
- apply_sector_cap: price_map の価格欠損（0.0）の場合、エクスポージャーが過小見積もられる可能性がある旨を TODO コメントで記載。将来的に前日終値や取得原価をフォールバックする検討が必要。
- signal_generator のエグジット条件: トレーリングストップや時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
- calc_position_sizes: lot_size を銘柄別にサポートする拡張（lot_map）や stocks マスタとの連携は未実装（TODO）。
- PortfolioSimulator.execute_orders は SELL を保有全量でクローズする（部分利確・部分損切り非対応）。部分約定戦略を適用するには拡張が必要。
- research モジュールは外部ライブラリ（pandas 等）に依存しない設計。大規模データ処理や高度な集計が必要な場合は別途検討。
- Settings._find_project_root は __file__ を起点に探索するため、特定の配布形態で動作が変わる可能性あり。自動ロードは環境変数で無効化可能。
- 一部の関数は入力データの欠損や非数値を厳密にチェックし、欠損時は None を返す・ログ出力する実装になっている（挙動を把握の上ご利用ください）。

参考
- 各モジュール内に設計方針・参考ドキュメント（PortfolioConstruction.md / StrategyModel.md / BacktestFramework.md 等）の参照がコメントで記載されています。実運用や拡張の際はこれらの仕様に合わせてください。

以上。将来的なリリースでは、部分約定対応・銘柄別 lot サイズ・価格フォールバック・追加のエグジット戦略などを優先で実装予定です。