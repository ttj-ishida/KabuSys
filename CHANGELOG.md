# Changelog

すべての注目すべき変更点を記録します。フォーマットは Keep a Changelog に準拠しています。  
このファイルはコードベースから推測して自動生成しています（実際のコミット履歴ではありません）。

## [0.1.0] - 2026-03-26

初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装しています。主な追加点は以下の通りです。

### 追加
- パッケージ基本情報
  - パッケージ名とバージョンを設定（kabusys v0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に定義。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装（プロジェクトルート判定: .git / pyproject.toml）。
  - .env のパース機能を強化（export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理などに対応）。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / システム環境（env, log_level, is_live 等）のプロパティを取得可能に。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定: select_candidates — スコア降順・同点は signal_rank でタイブレークして上位 N を選択。
  - 重み計算:
    - calc_equal_weights — 等金額配分。
    - calc_score_weights — スコア正規化による配分。全スコアが 0 の場合は等配分にフォールバックし警告を出力。
  - リスク調整:
    - apply_sector_cap — セクター集中制限。既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier — 市場レジームに応じた投下資金乗数（bull/neutral/bear のマッピング、未知レジームは警告と共に 1.0 フォールバック）。
  - ポジションサイズ決定:
    - calc_position_sizes — allocation_method に応じた株数算出を実装（risk_based, equal, score）。単元（lot_size）丸め、1銘柄上限や aggregate cap（available_cash に応じたスケールダウン）、cost_buffer による保守的コスト見積り、残差処理（fractional remainder に基づく追加配分）を実装。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features — research モジュールから取得した生ファクターをマージ、ユニバースフィルタ適用（最低株価・最低出来高）、Zスコア正規化（clip ±3）、DuckDB に対する日付単位の UPSERT（トランザクションで原子性保証）を実装。
  - 標準化対象カラムやフィルタ閾値は定数化（例: _MIN_PRICE=300, _MIN_TURNOVER=5e8）。

- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals — features と ai_scores を統合して最終スコア（final_score）を計算、BUY/SELL シグナルを生成・signals テーブルへ日付単位で置換保存する処理を実装。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算するユーティリティを実装。欠損コンポーネントは中立値 0.5 で補完。
  - レジーム判定: ai_scores の regime_score を集計して Bear 相場を判定（サンプル数が十分でない場合は Bear としない）。Bear 時は BUY を抑制。
  - SELL 判定: ストップロス（終値が平均取得単価に対して -8% 以下）およびスコア低下（final_score < threshold）を実装。SELL は BUY より優先され、signals の一貫性を保つため BUY から除外するロジックを含む。
  - weights の入力検証・正規化（未知キーや無効値は無視し、合計が 1 でない場合はスケール調整）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum — mom_1m/mom_3m/mom_6m と ma200_dev（200日移動平均乖離）を算出。
    - calc_volatility — atr_20, atr_pct, avg_turnover, volume_ratio を算出（true range の NULL 伝播の扱いに注意）。
    - calc_value — raw_financials から最新財務データを取得して PER/ROE を算出（EPS が 0/欠損なら PER は None）。
  - 特徴量解析（kabusys.research.feature_exploration）:
    - calc_forward_returns — 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic — Spearman ランク相関（IC）を計算（有効レコードが 3 未満なら None）。
    - factor_summary — count/mean/std/min/max/median を計算。
    - rank — 同順位は平均ランクで処理（round による ties 対応）。

- バックテスト（kabusys.backtest）
  - metrics — バックテスト評価指標を計算（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio, total trades）。DailySnapshot / TradeRecord のみを入力とする純粋関数群。
  - simulator — PortfolioSimulator を実装:
    - メモリ内でのキャッシュ・保有株数・コスト基準・履歴・約定履歴を管理。
    - execute_orders: SELL を先に処理（保有全量クローズ）、その後 BUY を処理。スリッページ（BUY:+ / SELL:-）・手数料率に基づく約定、lot_size をサポート。
    - TradeRecord / DailySnapshot のデータモデルを定義。

- DuckDB / トランザクション対応
  - 各種処理で DuckDB を使用した SQL クエリを採用。features / signals などへの書き込みはトランザクション（BEGIN / COMMIT / ROLLBACK）で原子性を担保。

### 変更
- 新規プロジェクトのため変更履歴はなし（初版）。

### 既知の制限・注意点（今後の改善予定）
- .env ローダ:
  - プロジェクトルート検出に .git / pyproject.toml を使用。これに該当しないレイアウトでは自動ロードをスキップする。
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する TODO が残る。
- calc_position_sizes:
  - 現状 lot_size は全銘柄共通として扱う。将来的に銘柄別 lot_map を受け取る拡張予定（TODO コメントあり）。
- シグナル生成（generate_signals）:
  - SELL の一部条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - Bear レジーム判定に必要なサンプル不足時の扱いは conservative に設計されている（サンプル不足なら Bear とみなさない）。
- バックテストシミュレータ:
  - SELL は保有全量をクローズする実装で、部分利確や部分損切りは未対応。
- 依存/統合ポイント:
  - kabusys.data.stats.zscore_normalize など一部ユーティリティは data パッケージ側に依存（本リリースで data モジュールの実装が別ファイルにある前提）。
- エラーハンドリング:
  - DuckDB のトランザクションで例外時に ROLLBACK を試みるが、ROLLBACK 自体が失敗した場合はログに警告を出力して再送出する実装。

### マイグレーション / 設定
- 環境変数例（必須）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
- 自動 .env ロードを無効化する場合:
  - 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定。

---

今後のリリースでは以下を想定しています（優先順の一例）:
- positions テーブルの拡張（peak_price / entry_date）によるトレーリングストップ・時間決済の導入
- 銘柄別 lot_size 対応
- 部分クローズ／部分利確のサポート
- price フォールバックロジック（前日終値等）の追加
- テストカバレッジと CI ワークフローの整備

（注）本 CHANGELOG は提供されたソースコードから機能・仕様を推定して作成しています。実際のコミットメッセージやリリースノートが存在する場合はそちらを優先してください。