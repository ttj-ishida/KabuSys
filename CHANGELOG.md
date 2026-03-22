# Changelog

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-22

最初の公開リリース。日本株自動売買システムのコアライブラリを追加します。以下の主要機能・モジュールを実装しています。

### 追加
- パッケージ基礎
  - kabusys パッケージの初期化（__version__ = 0.1.0）。公開 API として data, strategy, execution, monitoring をエクスポート。

- 環境設定（kabusys.config）
  - .env ファイルまたは環境変数からの設定読み込み機能を追加。
  - プロジェクトルートの自動検出（.git または pyproject.toml を探索）により、CWD に依存せず .env を読み込む実装。
  - .env パーサー（引用符対応、バックスラッシュのエスケープ処理、export プレフィックス対応、インラインコメント処理）を実装。
  - .env 読み込みの優先順位: OS 環境 > .env.local（override）> .env（override=False）。既存 OS 環境変数は protected として保護。
  - 自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD のサポート（テスト用途）。
  - Settings クラスを実装し、J-Quants / kabuステーション / Slack / DB パス 等のプロパティと、値の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）を提供。
  - 必須環境変数未設定時は明示的に ValueError を送出する _require() を実装。

- 研究用ファクター計算（kabusys.research.factor_research）
  - モメンタムファクター calc_momentum(): 約1/3/6ヶ月リターン、200日移動平均乖離率を計算。
  - ボラティリティ / 流動性ファクター calc_volatility(): 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
  - バリューファクター calc_value(): raw_financials からの最新財務データと組み合わせて PER / ROE を算出（EPS=0/欠損は None）。
  - DuckDB を用いた SQL ベースの実装。prices_daily / raw_financials テーブルのみ参照。外部 API にはアクセスしない設計。

- 特徴量正規化 / 保存（kabusys.strategy.feature_engineering）
  - research モジュールで計算した生ファクターを統合し、ユニバースフィルタ・Zスコア正規化（zscore_normalize を利用）・クリッピング（±3）を適用して features テーブルへ UPSERT（日付単位の置換）する build_features() を実装。
  - ユニバースフィルタ実装: 最低株価 300 円、20日平均売買代金 5 億円を閾値としてフィルタリング。
  - 休場日や当日欠損に対応するため target_date 以前の最新価格を参照。
  - トランザクション（BEGIN/COMMIT/ROLLBACK）とバルク挿入により日付単位の原子性を保証。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合して銘柄ごとのコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算し、重み付き合算で final_score を算出する generate_signals() を実装。
  - デフォルトの重みと閾値を実装:
    - デフォルト重み: momentum=0.40, value=0.20, volatility=0.15, liquidity=0.15, news=0.10
    - BUY 閾値: 0.60
    - ストップロス閾値: -8%
    - Bear 判定の最小サンプル数: 3
  - AI スコアの統合（ai_score を sigmoid でマッピング、regime_score を集計して Bear レジームを判定）。
  - 欠損コンポーネントは中立値 0.5 で補完する方針（欠損銘柄の不当な降格を防止）。
  - Bear レジーム検知時は BUY シグナルを抑制。
  - 保有ポジションのエグジット判定（ストップロス、スコア低下）を実装する _generate_sell_signals()。positions テーブル / 最新価格を参照し、価格欠損時は SELL 判定をスキップ。
  - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。

- 研究支援ツール（kabusys.research.feature_exploration）
  - 将来リターン計算 calc_forward_returns(): 指定 horizon（デフォルト [1,5,21]）に対する将来リターンを一度のクエリで取得。
  - IC（Spearman の ρ）計算 calc_ic(): factor と将来リターンのランク相関を計算。データ不足時は None を返す。
  - ランク変換ユーティリティ rank()（同順位は平均ランク）。
  - factor_summary(): 各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
  - pandas 等に依存せず標準ライブラリのみで実装。

- バックテストフレームワーク（kabusys.backtest）
  - ポートフォリオシミュレータ（kabusys.backtest.simulator）
    - PortfolioSimulator: BUY/SELL の擬似約定、平均取得単価の管理、履歴（DailySnapshot）・約定記録（TradeRecord）を保持。
    - 約定ロジック: SELL を先に処理、BUY は残資金と手数料を考慮して株数を算出。スリッページ率・手数料率に基づく価格調整。
    - mark_to_market() により終値での時価評価を行い DailySnapshot を記録。価格欠損時は 0 評価と警告ログ。
  - メトリクス計算（kabusys.backtest.metrics）
    - バックテスト評価指標を計算: CAGR、Sharpe Ratio（無リスク=0）、Max Drawdown、Win Rate、Payoff Ratio、取引数。
  - バックテストエンジン（kabusys.backtest.engine）
    - run_backtest(): 本番 DB から指定期間のデータをインメモリ DuckDB にコピーして日次ループでシミュレーションを実行。
    - _build_backtest_conn(): 必要なテーブル（prices_daily, features, ai_scores, market_regime, market_calendar）を日付範囲でコピー。signals / positions を汚染しない設計。
    - 日次ループの流れを実装:
      1. 前日シグナルを当日の始値で約定
      2. simulator の positions を positions テーブルに書き戻し（generate_signals の SELL 判定に利用）
      3. 終値で時価評価・スナップショット記録
      4. generate_signals() による当日シグナル生成
      5. シグナルに基づくポジションサイジングと翌日の約定準備
    - 実行結果を BacktestResult (history, trades, metrics) として返却。

- パッケージエクスポート
  - backtest パッケージで run_backtest / BacktestResult / DailySnapshot / TradeRecord / BacktestMetrics を __all__ で公開。
  - research パッケージで calc_* / zscore_normalize / factor_summary / rank 等を公開。
  - strategy パッケージで build_features / generate_signals を公開。

### 既知の制限（ドキュメントに明記されている未実装項目）
- signal_generator のエグジット条件では一部の条件（トレーリングストップ、時間決済）が未実装（positions テーブルに peak_price / entry_date が必要）。
- factor_research の一部（PBR・配当利回り等）は現バージョンで未実装。
- 外部依存のデータ操作（kabu API 実行層、Slack 通知等）の実動作はこのコアでは実装されておらず、別モジュール/実行層での統合が必要。

### 変更
- 初回リリースのためなし。

### 修正
- 初回リリースのためなし。

### セキュリティ
- 初回リリースのためなし。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時はリポジトリのコミット履歴やリリース日付、変更差分に基づいて更新してください。