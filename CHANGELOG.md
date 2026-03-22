# Changelog

すべての重要な変更はこのファイルで管理します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。主な追加点・設計方針は以下の通りです。

### 追加（Added）
- パッケージ初期化
  - パッケージメタ情報を追加（kabusys.__version__ = 0.1.0）。
  - 公開モジュールとして data, strategy, execution, monitoring を定義。

- 環境設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込むユーティリティを実装。
  - プロジェクトルート検出機能：.git または pyproject.toml を基準に自動検出（cwd に依存しない）。
  - .env の自動読み込み（優先順位: OS 環境 > .env.local > .env）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーは次の特徴をサポート：
    - コメント行／空行の無視、`export KEY=val` 形式への対応
    - シングル／ダブルクォートを含む値（バックスラッシュエスケープ対応）
    - クォートなし値でのインラインコメント処理（直前が空白/タブの場合のみ）
  - 環境変数取得ヘルパー（必須キー未設定時は ValueError）。
  - Settings クラスを提供（J-Quants / kabu ステーション / Slack / DB パス / 環境フラグ / ログレベル等のプロパティ）。

- 研究・ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算。
    - calc_volatility: 20日 ATR（atr_pct）、20日平均売買代金、出来高比率の計算。
    - calc_value: EPS を用いた PER と ROE の取得（target_date 以前の最新財務データを使用）。
    - DuckDB を用いた SQL + Python ベースの実装（prices_daily / raw_financials のみ参照）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: スピアマンのランク相関（IC）計算。
    - factor_summary: count/mean/std/min/max/median の統計要約。
    - rank: 同順位は平均ランクとするランク付けユーティリティ。
  - research パッケージのエクスポートを整備。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features:
    - research モジュールから取得した生ファクターをマージし、ユニバースフィルタ（最低株価、平均売買代金）を適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
    - DuckDB の features テーブルへ日付単位で置換（DELETE → INSERT）し、トランザクションで原子性を保証。
    - ルックアヘッドバイアス防止のため target_date 時点のデータのみ使用。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score は重み付き合算（デフォルト重みを定義）。ユーザ指定の weights を受け付け、検証・正規化して合計が 1 になるよう補正。
    - Bear レジーム判定（ai_scores の regime_score 平均 < 0 かつサンプル数閾値以上）。
    - BUY: threshold（デフォルト 0.60）を超えた銘柄を採用（Bear 時は BUY を抑制）。
    - SELL: positions を参照してストップロス・スコア低下でエグジット判定。
    - signals テーブルへ日付単位で置換（トランザクションで原子性）。
    - 不整合・欠損データ（価格欠損・features 欠落等）に対するロギングと安全対策を実装。

- バックテストフレームワーク（kabusys.backtest）
  - simulator:
    - PortfolioSimulator による擬似約定／ポートフォリオ管理（BUY は割当資金に基づく株数計算、SELL は保有全量クローズ）。
    - スリッページ・手数料モデル、約定記録（TradeRecord）、日次スナップショット（DailySnapshot）の記録。
    - mark_to_market: 終値が欠損する銘柄は 0 評価し WARNING を出力する安全策。
  - metrics:
    - calc_metrics: CAGR/Sharpe/MaxDrawdown/WinRate/PayoffRatio/TotalTrades を計算。
  - engine:
    - run_backtest: 本番 DB から必要期間のテーブルをインメモリ DuckDB にコピーしてバックテストを実行（signals/positions を汚染しない）。
    - 必要なデータ範囲に限定してコピーすることでパフォーマンスを改善（start_date - 300 日からコピー）。
    - 日次ループのステップ（前日シグナル約定 → positions 書込 → 時価評価 → generate_signals → ポジションサイジング）を実装。
    - positions 書き戻し（冪等）ユーティリティを提供。

- トランザクション・エラー処理
  - features / signals 更新でトランザクションを使用。失敗時はロールバックを試行し、ロールバック失敗時には警告ログを出力。

### 変更（Changed）
- 設計方針・実装上の注意を多数ドキュメント化（docstring 内に StrategyModel.md / BacktestFramework.md に準拠する旨を明記）。
- weights の検証ロジックを堅牢化：未知キーや非数値、NaN/Inf、負値をスキップして警告出力、合計が 0 の場合はデフォルトにフォールバック、合計が1でない場合はスケーリングして正規化。

### 修正（Fixed）
- データ欠損時の安全対策を強化：
  - シグナル生成・売却判定で価格が取得できない銘柄は SELL 判定をスキップし警告を出す。
  - 保有銘柄が features に存在しない場合は final_score=0 とみなして明示的に警告を出す（不整合検知）。
  - simulator の買付時に手数料込みで買付可能株数を再計算するロジックを追加し、資金不足時の誤約定を防止。

### 既知の制限（Known issues / TODO）
- signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等が必要であり未実装。
- feature_engineering は avg_turnover をフィルタに使用するが、features テーブル自体には avg_turnover を保存しない（フィルタ用のみ）。
- research モジュールは pandas 等の外部依存を使用せず標準ライブラリ＋DuckDBの SQL で実装しているため、一部の集計は手作業で実装している（将来的に最適化の余地あり）。

### 互換性と移行（Compatibility / Migration）
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN
  - SLACK_CHANNEL_ID
  - （任意）DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL
- 自動環境読み込みはプロジェクトルートの .env / .env.local を参照します。CI / テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DB スキーマ（features / ai_scores / positions / prices_daily / raw_financials / market_calendar 等）を期待します。バックテストは本番 DB を直接更新しないため、既存の DB をコピーして使用可能です。

---

今後のリリースでの予定（例）
- ポジション管理の詳細強化（部分利確・トレーリングストップ）
- execution 層（kabu ステーション連携）実装
- モニタリング／アラート（Slack 通知）の統合
- テストカバレッジ拡充とパフォーマンス最適化

（必要であれば、各ファイル単位のより詳細な変更点や実装方針の抜粋を別ドキュメントとして追記できます。）