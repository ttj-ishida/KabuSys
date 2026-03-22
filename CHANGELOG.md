CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従います。  

フォーマット:
- 見出しはリリースバージョン（YYYY‑MM‑DD）または Unreleased
- 各リリースはカテゴリ（Added, Changed, Fixed, Deprecated, Removed, Security）を含みます

Unreleased
----------
（現在のところ未リリースの変更はありません）

0.1.0 - 2026-03-22
-----------------
初期リリース。日本株向けの自動売買基盤ライブラリを提供します。主な追加点は以下のとおりです。

Added
- パッケージのエントリポイント
  - src/kabusys/__init__.py を追加。バージョン番号 __version__ = "0.1.0" と公開モジュール __all__ を定義。
- 環境設定管理
  - src/kabusys/config.py を追加。
    - .env および .env.local の自動読み込み（プロジェクトルートの検出は .git または pyproject.toml を基準）。
    - export 書式やクォート、インラインコメントを考慮した .env パーサー実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト向け）。
    - 必須環境変数取得の _require()、Settings クラスで各種設定プロパティ（J-Quants、kabu API、Slack、DB パス、環境／ログレベル判定など）を提供。
    - 環境値のバリデーション（KABUSYS_ENV / LOG_LEVEL の許容値チェック）。
- 戦略（feature engineering と signal generator）
  - src/kabusys/strategy/feature_engineering.py を追加。
    - research モジュールから取得した raw ファクターをマージ、ユニバースフィルタ（最低株価・最低売買代金）、Zスコア正規化、±3クリップ、features テーブルへの日単位 UPSERT（トランザクションで原子性確保）を実装。
    - duckdb 接続を受け取り安全に処理する設計（トランザクション、ROLLBACK のハンドリング）。
  - src/kabusys/strategy/signal_generator.py を追加。
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付けにより final_score を算出。
    - Bear レジーム判定（AI の regime_score 平均が負）による BUY 抑制。
    - BUY（閾値超過）および SELL（ストップロス／スコア低下）シグナル生成、signals テーブルへの日単位置換（トランザクション）。
    - 重みの受け取りと検証、合計が 1.0 でない場合のリスケーリング、無効な重みを無視する安全策を実装。
- Research（因子計算・解析）
  - src/kabusys/research/factor_research.py を追加。
    - Momentum（mom_1m, mom_3m, mom_6m, ma200_dev）、Volatility（atr_20, atr_pct, avg_turnover, volume_ratio）、Value（per, roe）などのファクター計算を実装。DuckDB のウィンドウ関数を活用し営業日ベースのラグ計算に対応。
    - データ不足時の None 処理（ウィンドウ長未満など）。
  - src/kabusys/research/feature_exploration.py を追加。
    - 将来リターン計算 calc_forward_returns（複数ホライズン対応、SQL 一括取得）、IC（Spearman の ρ）計算 calc_ic、ファクター統計サマリ factor_summary、ランク付け util を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - src/kabusys/research/__init__.py で主要関数を公開。
- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py を追加。
    - PortfolioSimulator（擬似約定、ポジション管理、スリッページ・手数料モデル、mark_to_market、TradeRecord / DailySnapshot データクラス）を実装。
    - BUY/SELL の約定処理ロジック（BUY は割当額に基づき株数を算出、手数料とスリッページ考慮、SELL は保有全量をクローズ）や警告ログを実装。
  - src/kabusys/backtest/metrics.py を追加。
    - バックテスト評価指標（CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio、総トレード数）を計算するユーティリティを実装。
  - src/kabusys/backtest/engine.py を追加。
    - run_backtest(): 本番 DuckDB から必要データをインメモリにコピーして日次ループでシミュレーションを実行するフローを実装。
    - コピー用の _build_backtest_conn、価格取得ユーティリティ、positions の書き戻し、signals 読み取りなどを提供。
    - シミュレーションでは generate_signals を呼び出して日次シグナルを生成、PortfolioSimulator と連携して取引を実行。
  - src/kabusys/backtest/__init__.py で API を公開（run_backtest 等）。
- パッケージ公開関係
  - src/kabusys/strategy/__init__.py で build_features と generate_signals を公開。
  - src/kabusys/backtest/__init__.py で主要クラス/関数を公開。

Changed
- なし（初期リリース）

Fixed
- なし（初期リリース）

Deprecated
- なし（初期リリース）

Removed
- なし（初期リリース）

Security
- なし（初期リリース）

Notes / Known limitations / TODO
- 一部のエグジット条件は未実装（コメント参照）
  - トレーリングストップ（peak_price が positions に必要）
  - 時間決済（保有 60 営業日超など）
- calc_forward_returns / factor 計算は prices_daily / raw_financials 等のテーブルが前提。スキーマ初期化関数（kabusys.data.schema.init_schema）を想定。
- generate_signals / build_features は外部発注 API に依存しない設計（signals テーブルへの書き込みまでを担う）。
- .env 自動読み込みはプロジェクトルート検出に依存する（.git または pyproject.toml）。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して無効化可能。
- DuckDB を主要なストレージ／分析エンジンとして利用。外部依存（pandas 等）は避ける方針。
- トランザクション処理時に例外が発生した場合の ROLLBACK の失敗をログ出力している（安全性に配慮）。

開発者向け補足
- ログは各モジュールで logger.getLogger(__name__) を使っており、外部でハンドラを設定することで統合的なログ管理が可能。
- Settings クラスはプロパティアクセスで環境値を遅延評価／検証するため、テスト時に環境変数を差し替えて挙動を確認しやすい。
- バックテストは本番 DB を汚さないためにインメモリコピーを行う設計。コピー時に問題が発生したテーブルはログ警告でスキップされる。

（今後）
- エグジットロジックの拡充（トレーリング・時間決済など）、ポジションサイジングの細化、AI スコア取得の IO 層整備、監視／実行層の実装拡張を予定。