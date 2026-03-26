# CHANGELOG

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-26

初回公開リリース。日本株自動売買システムのコア機能を実装しました。主な追加内容は以下のとおりです。

### Added
- パッケージ基盤
  - `kabusys` パッケージの初期バージョンを追加（`__version__ = "0.1.0"`、主要サブパッケージを `__all__` で公開）。
- 環境設定 / ロード
  - `kabusys.config`:
    - .env ファイル（`.env` / `.env.local`）をプロジェクトルート（.git または pyproject.toml）から自動読み込みする仕組みを実装。CWD に依存しない探索。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動読み込みの無効化が可能。
    - .env 行パーサーは `export KEY=val`、クォート付き値（バックスラッシュエスケープ対応）、インラインコメントの扱い等に対応。
    - OS 環境変数を保護する `protected` 挙動（`.env.local` は上書き可能だが OS 環境変数は保護）。
    - `Settings` クラスを公開し、主要な必須環境変数をプロパティ経由で取得（`JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID` 等）。デフォルト値やバリデーション（`KABUSYS_ENV` / `LOG_LEVEL` の許容値）を実装。
    - データベースパスのデフォルト（DuckDB: `data/kabusys.duckdb`, SQLite: `data/monitoring.db`）を提供。
- ポートフォリオ構築
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順、同点は `signal_rank` でタイブレーク）。
    - 重み計算 `calc_equal_weights`（等分配）および `calc_score_weights`（スコア比率）。全スコアが 0 の場合は等分配にフォールバックし WARNING を出力。
  - `kabusys.portfolio.risk_adjustment`:
    - `apply_sector_cap`：既存保有のセクター露出が上限を超える場合、新規候補を除外するロジック（当日売却予定銘柄を露出計算から除外可能、`unknown` セクターは除外対象としない）。
    - `calc_regime_multiplier`：市場レジーム (`bull`/`neutral`/`bear`) に基づく投下資金乗数（1.0, 0.7, 0.3）。未知レジームは 1.0 にフォールバックして WARNING を出力。
  - `kabusys.portfolio.position_sizing`:
    - `calc_position_sizes`：配分方式（`risk_based`, `equal`, `score`）に基づく発注株数の計算。単元（`lot_size`）丸め、1銘柄上限（`max_position_pct`）、集計上限（`available_cash`）、コストバッファ（`cost_buffer`）を考慮したスケーリングと端数配分（残差に基づく lot 単位での追加配分）を実装。
    - `risk_based` ではリスク許容率・損切り率から基準株数を算出。
    - 将来的な拡張のため銘柄別 lot_map についての TODO 注記あり。
- 特徴量・シグナル生成（戦略）
  - `kabusys.strategy.feature_engineering.build_features`:
    - 研究モジュールから生ファクターを取得し、ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定列に対して Z スコア正規化（`kabusys.data.stats.zscore_normalize` を利用）、±3 でクリップ。
    - DuckDB 接続を受け取り、日付単位で features テーブルへ冪等的に書き込み（トランザクションで原子性を保証）。
  - `kabusys.strategy.signal_generator.generate_signals`:
    - `features` と `ai_scores` を統合して各コンポーネントスコア（momentum / value / volatility / liquidity / news）を計算（シグモイド等を利用）。
    - 欠損コンポーネントは中立 0.5 で補完、weights は入力チェックとフォールバック/正規化を適用。
    - Bear レジーム時の BUY 抑制（AI のレジームスコアの平均により判定）。
    - BUY シグナル閾値デフォルト 0.60、エグジット（SELL）はストップロス（-8%）およびスコア低下で判定。SELL 優先ポリシーにより SELL 対象は BUY から除外。
    - signals テーブルへ日付単位で冪等的に書き込み（トランザクション）。
- 研究用ユーティリティ
  - `kabusys.research.factor_research`:
    - `calc_momentum`, `calc_volatility`, `calc_value` を実装。DuckDB の SQL（ウィンドウ関数）を用いて各種ファクター（mom_1m/3m/6m、MA200 乖離、ATR 20、avg_turnover、per/roe など）を算出。
  - `kabusys.research.feature_exploration`:
    - `calc_forward_returns`（複数ホライズンに対応した将来リターン）、`calc_ic`（スピアマン ρ によるランク相関）、`factor_summary`（基本統計量）、`rank`（平均ランクによる tied-rank 処理）を実装。外部ライブラリに依存せず標準ライブラリのみで計算。
  - `kabusys.research.__init__` で主要 API を公開。
- バックテスト
  - `kabusys.backtest.simulator.PortfolioSimulator`:
    - メモリ内でポジション・平均取得単価・キャッシュ管理を行うシミュレータを実装。
    - `execute_orders` により SELL を先、BUY を後に処理（SELL は全量クローズ、部分利確や部分損切りは未対応）。スリッページ（BUY:+、SELL:-）と手数料率を考慮した約定をシミュレート。
    - `DailySnapshot`, `TradeRecord` の dataclass を提供。
  - `kabusys.backtest.metrics`:
    - `calc_metrics` により CAGR、Sharpe（無リスク金利=0）、Max Drawdown、Win Rate、Payoff Ratio、合計クローズ取引数を算出するユーティリティを実装。
- 公開 API の整理
  - 各パッケージで必要な関数／クラスを `__all__` でエクスポート。

### Changed
- （初回リリースのため該当なし）

### Fixed
- ファイル読み込み失敗時に warning を出すなど、堅牢性向上（`.env` 読み込み時の例外ハンドリング）。
- DuckDB トランザクション処理での例外時に ROLLBACK を試み、失敗時に WARNING を出力する挙動を追加（features / signals の書込処理など）。

### Known limitations / Notes
- セクター露出計算で価格が 0.0 の場合、露出が過少見積もりされてしまう可能性がある（将来的に前日終値や取得原価等のフォールバックを検討）。
- `apply_sector_cap` は "unknown" セクターを無視（上限適用しない）する挙動。
- `calc_regime_multiplier` の Bear 値は 0.3 だが、signal 生成ロジック自体は Bear レジームでそもそも BUY シグナルを生成しない設計（安全弁）。
- `calc_position_sizes` や simulator の約定処理では銘柄ごとの単元（lot）をグローバル `lot_size` 前提で処理。将来的に銘柄別単元マップに拡張する予定。
- simulator は SELL を「保有全量クローズ」で実装しており、部分利確・部分損切り・トレーリングストップ・時間決済等は未実装。
- `generate_signals` は AI スコア未登録銘柄を中立（news = 0.5）で補完する。AI の regime_score のサンプル数が不足する場合は Bear 判定を行わない。
- 研究系関数は DuckDB に依存（`prices_daily`, `raw_financials`, `features`, `ai_scores`, `positions`, `signals` 等のテーブル構造が前提）。
- ロギング多め。警告やデバッグを通して運用上の注意点を出力する設計。

### Security
- 機密情報は環境変数で管理（必須: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`）。`.env` 自動ロード機能は開発利便を考慮しているが、運用環境では適切に管理してください。

---

今後の予定（短期）
- 単元を銘柄毎に扱う対応（lot_map の導入）。
- エクスポージャ計算の価格フォールバック改善。
- 部分約定・トレーリングストップ・時間決済などのエグジット拡張。
- テストやドキュメントの充実（サンプル DB スキーマ、実行例、運用手順）。

もし特定機能について追記や表現の調整を希望される場合はお知らせください。