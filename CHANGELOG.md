CHANGELOG
=========

すべての重要な変更はこのファイルに記載します。形式は「Keep a Changelog」に準拠します。

Unreleased
----------

（なし）

0.1.0 - 2026-03-26
------------------

Added
- パッケージ初期リリース (kabusys v0.1.0)
  - パッケージ初期エクスポート:
    - kabusys.__init__ により "data", "strategy", "execution", "monitoring" を公開。
  - 環境変数・設定管理 (kabusys.config)
    - .env/.env.local の自動ロード機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードの無効化が可能。
    - .env パーサ実装:
      - 空行・コメント対応、export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
      - クォートなしのインラインコメントは直前が空白/タブの場合のみコメントとして扱う。
    - 環境変数取得ユーティリティ _require()（未設定時は ValueError）。
    - 設定クラス Settings:
      - J-Quants / kabuステーション / Slack / DB パス等のプロパティ（必須環境変数を明示）。
      - デフォルト値 / バリデーション（KABUSYS_ENV: development|paper_trading|live、LOG_LEVEL: DEBUG|...）。
      - duckdb/sqlite パスはデフォルトで data/ 配下を使用。

  - ポートフォリオ構築 (kabusys.portfolio)
    - 銘柄選定・重み計算 (portfolio.portfolio_builder):
      - select_candidates: score 降順、同点時 signal_rank 昇順で上位 N を選定。
      - calc_equal_weights: 等金額配分。
      - calc_score_weights: スコア加重配分（全銘柄スコアが 0 の場合は等配分にフォールバックし WARNING）。
    - リスク調整 (portfolio.risk_adjustment):
      - apply_sector_cap: 既存保有からセクター別エクスポージャを計算し、max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは制限対象外）。
      - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に対する投下資金乗数。未知のレジームは警告の上 1.0 にフォールバック。
      - sell_codes パラメータにより当日売却予定銘柄をエクスポージャ計算から除外可能。
    - 株数決定・単元丸め・資金配分 (portfolio.position_sizing):
      - calc_position_sizes:
        - allocation_method: "risk_based" / "equal" / "score" をサポート。
        - risk_based: risk_pct / stop_loss_pct に基づくポジション寸法決定。
        - equal/score: weight に基づく配分、portfolio_value * weight * max_utilization による per-position 上限。
        - 単元（lot_size）で丸め、_max_per_stock による個別上限、aggregate cap（available_cash）によりスケーリング。スケーリング後の残差は fractional 残差順に lot 単位で再配分。
        - cost_buffer を用いた保守的な約定コスト見積り（スリッページ・手数料推定）。

  - 特徴量生成・戦略 (kabusys.strategy)
    - feature_engineering.build_features:
      - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得しマージ。
      - ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
      - 指定カラムを Z スコア正規化し ±3 でクリップ。
      - DuckDB 上で日付単位の置換（DELETE → INSERT）をトランザクションで行い冪等性を確保。ROLLBACK 失敗時は警告を出力。
    - signal_generator.generate_signals:
      - features / ai_scores / positions を参照して final_score を計算（momentum/value/volatility/liquidity/news の重み付け）。
      - AI スコアが未登録の銘柄は中立（0.5）で補完。
      - weights パラメータは入力検証（未知キー・非数値・負値を無視）、合計が 1.0 になるようリスケール。合計が 0 以下の場合はデフォルト重みへフォールバック。
      - Bear レジーム判定（ai_scores の regime_score の平均が負且つサンプル数 >= 3 の場合）で BUY シグナルを抑制。
      - BUY は閾値 (default=0.60) を超えた銘柄に対して付与。SELL はエグジット条件（ストップロス -8% / final_score が閾値未満）で判定。
      - SELL 優先ポリシー: SELL 対象は BUY から除外し、BUY のランクを再付与。
      - signals テーブルへ日付単位の置換（トランザクションによる原子性）。

  - リサーチツール (kabusys.research)
    - factor_research:
      - calc_momentum / calc_volatility / calc_value を実装。全て prices_daily / raw_financials を参照してファクターを出力（date, code キーを含む dict のリスト）。
      - momentum: 1M/3M/6M リターン、MA200 乖離（200 行未満は None）。
      - volatility: ATR20, atr_pct, avg_turnover, volume_ratio（ウィンドウサイズを考慮して NULL を適切に扱う）。
      - value: 最新財務（report_date <= target_date）に基づく PER/ROE（EPS=0 は None）。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons の妥当性チェックあり。
      - calc_ic: スピアマンランク相関（IC）を計算。有効レコードが 3 未満なら None。
      - factor_summary: count/mean/std/min/max/median を計算。
      - rank: 同順位は平均順位で扱う実装（round(...,12) で ties の安定化）。

  - バックテスト (kabusys.backtest)
    - metrics.calc_metrics:
      - DailySnapshot（date, portfolio_value 等）と TradeRecord（realized_pnl を使ったクローズ取引の計算）から各種メトリクスを算出（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades）。
      - 実装上の詳細: Sharpe は無リスク金利=0、年次化は営業日 252 日ベース。
    - simulator.PortfolioSimulator:
      - メモリ内でのポートフォリオ状態管理、SELL を先に処理してから BUY を処理。
      - SELL は保有全量をクローズ（部分利確・部分損切り非対応）。
      - スリッページ（BUY:+、SELL:-）と手数料率をサポート。TradeRecord に commission, realized_pnl を記録。
      - lot_size パラメータで約定単位を指定可能（現実運用は 100 を想定）。

Changed / Fixed
- N/A（初回リリースのため変更履歴なし）。

Known issues / Limitations / TODO
- config._find_project_root は .git / pyproject.toml を基準に探索するため、特殊な配布形態では .env 自動検知がスキップされる可能性あり。
- _parse_env_line のクォート外コメント処理は直前が空白/タブの '#' のみコメントとみなす設計。特殊な .env フォーマットは未対応。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に 0.0（欠損）があるとエクスポージャが過少見積りされる可能性あり。将来的に前日終値や取得原価によるフォールバックを検討。
  - "unknown" セクターはセクターキャップの対象外となる（設計決定）。
- position_sizing の lot_size は現状全銘柄共通。将来的に銘柄別 lot_map を受け取る拡張予定（TODO コメントあり）。
- signal_generator の未実装エグジット条件:
  - トレーリングストップ（peak_price が positions テーブルに必要）
  - 時間決済（保有日数ベース）
- PortfolioSimulator の SELL は全量クローズのみ。部分利確・複雑な注文ロジックは未対応。
- 一部処理で価格欠損時は判定をスキップまたは警告を出す挙動がある（安全側の設計）。
- DB 操作は DuckDB を前提として実装されており、SQL 文は DuckDB のウィンドウ関数を多用。互換性のある環境での利用を想定。

開発者向けメモ
- ロギングを多用しており、意図的に情報/警告/デバッグを出力する箇所が存在する（例: score 0 のフォールバック、未知レジームのフォールバック、価格欠損時の判定スキップ等）。
- トランザクション（BEGIN/COMMIT/ROLLBACK）を用いた日付単位の置換実装が複数箇所にあるため、DuckDB のトランザクション挙動に注意すること。
- public API（関数群）は純粋関数設計を心がけており、DB 参照箇所は明示的にドキュメント化されている（研究系関数は prices_daily/raw_financials のみ、実行系は DB に依存しない）。

-----  
この CHANGELOG はコードコメント・ドキュメント（PortfolioConstruction.md / StrategyModel.md 等の参照を想定したコメント）から推測して作成しています。実際のリリースノート作成時はリリース日付・著者・変更セットに合わせて調整してください。