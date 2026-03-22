# Changelog

すべての変更は "Keep a Changelog" のフォーマットに準拠しています。  
現在のパッケージバージョン: 0.1.0

注: コードベースから推測して作成した変更履歴です。実際の変更履歴（コミットログ等）と差異がある場合があります。

## [Unreleased]
- （現状変更なし）

## [0.1.0] - 2026-03-22
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ基礎
  - パッケージ名 `kabusys`、バージョン `0.1.0` を定義。
  - モジュールエクスポートの整理（strategy / execution / monitoring / data 等を想定した __all__）。

- 環境設定 / ロード処理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
    - プロジェクトルートは __file__ を起点に `.git` または `pyproject.toml` を探索して特定。
    - 読み込み優先順は OS 環境変数 > .env.local > .env。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能（テスト用）。
    - .env パースは `export KEY=val` やクォート、インラインコメントなどに対応。
    - OS の環境変数を保護するため、既存変数は上書きされない（.env.local は override 可）。
  - Settings クラスを提供（プロパティ経由で必須変数の取得・検証）。
    - 必須環境変数の例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID。
    - デフォルト値: KABUSYS_ENV=development、KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等。
    - KABUSYS_ENV / LOG_LEVEL の値検証（許可値のチェック）。

- ファクター計算（kabusys.research.factor_research）
  - Momentum ファクター:
    - mom_1m / mom_3m / mom_6m（営業日ベース）と 200 日移動平均乖離率（ma200_dev）を計算。
    - 過去スキャン範囲設定とデータ不足のハンドリング（必要行数未満は None を返す）。
  - Volatility / Liquidity ファクター:
    - 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比率（volume_ratio）を計算。
    - true_range の NULL 伝播を明示的に扱い、窓内欠損を考慮。
  - Value ファクター:
    - raw_financials から最新財務（target_date 以前）を取得し PER（price / EPS）と ROE を計算。
    - EPS が 0 または NULL の場合は PER を None にする。
    - PBR / 配当利回りは未実装（将来追加予定）。

- 研究ユーティリティ（kabusys.research.feature_exploration）
  - 将来リターン計算（calc_forward_returns）：target_date から各ホライズン先の終値リターンを計算（デフォルト [1,5,21]）。
  - IC（Information Coefficient）計算（calc_ic）：スピアマンランク相関を実装（同順位は平均ランク）。
  - ファクター統計サマリ（factor_summary）とランク変換ユーティリティ（rank）。
  - 外部依存ライブラリに依存しない純標準ライブラリ実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research で計算した生ファクターを統合・正規化して `features` テーブルへ保存する機能（build_features）。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ。
    - date 単位で DELETE→INSERT（トランザクション）することで冪等性を保証。

- シグナル生成（kabusys.strategy.signal_generator）
  - `features` と `ai_scores` を統合して最終スコア（final_score）を算出し `signals` テーブルへ書き込む機能（generate_signals）。
    - コンポーネントスコア: momentum / value / volatility / liquidity / news（AI）を計算。
    - news（AI）スコアはシグモイド変換で 0–1 に正規化、未登録は中立 0.5 で補完。
    - ファクター重みの検証・補完（デフォルト重みを持ち、不正値をスキップ、合計が 1 になるよう再スケール）。
    - Bear レジーム検出（ai_scores の regime_score 平均が負の場合）で BUY シグナルを抑制。
    - BUY 閾値デフォルト 0.60。BUY はスコア >= threshold、SELL はエグジット条件（ストップロス -8% / final_score 下回り）に基づく。
    - SELL は BUY より優先され、SELL 対象は BUY から除外してランクを再付与。
    - 日付単位で DELETE→INSERT（トランザクション）により signals を冪等に更新。

- バックテストフレームワーク（kabusys.backtest）
  - PortfolioSimulator（backtest.simulator）:
    - メモリ上でポートフォリオ状態を管理、BUY/SELL の擬似約定を実行。
    - スリッページ（指定率）、手数料モデル（約定金額 × commission_rate）に対応。
    - SELL を先、BUY を後に処理。BUY は割当（alloc）ベースで株数を算出、手数料込みで調整。
    - SELL は保有全量をクローズ（部分利確/部分損切りは未対応）。
    - mark_to_market で終値評価、終値欠損時は警告を出して 0 評価。
    - TradeRecord / DailySnapshot 用の dataclass を提供。
  - Backtest エンジン（backtest.engine）:
    - 本番 DB からインメモリ DuckDB へデータコピーしてバックテスト用接続を構築（signals/positions を汚さない）。
    - run_backtest() を実装（デフォルト初期資金 10,000,000 円、スリッページ 0.1%、手数料 0.055%、max_position_pct 20%）。
    - 日次ループ: 前日シグナルを当日始値で約定 → positions を書き戻し（generate_signals の SELL 判定用）→ 終値で時価評価 → generate_signals を呼び出し翌日のシグナル作成 → ポジションサイジングして発注。
    - データコピーは日付範囲で絞る（start_date - 300 日バッファ）。market_calendar は全件コピー。
  - メトリクス（backtest.metrics）:
    - CAGR、Sharpe Ratio（無リスク金利=0）、最大ドローダウン、勝率、Payoff Ratio、総トレード数を計算するユーティリティを実装。
    - Edge case（データ不足、ゼロ除算等）を考慮して 0.0 を返す設計。

- データ/統計ユーティリティの公開（kabusys.research/__init__ 等）
  - zscore_normalize などのユーティリティ参照を公開し、research API をまとめてエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- 環境変数管理において OS 環境変数を保護する仕組みを導入（.env で既存の OS 環境変数を上書きしない）。

### Known limitations / Notes
- 未実装のエグジット条件:
  - トレーリングストップ（peak_price に基づく -10% 等）は未実装。positions テーブルに peak_price / entry_date の追跡が必要。
  - 時間決済（保有 60 営業日超過）の判定は未実装。
- calc_value: PBR / 配当利回りは現状未対応。
- generate_signals:
  - AI ニューススコアはシグモイド変換で扱うが、AI スコアの取得・前処理は別モジュール（ai_scores テーブル）に依存。
  - weights の不正入力をスキップするロジックを持つが、ユーザーへ警告レベルで通知するのみ。
- Simulator の BUY は部分購入のロジックを持たない（shares は整数で切り捨て）。
- run_backtest は本番 DB からデータをコピーする際に一部テーブルのコピー失敗を許容してログに警告を出す設計。
- tests / CI に関する記述はコードからは確認できないため別途整備が必要。

### Migration / 環境設定メモ
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 任意設定（デフォルトあり）:
  - KABUSYS_ENV = {development, paper_trading, live}（デフォルト development）
  - LOG_LEVEL = {DEBUG, INFO, WARNING, ERROR, CRITICAL}（デフォルト INFO）
  - DUCKDB_PATH / SQLITE_PATH のデフォルトパスはそれぞれ data/kabusys.duckdb / data/monitoring.db
- 自動 .env ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

今後の開発予定（想定）
- エグジットロジックの拡張（トレーリングストップ、時間決済）
- 追加のファクター（PBR、配当利回り等）
- execution 層（kabu ステーション連携）と monitoring（Slack 通知等）の実装
- 単体テスト・統合テスト・CI パイプラインの整備

以上。