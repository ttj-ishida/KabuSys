CHANGELOG
=========
すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージエントリポイントを公開
    - src/kabusys/__init__.py: バージョン情報と公開サブパッケージ定義（data, strategy, execution, monitoring）。

- 環境変数 / 設定管理
  - src/kabusys/config.py
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml を基準）から自動読み込みする機能を実装。
    - .env パーサを実装（コメント行、export プレフィックス、クォート文字・バックスラッシュエスケープ、インラインコメント処理に対応）。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - OS 環境変数を保護する protected 上書きポリシーを導入（.env.local は override=true だが既存 OS 環境変数は上書きしない）。
    - Settings クラスを実装し、必須キーの検証（_require）や既定値、enum 検証（KABUSYS_ENV / LOG_LEVEL）を提供。
    - データベースパス（DUCKDB_PATH / SQLITE_PATH）や各種 API トークン（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / SLACK_*）の取得アクセサを追加。

- 戦略（feature engineering / signal generation）
  - src/kabusys/strategy/feature_engineering.py
    - research で算出した raw ファクターを統合して features テーブルへ UPSERT する build_features を追加。
    - ユニバースフィルタ（最低株価、20日平均売買代金）を実装。
    - Zスコア正規化、±3 でのクリップによる外れ値処理を実装。
    - DuckDB トランザクション＋バルク挿入で日付単位の置換（冪等性・原子性）を確保。
    - 欠損値・非有限値の扱いを明確化。

  - src/kabusys/strategy/signal_generator.py
    - features と ai_scores を統合し final_score を算出して BUY/SELL シグナルを生成する generate_signals を実装。
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）の計算ロジックを実装（シグモイド変換、PER 取り扱い、欠損補完は中立 0.5）。
    - ファクター重みのマージ・検証・正規化ロジックを実装（無効な重みはログ出力して無視、合計が 1.0 でなければ再スケール）。
    - Bear レジーム判定（AI レジームスコアの平均が負かつ十分なサンプル数）による BUY 抑制を実装。
    - 保有ポジションに対するエグジット判定（ストップロス -8% / final_score が閾値未満）を実装。
    - signals テーブルへの日付単位置換（トランザクション）で冪等性を担保。
    - 異常・欠損時はログで警告（価格欠損時の SELL 判定スキップ、features に存在しない保有銘柄は score=0 とみなす等）。

- リサーチ用ユーティリティ
  - src/kabusys/research/factor_research.py
    - calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照して各種ファクター（mom_1m/3m/6m、ma200_dev、atr_20/atr_pct、avg_turnover、volume_ratio、per, roe）を算出。
    - ウィンドウ不足時の None 返却、営業日数バッファを考慮したスキャン範囲設計。
  - src/kabusys/research/feature_exploration.py
    - calc_forward_returns: 指定日の終値から複数ホライズン（デフォルト 1,5,21 営業日）への将来リターンを一括取得するクエリを実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装（有効サンプルが 3 未満なら None）。
    - rank / factor_summary: 同順位の平均ランク処理、各ファクターの count/mean/std/min/max/median を計算するユーティリティを追加。
    - 外部依存を避け、標準ライブラリ + DuckDB のみで実装。

- データ統計ユーティリティ
  - src/kabusys/data/stats.py への参照を各所で利用（zscore_normalize を利用する設計）。（実コードは本差分で省略されているが、インターフェースを前提に実装された設計）

- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator を実装（キャッシュ管理、保有株数・平均取得単価管理、BUY/SELL の擬似約定、スリッページ/手数料処理、日次時価評価 mark_to_market、TradeRecord/DailySnapshot を定義）。
    - BUY は資金に応じて株数を切り詰めて約定、SELL は保有全量クローズというシンプルな約定ポリシー。
    - 欠損始値・終値時にログを出し保守的にスキップまたは 0 評価。
  - src/kabusys/backtest/metrics.py
    - バックテスト評価指標計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades）を実装。
    - 入力は DailySnapshot と TradeRecord のリストのみ（DB 参照なし）。
  - src/kabusys/backtest/engine.py
    - run_backtest を実装。実 DB からインメモリ DuckDB に必要データをコピーしてバックテスト実行（signals/positions を汚さない）。
    - 日次ループ: 前日シグナルの約定 → positions を DB に書き戻し → 終値で時価評価 → generate_signals 呼び出し → シグナル読み取り → ポジションサイジング → 次日約定予定作成のフローを実装。
    - _build_backtest_conn: date 範囲でのテーブルコピー、安全にコピーが失敗したテーブルは警告ログでスキップ。
    - _write_positions/_read_day_signals/_fetch_open_prices/_fetch_close_prices などの補助関数を実装。
    - デフォルトの手数料・スリッページ・最大ポジション割合をパラメータ化。

Changed
- （初回リリースにつき該当なし）

Fixed
- （初回リリースにつき該当なし）

Deprecated
- （初回リリースにつき該当なし）

Removed
- （初回リリースにつき該当なし）

Security
- 環境変数自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）で、テストや CI 環境での誤った設定読み込みを防止できる。

Notes / Limitations / Known issues
- features / signals / positions などの DB スキーマは本リリースのコードに依存する。初期化関数（data.schema.init_schema 等）を利用してスキーマを作成する必要あり。
- 一部のユースケース（トレーリングストップや時間決済、部分利確）は未実装（signal_generator のコメント参照）。
- AI スコア（ai_scores）が不足する場合の扱いは中立補完（0.5）としている。AI スコアの正規化や学習済みモデルの運用は本リリース外。
- zscore_normalize 実装は data.stats 側に依存。実動作にはその実装が必要。
- バックテストのデータコピーはメモリに依存するため大規模データ時にメモリ消費に注意。

-----

今後の予定（例）
- ポジション管理の強化（部分利確、トレーリングストップ、保持期間制限）
- リアルタイム実行層（execution）と監視（monitoring）の実装拡充
- AI スコア統合の改良と学習パイプラインの追加
- テストカバレッジの拡大と CI ワークフローの整備

（必要があれば、リリース日・変更点の追加・細分化を行います。）