CHANGELOG
=========

すべての重要な変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) の原則に従って記載しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-03-22
-------------------

Added
- 初回リリース: KabuSys 日本株自動売買フレームワークを追加。
  - パッケージメタ情報:
    - バージョン: 0.1.0
    - パッケージ名: kabusys
    - モジュール公開: data, strategy, execution, monitoring（execution のパッケージは存在するが実装ファイルは空の初期構成）
- 環境設定管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - 自動読み込みの探索はパッケージ自身のファイル位置を起点に .git または pyproject.toml を探索してプロジェクトルートを特定（CWDに依存しない）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - .env パーサは以下に対応:
    - 空行・コメント行（#）の無視
    - export KEY=val 形式のサポート
    - シングル/ダブルクォート内でのバックスラッシュエスケープ対応（閉じクォートまでを値として扱い以降のインラインコメントを無視）
    - クォートなしの場合、'#' の直前がスペース/タブなら以降をコメントと認識
  - .env 読み込み時に OS 環境変数を保護 (protected keys) し、override フラグによる上書き制御を実装。
  - 必須設定取得ヘルパ _require を提供（未設定時は ValueError を投げる）。
  - 設定オブジェクト Settings を提供し、J-Quants / kabu API / Slack / DB パス / 環境種別（development/paper_trading/live）/ログレベル等を取得。
  - KABUSYS_ENV と LOG_LEVEL の許容値検証を実装（不正値は ValueError）。

- 研究（research）モジュール
  - ファクター計算 (kabusys.research.factor_research):
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials から最新の財務データを取得して PER / ROE を計算。
    - SQL + DuckDB を用いた実装。prices_daily / raw_financials のみ参照（本番 API にはアクセスしない）。
  - 特徴量探索 (kabusys.research.feature_exploration):
    - calc_forward_returns: 指定日から複数ホライズン（デフォルト 1,5,21 営業日）先までのリターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマン IC（ランク相関）を計算（有効サンプル < 3 の場合は None）。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）を計算。
    - rank: 同順位は平均ランクで扱うランク関数。浮動小数点丸め対策を実装。
  - research パッケージから主要関数を再公開（__all__ を整備）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features:
    - research モジュールで計算した raw factors をマージし、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラム群を z スコア正規化（kabusys.data.stats.zscore_normalize を使用）し ±3 でクリップして外れ値の影響を抑制。
    - DuckDB の features テーブルへ日付単位で置換（DELETE + バルク INSERT）をトランザクションで行い冪等性を確保。
    - ユニバース閾値はコード内定数で管理（最低株価: 300 円、最低平均売買代金: 5 億円）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals:
    - features と ai_scores（AI ニューススコア・レジームスコア）を統合して銘柄ごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントは欠損時に中立値 0.5 で補完し、公平性を担保。
    - 最終スコア final_score は重み付き和（デフォルト重みは momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。
    - ユーザ指定 weights をマージして検証・正規化（未知キー・非数値・NaN/Inf・負値は無視、合計が 1 でなければ再スケール）。
    - BUY 閾値デフォルト 0.60（_DEFAULT_THRESHOLD）。Bear レジーム時は BUY を抑制（レジーム判定は ai_scores の regime_score 平均が負でサンプル数 >= 3 の場合）。
    - SELL（エグジット）判定:
      - ストップロス: 終値 / avg_price - 1 < -8%（最優先）
      - スコア低下: final_score が threshold 未満
      - SELL 判定は positions テーブルおよび最新価格を参照。価格欠損時は判定をスキップして警告ログ出力。
    - signals テーブルへ日付単位での置換（トランザクションで原子性を確保）。
    - ロギングと多くの防御的チェックを実装（入力データ欠損・不整合に対する挙動を明記）。

- バックテストフレームワーク (kabusys.backtest)
  - PortfolioSimulator（kabusys.backtest.simulator）:
    - メモリ内でポートフォリオ状態を管理。BUY/SELL の疑似約定ロジックを実装。
    - 約定は当日始値に対してスリッページ率と手数料率を適用。SELL は保有全量をクローズ（部分利確未対応）。
    - BUY は資金不足時に手数料込みで購入株数を再計算。
    - mark_to_market で終値評価し DailySnapshot（date, cash, positions, portfolio_value）を記録。評価価格欠損時は 0 で評価し警告。
    - TradeRecord（約定履歴）を蓄積。SELL 時に realized_pnl を算出。
  - バックテストエンジン（kabusys.backtest.engine）:
    - run_backtest: 実 DB からインメモリ DuckDB に必要データをコピーして日次ループでシミュレーションを実施。
    - _build_backtest_conn: date 範囲で prices_daily / features / ai_scores / market_regime をフィルタしてコピー、market_calendar は全件コピー。
    - 日次ルーチン:
      1. 前日シグナルを当日始値で約定（Simulator.execute_orders）
      2. positions テーブルにシミュレータの保有状態を書き戻し（generate_signals の SELL 判定に必要）
      3. 終値で時価評価・スナップショット記録
      4. generate_signals を呼びシグナル生成
      5. BUY シグナルに基づいて発注リスト（ポジションサイジング）を作成
    - デフォルト: 初期資金 10,000,000 円、スリッページ率 0.001（0.1%）、手数料率 0.00055（0.055%）、1 銘柄あたり最大 20%。
  - バックテストメトリクス（kabusys.backtest.metrics）:
    - calc_metrics で以下を計算して BacktestMetrics を返却:
      - CAGR（年平均成長率、暦日ベース）
      - Sharpe Ratio（無リスク金利=0、年次化営業日252日）
      - Max Drawdown（0〜1）
      - Win Rate（勝率）
      - Payoff Ratio（平均利益 / 平均損失）
      - total_trades（クローズされた SELL トレード数）

Changed
- なし（初回リリース）。

Fixed
- .env ファイル読み込み失敗時に警告を出力して続行するように実装（IO エラー耐性の強化）。

Removed
- なし（初回リリース）。

Security
- なし（公開コードから推測できるセキュリティ修正は特になし）。

Notes / Known limitations
- 一部のエグジット条件は未実装（コード内コメント参照）:
  - トレーリングストップ（peak_price / entry_date が positions テーブルに必要）
  - 時間決済（保有 60 営業日超過）
- execution パッケージはパブリック API に含まれているが、今回のコードベースでは発注実行層（実際のブローカー接続等）の実装は含まれていない。
- research モジュールは外部ライブラリ（pandas 等）に依存せず標準ライブラリ + DuckDB で実装しているため、大量データの操作は DuckDB に依存する想定。
- 各処理は DuckDB 接続を前提としており、DB のスキーマ（tables/columns）の存在を前提とする。実行前に init_schema 等でスキーマを準備する必要がある。

参考
- この CHANGELOG はリポジトリ内の docstring と実装内容から推測して作成しています。実際の公開リリースノートはコミット履歴やリリース管理ポリシーに基づいて調整してください。