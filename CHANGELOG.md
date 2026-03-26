# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。  

## [Unreleased]


## [0.1.0] - 2026-03-26
初回公開リリース。

### Added
- パッケージ基盤
  - kabusys パッケージ初期化（src/kabusys/__init__.py）。主要サブパッケージをエクスポート: data, strategy, execution, monitoring。
  - バージョン識別: `__version__ = "0.1.0"`。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env/.env.local 自動読み込み機能（プロジェクトルートを `.git` または `pyproject.toml` から探索）。
  - 読み込み優先度: OS 環境 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env の行パーサは `export KEY=val`、クォート（シングル/ダブル）とバックスラッシュエスケープ、インラインコメントの扱いに対応。
  - Settings クラスを提供（必須環境変数取得用 `_require`、各種プロパティ: JQUANTS/KABU/Slack トークンや DB パス、環境モード検証、ログレベル検証など）。
  - 有効な環境値やログレベルの検証を実装（不正な値は ValueError）。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 候補選定: `select_candidates`（スコア降順、同点は signal_rank でブレーク）。
  - 重み計算: `calc_equal_weights`, `calc_score_weights`（スコア合計が 0 の場合は等分配にフォールバックし警告）。
  - リスク調整: `apply_sector_cap`（既存保有のセクター比率が閾値を超える場合に該当セクターの新規候補を除外）、`calc_regime_multiplier`（市場レジームに応じた投下資金乗数）。
  - ポジションサイジング: `calc_position_sizes`（allocation_method = "risk_based" / "equal" / "score" をサポート、単元株丸め、per-position と aggregate 上限、cost_buffer を用いた保守的見積り、available_cash に基づくスケーリングロジック）。

- 戦略（strategy）
  - 特徴量エンジニアリング: `build_features`（research モジュールの生因子を結合しユニバースフィルタ->Z スコア正規化->クリップ->DuckDB の features テーブルへ日付単位で UPSERT）。
    - ユニバース基準: 最低株価 300 円、20 日平均売買代金 >= 5 億円。
  - シグナル生成: `generate_signals`（features + ai_scores を統合して component スコアを算出、final_score に基づく BUY/SELL 判断、Bear レジーム検知による BUY 抑制、SELL はストップロスとスコア低下判定）。
    - デフォルトのファクター重み、閾値、stop_loss など StrategyModel に準拠した実装。
    - signals テーブルへトランザクションを用いた日付単位置換（冪等）。

- リサーチ（research）
  - ファクター計算: `calc_momentum`, `calc_volatility`, `calc_value`（prices_daily / raw_financials を参照、各種期間のリターン・MA・ATR・出来高指標・PER/ROE 等を算出）。
  - 特徴量探索ユーティリティ: `calc_forward_returns`（任意ホライズンの将来リターン）、`calc_ic`（Spearman ランク相関による IC）、`factor_summary`（基本統計量）、`rank`（同順位は平均ランクで処理）。
  - 実装は DuckDB を用いた SQL ベースで、外部ライブラリ（pandas 等）には依存しない設計。

- バックテスト（backtest）
  - ポートフォリオシミュレータ: `PortfolioSimulator`（メモリ内での約定処理、SELL を先に処理、BUY は与えられた株数で約定、スリッページ/手数料モデル対応、履歴と約定記録を保持）。
  - データクラス: `DailySnapshot`, `TradeRecord`。
  - メトリクス: `calc_metrics` と内部計算関数（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio 等）。

- 依存・設計ノート
  - DuckDB を用いる設計（DuckDB 接続を引数に取る関数が多数）。
  - 研究/特徴量・シグナル生成は発注 API や execution 層に依存しない純粋関数群（ルックアヘッドバイアス防止のため target_date 時点のデータのみ使用）。
  - 標準ライブラリ中心の実装（外部ライブラリへの依存最小化）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Security
- （該当なし）

### Notes / Known limitations
- `.env` の読み込みで、プロジェクトルートが検出できない場合は自動ロードをスキップする（ライブラリ配布後でも安全に動作する設計）。
- `apply_sector_cap` は "unknown" セクターをセクター上限の対象外とする（明示的に除外しない）。price が 0.0 の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。
- `generate_signals` の SELL 判定で利用する positions テーブルは peak_price / entry_date 等がまだ存在しないことを想定しており、トレーリングストップや時間決済は未実装。
- `calc_position_sizes` の将来的拡張として銘柄別 lot_size（単元）対応の TODO がある（現状は共通 lot_size を引数で指定）。
- AI スコアが未登録の銘柄に対しては中立値（news = 0.5）で補完する実装。
- `calc_score_weights` はスコア合計が 0 の場合に等金額配分へフォールバックし、ログに WARNING を出す。
- レジーム乗数（calc_regime_multiplier）は未知のレジームでフォールバック 1.0、Bear レジームでは BUY シグナル自体を生成しない設計（multiplier は追加セーフガード）。
- 外部データ欠損（価格や財務データ等）がある場合は該当銘柄をスキップまたは中立値で補完する安全志向の実装。

---

この CHANGELOG はコードベースの現状（src/ 配下の実装）から推測して作成しています。詳細なユーザー向け変更履歴やリリースノートは、今後のリリースで追記してください。