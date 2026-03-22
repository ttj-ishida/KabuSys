CHANGELOG
=========
All notable changes to this project will be documented in this file.

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
各リリースには主要な追加機能・変更点・既知の制限点を記載しています。

Unreleased
----------
（現在なし）

0.1.0 - 2026-03-22
------------------
初期リリース。以下の主要機能とモジュールを実装しました。

Added
- パッケージ基盤
  - kabusys パッケージの公開 API を定義（__version__ = "0.1.0", __all__ に data / strategy / execution / monitoring を含む）。
- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を起点に探索）。
  - .env パーサ（export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの取り扱い等に対応）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数の保護（protected set）を実装。
  - 自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ対応（テスト用など）。
  - Settings クラスを提供し、必要な環境変数の取得とバリデーション（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN 等）、パスの Path 変換、KABUSYS_ENV / LOG_LEVEL の検証を実装。
- 研究（research）モジュール群
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率(ma200_dev) の計算（DuckDB のウィンドウ関数を利用）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高変化率(volume_ratio) の計算。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（price と結合）。
    - 実装は prices_daily / raw_financials テーブルのみを参照し、欠損やデータ不足時に None を返す堅牢な設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得する SQL 実装。
    - calc_ic: スピアマン順位相関（IC）を計算する実装（ties は平均順位で処理）。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を計算。
    - rank: 同順位の平均ランクを返すランク付けユーティリティ。
  - research パッケージの公開 API をエクスポート。
  - 実装方針として外部ライブラリ（pandas 等）に依存しない純粋 Python + DuckDB 実装。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features(conn, target_date): research のファクターを取得・マージしてユニバースフィルタを適用、指定カラムを Z スコア正規化（zscore_normalize を利用）し ±3 でクリップ、その日の features テーブルを日付単位で置換（トランザクション＋バルク挿入）する冪等処理を実装。
  - ユニバースフィルタ: 最低株価（300 円）・20 日平均売買代金（5 億円）でフィルタ。
  - ルックアヘッドバイアス回避のため target_date 時点のデータのみ使用する設計。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals(conn, target_date, threshold=0.60, weights=None): features と ai_scores を読み込み、各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算して final_score を算出、閾値超過で BUY、保有ポジションに対するエグジット条件で SELL を作成し signals テーブルへ日付単位で置換する実装。
  - コンポーネントスコア計算:
    - momentum: momentum_20 / momentum_60 / ma200_dev をシグモイド変換して平均化。
    - value: PER に対する 1/(1 + per/20) 型の変換（PER が有効でない場合は None）。
    - volatility: atr_pct の Z スコアを反転してシグモイド変換。
    - liquidity: volume_ratio をシグモイド変換。
    - news: ai_score をシグモイド変換（未登録の場合は中立補完）。
  - Bear レジーム判定: ai_scores の regime_score 平均が負であれば Bear と判定し BUY を抑制（サンプル数閾値あり）。
  - 重みの検証と正規化: ユーザー指定 weights のバリデーション、フォールバック、合計が 1.0 でない場合の再スケール処理。
  - SELL 処理の優先（SELL が BUY を排除）、ストップロス（-8%）とスコア低下によるエグジットを実装（トレーリングストップ・長期時間決済は未実装）。
  - DB 書き込みはトランザクションで原子性を確保し、ROLLBACK 障害時は警告を出力。
- バックテストフレームワーク (kabusys.backtest)
  - simulator:
    - PortfolioSimulator: メモリ内ポートフォリオ管理・擬似約定処理。BUY/SELL の約定ロジック（スリッページ、手数料、全量クローズの仕様）、平均取得単価管理、mark_to_market（終値による評価と DailySnapshot 記録）を実装。
    - TradeRecord / DailySnapshot の dataclass 定義。
  - metrics:
    - calc_metrics と BacktestMetrics: CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio、総トレード数を計算する実装。
  - engine:
    - run_backtest(conn, start_date, end_date, ...): 本番 DuckDB から日付範囲でデータをインメモリ DB にコピーしてバックテストを実行するワークフローを実装。日次ループで (1) 前日シグナルを当日始値で約定、(2) positions を DB に書き戻し、(3) 終値で評価してスナップショットを記録、(4) generate_signals を呼び出して翌日シグナル生成、(5) 発注量決定 といった流れを提供。
    - _build_backtest_conn: 必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を期間フィルタ付きでコピーする機能。
    - DB コピー処理はエラー時にログ警告を出してスキップする堅牢化。
  - 公開 API として run_backtest / BacktestResult / DailySnapshot / TradeRecord / BacktestMetrics をエクスポート。
- 一般的な設計方針
  - ルックアヘッドバイアス防止（target_date ベースの計算）。
  - DuckDB を中心とした SQL ベースのデータ処理と Python ロジックの組合せ。
  - 外部データベースや発注 API への直接アクセスを行わない（execution 層への依存を排除）。
  - 主要な DB 書き込みはトランザクション＋バルク挿入で原子性を確保。
  - ログ出力と警告を多用して欠損データや予期しない条件を通知。

Known limitations / Notes
- execution モジュール（src/kabusys/execution）は空のパッケージとして置かれており、実際の発注 API 統合（kabu ステーション等）は未実装。
- monitoring モジュールは本リリースのソース一覧には実装が見当たりません（将来追加予定）。
- 一部のエグジット条件（トレーリングストップ、保有日数による時間決済）は未実装（signal_generator 内に注記あり）。
- research 関連は pandas 等に依存しない実装のため、非常に軽量だが高度な統計処理や可視化は別途ツールを想定。
- features / signals / positions 等は DuckDB のスキーマを前提とする。テーブル定義は kabusys.data.schema に依存。
- AI スコア周り（ai_scores テーブル）は外部での生成を想定。未登録の場合は中立（0.5）で補完される。
- 単体テストおよび統合テストの記述は本コードベース内に含まれていないため、運用前に環境・データでの検証を推奨。

Security
- 既知のセキュリティ脆弱性の修正は本リリース時点ではありません。

Credits
- 本プロジェクト初期実装（0.1.0）。README / ドキュメントや使用例は別途提供予定。

--- 
この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートに反映する際は追加の説明（互換性、移行手順、環境変数例など）を追記してください。