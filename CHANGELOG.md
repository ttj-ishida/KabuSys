CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" と Semantic Versioning に従います。

[Unreleased]
------------

（現在未リリースの変更はありません）

[0.1.0] - 2026-03-22
-------------------

Added
- 初回公開: KabuSys 日本株自動売買システムの基本モジュール群を追加。
  - パッケージ情報:
    - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - 設定管理:
    - src/kabusys/config.py
      - .env / .env.local ファイルおよび環境変数から設定を自動読み込みする Settings クラスを実装。
      - プロジェクトルート検出（.git または pyproject.toml を起点）によりカレントディレクトリに依存しない自動ロードを実装。
      - .env パーサを実装（export 形式、引用符内のエスケープ、インラインコメント処理、protected 値の取り扱い等に対応）。
      - 必須環境変数取得用の _require とデフォルト値（KABUSYS_ENV, LOG_LEVEL, DB パス等）を提供。
      - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
      - 管理対象の主な環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH など。
  - 研究（research）モジュール:
    - src/kabusys/research/factor_research.py
      - calc_momentum, calc_volatility, calc_value を実装。prices_daily / raw_financials テーブルを参照し、モメンタム・ボラティリティ・バリュー関連の生ファクターを算出。
      - 長期移動平均（MA200）や ATR20、20日平均売買代金、volume_ratio 等を計算。
    - src/kabusys/research/feature_exploration.py
      - calc_forward_returns: 指定日から将来リターン（デフォルト: 1,5,21営業日）を計算。
      - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。
      - factor_summary / rank: ファクター列の統計サマリーとランク変換ユーティリティを提供。
    - research パッケージのエクスポート（calc_momentum 等）を提供。
  - 特徴量エンジニアリング＆戦略:
    - src/kabusys/strategy/feature_engineering.py
      - research モジュールから得た生ファクターを統合し、ユニバースフィルタ（最低株価、平均売買代金）を適用、Zスコア正規化（zscore_normalize を利用）→ ±3 でクリップして features テーブルへ日付単位で UPSERT（トランザクションで原子性を保証）。
      - ルックアヘッドバイアスを避けるため target_date 時点のデータのみを利用。
    - src/kabusys/strategy/signal_generator.py
      - features と ai_scores を統合してコンポーネントスコア（momentum / value / volatility / liquidity / news）を算出。重み付け合算により final_score を算出して BUY/SELL シグナルを生成し、signals テーブルへ日付単位で置換挿入。
      - Bear レジーム検知（ai_scores の regime_score 平均が負の場合）による BUY シグナル抑制。
      - SELL 判定にはストップロスやスコア低下を採用（positions / prices_daily を参照）。SELL を優先して BUY から除外するポリシーを実装。
      - ユーザ提供重みのバリデーションと自動リスケール、欠損コンポーネントの中立補完（0.5）等の堅牢性を確保。
    - strategy パッケージから build_features / generate_signals をエクスポート。
  - バックテストフレームワーク:
    - src/kabusys/backtest/simulator.py
      - PortfolioSimulator 実装: メモリ内でのポートフォリオ状態管理、BUY/SELL の擬似約定（始値・スリッページ・手数料を考慮）、約定履歴（TradeRecord）と日次スナップショット（DailySnapshot）を記録。
      - mark_to_market による時価評価、保有株に終値がない場合は 0 で評価して警告ログを出す実装。
    - src/kabusys/backtest/metrics.py
      - バックテスト評価指標を計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades）。
    - src/kabusys/backtest/engine.py
      - run_backtest を実装。実運用 DB からインメモリ DuckDB へデータコピー（_build_backtest_conn）して日次ループを実行、generate_signals を利用したシミュレーションを行い、最終的に履歴・トレード・メトリクスを返却。
      - signals / positions の読み書き、当日始値/終値の取得、positions を用いた SELL 判定フローを整備。
    - backtest パッケージの公開 API（run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics）を提供。
  - パッケージ構成:
    - __all__ に data, strategy, execution, monitoring を含め、モジュール分割を想定（execution は雛形ファイルを含む）。

Changed
- 実装方針の明記:
  - 各モジュールに docstring を充実させ、設計方針（ルックアヘッドバイアス回避、本番 DB への書き込み回避、DuckDB のみ参照等）を明示。
- DB 操作の堅牢化:
  - features / signals への書き込みは日付単位で DELETE→INSERT のトランザクション（BEGIN/COMMIT/ROLLBACK）を使用して原子性を確保。
  - 各所で None / 非有限値のチェック（math.isfinite）を行い、NaN/Inf による誤動作を防止。

Fixed
- ロバストネス向上:
  - .env パーサにおいて引用符内のエスケープやインラインコメント処理を正しく扱うように実装（実環境での .env 読み込み誤動作を低減）。
  - シグナル生成／売買ロジックにおいて、欠損データ（価格欠損、財務データ欠損等）発生時は警告ログを出して安全側の挙動（SELL 判定スキップや中立補完）を適用。

Security
- 特記事項なし。

Notes / Implementation details
- 依存・前提:
  - DuckDB を利用してローカル DB（prices_daily, raw_financials, features, ai_scores, positions, market_calendar 等）を操作する設計。
  - data.stats.zscore_normalize 等、data パッケージのユーティリティを利用する箇所があるため、data モジュール実装が必要。
  - Slack トークンや各種 API 情報は環境変数で提供する前提（設定管理モジュールにて必須チェックあり）。
- 未実装 / 将来の拡張候補:
  - factor_research の一部ファクター（PBR・配当利回り）や signal_generator の一部エグジット条件（トレーリングストップ、時間決済）は docstring にて未実装として明示。
  - execution 層（実際の発注 API 統合）はまだ実装ファイルが雛形のみ。monitoring も同様に拡張を想定。

以上が v0.1.0 (初版) の主な変更点・機能です。各モジュールの docstring とログ出力に実装意図・注意点が記載されているため、開発・運用時はそちらも参照してください。