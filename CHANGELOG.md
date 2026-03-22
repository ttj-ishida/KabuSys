# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

現在のバージョン: 0.1.0

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」のコア機能を提供します。

### Added
- パッケージ基盤
  - パッケージ情報を格納する __init__.py を追加（バージョン 0.1.0）。
  - 公開 API: strategy.build_features / strategy.generate_signals を __all__ でエクスポート。

- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを実装。
  - 自動ロード機能:
    - プロジェクトルートを .git または pyproject.toml から探索して .env / .env.local を自動読み込み。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - 高度な .env パーサ:
    - export KEY=value 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなしのコメント認識を実装。
    - 読み込み失敗時に警告を発行。
  - 設定プロパティ:
    - JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID 等の必須設定取得（未設定時は ValueError）。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の検証付きプロパティ。
    - デフォルトの DB パス（DUCKDB_PATH / SQLITE_PATH）の展開。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date)
    - research モジュールの calc_momentum / calc_volatility / calc_value を用いて生ファクターを取得。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）を適用。
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップして外れ値の影響を抑制。
    - features テーブルへ日付単位での置換（削除→挿入）をトランザクションで行い冪等性を確保。
    - 休場日や当日欠損に対応するため、target_date 以前の最新終値を参照。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold, weights)
    - features / ai_scores / positions を参照し、各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換によるスケーリングと欠損補完（None は中立0.5で補完）。
    - デフォルト重み（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）を採用。ユーザ指定の weights は検証（負値・NaN・Inf 等を除外）し、合計を 1.0 に再スケール。
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY シグナルを抑制。
    - BUY シグナル閾値はデフォルト 0.60。SELL 条件はストップロス（-8%）およびスコア低下（threshold 未満）。
    - SELL を優先して BUY から除外し、signals テーブルへ日付単位で置換（トランザクションで原子性保証）。

- 研究用ツール群 (kabusys.research)
  - factor_research: calc_momentum / calc_volatility / calc_value
    - 各種ファクター（モメンタム、MA200乖離、ATR/atr_pct、avg_turnover、volume_ratio、per/roe）をprices_daily/raw_financialsから計算。
    - 欠損やデータ不足条件（必要行数未満）の扱いを明確化。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21])：LEAD を利用して複数ホライズンの将来リターンを一括取得。horizons の検証あり。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：スピアマンランク相関（ICC）を計算。サンプル不足時は None を返す。
    - rank(values)：同順位は平均ランクとする安定なランク計算（丸め処理あり）。
    - factor_summary(records, columns)：count/mean/std/min/max/median を算出。

- バックテストフレームワーク (kabusys.backtest)
  - simulator: PortfolioSimulator / DailySnapshot / TradeRecord
    - BUY/SELL の擬似約定ロジック（始値を基準、スリッページ・手数料適用、SELL 先行処理、BUY は資金に応じてシェア数を調整）。
    - SELL は保有全量クローズ。平均取得単価（cost_basis）の更新、トレード履歴の記録。
    - mark_to_market() による終値評価と DailySnapshot 記録（終値欠損時の警告と 0 評価）。
  - metrics: バックテスト評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）計算ロジックを提供。
  - engine: run_backtest(conn, start_date, end_date, ...)
    - 本番 DB から必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を日付範囲でインメモリ DuckDB へコピーしてバックテスト用接続を作成（本番テーブル汚染を回避）。
    - 日次ループ: 前日シグナルを始値で約定 → positions テーブルへ書き戻し → 終値評価 → generate_signals による当日シグナル生成 → シグナルに基づく発注。
    - positions の書き戻しは generate_signals の SELL 判定に必要なため冪等に実装。

### Changed
- （初回リリースのため該当なし）

### Fixed
- トランザクション失敗時の取り扱いを明確化:
  - build_features / generate_signals でコミット失敗時は ROLLBACK を試行し、ROLLBACK 自体失敗した場合は警告ログを出力して例外を再送出。

### Security
- 設定読み込みで OS 環境変数を保護する仕組みを導入（.env の上書きを制御する protected set）。
- .env の読み込み失敗は例外で止めず警告とし、プロセスが意図せず停止しないよう配慮。

### Notes / Known limitations
- 一部の高度な売買ロジック（トレーリングストップ、時間決済など）は未実装（engine / _generate_sell_signals のコメント参照）。positions テーブルに peak_price / entry_date 等が必要。
- calc_forward_returns は最大ホライズンの 2 倍のカレンダー日をスキャンするバッファを使用しているため、極端に欠損したデータセットでは期待通りの結果にならない可能性あり。
- バックテストは in-memory DuckDB を利用するため、大規模データではメモリ制約に注意。

---

今後のリリースでは以下を検討しています:
- 部分利確／部分損切り・トレーリングストップ等のエグジット戦略実装
- リアルタイム execution 層との統合（実運用向けの注文・監視モジュール）
- モデル管理（AI スコアの学習・履歴管理）および More robust error handling/observability

もし CHANGELOG に追加してほしい点や、各機能の詳細な説明を希望される場合は教えてください。