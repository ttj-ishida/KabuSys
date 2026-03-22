# Changelog

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システムのコア機能を提供します。主にデータ処理・ファクター計算・特徴量生成・シグナル生成・バックテスト基盤を含みます。

### Added
- パッケージ初期化
  - kabusys パッケージのバージョンを 0.1.0 として公開。
  - __all__ に主要サブパッケージ（data, strategy, execution, monitoring）を定義。

- 設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - プロジェクトルートの検出は __file__ を基点に .git または pyproject.toml を探索して行い、配布後も動作するよう設計。
  - .env ファイルの柔軟なパーサを実装（export 構文対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理など）。
  - 環境変数の必須チェック用ヘルパー _require を提供。未設定時は ValueError を送出。
  - 各種設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティとして公開する Settings クラスを提供。
  - 設定値のバリデーション:
    - KABUSYS_ENV は development / paper_trading / live のいずれかのみ許容。
    - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容。
  - データベースパスのデフォルト（duckdb / sqlite）を設定。

- 研究 (research) モジュール
  - factor_research
    - モメンタム（1M/3M/6M リターン、200日移動平均乖離率）計算（calc_momentum）。
    - ボラティリティ / 流動性（20日 ATR、相対ATR、平均売買代金、出来高比率）計算（calc_volatility）。
    - バリュー（PER, ROE）計算（calc_value）。raw_financials から最新の財務データを取得して株価と組合せ。
    - DuckDB 上で SQL とウィンドウ関数を用いて効率的に計算する設計。
  - feature_exploration
    - 将来リターン計算（calc_forward_returns）：複数ホライズン（デフォルト [1,5,21]）に対応し、営業日ベースで LEAD を用いて取得。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関を実装（ランク付けは同順位を平均ランクにする方式）。
    - ファクター統計サマリ（factor_summary）等のユーティリティ。
    - ランク関数（rank）を提供（浮動小数点丸めを意識した同順位処理）。

- 特徴量エンジニアリング（strategy.feature_engineering）
  - research で算出した生ファクターをマージ・フィルタ・正規化して features テーブルに UPSERT（日付単位で削除 → 挿入）する build_features を実装。
  - ユニバースフィルタ:
    - 株価 >= 300 円、20日平均売買代金 >= 5 億円を基準にフィルタリング。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 のクリッピングを行い外れ値影響を抑制。
  - トランザクション + バルク挿入で日付単位の置換を行い冪等性と原子性を担保。ロールバックの失敗を警告ログで通知。

- シグナル生成（strategy.signal_generator）
  - features と ai_scores を統合して final_score を計算し、BUY / SELL シグナルを生成する generate_signals を実装。
  - コンポーネントスコア:
    - momentum, value, volatility, liquidity, news（AI）を算出するユーティリティを実装。
    - Z スコアをシグモイド変換して [0,1] にマッピング。
    - PER は低いほど高スコアとなる独自関数で変換。
  - 重み付け:
    - デフォルト重みを定義し、ユーザ指定 weights はバリデーション／マージ／リスケールされる。
  - AI ニューススコアは未登録時に中立 0.5 で補完。
  - Bear レジーム判定:
    - ai_scores の regime_score の平均が負なら Bear（ただしサンプル数が一定以上の場合のみ判定）。
    - Bear では BUY シグナルを抑制。
  - エグジット（SELL）判定:
    - ストップロス（終値 / avg_price - 1 <= -8%）を最優先。
    - final_score が閾値未満の場合に score_drop を出す。
    - features に存在しない保有銘柄は final_score = 0.0 扱い（警告ログ）。
  - signals テーブルへの日付単位置換（トランザクション + バルク挿入）で冪等性を実現。

- バックテストフレームワーク（backtest）
  - simulator
    - PortfolioSimulator を実装。メモリ上で cash / positions / cost_basis / history / trades を管理。
    - 約定ロジック:
      - SELL を先に処理してから BUY を処理（資金確保のため）。
      - BUY は alloc から始値・スリッページ・手数料を考慮して購入株数を floor で計算。
      - 手数料を考慮して再計算するロジックを実装。
      - SELL は保有全量をクローズ（部分利確・部分損切りは未対応）。約定後に realized_pnl を計算。
    - mark_to_market で終値評価し DailySnapshot を記録（終値欠損は 0 評価とし警告ログ）。
  - metrics
    - バックテスト評価指標を計算する calc_metrics（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
    - 各指標の内部計算関数は入力不十分な場合に安全に 0 や None を返す実装（堅牢性重視）。
  - engine
    - run_backtest を実装。実行フローは:
      1. 本番 DuckDB からインメモリ DuckDB へ必要データをコピー（start_date - 300日〜end_date のフィルタリング）。market_calendar は全件コピー。
      2. 日次ループ: 前日シグナルを当日始値で約定 → positions を DB に書き戻し → 終値評価でスナップショットを記録 → generate_signals で当日分シグナル生成 → シグナルに基づいて翌日約定用リストを構築。
    - positions の書き戻しは冪等（DELETE + INSERT）で行う。
    - 日付範囲コピー時やテーブルコピーで例外発生時は警告ログを出しスキップする耐障害処理。
    - run_backtest は BacktestResult（history, trades, metrics）を返す。

- パッケージの __all__ エクスポート
  - backtest / research / strategy モジュールで主要 API（run_backtest, calc_momentum 等）を明示的に公開。

### Fixed
- DB トランザクション操作での例外発生時にロールバック失敗があれば警告ログを出すようにして、例外の原因追跡と運用上の可観測性を向上。

### Design / Notes
- ルックアヘッドバイアス対策:
  - 全ての戦略・特徴量・シグナル生成処理は target_date 時点のデータのみを参照するよう設計。
- 外部ランタイム依存の最小化:
  - research/feature_exploration は pandas 等に依存せず標準ライブラリ＋DuckDB SQL で実装。
- 冪等性・原子性:
  - features / signals / positions の日付単位の置換はトランザクション + バルク挿入で実施。
- ロギング:
  - 重要な分岐やデータ欠損時に詳細な警告/情報ログを出力することで運用上の原因特定を容易に。

今後の予定（未実装・拡張候補）
- execution 層と実際の発注 API 連携。
- 部分利確やトレーリングストップ、時間決済などのエグジット戦術を positions 側のメタ情報（peak_price, entry_date 等）を導入して実装。
- PBR や配当利回りなど追加ファクターの実装。
- モデル検証用の追加メトリクスや可視化ツールの提供。

---
この CHANGELOG はリポジトリに含まれるソースコードから推測して作成しています。実際のリリースノートとして用いる際は、対象コミットやリリース日・担当者に合わせて調整してください。