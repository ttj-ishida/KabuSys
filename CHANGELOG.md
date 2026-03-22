Keep a Changelog に準拠した CHANGELOG.md（日本語）を以下に作成しました。コードベースの内容から推測して記載しています。

CHANGELOG.md
-------------

全般的な方針:
- この CHANGELOG は Keep a Changelog のフォーマットに従います。
- バージョン付けはパッケージ内の __version__（現時点 0.1.0）に基づきます。
- 日付は本ファイル作成日（2026-03-22）を使用しています。

## [Unreleased]
該当なし。

## [0.1.0] - 2026-03-22
初回リリース

Added
- パッケージ基盤
  - kabusys パッケージを初期実装。公開 API（__all__）として data, strategy, execution, monitoring をエクスポート。
  - バージョン: 0.1.0

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルートの検出は __file__ を起点に .git または pyproject.toml を探索し、CWD に依存しない動作を実現。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
  - .env パーサーは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント（クォート外）を適切に処理。
  - _load_env_file による protected（既存 OS 環境変数保護）機構、override フラグを提供。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_* 等）をプロパティ経由で取得。未設定時は ValueError を送出。
  - KABUSYS_ENV / LOG_LEVEL のバリデーション（allowed 値チェック）を実装。

- 戦略: 特徴量生成 (kabusys.strategy.feature_engineering)
  - research で算出した生ファクターをマージ・正規化して features テーブルへ保存する build_features(conn, target_date) を実装。
  - ユニバースフィルタ（最低株価、20 日平均売買代金）を実装。
  - Z スコア正規化（外部ユーティリティ zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
  - 日単位で features テーブルを置換（DELETE + bulk INSERT）し、トランザクションで原子性を担保。
  - ルックアヘッドバイアスを避ける設計（target_date 時点のデータのみ使用）。

- 戦略: シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成する generate_signals(conn, target_date, ...) を実装。
  - コンポーネントスコア（momentum, value, volatility, liquidity, news）ごとの計算ロジックを実装（シグモイド変換、PER の逆数スコア等）。
  - weights の入力受け入れと補完・再スケール処理（不正値の無視、合計が 1 でない場合の正規化）。
  - Bear レジーム判定（ai_scores の regime_score を集計して市場が Bear なら BUY を抑制）。
  - SELL（エグジット）判定の実装（ストップロス、score 低下）。保有銘柄の price 欠損時は判定をスキップする保護ロジックを追加。
  - signals テーブルへの日付単位の置換（トランザクション＋バルク挿入）で冪等性を確保。
  - ログ出力により異常ケース（価格欠損、features 未登録、無効な weights 値等）を通知。

- リサーチ/解析 (kabusys.research)
  - ファクター計算モジュール（kabusys.research.factor_research）
    - calc_momentum, calc_volatility, calc_value を実装。
    - momentum: 約1/3/6ヶ月のリターン、200 日移動平均乖離率（データ不足時は None）。
    - volatility: 20 日 ATR（true_range を NULL 伝播で正確に扱う）、相対 ATR(atr_pct)、20 日平均売買代金・出来高比を実装。
    - value: raw_financials から最終財務データを参照し PER / ROE を計算（EPS が無効なら PER は None）。
    - 全関数は prices_daily / raw_financials のみ参照し、外部 API に依存しない設計。
  - 特徴量探索モジュール（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定日から複数ホライズンの将来リターンを一括で取得する SQL 実装（ホライズンのバリデーションあり）。
    - calc_ic: スピアマンのランク相関（IC）計算（同順位は平均ランクで処理、データ不足時は None）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を実装。
    - rank: 同順位の平均ランク取り扱いと丸めによる ties 対策を実装。
  - 研究向けの設計方針を明記（DuckDB のみ参照、外部ライブラリに依存しない）。

- バックテストフレームワーク (kabusys.backtest)
  - ポートフォリオシミュレータ（kabusys.backtest.simulator）
    - PortfolioSimulator を実装（cash, positions, cost_basis, history, trades 管理）。
    - execute_orders で SELL を先に処理し BUY を後に処理する振る舞い。BUY は alloc 基準の購入、SELL は全量クローズ（部分利確は未対応）。
    - スリッページ・手数料モデルの適用（買いは entry_price = open*(1+slippage)、売りは exit_price = open*(1-slippage)、commission_rate を適用）。
    - mark_to_market で終値評価し DailySnapshot を記録。終値欠損時は 0 評価かつ警告ログ。
    - TradeRecord / DailySnapshot の dataclass を定義。
  - バックテストエンジン（kabusys.backtest.engine）
    - run_backtest を実装。実運用 DB から必要なテーブルをインメモリ DuckDB にコピーし（日付フィルタあり）、日次ループでシミュレーションを実行。
    - _build_backtest_conn で一部テーブル（prices_daily, features, ai_scores, market_regime, market_calendar）をコピー。コピー失敗は警告ログでスキップ。
    - トレード実行→positions の書き戻し→時価評価→generate_signals→ポジションサイジングの流れを実現。
    - positions 書込は冪等に（当日分 DELETE の後に INSERT）。
  - バックテストメトリクス（kabusys.backtest.metrics）
    - calc_metrics と複数の内部計算（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio）を実装。
    - 小サンプル・エッジケース（分母 0、履歴不十分等）に対して安全なデフォルト（0.0 など）を返す設計。

- 公開モジュール初期化
  - 各サブパッケージ（strategy, research, backtest）の __init__ で主要関数/クラスを再エクスポートし、ユーザー API を整備。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- なし。

Removed
- なし。

Security
- なし。

Notes / Known limitations
- 一部のエグジット条件（トレーリングストップ、保有期間による自動決済等）はコメントで未実装と明記されており、今後の実装項目です。
- feature_engineering / signal_generator は DB のスキーマ（テーブル名・カラム）に依存します。導入時は data/schema の init_schema 等でスキーマ整備が必要です。
- research モジュールは外部依存を避ける設計だが、データ前処理や追加解析のために将来的に pandas 等を導入する余地はあります。
- バックテストは本番 DB を直接変更しないため安全だが、コピー対象テーブルの差異や欠損により挙動が異なる場合があります（コピー失敗は警告ログでスキップ）。

参考（設計・実装上の特徴）
- 冪等性: features / signals / positions への書き込みは「指定日を DELETE して挿入」という日付単位の置換で実装し、トランザクションで原子性を保証。
- ロギング: 重要な異常（データ欠損、無効な入力等）は logger に WARN/INFO/DEBUG で記録。
- バリデーション: 環境変数 / 引数（horizons, weights 等）の入力チェックを多くの箇所で実施し早期エラーを発生させる。
- 研究と本番の分離: research 側は本番 API にアクセスしない設計、戦略層も execution 層に依存しない（シグナル生成と発注を分離）。

今後の予定（候補）
- 未実装のエグジット条件（トレーリングストップ、保有日数による決済）を実装。
- 部分利確・分割売買のサポート。
- より詳細な単体テスト・統合テストの追加（現在は自動ロードの無効化フラグなどテスト向け機構あり）。
- ドキュメント整備（StrategyModel.md / BacktestFramework.md 等の参照ドキュメントを公開）。

--------------------------------
（この CHANGELOG はソースコードのコメント・関数名・ログ文等から推測して作成しています。実際のリリースノート作成時はコミット履歴や意図を反映して必要に応じて調整してください。）