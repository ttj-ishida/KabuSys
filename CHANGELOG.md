# CHANGELOG

すべての注記は Keep a Changelog の形式に準拠します。

全般:
- バージョニングは package の __version__ に従います（現在: 0.1.0）。
- 日付は本リリース作成日: 2026-03-26。

[0.1.0] - 2026-03-26
====================

Added
-----
- 基本パッケージ初期実装 (kabusys 0.1.0)。
  - パッケージエントリポイント: src/kabusys/__init__.py にて version と主要サブモジュールを公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは既存の OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート探索: .git または pyproject.toml を基準にルートを探索して .env / .env.local を読み込む（CWD に依存しない）。
  - .env 解析ロジック:
    - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメント処理（クォート有無で挙動を分岐）。
    - 無効行（空行・コメント行・等号無し行）は無視。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用途）。
  - Settings クラスを提供し、必須環境変数の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や既定値（KABU_API_BASE_URL, DB パス等）を公開。
  - KABUSYS_ENV と LOG_LEVEL の値検証を実装（許容値外は ValueError）。

- ポートフォリオ構築モジュール (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: score 降順、同点は signal_rank 昇順でタイブレーク。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア割合で重みを算出。全スコアが 0 の場合は等金額にフォールバックして WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中度チェック。既存保有のセクター別時価からセクター上限を判定し、超過セクターからの新規候補を除外。'unknown' セクターは除外対象外。
    - calc_regime_multiplier: 市場レジームに基づく投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバックして WARNING を出力。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を算出。
    - 単元株丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）に基づくスケーリング、cost_buffer を使った保守的コスト見積もり、残差処理（lot 単位での追加配分）を実装。
    - 一部設計上の TODO（将来的に銘柄別 lot_size の導入記載）。

- 戦略関連 (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュールから生ファクターを取得（momentum, volatility, value）。
    - ユニバースフィルタ（最低株価・最低売買代金）適用。
    - 指定列を Z スコア正規化し ±3 でクリップ。
    - DuckDB を用いたトランザクションベースの日付単位 UPSERT（DELETE→INSERT）を実装。例外時は ROLLBACK、失敗警告を記録。
  - signal_generator.generate_signals:
    - features と ai_scores を統合して各コンポーネントスコア（momentum, value, volatility, liquidity, news）を算出。
    - 標準の重みセットを持ち、ユーザー重みは検証・補完・正規化（合計=1 にリスケール）して使用。
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完。
    - Bear レジーム検知時は BUY シグナルを抑制（ただし Bear 判定はサンプル閾値を設けて誤判定抑止）。
    - SELL シグナル生成ロジック（ストップロス、スコア低下）を実装。保有銘柄の価格欠損時は SELL 判定をスキップし警告を出力。
    - signals テーブルへの日付単位置換（トランザクション）を行う。

- リサーチ関連 (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials を用いた SQL ベースのファクター計算（DuckDB）。
    - 各ファクターはウィンドウ不足時に None を返す設計で、実務データ欠損に耐性あり。
  - feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: Spearman ランク相関（ties は平均ランク）で IC を計算。サンプル不足（<3）では None。
    - factor_summary: 各列の基本統計（count, mean, std, min, max, median）。
    - rank: 同順位は平均ランクとする実装。丸めで ties 検出漏れを防ぐ工夫あり。

- バックテスト関連 (kabusys.backtest)
  - metrics.calc_metrics:
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティを実装。
  - simulator.PortfolioSimulator:
    - DailySnapshot / TradeRecord データクラス。
    - execute_orders: SELL を先に処理してから BUY（資金確保のため）。スリッページ・手数料モデルをサポート。SELL は保有全量クローズ（部分利確未対応）。
    - メモリ内でのポートフォリオ状態管理と約定記録の保持。

Changed
-------
- （初回リリースのため該当なし）

Fixed
-----
- （初回リリースのため該当なし）

Known issues / Notes
--------------------
- position_sizing と simulator の lot_size / 単元扱いは将来的な拡張（銘柄別単元サポート）を想定しているが、現バージョンでは一括パラメータでの運用を想定。
- apply_sector_cap: price_map に価格が欠損（0.0）だとセクターエクスポージャーが過少見積もられる可能性があり、将来は前日終値や取得原価などのフォールバックを検討する旨の TODO がある。
- generate_signals:
  - Bear 相場時の完全な BUY 抑制は AI スコアに依存する判定ロジックのため、ai_scores テーブルのデータ品質に影響を受ける。
  - トレーリングストップや時間決済などの一部エグジット条件は未実装（positions テーブルに peak_price / entry_date が必要）。
- .env パーサは多くの実用ケースに対応しているが、複雑なシェル展開や外部ファイル参照などは非対応。

Compatibility / Breaking changes
-------------------------------
- 初回公開バージョンのため、互換性の破壊変更はありません。

開発者向け補足
----------------
- 自動 .env ロードはデフォルトで有効。テストや CI 環境で無効化するには環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB 接続を前提とする関数群（strategy / research / feature_engineering）は、該当テーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）のスキーマとデータ品質に依存します。開発・テスト時は最小限のモックデータを用意してください。
- ロギングが各モジュールで利用されています。運用時は LOG_LEVEL / ロガー設定で出力調整してください。

（以降のリリースでは Unreleased セクションに差分を記載してください）