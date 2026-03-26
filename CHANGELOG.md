CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。
リリースは SemVer に従います。

v0.1.0 - 2026-03-26
-------------------

Added
- 初回公開リリース。
- パッケージ基礎
  - パッケージ名: kabusys, バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 主要サブパッケージを公開: data, strategy, execution, monitoring（__all__）。
- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック: __file__ を基点に親ディレクトリを探索し .git または pyproject.toml を検出してルートを特定。
  - .env パーサ実装: コメント、export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理をサポート。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動ロードを無効化するための KABUSYS_DISABLE_AUTO_ENV_LOAD を用意（テスト向け）。
  - 必須キー取得ヘルパ _require と Settings クラスを提供。各種設定プロパティを定義（J-Quants・kabu API・Slack・DB パス・環境種別・ログレベルなど）。
  - 環境値検証: KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。
  - デフォルトパス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"（expanduser による展開）。
- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 候補選定: select_candidates — スコア降順で上位 N を選択（同点は signal_rank でブレーク）。
  - 重み計算: calc_equal_weights（等分配）と calc_score_weights（スコア加重、全スコアが0の際は等分配にフォールバック & WARNING）。
  - リスク制御:
    - apply_sector_cap: 現有ポジションからセクター別エクスポージャを計算し、1セクター当たりの最大比率を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。売却予定銘柄をエクスポージャ計算から除外可能。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（"bull":1.0, "neutral":0.7, "bear":0.3）。未知レジームは 1.0 でフォールバック（警告ログ）。
  - ポジションサイジング: calc_position_sizes
    - allocation_method による株数決定（"risk_based" / "equal" / "score"）。
    - risk_based: リスク許容率 (risk_pct) と stop_loss_pct から目標株数を計算。
    - 等配・スコア配分: 各銘柄の weight を用いた割当、ポートフォリオ内 per-position 上限 (max_position_pct) と aggregate 上限 (max_utilization / available_cash) を考慮。
    - lot_size による単元丸め、price が欠損/0 の場合はスキップ。
    - cost_buffer を用いた約定コスト保守見積もりと aggregate cap 超過時のスケーリング（スケールダウン → fractional 残差に基づく lot 単位での追加配分を行い再現性を確保）。
    - 将来的な拡張として銘柄別 lot_size（stocks マスタ）への注記あり。
- ストラテジー（src/kabusys/strategy/*）
  - 特徴量エンジニアリング: build_features
    - research モジュールの生ファクター（momentum / volatility / value）を取得し統合。
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8）を適用。
    - 指定列を z-score 正規化（zscore_normalize を利用）、±3 でクリップ。
    - DuckDB を用いた日付単位の置換（DELETE + INSERT）で冪等な upsert を実装。
  - シグナル生成: generate_signals
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重みを持ち（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）、入力重みの検証・補完・再正規化を実装。
    - final_score の閾値デフォルトは 0.60。Bear レジーム判定時は BUY シグナルを抑制（Bear 判定ロジックは ai_scores の regime_score 平均が負かつ十分なサンプル数）。
    - SELL シグナルのエグジット判定を実装（ストップロス: -8% を優先、スコア低下によるエグジットなど）。SELL は BUY より優先され、signals テーブルに日付単位で置換書込。
    - 欠損ハンドリング: features に存在しない保有銘柄は final_score=0 と見なして SELL 判定（警告ログ）。
- リサーチ（src/kabusys/research/*）
  - ファクター計算: calc_momentum, calc_volatility, calc_value — prices_daily / raw_financials を用いた純粋関数群。
    - momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200日ウィンドウの存在チェック）。
    - volatility: ATR（20日平均）および相対 ATR（atr_pct）、avg_turnover、volume_ratio（20日）。
    - value: 最新財務データと当日株価から PER, ROE を算出（EPS が 0 または欠損なら PER は None）。
  - 解析ユーティリティ:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得可能な SQL 実装。
    - calc_ic: スピアマンのランク相関（IC）計算。データ不足（有効ペア < 3）時は None を返す。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで処理するランク関数（丸めによる ties 検出安定化あり）。
- バックテスト（src/kabusys/backtest/*）
  - メトリクス: calc_metrics が複数の内部指標を計算して BacktestMetrics を返す（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades）。
  - シミュレータ: PortfolioSimulator
    - メモリ内でポートフォリオ状態管理（cash, positions, cost_basis, history, trades）。
    - execute_orders: SELL を先に、BUY を後に処理。SELL は保有全量クローズ（部分利確・部分損切りは未対応）。
    - スリッページ・手数料を考慮した約定モデル（BUY: +slippage, SELL: -slippage、手数料率 commission_rate）。
    - TradeRecord / DailySnapshot の dataclass 定義。
- 内部実装上の注意点（ログと堅牢性）
  - 価格欠損・データ不足時にスキップや警告ログを出す実装を多所に導入しており、安全側に倒した動作を重視。
  - DB 書込はトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を確保、ROLLBACK 失敗時は警告ログ。

Changed
- 初回リリースにつき該当なし。

Fixed
- 初回リリースにつき該当なし。

Deprecated
- 初回リリースにつき該当なし。

Removed
- 初回リリースにつき該当なし。

Security
- 初回リリースにつき該当なし。

Known issues / Notes
- apply_sector_cap: price_map における price が欠損（0.0）の場合、エクスポージャが過少見積りされ期待どおりのブロックが行われない旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックを検討。
- calc_position_sizes: 現状 lot_size は共通値で 100 を想定。将来的に銘柄別単元サイズを受け取る設計への拡張を注記。
- generate_signals: Bear レジーム発生時には BUY を抑止する仕様。Bear 判定は ai_scores の regime_score に依存するため ai_scores データの品質・カバレッジに注意。
- _require による必須環境変数チェックは ValueError を投げるので、実行環境の設定漏れに注意。
- Simulator の SELL は現状「保有全量クローズ」であり、部分決済やトレーリングストップ等は未実装。

今後の予定（例）
- 銘柄別 lot_size の導入（position_sizing 側拡張）
- apply_sector_cap の price フォールバック実装
- signal_generator のトレーリングストップ・時間決済の実装（positions テーブルに peak_price / entry_date 情報が必要）
- execution 層（kabu API 連携）・monitoring の実装強化

-----
（この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴やリリースポリシーに応じて適宜編集してください。）