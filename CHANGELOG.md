CHANGELOG.md
=============

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-03-22

Added
-----
- 初期リリース: KabuSys — 日本株自動売買システムの骨組みを追加。
- パッケージエントリポイント
  - src/kabusys/__init__.py にバージョンと主要サブパッケージを公開（data, strategy, execution, monitoring）。
- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）。
  - 高度な .env パーサ実装（export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメント判定のルール）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD サポート。
  - OS 環境変数の保護（.env.local による上書き時も保護可能）。
  - Settings クラスにアプリケーション設定プロパティを追加（J-Quants / kabu API / Slack / DB パス / 環境・ログレベル検証など）。不正値は ValueError を送出。

- 戦略（src/kabusys/strategy）
  - 特徴量エンジニアリング（feature_engineering.build_features）
    - research モジュールが算出した生ファクターを取得してマージ、ユニバースフィルタ（最低株価・平均売買代金）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（DELETE + bulk INSERT）し、トランザクションで原子性を担保。
    - 欠損や異常値への耐性を考慮した実装。
  - シグナル生成（signal_generator.generate_signals）
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - コンポーネントはシグモイド変換・平均化で統合し final_score を算出。重みはデフォルト値を提供し、ユーザー指定値は検証・正規化して反映。
    - Bear レジーム判定（ai_scores の regime_score の平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - BUY / SELL シグナルの生成（BUY は閾値超過、SELL はストップロスやスコア低下）と signals テーブルへの日付単位置換（トランザクション）。
    - SELL 優先ポリシー（SELL 対象は BUY から除外してランク再付与）。
    - 不正な入力（重みの非数値・負値など）はログ出力して無視。
    - ログによる詳細な状況通知（欠損データや価格取得失敗時の警告）。

- リサーチ（src/kabusys/research）
  - ファクター計算モジュール（factor_research）
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）の計算（DuckDB SQL ベース、ウィンドウ関数使用）。
    - Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）および true_range の厳密な NULL 扱い。
    - Value（per, roe）の計算。raw_financials から target_date 以前の最新レコードを選択して価格と組合せ。
    - 各関数は prices_daily / raw_financials のみ参照し、外部 API へアクセスしない設計。
  - 特徴量探索（feature_exploration）
    - 将来リターンの一括取得（任意ホライズン。SQL で LEAD を利用して効率的に取得）。
    - IC（Spearman の ρ）計算（ランク付け関数を実装、同順位は平均ランクで処理）。
    - factor_summary による基本統計量計算（count/mean/std/min/max/median）。
    - pandas 等に依存しない、標準ライブラリと DuckDB のみで完結する実装。
  - research パッケージの主要関数を __all__ で公開。

- バックテスト（src/kabusys/backtest）
  - メトリクス（metrics.calc_metrics）
    - CAGR / Sharpe / Max Drawdown / Win Rate / Payoff Ratio / 総約定数を計算するユーティリティ。
  - シミュレータ（simulator.PortfolioSimulator）
    - cash, positions, cost_basis を管理し、BUY/SELL の擬似約定（スリッページ・手数料考慮）を実装。
    - BUY の株数調整（手数料込みで資金内に収める再計算）と SELL の全量クローズ挙動。
    - mark_to_market による日次スナップショット記録（終値欠損時は警告して 0 扱い）。
    - TradeRecord / DailySnapshot のデータモデルを dataclass で定義。
  - エンジン（engine.run_backtest）
    - 本番 DuckDB からインメモリ DuckDB へ必要テーブルをコピー（signals/positions を汚さないため）。
    - 日次ループ: 前日シグナル約定 → positions 書き戻し → 時価評価記録 → generate_signals 実行 → 発注リスト作成 の流れを実装。
    - 取引日カレンダー取得、始値/終値の取得ユーティリティ、positions の冪等書き戻しを提供。
    - バックテスト結果を BacktestResult（history, trades, metrics）で返却。

Changed
-------
- （初回リリースにつき該当なし）

Fixed
-----
- （初回リリースにつき該当なし）

Security
--------
- （初回リリースにつき該当なし）

注意事項 / 既知の制限
--------------------
- 一部戦略ロジックの未実装箇所を注記（feature_engineering / signal_generator 内の docstring に記載）。
  - 例: トレーリングストップ・時間決済（positions テーブルに peak_price / entry_date が必要）などは未実装。
- Value ファクター: PBR・配当利回りは現バージョンでは未対応。
- signals / features / positions などの DB スキーマ（カラム名・NULL 可否）は data.schema 側の定義に依存。実行前にスキーマ初期化が必要。
- .env 自動ロードはプロジェクトルートが特定できない場合スキップされる。CI/テスト等で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。
- generate_signals は AI スコアが未登録でも中立値（0.5）で補完して扱う設計。ただし ai_scores が少ない場合のレジーム判定はサンプル閾値で保護。

公開 API（抜粋）
----------------
- kabusys.settings (Settings インスタンス)
- kabusys.strategy.build_features(conn, target_date) -> int
- kabusys.strategy.generate_signals(conn, target_date, threshold=..., weights=None) -> int
- kabusys.research.calc_momentum / calc_volatility / calc_value / calc_forward_returns / calc_ic / factor_summary / rank
- kabusys.backtest.run_backtest(conn, start_date, end_date, ...) -> BacktestResult
- kabusys.backtest.DailySnapshot, TradeRecord, BacktestMetrics

その他
-----
- 各モジュールはログ出力（logging）を利用しており、詳細なデバッグ情報と警告が得られます。
- DuckDB を主要な時系列・ファクタ計算のデータ処理基盤として利用する設計で、SQL と Python の組合せで効率的に処理を行います。

今後の予定（例）
----------------
- 未実装のエグジット条件（トレーリングストップ・時間決済）を実装。
- 追加ファクター（PBR・配当利回り）とより高度なポジションサイジング（部分利確等）。
- execution 層（kabu API 連携）および monitoring 周りの実装拡充。

--- 
（この CHANGELOG はソースコードからの推測に基づいて作成しています。実際のリリースノートとして使用する場合は必要に応じて補足・修正してください。）