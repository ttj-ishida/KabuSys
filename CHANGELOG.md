# CHANGELOG

すべての変更は「Keep a Changelog」形式に従います。  
このプロジェクトはセマンティック バージョニングに準拠します。  

- 未リリースの変更は "Unreleased" に記載します。  
- 既存リリースには日付を付与します。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-22
初期リリース。

### 追加 (Added)
- パッケージ基盤
  - パッケージエントリポイントを追加。バージョンは 0.1.0（src/kabusys/__init__.py）。
  - モジュール公開一覧を定義（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理 (src/kabusys/config.py)
  - .env / .env.local ファイルを自動ロードする仕組みを追加（プロジェクトルートを .git または pyproject.toml で探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサー実装（export プレフィックスの対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどに対応）。
  - 上書きフラグ（override）と保護キーセット（protected）による環境変数の安全な読み込み。
  - 必須環境変数取得ヘルパー _require と Settings クラスを追加。標準的な設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）
    - SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV（development/paper_trading/live の検証）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - 環境判定プロパティ (is_live / is_paper / is_dev)

- ストラテジー: 特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールで計算した生ファクターを読み込み、ユニバースフィルタ・正規化・クリッピングを行い features テーブルへ UPSERT する build_features を実装。
  - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を追加。
  - 正規化対象カラムの Z スコア正規化と ±3 でのクリッピングを実装。
  - DuckDB を用いた日次単位のトランザクションによる置換（BEGIN/COMMIT/ROLLBACK）で冪等性と原子性を確保。

- ストラテジー: シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して final_score を計算し、signals テーブルに BUY / SELL を書き込む generate_signals を実装。
  - コンポーネントスコア計算（momentum, value, volatility, liquidity, news）とデフォルト重みを実装（デフォルト重みは momentum=0.40 など）。
  - 重みの外部指定をサポートし、不正な値を除外、合計が 1.0 にならない場合は再スケールするロジックを実装。
  - シグモイド変換、欠損コンポーネントの中立補完（0.5）、スコア降順ランク付けを採用。
  - Bear レジーム判定（ai_scores の regime_score 平均が負の場合に BUY を抑制。サンプル数閾値あり）。
  - SELL（エグジット）判定:
    - ストップロス（終値 / avg_price - 1 < -8%）
    - final_score が閾値未満（デフォルト閾値 0.60）
    - 保有銘柄で価格が取得できない場合は判定をスキップ（警告ログ）。
  - signals テーブルへの日付単位置換もトランザクションで実施。

- research モジュール (src/kabusys/research/)
  - ファクター計算関数を公開: calc_momentum, calc_volatility, calc_value（prices_daily / raw_financials を参照）。
  - 研究向けユーティリティ:
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1/5/21 営業日）の将来リターンを一括で算出。
    - calc_ic: スピアマンのランク相関（IC）計算（欠損/サンプル不足時は None）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - rank: ties を平均ランクで扱うランク変換ユーティリティ。
  - pandas 等外部ライブラリを使わず標準ライブラリ + duckdb で実装。

- data 側ユーティリティ（参照）
  - zscore_normalize を利用して特徴量の正規化を実行（kabusys.data.stats を通じて研究/戦略で共有）。

- バックテストフレームワーク (src/kabusys/backtest/)
  - ポートフォリオ シミュレータ（PortfolioSimulator）を実装:
    - BUY/SELL の擬似約定、スリッページ（entry/exit に対する加減算）、手数料モデル、平均取得単価管理をサポート。
    - SELL は保有全量をクローズ（部分利確未対応）。
    - mark_to_market による日次スナップショット（DailySnapshot）記録。
    - TradeRecord と DailySnapshot の dataclass を公開。
  - run_backtest エンジンを実装:
    - 本番 DB からインメモリ DuckDB へ必要データをコピー（signals/positions を汚さない）。
    - 日次ループ: 約定（前日シグナルを当日始値で約定）→ positions 書き戻し → 時価評価 → シグナル生成（generate_signals）→ 発注リスト作成 の一連処理を実行。
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20。
  - バックテスト用コネクション作成時に date 範囲でテーブルをフィルタしてコピーすることでパフォーマンスとメモリ使用を制御。market_calendar は全件コピー。

- バックテストメトリクス (src/kabusys/backtest/metrics.py)
  - バックテスト評価指標を計算する calc_metrics を実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）。
  - 内部実装で各指標の数式とエッジケース（データ不足やゼロ分散等）への安全処理あり。

### 変更 (Changed)
- 初期リリースのため、既存コードベースの設計方針・API 仕様をドキュメント的に整備（各モジュールの docstring に設計方針・参照テーブル・挙動を明記）。

### 修正 (Fixed)
- トランザクション失敗時の ROLLBACK に失敗するケースをキャッチして警告ログを出すようにし、例外の透明性を確保（feature_engineering / signal_generator の COMMIT/ROLLBACK 周り）。
- .env ファイル読み込み時のファイルオープン失敗を warnings.warn で通知し、処理を継続するように堅牢化。

### 注意 / 未実装 (Known issues / Unimplemented)
- signal_generator/_generate_sell_signals 内の未実装条件:
  - トレーリングストップ（peak_price に依存）および時間決済（保有 60 営業日超過）は positions テーブルに追加カラム（peak_price / entry_date）が必要で現バージョンでは未実装。
- PortfolioSimulator の BUY は資金配分（alloc）に基づくが部分約定や複雑な注文タイプは未対応。
- research モジュールは DuckDB の prices_daily / raw_financials を前提。データの前処理が必要。

### セキュリティ (Security)
- なし

---

将来的なリリースで追加検討する事項（例）
- positions に peak_price / entry_date を導入してトレーリングストップや時間決済を実装
- 部分利確 / 指値/成行の注文シミュレーション拡張
- 外部依存（pandas 等）の導入と高速化オプション
- 詳細なモニタリング・Slack 通知連携（既に Slack のトークン等設定は用意）

（注）本 CHANGELOG はソースコードの内容から推測して作成しています。実際の設計ドキュメントや運用ルールに基づく変更履歴とは差異が生じる可能性があります。必要であれば追加情報（意図したリリースノート項目、想定読者、重要度）に合わせて調整します。