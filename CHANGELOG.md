# CHANGELOG

すべての重要な変更は Keep a Changelog の慣例に従って記載します。  
日付はコードベースの現状（バージョン 0.1.0）を元に推定しています。

全般的な方針：
- 初回公開に相当するリリースとして機能群（データ処理・研究・戦略・バックテスト・設定管理）を実装。
- DuckDB をデータレイヤーの中核として利用し、SQL と純粋な標準ライブラリでの処理を重視。
- 本番の発注実行層（外部 API 呼び出し）とは明確に分離した設計（戦略は発注層に依存しない）。
- 冪等性・トランザクション制御・欠損値・外れ値対処に配慮した実装。

## [0.1.0] - 2026-03-22

### Added
- パッケージ骨組みと公開 API
  - パッケージバージョンを `kabusys.__version__ = "0.1.0"` としてリリース。
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring（ダミー含む）。
  - strategy パッケージで `build_features`、`generate_signals` を公開。

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動読み込み（プロジェクトルートを .git / pyproject.toml で探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - 自動ロードの無効化オプション: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサ実装: コメント行、export プレフィックス、クォートとバックスラッシュエスケープ、行内コメント処理を考慮。
  - Settings クラス: 必須環境変数取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）・デフォルト値（KABU_API_BASE_URL, DB パス等）・バリデーション（KABUSYS_ENV, LOG_LEVEL）を提供。

- 戦略: 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究モジュール（research.factor_research から）で計算した生ファクターを結合して features テーブルへ保存する `build_features(conn, target_date)` を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用。
  - 正規化: 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
  - 日付単位で既存データを削除してから挿入することで冪等性を保証（トランザクション + バルク挿入）。

- 戦略: シグナル生成（kabusys.strategy.signal_generator）
  - `generate_signals(conn, target_date, threshold=0.60, weights=None)` を実装。
  - features と ai_scores を統合してコンポーネントスコア（momentum, value, volatility, liquidity, news）を計算し、重み付き合算で final_score を算出。
  - 重みはデフォルト値を持ち、ユーザー指定は検証・正規化（非数値や負値は無視、合計を 1.0 に再スケール）。
  - Bear レジーム判定（ai_scores の regime_score の平均が負かどうか）を行い、Bear 時は BUY シグナルを抑制。
  - BUY（閾値超）・SELL（ストップロス・スコア低下）シグナルを作成し、signals テーブルへ日付単位で置換（冪等）で書き込み。
  - SELL を優先し、SELL 対象は BUY から除外してランクを再付与するポリシーを採用。
  - 欠損の扱い: コンポーネントが None の場合は中立値 0.5 を補完。features にない保有銘柄は final_score=0.0 扱いで SELL 判定対象。

- 研究用ユーティリティ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）を DuckDB SQL ベースで計算。
    - 各計算は target_date 時点のデータのみ参照し、データ不足に対して None を返す設計。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=[1,5,21])（単一クエリで複数ホライズン）。
    - IC 計算 calc_ic（Spearman の ρ をランク関数を使って算出、サンプル不足時は None）。
    - factor_summary（count, mean, std, min, max, median）。
    - ランク関数 rank（同順位は平均ランク、浮動小数丸めで ties の誤検出を防止）。
  - 研究モジュールは pandas 等の外部ライブラリに依存しない純粋な標準ライブラリ実装。

- バックテストフレームワーク（kabusys.backtest）
  - ポートフォリオシミュレータ（kabusys.backtest.simulator）
    - PortfolioSimulator: 現金・保有・平均取得単価・トレード履歴・日次スナップショットを管理。
    - 約定ロジック: 指定した始値での擬似約定、スリッページ・手数料の適用、SELL を先に処理、SELL は全量クローズ（部分利確非対応）。
    - mark_to_market で終値評価と DailySnapshot 記録（終値欠損時は 0 で評価して WARNING）。
  - メトリクス（kabusys.backtest.metrics）
    - CAGR, Sharpe Ratio（無リスク=0 前提、252 日で年次化）, Max Drawdown, Win Rate, Payoff Ratio, total_trades の計算とラッパー BacktestMetrics。
  - エンジン（kabusys.backtest.engine）
    - run_backtest(conn, start_date, end_date, 初期資金等) を提供。
    - 本番 DB から期間を絞ってインメモリ DuckDB へデータコピー（signals/positions を汚染しない）。market_calendar は全件コピー。
    - 日次ループ:
      1. 前日シグナルを当日始値で約定
      2. positions を DB に書き戻し（generate_signals の SELL 判定に必要）
      3. 終値で時価評価・スナップショット記録
      4. generate_signals を呼び翌日用シグナル作成
      5. ポジションサイジングして次日の発注リストを組立て
    - バックテスト用接続構築で init_schema(":memory:") を利用して隔離されたテスト環境を構築。

### Changed
- 初回リリースのため特に該当なし（新規実装）。

### Fixed
- 初期リリース時点での堅牢化対応（実装に含まれる改善点の列挙）
  - .env 読み込みでの IO エラーを警告として処理し、プロセスを継続。
  - features / signals への挿入はトランザクションでラップし、例外発生時にロールバックを試行。ロールバック失敗時には警告ログを出力。
  - prices/positions 取得時の欠損（価格欠損）に対して警告を出し、誤ったクローズを防ぐため判定をスキップする保護ロジックを追加。

### Known issues / Not implemented / Limitations
- 戦略・シグナルに関する未実装・簡略化点（将来の改善候補）
  - トレーリングストップ・時間決済（保有 60 営業日超過）等のエグジット条件は未実装（_generate_sell_signals 内に注記あり）。これらは positions テーブルに peak_price / entry_date 等の追加情報が必要。
  - 部分利確・部分損切りは未対応。SELL は常に保有全量をクローズする。
  - Value 指標として PBR・配当利回りは現バージョンで未実装。
- バックテストと実運用の差分
  - バックテストは generate_signals を同じロジックで使用するが、実際の発注・約定は発注 API（execution 層）実装によるため、実運用ではスリッページや流動性の差で挙動が異なる可能性あり。
- データ要件
  - 多くの指標で過去 N 日分の連続した営業日データが必要（例: MA200 は 200 件）。データ不足時は None を返すため、その扱いがスコアに影響する。
- AI スコア依存
  - ai_scores が未登録の銘柄はニューススコアを中立（0.5）で補完する挙動。regime 判定はサンプルが 3 件未満の場合は Bear とみなさない設計。
- 依存外部ライブラリ
  - 研究モジュールは pandas 等に依存しないため、データ操作が手作業的（ただし軽量・自己完結）であることに注意。

### Security
- 現時点で明示的なセキュリティフィックスはなし。機密情報（API トークン等）は Settings 経由で環境変数管理を前提としているため、.env の取り扱いには注意が必要。

---

このリリースノートは、リポジトリ内の実装内容（モジュール構造、関数シグネチャ、コメント・ドキュメンテーション）から推測して作成しています。実際のリリースノート作成時は、コミット履歴やリリース差分、テスト結果を併せて反映してください。