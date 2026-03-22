# Changelog

すべての重要な変更をこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠しています。  
<https://keepachangelog.com/ja/1.0.0/>

## [Unreleased]

## [0.1.0] - 2026-03-22
初回リリース — KabuSys v0.1.0

### Added
- 基本パッケージ構成を追加
  - パッケージ名: kabusys（src/kabusys）
  - バージョン: 0.1.0（src/kabusys/__init__.py）
  - パブリック API エクスポート: data, strategy, execution, monitoring（__all__）

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルもしくは環境変数から設定を読み込む自動ロード機能を実装
    - 自動ロード順序: OS 環境変数 > .env.local > .env
    - プロジェクトルート検出: 現在ファイル位置から `.git` または `pyproject.toml` を探索（CWD 非依存）
    - 環境変数自動ロードを無効化するためのフラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - .env パーサーの強化
    - export プレフィックスをサポート（export KEY=val）
    - シングル/ダブルクォート中のエスケープを考慮して値を抽出
    - クォートなし値の行内コメント扱い（'#' の直前が空白/タブの場合）
    - 無効行のスキップや読み込み失敗時の警告
    - .env の読み込み時に既存 OS 環境変数を保護する protected モードを実装（.env.local は override=True）
  - Settings クラスを提供（settings インスタンスを公開）
    - J-Quants / kabu station / Slack / DB（duckdb/sqlite）などの設定プロパティ
    - 入力検証: KABUSYS_ENV（development/paper_trading/live）と LOG_LEVEL（DEBUG/…/CRITICAL）の値検査
    - パスのデフォルト値: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"

- 戦略: 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
  - build_features(conn, target_date) を実装
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を適用
    - 指定カラムに対し Z スコア正規化を行い ±3 でクリップ（外れ値抑制）
    - features テーブルへ日付単位での置換（DELETE → INSERT）をトランザクションで実行（冪等）
    - 価格取得は target_date 以前の最新レコードを参照（ルックアヘッド回避、休場日対応）
  - 正規化処理に kabusys.data.stats.zscore_normalize を利用

- 戦略: シグナル生成（src/kabusys/strategy/signal_generator.py）
  - generate_signals(conn, target_date, threshold=0.60, weights=None) を実装
    - features と ai_scores を統合し、コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算
    - シグモイド変換、欠損コンポーネントは中立 0.5 で補完
    - デフォルト重みと閾値を実装（重みは入力で上書き可、検証・正規化あり）
    - Bear レジーム検知（ai_scores の regime_score 平均が負かつ十分なサンプル数）により BUY を抑制
    - SELL（エグジット）判定を実装
      - ストップロス（終値 / avg_price - 1 < -8%）
      - final_score が閾値未満
      - 保有ポジションで価格欠損時は判定スキップ（安全性）
    - signals テーブルへ日付単位の置換をトランザクションで実行（BUY と SELL を挿入、SELL は signal_rank NULL）
    - SELL 優先ポリシー: SELL 対象は BUY から除外しランキングを再付与
    - ログ出力（情報/警告/デバッグ）を適切に配置

- Research（src/kabusys/research/）
  - factor_research.py
    - calc_momentum: mom_1m/mom_3m/mom_6m、200日移動平均乖離率(ma200_dev) を SQL ウィンドウで計算
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials から最新財務を取得して PER / ROE を計算（EPS=0 や欠損は None）
    - DuckDB を用いた SQL ベース実装。prices_daily / raw_financials のみ参照（外部 API 不使用）
  - feature_exploration.py
    - calc_forward_returns: 任意ホライズン（デフォルト 1,5,21 営業日）での将来リターンを計算
    - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算
    - factor_summary / rank: ファクターの統計サマリー（count, mean, std, min, max, median）と順位処理
    - pandas 等に依存せず純粋 Python 実装

- バックテストフレームワーク（src/kabusys/backtest/）
  - simulator.py
    - PortfolioSimulator クラスを実装
      - 約定ロジック（execute_orders）: SELL を先、BUY を後で処理、全量クローズのポリシー
      - スリッページ（割増・割引）と手数料モデル（commission_rate）を適用
      - 約定記録（TradeRecord）、日次スナップショット（DailySnapshot）を保持
      - mark_to_market による時価評価と履歴保存（終値欠損時は 0 評価で警告）
  - metrics.py
    - calc_metrics と各評価指標を実装（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades）
  - engine.py
    - run_backtest(conn, start_date, end_date, ...) を実装
      - 本番 DB からインメモリ DuckDB へ必要テーブルをコピー（signals/positions を汚染しない）
      - 日次ループ: 前日シグナル約定 → positions 書き戻し → mark_to_market → generate_signals（当日分）→ サイジング → 次日約定
      - 取引日の取得は market_calendar を利用（get_trading_days を使用）
      - positions の書き戻し／signals の読み取りなどのユーティリティを提供
      - コピー処理・書き込みで失敗したテーブルは警告でスキップ（堅牢化）
  - backtest パッケージの公開 API を追加（run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics）

- その他
  - pure-Python / DuckDB を中心とした実装方針（研究コードは外部ライブラリ非依存）
  - 多くのテーブル操作で「日付単位の置換（DELETE→INSERT）」を採用し、トランザクションで原子性を確保
  - ロギングを各所に導入し、異常時に警告/情報を出力するように実装

### Known limitations / Notes
- 未実装の機能（将来的な拡張ポイントとして明記）
  - トレーリングストップ（peak_price に基づく -10% など）および時間決済（保有 60 営業日超）:
    - positions テーブルに peak_price / entry_date が必要だが現時点で未実装
  - Value 側の PBR、配当利回りは未実装
  - execution パッケージは空（発注 API との接続は本リリースで実装されていない）
- 一部の挙動は設計上の選択（注意点）
  - 欠損データへの扱い: 多くの指標で None を許容し、中立値 0.5 で補完して不当な降格を防止
  - features / signals / positions への書き込みは日付単位で置換するため、同一日付での再実行は冪等
  - research レイヤは prices_daily / raw_financials のみ参照するため、外部データの事前投入が前提
- 入出力・環境依存の注意
  - .env の自動ロードはプロジェクトルートの検出に依存。配布後や特殊環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を推奨
  - LOG_LEVEL / KABUSYS_ENV の不正値は起動時に ValueError を発生させるため設定に注意

### Security
- 本リリースではセキュリティ関連の修正はありません。

---

参考: 実装内のコメントやドキュメント（StrategyModel.md / BacktestFramework.md 等）に準拠した設計を反映しています。今後のリリースでは execution 層の実装、追加の exit ルール、指標の拡張、テスト補完を予定しています。