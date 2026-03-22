KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠し、[Unreleased] と各リリースごとにセクションを分けています。

[Unreleased]
- なし

[0.1.0] - 2026-03-22
Added
- 初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装。
- パッケージ情報
  - バージョン: 0.1.0 (src/kabusys/__init__.py)
  - パッケージ公開用エクスポート: data, strategy, execution, monitoring
- 環境変数／設定管理
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git / pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - 詳細な .env 行パーサ実装（export プレフィックス対応、クォート内エスケープ、インラインコメント処理）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 実行環境 / ログレベルなどを取得可能。
  - 必須変数未設定時に明示的な ValueError を返す _require ユーティリティを実装。
- 戦略（strategy）
  - feature_engineering.build_features(conn, target_date)
    - research で作成した生ファクターを読み込み、ユニバースフィルタ（最低株価・平均売買代金）、Zスコア正規化、±3 でのクリップを行い features テーブルへ日付単位で置換（冪等）して保存。
    - DuckDB を利用したバルク挿入・トランザクション処理を実装し、ロールバック失敗時に警告出力。
  - signal_generator.generate_signals(conn, target_date, threshold=0.6, weights=None)
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、final_score を算出。
    - Bear レジーム判定（ai_scores の regime_score 平均で判定）を実装し、Bear 時には BUY を抑制。
    - BUY / SELL シグナルを生成し、signals テーブルへ日付単位で置換（冪等）。
    - 重みの入力検証と合計が 1.0 でない場合の再スケール処理、無効値のスキップを実装。
    - 欠損コンポーネントは中立値 0.5 で補完し、不当な降格を防止。
    - SELL の判定ロジックにストップロス（-8%）とスコア低下を実装。価格欠損時の判定スキップ・ログ出力あり。
- Research（research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials のみ参照し、各ファクター（モメンタム、ATR、PER/ROE、流動性等）を計算して dict リストで返す。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21])：各銘柄の将来リターンを一度のクエリで取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：ランク相関（Spearman ρ）による IC 計算（有効データが 3 件未満の場合 None を返す）。
    - factor_summary(records, columns)：count/mean/std/min/max/median を返す統計サマリー。
    - rank(values)：同順位は平均ランクになるよう実装（丸めによる ties 対応）。
  - research パッケージは外部ライブラリに依存せず、標準ライブラリのみで実装。
- Data / DB 周り（間接参照）
  - DuckDB を前提にした SQL 実装（複雑なウィンドウ関数や LEAD/LAG を多用）。
  - features / ai_scores / prices_daily / raw_financials / positions / signals などのテーブルを前提。
- バックテスト（backtest）
  - simulator.PortfolioSimulator：メモリ内でのポジション管理、約定ロジック、スリッページ・手数料モデル、日次評価（mark_to_market）を実装。
    - BUY は資金に応じて株数を切り上げて約定、平均取得単価（cost_basis）を管理。
    - SELL は保有全量クローズ（部分利確未対応）。約定記録（TradeRecord）を保存。
    - 約定時・評価時の価格欠損に対してロギングと安全な挙動を提供。
  - metrics.calc_metrics：history（DailySnapshot）と trades（TradeRecord）から CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を算出。
  - engine.run_backtest(conn, start_date, end_date, ...)
    - 本番 DuckDB からインメモリ DuckDB へ必要データをコピー（signals/positions に影響を与えない）。
    - 日次ループ：前日シグナルを当日始値で約定 → positions を書き戻し（generate_signals の SELL 判定用）→ 終値で評価 → generate_signals による翌日シグナル生成 → ポジションサイジング → 次日注文作成 のフローを実装。
    - データコピー時は日付フィルタを適用して必要データのみを移植（性能配慮）。
    - エラー時はログを残して個別テーブルのコピーをスキップする堅牢性を実装。
- コード設計上の注力点（ドキュメント化された設計方針）
  - ルックアヘッドバイアスを防ぐため target_date 時点のデータのみを使用する方針を各モジュールで徹底。
  - 発注 API / 本番 execution 層への直接依存を持たない設計（strategy は signals テーブルまでを生成する責務）。
  - 冪等性の確保（features / signals / positions への日付単位の置換処理）。
  - 外部依存を最小化し、DuckDB と標準ライブラリ中心で構築。

Fixed / Robustness
- .env 読み込みでのファイル I/O 失敗時に警告を出して処理を継続するように（テストや権限不足等に対する耐性）。
- .env 行パーサでクォート内のバックスラッシュエスケープとインラインコメント処理を適切に扱うように改善。
- DB トランザクション失敗時に COMMIT / ROLLBACK の両方で発生した例外をハンドリングし、ログを残すように実装（build_features / generate_signals）。
- ファクター正規化後に ±3 でクリップし、外れ値の影響を抑制（feature_engineering）。
- generate_signals の weights 検証を厳格化（未知キー、非数値、NaN/Inf、負値は無視）し、合計が 1 でない場合は再スケールまたはデフォルトへフォールバック。
- 各種関数でデータ欠損（価格や財務データ）時の安全なフォールバック（None の扱い・ログ出力）を徹底。

Notes / Known limitations
- signal_generator の SELL の一部条件（トレーリングストップや時間決済）は未実装（positions に peak_price / entry_date が必要）。
- BUY のポジションサイジングロジックは engine.run_backtest の中で簡素な割当方式を使用（改善余地あり）。
- PBR・配当利回りなどのバリューファクターは未実装。
- execution パッケージの公開はあるが、実際の発注 API との接続層はこのリリースでは実装されていない（strategy は signals テーブル生成までを担当）。

参考
- 実装は多くの設計・仕様をコメントや docstring（StrategyModel.md / BacktestFramework.md 等）で明確にしているため、今後の追加実装・外部接続の実装に向けた拡張が容易。
- テストフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD により CI/テスト環境での環境変数制御が可能。

-----
この CHANGELOG はソースコード記述（docstring・定数名・関数署名・ログメッセージ等）から推測して作成しています。実際のリリースノートとして公開する際は、実際の変更差分・リリース日・影響範囲を確認のうえ調整してください。