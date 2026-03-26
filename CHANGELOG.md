# CHANGELOG

すべての注目すべき変更点を記録します。本 CHANGELOG は Keep a Changelog に準拠しています。

## [0.1.0] - 2026-03-26

### Added
- 初回リリース。日本株自動売買ライブラリ "KabuSys" を公開。
- パッケージ公開情報
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - パッケージ外部公開 API: data, strategy, execution, monitoring を __all__ でエクスポート。

- 設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定を自動ロードする機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索して特定（cwd 非依存）。自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサ実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの扱いに対応）。
  - Settings クラスを提供し、以下の主要設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH（デフォルト data/kabusys.duckdb）, SQLITE_PATH（デフォルト data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 未設定の必須環境変数取得時は ValueError を送出。

- ポートフォリオ構築（src/kabusys/portfolio/）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順にソートし上位 N を選択（同点時のタイブレーク実装）。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等分配にフォールバック（WARNING ログ）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有を考慮したセクター集中制限。売却予定銘柄の除外、"unknown" セクターの取扱い（上限不適用）をサポート。価格欠損時の注意点はログ/コメントで明示。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対する投下資金乗数を返却。未知レジーム時は 1.0 をフォールバックし警告ログ。
  - position_sizing:
    - calc_position_sizes: allocation_method("risk_based","equal","score") に基づく発注株数計算。リスクベースの計算、単元株（lot_size）丸め、1銘柄上限・ aggregate cap（利用可能現金に基づくスケーリング）、手数料/スリッページ見積り用 cost_buffer による保守的見積り、残差処理による再配分ロジックを実装。

- 戦略（src/kabusys/strategy/）
  - feature_engineering.build_features:
    - research モジュールで計算した生ファクターを取得、ユニバースフィルタ（最低株価・最低平均売買代金）、Z スコア正規化（指定カラム）、±3 でのクリップを行い features テーブルへ日付単位で UPSERT（トランザクション処理で原子性保証）。DuckDB を用いた SQL 結合・トランザクション実装。
  - signal_generator.generate_signals:
    - features と ai_scores を統合し、モメンタム／バリュー／ボラティリティ／流動性／ニュースのコンポーネントスコアを算出。欠損コンポーネントは中立値 0.5 で補完。final_score に基づき BUY シグナルを生成（デフォルト閾値 0.60）。Bear レジーム検知により BUY を抑制。保有ポジションに対してはストップロス／スコア低下による SELL 判定を実装。signals テーブルへ日付単位で置換（トランザクション処理）。
    - weights の検証（未知キーや無効値のスキップ、合計が 1 でない場合の再スケール）を実装。

- リサーチ（src/kabusys/research/）
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を参照し、モメンタム（1/3/6ヶ月、MA200乖離）、ATR ベースのボラティリティ、流動性、PER/ROE の取得を提供。データ不足時の None ハンドリングを行う。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。パフォーマンスのためスキャン範囲を制限。
    - calc_ic: スピアマンのランク相関（IC）を実装。サンプル不足時は None。
    - factor_summary / rank: 基本統計量（count/mean/std/min/max/median）とランク付けユーティリティを提供。
  - zscore_normalize を含む研究ユーティリティを公開。

- バックテスト（src/kabusys/backtest/）
  - metrics.calc_metrics: DailySnapshot / TradeRecord から各種評価指標（CAGR、Sharpe、MaxDrawdown、WinRate、PayoffRatio、TotalTrades）を計算するユーティリティ。
  - simulator.PortfolioSimulator:
    - 擬似約定・ポートフォリオ管理クラスを実装。SELL を先に処理し全量クローズ、BUY は指定株数で約定。スリッページ・手数料モデルを適用し TradeRecord / 日次スナップショットを保持。約定処理におけるログ出力と入力バリデーションを実装。

- トランザクションとエラー安全性
  - DuckDB を用いた書き込み処理では BEGIN/COMMIT/ROLLBACK を使用し、ROLLBACK に失敗した場合は警告ログを出力してエラーが上位に伝搬されるように実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Known limitations / Notes
- apply_sector_cap:
  - "unknown" セクター（sector_map に未登録の銘柄）はセクター上限チェックの対象外になる（設計上の選択）。
  - price_map に価格が欠損（0.0 や未設定）するとセクターエクスポージャーが過小見積りされ、本来ブロックされるべき候補が通ってしまう可能性がある（将来的にフォールバック価格の導入を検討）。
- calc_score_weights:
  - 全銘柄のスコア合計が 0 の場合は等金額配分にフォールバックする。
- signal_generator:
  - Bear レジームでは仕様により generate_signals が BUY をほぼ生成しない設計（さらに safeguard として regime_multiplier が導入されている）。
  - SELL の一部条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price や entry_date が必要）。
- feature_engineering / research:
  - 一部計算はデータ不足時に None を返す。Z スコア正規化やクリップにより外れ値の影響を抑制しているが、入力データ品質を前提とする部分がある。
- パッケージング/エクスポート:
  - public API は __all__ で管理。内部ユーティリティは公開されていない場合がある。

### TODO / Future
- position_sizing: 銘柄ごとの lot_size を stocks マスタから取得する拡張（現在は global lot_size）。
- risk_adjustment の価格フォールバック（前日終値や取得原価）導入検討。
- signal_generator の追加エグジット条件（トレーリングストップ、時間決済）実装。
- 実行層（execution）・モニタリング（monitoring）モジュールの充実（本リリースでは骨組み中心）。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合は適宜調整してください。