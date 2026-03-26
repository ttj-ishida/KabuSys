# Changelog

すべての注目すべき変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」準拠で、バージョニングは SemVer に従います。

## [0.1.0] - 2026-03-26

初回リリース。本プロジェクトのコア機能を実装しました（日本株向け自動売買フレームワークの基盤）。

### 追加
- パッケージ基盤
  - パッケージエントリポイントとバージョンを追加（kabusys.__version__ = 0.1.0）。
  - モジュール構造: config, portfolio, strategy, research, backtest, execution（骨組み）、monitoring（公開APIに含むが実装は別途）のエクスポートを定義。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git / pyproject.toml を基準に探索）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサを強化: export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープのサポート、インラインコメントの取り扱い（クォートあり/なしの差分処理）。
  - 読み込み時の上書きポリシー: OS 環境変数を保護する protected キーセットを導入（.env は既存変数を上書きせず、.env.local は上書き）。
  - Settings クラスを提供し、アプリケーションで使用する環境変数をプロパティ経由で取得（必須変数は未設定時に ValueError を送出）。
  - 主要設定項目: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト付与）, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV（検証）, LOG_LEVEL（検証）など。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順で選択（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算（全スコアが 0 の場合は等分配へフォールバックして WARNING を出力）。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限。既存保有を基にセクター別エクスポージャーを計算し、上限を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（"bull"=1.0, "neutral"=0.7, "bear"=0.3、未知レジームは 1.0 として WARN）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて銘柄ごとの発注株数を計算。単元株（lot_size）で丸め、単銘柄上限・aggregate cap（利用可能現金）・cost_buffer（手数料・スリッページ見積り）考慮のスケーリングを実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features: research モジュールの生ファクター（momentum / volatility / value）を取得し、
    - ユニバースフィルタ（最低株価・最低平均売買代金）を適用、
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ、
    - DuckDB 上で日付単位の置換（DELETE + INSERT をトランザクションで実行）して features テーブルへ保存（冪等処理）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals:
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算。
    - final_score を重み付きで算出（デフォルト重みは StrategyModel.md 所定の値）。weights 引数は検証・補正（未知キー無視、負値/非数値スキップ、合計を 1 に正規化）。
    - Bear レジーム検出時には BUY シグナルを抑制（ai_scores の regime_score 平均で判定、サンプル数不足では Bear としない）。
    - BUY シグナル閾値（デフォルト 0.60）超過で BUY、エグジット条件（ストップロス・スコア低下）で SELL を生成。
    - SELL が出た場合は同日の BUY 候補から除外し、シグナルを書き込み（transactions により日付単位置換を実施）。
    - 価格欠損や features 未登録時の防御的なログ出力と挙動（スキップや score=0 扱い）を装備。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率を計算（データ不足時は None）。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算（必要サンプル不足時は None）。
    - calc_value: raw_financials から最新財務を取得し PER/ROE を計算。EPS 欠損/0 の場合は PER を None。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: スピアマン ランク相関（IC）を計算（有効サンプルが 3 未満なら None）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランクを返すランク付けユーティリティ（丸めによる ties 検出対策あり）。
  - 研究モジュールは DuckDB のみ依存し、外部ライブラリ（pandas 等）を使用しない設計。

- バックテスト（kabusys.backtest）
  - metrics:
    - BacktestMetrics dataclass と calc_metrics 実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades）。
    - それぞれの内部計算に対する境界条件チェック（サンプル不足やゼロ除算回避）。
  - simulator:
    - DailySnapshot / TradeRecord 定義。
    - PortfolioSimulator: メモリ内でのポートフォリオ状態管理と擬似約定ロジックを実装。約定時にスリッページ・手数料を適用し、SELL を先に処理してから BUY を実行する方針。部分約定は今後の lot_size 運用で対応（デフォルト lot_size=1）。

### 変更（実装上の防御・改善）
- DB 書き込みは日付単位の置換（DELETE→INSERT）をトランザクションで実行し、例外時には ROLLBACK を試みることで整合性を確保。
- 多くの関数で入力の欠損値・不正値を検査し、欠損時にはログ出力の上でスキップまたは中立値で補完する動作を採用（例: features 未登録銘柄の final_score=0.0 扱い、AI スコア欠損時は中立 0.5 補完など）。
- .env パーサと Settings により環境変数の取り扱いを厳格化（検証エラーで早期に通知）。

### 修正（バグ回避・制約）
- price が欠損している場合に発生しうる誤判定を防止する防御コードを複数個所に追加（例: セクターエクスポージャー計算で price が 0 の場合の注意コメント、売却判定で価格欠損時は SELL 判定をスキップして警告ログを出す）。
- weight 引数の不正な値（負、非数値、未知キー）を無視してデフォルトにフォールバックするロジックを実装。

### 既知の制約・TODO（今後の改善項目）
- apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられ、ブロックが外れる懸念あり。前日終値や取得原価を用いたフォールバックの検討が必要。
- position_sizing: 将来的には銘柄ごとの lot_size（stocks マスタの導入）に対応する設計に拡張予定。
- signal_generator のエグジット条件: トレーリングストップ（peak_price）や時間決済（保有日数によるエグジット）は positions テーブルの拡張（peak_price / entry_date）を要するため未実装。
- strategy.feature_engineering は zscore 正規化ユーティリティに依存。外れ値処理や別の正規化方針を将来検討予定。
- execution パッケージはエクスポート位置存在するが、外部発注（kabuステーション等）との統合実装は別途。

### セキュリティ
- 機密情報（API トークン等）は Settings で必須項目として管理し、未設定時に例外を発生させることで不注意な起動を防止する設計。

---

今後のリリースでは、実取引の execution 層統合、銘柄別取引単位の対応、追加のエグジット戦略、テストカバレッジ拡充、ドキュメントの整備を予定しています。