# CHANGELOG

すべての変更は「Keep a Changelog」形式に従い、セマンティック バージョニングを採用しています。  
このファイルはコードベース（初期実装）から推測して作成した変更履歴です。

## [Unreleased]

## [0.1.0] - 2026-03-22
初回リリース。日本株自動売買システム「KabuSys」のコア機能群を実装したバージョン。

### Added
- パッケージ基盤
  - パッケージ情報: kabusys v0.1.0 を定義（src/kabusys/__init__.py）。
  - public API エクスポート: data, strategy, execution, monitoring（__all__）。

- 環境設定 / .env ロード機能（src/kabusys/config.py）
  - プロジェクトルート検出: .git または pyproject.toml を基準にルートを探索する自動検出を実装（CWD非依存）。
  - .env ファイルパーサ: export 前置、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応した堅牢な行パーサを実装。
  - 自動ロードの優先順位: OS環境変数 > .env.local > .env。OS変数は protected として保護。
  - 自動ロード無効化オプション: 環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラス: アプリケーション設定をプロパティで提供（J-Quants / kabu API / Slack / DB パス / env/log_level 判定等）。
    - 必須変数未設定時に ValueError を送出する _require を提供。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
    - duckdb / sqlite のデフォルトパス設定（expanduser 対応）。

- 戦略 (feature engineering / signal generation)
  - features 作成（src/kabusys/strategy/feature_engineering.py）
    - build_features(conn, target_date): research モジュールが出力する生ファクターを統合し、ユニバースフィルタ、Zスコア正規化（zscore_normalize 依存）、±3 でのクリップを行い features テーブルへ日付単位で置換（冪等）。
    - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
    - DuckDB を用いた価格取得、トランザクション（BEGIN/COMMIT/ROLLBACK）を利用した原子的な削除→挿入。
    - ログ出力による処理件数の記録とエラーハンドリング（ROLLBACK 失敗時の警告）。

  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - generate_signals(conn, target_date, threshold=0.60, weights=None): features / ai_scores / positions を参照し BUY/SELL シグナルを生成して signals テーブルへ日付単位で置換（冪等）。
    - ファクター統合: momentum / value / volatility / liquidity / news の重み付け（デフォルト設定を提供）、ユーザ指定 weights のバリデーションと正規化。
    - スコア計算:
      - Zスコアをシグモイド関数で [0,1] に変換、欠損成分は中立 0.5 で補完。
      - AI ニューススコアを統合、regime_score を用いた市場レジーム判定（Bear レジームで BUY 抑制）。
    - SELL（エグジット）判定:
      - 実装済み条件: ストップロス（-8%）、final_score が閾値未満。
      - 価格欠損時は SELL 判定をスキップし警告ログを出力。
      - positions にない銘柄は final_score=0.0 扱いで SELL 対象に（警告ログ）。
    - signals テーブルへの書き込みはトランザクションで行い、BUY と SELL を分けて挿入。SELL 優先で BUY から除外。

  - strategy パッケージの public API（src/kabusys/strategy/__init__.py）
    - build_features, generate_signals をエクスポート。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev（200日MA乖離）を DuckDB SQL で計算。
    - calc_volatility(conn, target_date): ATR20、atr_pct、avg_turnover、volume_ratio を計算（true_range の NULL 伝播制御を含む）。
    - calc_value(conn, target_date): raw_financials から最新財務データを取得し PER / ROE を計算（EPS が 0 または欠損の場合は None）。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons=[1,5,21]): 各ホライズンの将来リターンを計算（LEAD を使用、日付スキャン範囲最適化）。
    - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンランク相関（IC）を計算、少数サンプル時は None。
    - factor_summary(records, columns): count/mean/std/min/max/median を計算。
    - rank(values): 同順位に平均ランクを割当てるランク関数（round で丸めて ties 判定精度向上）。
  - research パッケージの public API をエクスポート。

- バックテスト（src/kabusys/backtest）
  - シミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator: メモリ内での保有管理、約定ロジック、スリッページ/手数料モデル、マーク・トゥ・マーケットを実装。
      - execute_orders: SELL を先に処理、BUY は alloc に基づく建玉（shares は floor）、BUY 時の手数料込みで再計算して資金越えを防止。
      - SELL は保有全量クローズ（部分利確・部分損切りは未対応）。
      - mark_to_market: 終値で評価、終値欠損時は 0 として警告ログ。
      - TradeRecord / DailySnapshot を記録。
  - メトリクス（src/kabusys/backtest/metrics.py）
    - calc_metrics(history, trades) -> BacktestMetrics: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算。
    - 内部計算関数として年次化や標準偏差、最大ドローダウン等を実装（営業日ベースで年次化は 252 日）。
  - バックテストエンジン（src/kabusys/backtest/engine.py）
    - run_backtest(conn, start_date, end_date, ...): 本番 DB から日付範囲を限定してインメモリ DuckDB へコピーし、日次ループでシグナル生成→約定→マーク・トゥ・マーケット→positions書き戻しを実行する一連のワークフローを実装。
    - _build_backtest_conn: 本番 conn から必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）をコピー（失敗時は警告でスキップ）。
    - _fetch_open_prices / _fetch_close_prices / _write_positions / _read_day_signals: バックテスト時の補助ユーティリティを実装。
    - ポジションサイジングのための max_position_pct を受け取り、alloc を計算して BUY を配分。

- 汎用設計・運用面の実装
  - 外部依存を極力抑え、DuckDB と標準ライブラリ中心で実装（research モジュールは pandas 等に依存しない設計）。
  - ルックアヘッドバイアス回避: target_date 時点のデータのみ参照する設計方針を各所に明記。
  - データ書き込みは日付単位で「削除→挿入」の置換を行い、トランザクションで原子性を担保。
  - ログ出力と警告を多用し、欠損データや異常時の挙動を可視化。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Known issues / 未実装・制約
- 戦略の一部仕様は未実装（ソースコメント参照）:
  - トレーリングストップ（直近最高値基準の -10%）は未実装（positions テーブルに peak_price / entry_date が必要）。
  - 時間決済（保有 60 営業日超過）未実装。
  - PBR・配当利回りなどのバリューファクターは未実装。
- execution 層（実際の発注 API との連携）は実装されていない（execution パッケージは空のプレースホルダ）。
- AI スコア・regime_score の供給がない場合は中立扱いやサンプル数閾値での判定回避を行う設計のため、AI 機能依存の結果は供給状況により変化する。
- 一部計算はデータ不足時に None / 0.0 を返す動作があり、後続処理で中立補完される。
- market_calendar 等のコピーが失敗した場合は警告ログを出すが、バックテストの挙動に影響を与える可能性あり。

### Notes / 設計上の重要点
- 冪等性: features / signals / positions への書き込みは日付単位での置換による冪等操作を前提とする。
- データ欠損に対する安全策（価格欠損時の SELL 判定スキップ、警告ログ）を講じている。
- 重み付けや閾値はデフォルト値を定義しており、generate_signals の weights 引数で調整可能。外部から不正な weights を渡した場合は入力を無視または正規化する。
- DuckDB を中心に SQL と Python を組み合わせてパフォーマンスと可読性を確保している（ウィンドウ関数やLEAD/LAGを多用）。

贡献・メンテナ
- 初期実装（推定）：リポジトリ内の各モジュールを構成する開発者（詳細はコミット履歴参照）。

---

参考:
- 本CHANGELOGはコードの実装内容から推測して作成しています。実際のリリースノートとして公開する際は、コミットログや実際の変更履歴と照合してください。