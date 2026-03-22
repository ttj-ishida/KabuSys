CHANGELOG
=========

すべての重要な変更点は Keep a Changelog の形式に従って記録しています。

フォーマット:
- Unreleased: 今後の変更（現時点では未リリース）
- 各リリースはバージョンと日付を記載
- セクション: Added / Changed / Fixed / Security / Breaking Changes

Unreleased
----------
（なし）

[0.1.0] - 2026-03-22
-------------------

Added
- パッケージの初期公開（kabusys v0.1.0）
  - パッケージ概要: 日本株自動売買システムのコアライブラリ。
  - エントリポイント: src/kabusys/__init__.py にて __version__ = "0.1.0"、主要サブパッケージを公開。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
  - 自動ロードの探索はパッケージファイル位置から親ディレクトリを上向きに検索し、.git または pyproject.toml をプロジェクトルートと判定。
  - .env と .env.local の読み込み順（OS 環境 > .env.local > .env）。.env.local は override=True（OS 環境で保護されたキーは上書きされない）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
  - Settings クラスを提供し、必須環境変数の取得（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）やパス（DUCKDB_PATH, SQLITE_PATH）、実行環境（KABUSYS_ENV）・ログレベル（LOG_LEVEL）等を取得可能。不正値時は ValueError を送出。

- 戦略: 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date): research モジュールで計算した生ファクターを正規化・合成し、features テーブルへ日付単位で置換（冪等）して書き込む。
  - ユニバースフィルタを実装（最低株価 _MIN_PRICE = 300 円、20日平均売買代金 _MIN_TURNOVER = 5e8 円）。
  - 正規化: 指定の数値カラムを Z スコア正規化し、±3 でクリップして外れ値を抑制。
  - DuckDB を前提とした SQL 取得とトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を担保。
  - 依存: kabusys.research.factor_research の calc_momentum / calc_volatility / calc_value、および kabusys.data.stats.zscore_normalize を利用。

- 戦略: シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None):
    - features, ai_scores, positions を参照して BUY/SELL シグナルを生成し、signals テーブルへ日付単位で置換（冪等）して書き込む。
    - ファクターコンポーネント（momentum/value/volatility/liquidity/news）ごとのスコア計算を実装（デフォルト重み momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10）。
    - スコア変換: Z スコアに対してシグモイド関数を適用し、None は中立値 0.5 で補完。
    - Bear レジーム判定: ai_scores の regime_score 平均が負なら Bear（サンプル数が閾値未満なら Bear とみなさない）。Bear 時は BUY を抑制。
    - SELL（エグジット）判定の実装:
      - ストップロス: (close / avg_price - 1) < -0.08（-8%）
      - スコア低下: final_score < threshold
      - 保有銘柄に価格がない場合は SELL 判定をスキップして警告ログを出力。
    - weight 辞書は不正値をスキップし、デフォルトでフォールバック。合計が 1.0 でない場合は正規化して適用。
    - 生成された BUY・SELL は signals テーブルへ書き込み（BUY は signal_rank を付与、SELL は NULL）。

- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev を計算（200 日未満は None）。
    - calc_volatility(conn, target_date): atr_20、atr_pct（ATR/close）、avg_turnover、volume_ratio を計算（ATR・移動窓のデータ不足は None）。
    - calc_value(conn, target_date): raw_financials から直近財務データを取得して PER・ROE を計算（EPS が 0/欠損なら PER は None）。
  - feature_exploration:
    - calc_forward_returns(conn, target_date, horizons=[1,5,21])：各銘柄の将来リターンを一括 SQL で取得。
    - calc_ic(factor_records, forward_records, factor_col, return_col)：Spearman（ランク相関）に基づく IC を計算（有効レコード >=3 必須）。
    - factor_summary(records, columns)：各カラムの count/mean/std/min/max/median を算出。
    - rank(values)：同順位は平均ランクを割り当てるランク関数。
  - research は標準ライブラリのみ（pandas 等に依存しない）で実装。

- データ層との連携
  - DuckDB を使用した SQL ベースのデータアクセスを前提。
  - features/ai_scores/prices_daily/positions 等のスキーマ前提で設計。
  - features・signals・positions への書き込みは日付単位の DELETE→INSERT による置換で冪等性を保持。

- バックテストフレームワーク (kabusys.backtest)
  - engine.run_backtest(conn, start_date, end_date, initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20)
    - 本番 DB からインメモリ DuckDB へ必要テーブルをコピーしてバックテスト用環境を構築（signals/positions を汚染しない）。
    - 日次ループ: 前日シグナルの約定、positions テーブルへの書き戻し、時価評価、generate_signals によるシグナル生成、発注（サイジング）、履歴記録を実施。
    - 取引ルールの一部（ポジションサイジング）を engine 内で実施。
  - simulator.PortfolioSimulator
    - 擬似約定ロジック（BUY は始値にスリッページを加算、SELL は始値にスリッページを差し引き）。
    - 手数料は約定金額 × commission_rate。BUY の手数料は現金引き落としで処理、SELL の realized_pnl は手数料差引きで計算。
    - BUY は全額買い付け可能な株数まで切り捨て（floor）。SELL は保有全量クローズのみ（部分利確は未対応）。
    - mark_to_market で終値評価、不足価格は 0 として警告を出す。
  - metrics.calc_metrics: history（DailySnapshot）と trades（TradeRecord）から各種評価指標（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）を算出。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Breaking Changes
- 初回リリースのため該当なし。

Notes / 実装上の重要事項
- 多くの機能が DuckDB の SQL とトランザクションに依存しています。適切なテーブルスキーマ（prices_daily, features, ai_scores, positions, signals, raw_financials, market_calendar 等）が前提です。
- 冪等性: features / signals / positions への書き込みは日付ごとの削除→挿入を行い、複数回実行しても同じ結果になることを目指しています（トランザクションで原子性を担保）。
- 欠損データの扱い:
  - ファクター計算でデータ不足の場合は None を返し、シグナル生成時は中立値（0.5）で補完する設計。
  - 価格欠損など致命的な場合は処理をスキップし、ログ出力で通知。
- 環境変数と自動ロード: プロジェクトルートの検出に失敗した場合は自動ロードをスキップするため、配布後の利用で .env を明示的に読み込ませることが可能。

今後の予定（例）
- 部分利確／部分損切りやトレーリングストップの追加（現状は SELL は保有全量クローズ）。
- PBR・配当利回り等のバリューファクター拡張。
- ポートフォリオのより柔軟なサイジング戦略の実装。
- 単体テスト・CI の充実化、ドキュメント生成。

---

貢献・フィードバック歓迎。コード内の docstring とコメントに設計意図・参照ドキュメント（StrategyModel.md 等）が記載されていますので、実装確認時に参照してください。