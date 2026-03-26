# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを採用しています。

## [Unreleased]

### 追加予定
- ドキュメント整備、テストケース追加、CI設定
- 銘柄別単元情報やより細かい手数料モデルの導入（todoで示唆あり）
- 未実装のエグジット条件（トレーリングストップ、時間決済）の実装

---

## [0.1.0] - 2026-03-26

初回公開リリース。本バージョンは日本株自動売買システムのコア機能群を含みます。

### 追加
- パッケージ基盤
  - kabusys パッケージ初期構成。公開 API として data, strategy, execution, monitoring をエクスポート。

- 設定・環境変数管理 (kabusys.config)
  - .env 自動読み込み（プロジェクトルート判定: .git または pyproject.toml を探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト用）。
  - .env パーサ実装:
    - export KEY=VAL 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメント処理（クォート無しは '#' の直前が空白/タブの場合のみコメント扱い）
  - .env 読み込み時の上書き制御（OS環境変数保護用 protected セット）。
  - Settings クラス提供:
    - 必須環境変数取得時の検証とエラーメッセージ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID 等）
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）
    - デフォルト値（KABU_API_BASE_URL、データベースパス等）を提供

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定: select_candidates（スコア降順、同点は signal_rank でタイブレーク）
  - 重み計算:
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア加重、全スコア0の際は等配分にフォールバックし WARNING 出力）
  - リスク調整:
    - apply_sector_cap（同一セクター集中防止。売却予定銘柄はエクスポージャー計算から除外、"unknown" セクターは制限適用しない）
    - calc_regime_multiplier（market regime に基づく投下資金乗数を返す。既知レジーム以外は警告を出して 1.0 にフォールバック）
  - 口数（株数）計算:
    - calc_position_sizes
      - allocation_method: "risk_based", "equal", "score" に対応
      - risk_based: risk_pct / (price * stop_loss_pct) に基づく算出
      - 等配分/スコア配分: portfolio_value と weight に基づく割当
      - 単元丸め（lot_size）、1銘柄上限（max_position_pct）、投下資金上限（max_utilization）
      - cost_buffer を考慮した合計資金超過時のスケールダウンと残差処理（lot 単位で再配分するアルゴリズム実装）
      - 価格欠損時のスキップ（ログ出力）

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features 実装:
    - research モジュールから生ファクター取得（momentum / volatility / value）
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）
    - Z スコア正規化（指定カラム）、±3 でクリップ
    - DuckDB に対する日付単位の置換アップサート（トランザクションで原子性保証、失敗時はロールバック）
    - 処理ログ（INFO/DEBUG）出力

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals 実装:
    - features と ai_scores を組み合わせてコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完
    - ファクタ重みのマージと正規化（不正値はスキップ、合計が1でない場合は再スケール）
    - Bear レジーム検知に基づく BUY 抑制（AI の regime_score の平均が負の場合、サンプル数閾値あり）
    - BUY シグナル閾値（デフォルト 0.60）超過銘柄の BUY 生成（ランク付け）
    - SELL シグナル生成（エグジット判定）:
      - ストップロス（終値 / avg_price - 1 < -8%）
      - スコア低下（final_score < threshold）
      - 価格欠損時は SELL 判定をスキップし警告（誤クローズ防止）
      - features に存在しない保有銘柄は final_score=0.0 とみなし SELL 対象にする（警告）
    - signals テーブルへの日付単位置換（トランザクションで原子性保証）

- リサーチ機能 (kabusys.research)
  - ファクター計算:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（20日 ATR、atr_pct、avg_turnover、volume_ratio）
    - calc_value（最新財務データに基づく PER / ROE）
  - 特徴量探索:
    - calc_forward_returns（指定ホライズンの将来リターンを一括取得、horizons バリデーション）
    - calc_ic（Spearman のランク相関で IC を計算。有効レコード 3 未満で None）
    - factor_summary（count/mean/std/min/max/median を計算）
    - rank（同順位は平均ランク。round(..., 12) により ties の安定化）

- バックテスト (kabusys.backtest)
  - PortfolioSimulator:
    - DailySnapshot / TradeRecord データクラス
    - execute_orders: SELL を先に処理し全量クローズ、BUY を後処理（スリッページ・手数料を考慮）
    - スリッページ率・手数料率を引数で指定。lot_size による丸めに対応
  - メトリクス計算:
    - calc_metrics により CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades を算出
    - 相応の数値安定化（データ不足時は 0.0 を返す等）

### 変更
- 初版のため過去バージョンからの変更点はありません。

### 修正
- 初版のため過去バージョンからの修正点はありません。

### 注意事項 / 既知の制限
- 一部機能は将来拡張想定（銘柄ごとの lot_size マスタ、トレーリングストップ / 時間決済など）。
- apply_sector_cap 内で price が欠損（0.0）の場合、エクスポージャーが過少見積りされる可能性がある旨を TODO として注記。
- generate_signals の Bear 判定は ai_scores のサンプル数に依存しており、サンプル不足時は誤判定を避けるため Bear とみなさない挙動。
- 一部 SQL は DuckDB を前提としている（ROW_NUMBER/ウィンドウ関数等）。

---

（注）この CHANGELOG は与えられたコードベースの内容から推測して作成した要約です。実際のコミット履歴やリリースノートがある場合はそちらに基づいて調整してください。