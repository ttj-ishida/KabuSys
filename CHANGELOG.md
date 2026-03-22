# Keep a Changelog — kabusys

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]


## [0.1.0] - 2026-03-22

初期リリース。日本株自動売買システムのコア機能群を実装しました。以下はコードベースから推測した主な追加点・設計上の注意点です。

### Added
- 基本パッケージ構成
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）
  - サブモジュール群を公開: data, strategy, execution, monitoring（__all__）

- 環境変数・設定管理（src/kabusys/config.py）
  - .env / .env.local を自動読み込み（プロジェクトルートは .git または pyproject.toml から検出）
  - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能
  - .env のパース機能を独自実装（export プレフィクス、シングル/ダブルクォート、コメントの取り扱い、バックスラッシュエスケープに対応）
  - override/protected を考慮した env 上書きロジック
  - Settings クラスを提供（J-Quants / kabu API / Slack / DB パス / 実行環境／ログレベル判定など）
  - 必須環境変数未設定時に ValueError を送出する _require() を実装
  - 許容される実行環境は development, paper_trading, live。LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL を検証

- 研究（research）モジュール（src/kabusys/research/*）
  - ファクター計算（factor_research）
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（ma200_dev）を算出
    - calc_volatility: 20日 ATR（atr_20 / atr_pct）、20日平均売買代金、出来高比率を算出
    - calc_value: EPS からの PER、ROE を算出（raw_financials と prices_daily を参照）
    - 各関数は DuckDB の prices_daily / raw_financials のみを参照し、研究用途（ルックアヘッド回避）を考慮して実装
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 指定ホライズンの将来リターン（デフォルト [1,5,21] 営業日）をまとめて取得
    - calc_ic: スピアマンのランク相関（IC）計算、サンプル不足時は None を返す
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクとするランク付けユーティリティ
  - 研究側ユーティリティ（zscore_normalize は外部 data.stats から利用）

- 戦略（strategy）モジュール（src/kabusys/strategy/*）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research 側の生ファクター(calc_momentum/calc_volatility/calc_value)を収集して統合
    - ユニバースフィルタ（最低株価 _MIN_PRICE=300 円、20日平均売買代金 _MIN_TURNOVER=5e8 円）を適用
    - 正規化: 指定カラムを Z スコア正規化（zscore_normalize）、±3 でクリップ（外れ値抑制）
    - 日付単位で features テーブルを置換（堅牢なトランザクション処理、冪等）
    - per（PER）は正規化対象から除外（逆数スコアなど別扱い）
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を組み合わせ、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - コンポーネントはシグモイド変換や反転を利用（例: volatility は反転して低ボラ = 高スコア）
    - final_score を重み付き和で算出（デフォルト重みは StrategyModel.md に準拠）
    - Bear レジーム検知（ai_scores の regime_score 平均が負であり、サンプル数が閾値を満たす場合に Bear と判定）→ Bear 時は BUY を抑制
    - BUY 閾値デフォルト _DEFAULT_THRESHOLD=0.60
    - SELL（エグジット）判定を実装（ストップロス _STOP_LOSS_RATE=-0.08、スコア低下）
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入、冪等）
    - weights の補完・検証（未定義キーや不正値を無視し、合計が 1.0 でなければ再スケール）

- バックテストフレームワーク（src/kabusys/backtest/*）
  - ポートフォリオシミュレータ（simulator.PortfolioSimulator）
    - メモリ内で positions / cost_basis / history / trades を管理
    - execute_orders: SELL を先に処理し（保有全量クローズ）、その後 BUY（alloc に基づくサイジング）
    - スリッページと手数料を考慮した約定価格・約定数量の計算（slippage_rate / commission_rate）
    - BUY は手数料込みで買付可能な株数に再計算するロジック
    - mark_to_market: 終値で時価評価、終値欠損時は 0 評価で WARNING を出力
    - TradeRecord / DailySnapshot のデータ構造を提供
  - メトリクス計算（metrics.calc_metrics）
    - CAGR, Sharpe Ratio（無リスク金利=0）、最大ドローダウン、勝率、ペイオフレシオ、総トレード数 を計算
  - バックテストエンジン（engine.run_backtest）
    - 本番 DuckDB からインメモリ DB へ必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar）をコピー
      - 日付範囲でフィルタし、start_date - 300 日から end_date までをコピー（signals/positions の汚染回避）
      - コピー失敗時は警告ログを出してスキップする処理あり
    - 日次ループ:
      1. 前日シグナルを当日始値で約定（simulator.execute_orders）
      2. positions を DB に書き戻し（generate_signals の SELL 判定が positions を読むため）
      3. 終値で時価評価・スナップショット記録
      4. generate_signals で当日分のシグナルを生成
      5. シグナルに基づき翌日の発注リストを組成（ポジションサイズ上限 max_position_pct）
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20

- ドキュメント的な注記を多数の docstring に記載（設計方針・処理フロー・参照テーブル等）

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Deprecated
- （初回リリースのため該当なし）

### Security
- （本リリースで特筆すべき既知のセキュリティ修正はありません）

### Notes / Known limitations（実装から読み取れる注意点）
- 一部の出口条件は未実装（コメントあり）:
  - トレーリングストップ（peak_price の追跡が必要）
  - 時間決済（保有 60 営業日超過）
  - これらは positions テーブルに peak_price / entry_date 等の追加フィールドが必要
- feature_engineering では per（PER）を正規化対象から外しているため別処理で扱う必要あり
- research モジュールは外部依存（pandas 等）を使わない設計になっているため高速化や複雑な統計処理が必要な場合は拡張の余地あり
- .env の自動読み込みはプロジェクトルート検出に依存する（配布後やインストール環境での挙動に注意）
- バックテスト用データのコピー処理で例外が出た場合は該当テーブルをスキップするため、部分的にデータが欠ける状態でバックテストが進む可能性がある（ログを確認すること）

---

今後のリリースでは、実運用に向けた execution 層（kabu ステーション連携）、監視・アラート（Slack 連携の具体実装）、テストカバレッジの整備、未実装のエグジット条件（トレーリング/時間決済）や追加ファクター（PBR・配当利回り）などの追加が想定されます。