# Changelog

すべての注目すべき変更点はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

- フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]


## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装しました。主な追加点は以下の通りです。

### Added
- パッケージ初期化
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - モジュールエクスポート: data, strategy, execution, monitoring を公開対象に設定。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数読み込み機能を実装。
  - 自動ロード:
    - プロジェクトルートを .git または pyproject.toml を基準に探索して .env / .env.local を自動読み込み（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - OS 環境変数を保護する protected 機構を実装（.env.local は上書き可能だが既存 OS 環境変数は保護）。
  - .env パース実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュによるエスケープ、行内コメント処理等に対応。
  - Settings クラス:
    - J-Quants / kabuステーション / Slack / データベースパス等の設定プロパティを提供。
    - 必須環境変数未設定時は明示的に ValueError を投げる `_require` を実装。
    - KABUSYS_ENV / LOG_LEVEL のバリデーションとユーティリティプロパティ（is_live/is_paper/is_dev）。

- ファクター計算（研究用）(kabusys.research.factor_research)
  - モメンタム、ボラティリティ、バリュー関連のファクター計算関数を実装:
    - calc_momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）。
    - calc_volatility: 20日 ATR、atr_pct、avg_turnover、volume_ratio。
    - calc_value: target_date 以前の最新財務データ (EPS/ROE) と株価から PER/ROE を計算。
  - DuckDB のウィンドウ関数を用いた効率的な SQL 実装。
  - データ不足時は None を返すことで欠損に寛容な設計。

- 研究支援ユーティリティ (kabusys.research.feature_exploration)
  - 将来リターン計算（calc_forward_returns）: 指定ホライズン（デフォルト 1/5/21 営業日）に対応。
  - IC（Information Coefficient）計算（calc_ic）: スピアマンランク相関を実装。最小サンプル数チェックを実施。
  - factor_summary / rank: 基本統計量と同順位の平均ランク処理を提供。
  - 外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research モジュールで算出した生ファクターを統合・正規化して features テーブルへ UPSERT する機能（build_features）。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
  - Z スコア正規化（kabusys.data.stats の zscore_normalize を使用）、±3 でクリップして外れ値の影響を抑制。
  - トランザクション + バルク挿入で日付単位の置換（冪等性、原子性確保）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合して最終スコア（final_score）を計算、BUY / SELL シグナルを生成（generate_signals）。
  - スコア計算:
    - momentum/value/volatility/liquidity/news のコンポーネントスコアを計算し、重み付き合算で final_score を算出（デフォルト重みを実装）。
    - シグモイド変換・欠損値補完（None を中立 0.5 で補完）により欠損への頑健性を確保。
    - ユーザ指定 weights の検証と正規化（不正値や未知キーは無視、合計が 1 になるよう再スケール）。
  - Bear レジーム判定:
    - ai_scores の regime_score の平均が負であれば Bear と判定（サンプル数閾値を設定）。
    - Bear 時は BUY シグナルを抑制。
  - エグジット判定:
    - ストップロス（終値ベースの -8%）および final_score が閾値未満の場合に SELL を生成。
    - positions / prices の欠損時は安全策として警告を出し適切にスキップ or デフォルトスコア扱い。
  - signals テーブルへの日付単位置換（トランザクションで原子性確保）。

- バックテストフレームワーク (kabusys.backtest)
  - ポートフォリオシミュレータ（PortfolioSimulator）を実装:
    - BUY/SELL 約定処理、スリッページ（BUY:+、SELL:-）・手数料モデル、平均取得単価更新、全量売却の扱い。
    - mark_to_market による日次スナップショット記録（終値欠損時は 0 評価し警告）。
    - TradeRecord / DailySnapshot のデータモデルを定義。
  - バックテストメトリクス (kabusys.backtest.metrics):
    - CAGR、Sharpe Ratio（無リスク=0 想定、年次化）、Max Drawdown、Win Rate、Payoff Ratio、Total Trades を計算。
  - バックテストエンジン (run_backtest):
    - 本番 DuckDB から必要なテーブルを切り出してインメモリ DuckDB にコピー（signals/positions を汚染しない）。
    - 日次ループを構築し、約定→positions書き戻し→時価評価→シグナル生成→ポジションサイジングの流れを実装。
    - get_trading_days 等のカレンダー連携を想定。
    - パラメータ: 初期資金、スリッページ率、手数料率、1銘柄最大ポジション割合などを受け付ける。

- DB 操作 / 安全性
  - 各種日別置換操作（features / signals / positions）はトランザクション + bulk insert により冪等性と原子性を確保。
  - 例外発生時の ROLLBACK を試み、失敗すると warning ログを出力する実装。
  - データ欠損・不正入力に対しては警告ログを出し、処理を安全にスキップまたはデフォルト補完する方針を採用。

### Changed
- 該当なし（初回リリースのため過去差分はありません）。

### Fixed
- 該当なし（初回リリース）。

### Notes / Design decisions
- 外部 API への直接呼び出しは最小化:
  - 研究・ファクター計算・シグナル生成・バックテストは DuckDB のテーブルのみを参照する設計で、本番発注層や外部サービスへの依存を持たない（execution 層と分離）。
- 欠損データに対する挙動を明示的に設計:
  - 欠損コンポーネントは中立値で補完、価格欠損時は SELL 判定や評価をスキップするなど、誤動作防止を重視。
- 設定の安全性:
  - OS 環境変数を優先し .env.local/.env の上書き順序を明確化。保護されたキーは上書きしない。

――――――――――
今後の予定（例）
- execution 層の実装（kabuステーション連携）、モニタリング/通知機能（Slack統合）の追加。
- features の追加・重み最適化用ユーティリティ、トレーリングストップ等のエグジット条件拡張。
- テストケース・CI の整備、型注釈の強化とドキュメントの追加。

(初回リリースのため互換性破壊はありません。)