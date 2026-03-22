# Changelog

すべての notable な変更は Keep a Changelog の慣習に従って記載します。  
このファイルはコードベースから推測した初期リリースの変更履歴です。

すべての注釈は実装ソースコードに基づいて推定しています。

## [0.1.0] - 2026-03-22

### Added
- 初回リリース。日本株自動売買システム「KabuSys」のコアモジュールを実装。
- パッケージメタ情報
  - src/kabusys/__init__.py に __version__ = "0.1.0" を設定。
  - パッケージ公開 API に data, strategy, execution, monitoring を含める（execution パッケージは空の __init__、monitoring は参照のみ）。
- 環境設定・ロード機能（src/kabusys/config.py）
  - .env/.env.local ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルートの検出は __file__ から親ディレクトリを探索し、.git または pyproject.toml を目印に判定するため、CWD に依存しない実装。
  - .env パーサは:
    - コメント行（#）や空行を無視、
    - export KEY=val 形式に対応、
    - シングル/ダブルクォートを考慮したエスケープ処理をサポート、
    - クォートなしの行では行内コメントを正しく切り離すロジックを導入。
  - .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により無効化可能。
  - Settings クラスを提供し、アプリケーション設定（J-Quants トークン、kabu API パスワード、Slack トークン/チャンネル、DB パス等）をプロパティで取得可能。環境値の妥当性チェックを実施（KABUSYS_ENV, LOG_LEVEL の列挙チェックなど）。
- 戦略（strategy）関連
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research 層で計算した生ファクターを統合・正規化して features テーブルへUPSERT（日付単位の置換）する build_features(conn, target_date) を実装。
    - ユニバースフィルタを実装（最低株価 300 円、20 日平均売買代金 5 億円）。
    - 正規化は zscore_normalize を利用し ±3 でクリップする。
    - 処理は冪等（target_date のデータを削除して挿入）でトランザクションを使用し原子性を確保。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features テーブルと ai_scores を統合して final_score を計算し、BUY/SELL シグナルを生成する generate_signals(conn, target_date, threshold, weights) を実装。
    - デフォルト重みおよび閾値: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10、BUY 閾値 0.60。
    - Z スコアはシグモイドで [0,1] に変換し、欠損コンポーネントは中立値 0.5 で補完。
    - Bear レジーム判定: ai_scores の regime_score の平均が負なら Bear（ただしサンプル数が 3 未満なら判定しない）。Bear 時は BUY を抑制。
    - SELL 条件の実装: ストップロス（終値ベースで -8% 以下）および final_score が閾値未満の場合のエグジット。positions/price 欠損時の安全対策（スキップ・警告）あり。
    - signals テーブルへの日付単位置換（トランザクション + バルク挿入）。
- Research（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - calc_momentum(conn, target_date): mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均を厳密にチェック）を SQL ウィンドウ関数で計算。
    - calc_volatility(conn, target_date): ATR（20日）、相対 ATR（atr_pct）、20日平均売買代金、volume_ratio を計算。true_range の NULL 処理を慎重に扱う。
    - calc_value(conn, target_date): raw_financials から最新財務を取得し PER（EPS が 0/NULL の場合は None）、ROE を計算。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - calc_forward_returns(conn, target_date, horizons): 翌日/翌週/翌月などの将来リターンを LEAD 関数で一括取得。horizons のバリデーションあり。
    - calc_ic(factor_records, forward_records, factor_col, return_col): Spearman の ρ をランク計算で実装（同順位は平均ランク処理）。有効レコード数 3 未満の場合は None。
    - factor_summary(records, columns): 各ファクター列の count/mean/std/min/max/median を計算。
    - rank(values): 同順位を平均ランクにするランク関数を実装（浮動小数の丸めで ties の検出を堅牢化）。
  - research パッケージの __all__ に主要関数を公開（calc_momentum 等、zscore_normalize を re-export）。
- バックテスト（src/kabusys/backtest）
  - ポートフォリオシミュレータ（src/kabusys/backtest/simulator.py）
    - PortfolioSimulator によりメモリ内で約定・状態管理を実装。BUY/SELL の約定ロジック、スリッページ・手数料計算、平均取得単価管理、全量クローズの方針を実装。
    - mark_to_market で DailySnapshot を記録。価格欠損時は 0 として評価し警告ログを出す。
  - メトリクス計算（src/kabusys/backtest/metrics.py）
    - CAGR（暦日ベース）、Sharpe（年次化、252営業日換算、無リスク金利=0）、最大ドローダウン、勝率、ペイオフレシオ、トレード数を計算するユーティリティを実装。
  - バックテストエンジン（src/kabusys/backtest/engine.py）
    - 本番 DB からインメモリ DuckDB へ必要テーブルを日付範囲でコピーする _build_backtest_conn を実装（signals/positions を汚染しない）。
    - 日次ループでの処理フローを実装:
      1. 前日シグナルの当日始値約定（simulator.execute_orders）
      2. positions テーブルへシミュレータの保有状態を書き戻し（_write_positions）
      3. 終値で時価評価しスナップショットを記録（mark_to_market）
      4. generate_signals を用いた当日シグナル生成
      5. ポジションサイジングを行い翌日の注文配分を決定
    - run_backtest API と BacktestResult の公開。
  - backtest パッケージの __all__ に主要クラス・関数を公開（run_backtest, BacktestResult 等）。

### Changed
- （初回リリースのため無し）

### Fixed
- （初回リリースのため無し）

### Deprecated
- （初回リリースのため無し）

### Security
- 環境変数の読み込みで OS 環境変数を上書きしない挙動（.env の上書き防止）をデフォルトに実装。自動ロードの無効化フラグ（KABUSYS_DISABLE_AUTO_ENV_LOAD）を提供。

### Notes / Known limitations
- execution パッケージは空の __init__ のみ（発注 API 連携等の実装は未含）。実運用の発注・取引連携は別実装が必要。
- features / signals / positions 等のテーブルスキーマは src/kabusys/data/schema 等に依存している想定（この差分には schema の具体実装は含まれていない）。
- 一部の機能は外部データ（prices_daily, raw_financials, ai_scores, market_calendar 等）を前提としているため、テスト・バックテストには該当テーブルの初期化が必要。
- SELL は現在「保有全量クローズ」のみ対応（部分利確・トレーリングストップ・時間決済等は未実装で将来的な拡張項目）。
- calc_forward_returns の範囲選択はカレンダーバッファを用いているが、極端に欠損が多いデータセットでは戻り値が None を含む可能性あり。

---

（この CHANGELOG はソースコードの実装内容をもとに作成した推測ドキュメントです。実際のリリースノートに合わせて必要に応じて修正してください。）