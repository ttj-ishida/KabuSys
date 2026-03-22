# CHANGELOG

すべての重要な変更はこのファイルに記録します。本ファイルは「Keep a Changelog」の形式に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0 — 2026-03-22

## [0.1.0] - 2026-03-22
初回公開リリース。日本株向け自動売買システムのコア機能を提供する初期実装を追加しました。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期化（バージョン情報、サブパッケージ公開）を追加。
  - __all__ に data, strategy, execution, monitoring を公開。

- 環境設定 / .env 管理（kabusys.config）
  - .env / .env.local ファイルの自動読み込み機能を追加（プロジェクトルート判定：.git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションを追加。
  - .env パースの強化:
    - export キーワード対応
    - シングル／ダブルクォート内でのバックスラッシュエスケープ処理
    - インラインコメントの取り扱い（クォート有無に応じた挙動）
  - 上書きポリシー:
    - OS 環境変数を保護する protected オプションをサポート
    - .env と .env.local の読み込み優先度を実装（OS 環境変数 > .env.local > .env）
  - Settings クラスを追加し、アプリ設定値の取得プロパティを提供（J-Quants / kabu API / Slack / DB パス / システム設定）。
  - 必須環境変数未設定時の明確なエラー（_require）と入力値検証（KABUSYS_ENV, LOG_LEVEL の許容値チェック）を導入。

- リサーチ（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率（MA200）を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: target_date 以前の最新財務データと株価から PER / ROE を計算。
    - DuckDB を用いた効率的なウィンドウ集計と欠損制御。
  - feature_exploration:
    - calc_forward_returns: 翌日/翌週/翌月等の将来リターンを一括取得する関数を追加（ホライズンの検証あり）。
    - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
    - rank: 同順位は平均ランクとするランク変換ユーティリティ。
  - research パッケージの __all__ を整備して主要ユーティリティを公開。
  - 研究用モジュールは外部ライブラリ（pandas 等）に依存しない実装方針。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features: research で計算した生ファクターをマージ・ユニバースフィルタ（最低株価・最低平均売買代金）を適用し、指定カラムを Z スコア正規化・±3 クリップして features テーブルへ日付単位で UPSERT（DELETE + bulk INSERT + トランザクション）する処理を実装。
  - 正規化ユーティリティとして kabusys.data.stats.zscore_normalize を参照。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals: features と ai_scores を統合して各銘柄のコンポーネント（momentum/value/volatility/liquidity/news）スコアを算出し、重み付け合算で final_score を計算、BUY（閾値超え）/SELL（エグジット条件）を生成して signals テーブルへ日付単位で書き込む処理を実装。
  - デフォルト重み・閾値を実装（デフォルト重みは momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10、閾値 0.60）。
  - weights の入力バリデーションと自動正規化（合計が 1.0 でない場合の再スケール）を実装。
  - Bear レジーム判定（AI の regime_score 平均が負でかつ十分サンプルがある場合）による BUY 抑制を実装。
  - SELL 条件:
    - ストップロス（終値/avg_price - 1 < -8%）
    - final_score の閾値割れ
  - _generate_sell_signals は positions / prices_daily を参照し、価格欠損や不正データ時のログ出力・スキップ動作を実装。
  - signals テーブルの置換はトランザクション + バルク挿入で原子性を確保。

- バックテストフレームワーク（kabusys.backtest）
  - simulator:
    - PortfolioSimulator: メモリ内でのポジション管理、BUY/SELL 約定ロジック、スリッページ・手数料考慮、約定記録（TradeRecord）、日次時価評価（DailySnapshot）を実装。
    - BUY は資金配分に基づき発注、SELL は保有全量クローズ（部分利確/部分損切りは未対応）。
    - 約定処理は SELL を先に処理し、BUY を後に処理することで資金確保（SELL 優先）を実装。
    - mark_to_market は終値欠損時に 0 として評価し警告ログを出力。
  - metrics:
    - calc_metrics / BacktestMetrics: CAGR、Sharpe、最大ドローダウン、勝率、ペイオフレシオ、総トレード数を計算するユーティリティを実装。
  - engine:
    - run_backtest: 本番 DuckDB から指定期間分をインメモリ DuckDB にコピーしてバックテストを実行するワークフローを実装。
    - データコピーは date フィルタリング済み（prices_daily, features, ai_scores, market_regime）で、market_calendar は全件コピー。
    - 日次ループ:
      1. 前日シグナルを当日始値で約定（simulator）
      2. positions を DB に書き戻し（generate_signals の SELL 判定で参照）
      3. 終値で時価評価・スナップショット記録
      4. generate_signals を実行して翌日のシグナルを生成
      5. ポジションサイジング（max_position_pct に基づく割当）
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20
    - DBコピー時の例外は警告ログとして扱い、可能な範囲で処理を継続。

### 変更
- （初期リリースのため履歴上の変更はありません）

### 修正
- （初期リリースのため履歴上の修正はありません）

### 既知の制限 / 未実装事項
- signal_generator のトレーリングストップ、時間決済（保有 60 営業日超）等の一部エグジット条件は未実装（コード内コメントに記載）。
- simulator の約定モデルは簡易化（SELL は全量クローズ、部分利確非対応）。
- 各処理は DuckDB 上の特定テーブル（prices_daily, features, ai_scores, raw_financials, positions, signals, market_calendar 等）に依存します。これらのスキーマ・データが整っていることが前提です。
- AI スコアや財務データ欠損時は中立値や None 補完を行う設計のため、データ供給が結果に大きく影響します。

### セキュリティ
- 特筆すべき既知のセキュリティ問題はありません（ただし環境変数にトークンを格納する使い方は運用上の注意が必要です）。

---

次回リリースでは、以下の改善が検討されています（非網羅）:
- 部分利確・部分損切り、トレーリングストップの実装
- position sizing の多様化（等分割、リスクベース等）
- モジュール単位のユニットテスト追加と CI 設定
- より高度なシミュレーション（流動性制約・板情報の反映）

（注）本 CHANGELOG はソースコード中の docstring と実装内容から推測して作成しています。実際の運用・設計ドキュメントと差異がある可能性があります。