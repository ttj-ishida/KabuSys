# Changelog

すべての重要な変更点をこのファイルに記録します。
フォーマットは「Keep a Changelog」仕様に準拠します。

## [0.1.0] - 2026-03-26

初回リリース。日本株自動売買システムのコアライブラリ群を実装しました。
以下は実装済みの主要機能・モジュールと設計上の注意点です。

### 追加 (Added)
- パッケージ基盤
  - パッケージ初期化と公開 API を定義（kabusys.__init__）。
  - バージョン番号を `__version__ = "0.1.0"` として設定。

- 環境設定 (kabusys.config)
  - .env ファイル（.env, .env.local）および OS 環境変数からの自動読み込み機能を実装。
    - プロジェクトルート判定は .git または pyproject.toml を基準に行い、パッケージ配布後も CWD に依存しない挙動を実現。
    - 環境変数の自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env パーサ実装（引用符、エスケープ、export プレフィックス、インラインコメント処理に対応）。
  - 読み込み時の上書き挙動（override）と OS 環境変数保護（protected keys）に対応。
  - Settings クラスを提供し、主要設定値をプロパティで取得：
    - 必須環境変数検証（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）
    - デフォルト値（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH 等）
    - KABUSYS_ENV の検証（development / paper_trading / live）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の便宜プロパティ

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: スコア降順、同点時は signal_rank 昇順で上位 N を選定。
    - calc_equal_weights: 等金額配分の重みを返す。
    - calc_score_weights: スコア加重配分を実装（スコア合計が 0 の場合は等配分にフォールバックし WARNING を出力）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター別エクスポージャー計算を行い、指定比率を超過するセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す（未知レジームは 1.0 でフォールバックし WARNING を出力）。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に対応した株数計算を実装。
      - risk_based: risk_pct・stop_loss_pct に基づく株数算出。
      - equal/score: 重みと max_utilization に基づく配分。
      - _max_per_stock（1銘柄上限）計算、lot_size（単元）丸め処理。
      - aggregate cap（available_cash）を超える場合のスケーリング処理を実装。cost_buffer により手数料・スリッページを保守的に見積もり、端数は lot_size 単位で残差順に追加配分するアルゴリズムを採用。
      - 将来的に銘柄別 lot_size マップへの拡張を想定する設計コメントを追加。

- 特徴量処理・シグナル生成 (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュール（calc_momentum / calc_volatility / calc_value）からファクター取得。
    - ユニバースフィルタ（最低株価・最低平均売買代金）適用。
    - 指定列を Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 にクリップ。
    - DuckDB に対して対象日分を削除してから挿入する日付単位の置換（トランザクションで原子性確保）。
  - signal_generator.generate_signals:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完、最終スコアを重み付け合成。
    - デフォルト重みを用意し、ユーザ指定重みの検証と合計が 1.0 でない場合のリスケールを実装。
    - Bear レジーム検知時は BUY シグナルを抑制（regime_score の平均が負かつサンプル数閾値以上）。
    - SELL シグナルはストップロス（終値/avg_price -1 < -8%）とスコア低下に基づいて判定（positions / prices を参照）。SELL は BUY より優先され、signals テーブルへ日付単位の置換で書き込み。
    - features が空の場合は BUY 生成を行わず SELL 判定のみ実施。
    - features に存在しない保有銘柄は SELL 判定時に final_score=0.0 と見なす（警告ログあり）。

- リサーチユーティリティ (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装（DuckDB SQL を用いた計算）。
    - 各関数は (date, code) 単位の dict リストを返す仕様。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）での将来リターンを LEAD を使って一括取得。
    - calc_ic: スピアマン相関（ランク相関）を実装。ties は平均ランクで処理。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位は平均ランク扱いでランク付け（丸めによる ties 検出漏れ対策あり）。

- バックテスト (kabusys.backtest)
  - metrics.calc_metrics: DailySnapshot と TradeRecord から主要評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を算出。
    - Sharpe は年次化標準偏差（営業日252日）を使用。
  - simulator.PortfolioSimulator:
    - シンプルなポートフォリオシミュレータを実装（メモリ内状態のみ、DB 参照なし）。
    - execute_orders: SELL を先に処理し（保有全量クローズ）、その後 BUY を処理。スリッページ・手数料モデルに対応し TradeRecord / DailySnapshot を管理。
    - TradeRecord / DailySnapshot の dataclass 定義を提供。

### 修正 (Changed)
- 初回リリースのため該当なし。

### 修正 (Fixed)
- 初回リリースのため該当なし。

### 非推奨 (Deprecated)
- 初回リリースのため該当なし。

### 削除 (Removed)
- 初回リリースのため該当なし。

### セキュリティ (Security)
- 初回リリースのため該当なし。

---

## 注意点・既知の制約
- .env 読み込み:
  - プロジェクトルートが特定できない場合は自動ロードをスキップする（テスト・ライブラリ配布時の安全策）。
  - .env の読み込みに失敗した場合は警告を出して続行する。
- apply_sector_cap:
  - price_map に価格が欠損（0.0 や未定義）があるとエクスポージャーが過少評価される可能性がある旨をコメント（将来、前日終値等のフォールバックを検討）。
- signal_generator の SELL 条件に未実装の項目:
  - トレーリングストップ（peak_price が必要）
  - 時間決済（保有日数による自動決済）
- position_sizing:
  - 現状 lot_size は全銘柄共通の単一パラメータ。将来的に銘柄別 lot_map を受け取る拡張を想定。
- feature_engineering / generate_signals:
  - いずれも DuckDB のテーブル構成（prices_daily, raw_financials, features, ai_scores, positions, signals 等）に依存するため、スキーマが揃っていることが前提。
- 一部のロジックはログ出力や WARNING を伴うフォールバックを採用しており、運用時にはログ確認が推奨されます。

---

この CHANGELOG はコードベース（src/ 以下）から推測して作成しています。実際のリリースノートとして使用する場合は、ビルド・リリース工程での追加情報（変更日、コミットハッシュ、移行手順など）を補完してください。