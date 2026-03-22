Keep a Changelog 準拠 — CHANGELOG.md

すべての変更は意図的にコードベース（src/kabusys/ 以下）から推測して記載しています。実際のコミット履歴ではなく、現行実装の機能・設計方針・既知の制約に基づく初回リリースの説明です。

Unreleased
---------
- 今後の予定（推奨改善点・未実装の機能）
  - トレーリングストップ / 時間決済の実装（戦略のエグジット条件）
  - features / ai_scores の更なる整合性チェックと欠損値ハンドリングの強化
  - パフォーマンス改善（DuckDB クエリの最適化、バルク処理の高速化）
  - より詳細なエンドツーエンドの統合テスト（.env 自動ロードやバックテストの境界条件）
  - ドキュメント拡充（StrategyModel.md / BacktestFramework.md の公開）
  - 発注 API（execution 層）との統合例およびモック

[0.1.0] - 2026-03-22
-------------------
Added
- パッケージ初回リリース（kabusys v0.1.0 相当）
  - パッケージエントリポイント: src/kabusys/__init__.py にて __version__ = "0.1.0" を定義。
- 環境設定管理
  - src/kabusys/config.py
    - .env / .env.local の自動ロード機能（プロジェクトルートは .git または pyproject.toml で探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト等で使用）。
    - export KEY=val や quoted value、インラインコメントなど一般的な .env 書式の柔軟なパース。
    - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パスなどの設定をプロパティ経由で取得。
    - 必須設定は _require() で検証（未設定時は ValueError を送出）。
    - デフォルトや許容値の定義:
      - KABUSYS_ENV の有効値: development / paper_trading / live
      - LOG_LEVEL の有効値: DEBUG / INFO / WARNING / ERROR / CRITICAL
      - デフォルト DB パス: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
      - KABUSYS_DISABLE_AUTO_ENV_LOAD を使った自動ロード回避
- 戦略関連
  - src/kabusys/strategy/feature_engineering.py
    - research で算出した生ファクターを取得し、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムの Z スコア正規化（zscore_normalize を利用）と ±3 のクリップ処理。
    - features テーブルへ日付単位で置換（トランザクション＋バルク挿入）する build_features(conn, target_date) を提供。冪等性を保持。
  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合して最終スコア（final_score）を算出し、BUY / SELL シグナルを生成する generate_signals(conn, target_date, threshold, weights) を提供。
    - デフォルトの重み配分 / 閾値を実装（momentum:0.40, value:0.20, volatility:0.15, liquidity:0.15, news:0.10、threshold=0.60）。
    - AI レジーム集計により Bear レジーム検出を実装（サンプル数閾値あり）。Bear レジーム時は BUY を抑制。
    - SELL 判定ロジックを実装（ストップロス: 損益率 <= -8%、final_score の閾値割れ）。未実装のルール（トレーリングストップ、時間決済）について注記。
    - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）するため冪等。
- リサーチ（研究用）機能
  - src/kabusys/research/factor_research.py
    - モメンタム（1/3/6 か月リターン、MA200 乖離）、ボラティリティ（20日 ATR、相対 ATR、平均売買代金、出来高比率）、バリュー（PER/ROE）を計算する calc_momentum / calc_volatility / calc_value を実装。
    - prices_daily / raw_financials のみ参照（外部 API にはアクセスしない設計）。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns（デフォルト horizons = [1,5,21]）を実装。
    - ランク相関（Spearman）による IC 計算 calc_ic、factor_summary（基本統計量）、rank（平均ランク処理）を実装。
    - pandas 等に依存せず標準ライブラリ + DuckDB のみで実装。
  - research パッケージの __all__ に主要ユーティリティを公開。
- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator クラスを実装（資金・保有株・コストベース・履歴・約定履歴の管理）。
    - 約定ロジック（execute_orders）: SELL を先、BUY を後に処理。BUY は割当資金に基づき始値で約定、スリッページ・手数料考慮。SELL は保有全量をクローズ。
    - mark_to_market により終値で時価評価して DailySnapshot を記録。
    - TradeRecord / DailySnapshot のデータクラス定義を提供。
  - src/kabusys/backtest/metrics.py
    - calc_metrics により CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算する機能を実装。
  - src/kabusys/backtest/engine.py
    - run_backtest 関数を実装。実運用 DB からインメモリ DuckDB へ必要テーブルをコピー（_build_backtest_conn）して日次ループを実行、generate_signals を用いたシグナル生成と約定シミュレーション、positions の書き戻し、履歴・約定の収集を実施。
    - get_trading_days の利用、open/close 価格の取得ユーティリティ、positions の冪等書き込みを実装。
- モジュールエクスポート
  - 各サブパッケージの __init__.py で主な関数 / クラスを公開（backtest, research, strategy など）。
- DB / トランザクション安全性
  - features / signals 等のテーブル更新はトランザクション + 冪等な日付置換（DELETE + INSERT）で原子性を保持。
  - DuckDB を主要な時系列 DB として想定。

Changed
- （初回リリースのため過去変更なし。設計上の決定を列挙）
  - .env 自動ロードはプロジェクトルート探索（.git / pyproject.toml）に基づき、CWD に依存しない設計。
  - 欠損値や非有限値（NaN/Inf）に対する堅牢な扱いを各所で実装（スコア計算、統計、クエリ結果のフィルタリング）。

Fixed
- （初回リリース。既知のワークアラウンド・制約を実装段階で反映）
  - .env 読み込み失敗時の警告出力（warnings.warn）。
  - トランザクション失敗時の ROLLBACK 試行と警告ロギング。

Deprecated
- なし。

Removed
- なし。

Security
- 環境変数の取り扱いについて
  - OS 環境変数は自動ロードで保護（.env の上書きを防ぐため protected set を使用）。
  - 必須トークン類（JQUANTS_REFRESH_TOKEN / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / KABU_API_PASSWORD）は Settings で明示的に要求し、未設定時はエラーを投げることで運用ミスを早期に検出。

注記（実装上の既知制約／設計決定）
- 戦略面の未実装点
  - トレーリングストップや時間決済（保有期間による強制決済）は未実装。コード中に注釈あり。
- アルゴリズム的な欠損値扱い
  - コンポーネントスコアが None の場合、最終スコア計算時に中立値 0.5 で補完する設計（欠損銘柄の不当な降格を防止）。
- Bear 判定は ai_scores の regime_score の平均で行い、サンプル数が閾値未満なら Bear と判定しない（誤判定防止）。
- 外部依存最小化
  - research モジュールは pandas 等を使わず標準ライブラリと DuckDB のみで実装。
- テスト / 運用
  - 自動 .env ロードは便利だが、テスト環境では KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を推奨。

補足
- 本 CHANGELOG はコードからの推測に基づくため、実際のコミットメッセージやリリースノートと差異がある可能性があります。正式なリリースノートを作成する際は、実際の変更履歴（Git コミット／PR）を参照してください。