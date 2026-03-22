# Changelog

すべての変更は Keep a Changelog の形式に従います。  
安定化・仕様追記・バグ修正はセクション別に記載しています。

なお、この CHANGELOG は与えられたコードベース（初期リリース相当）から推測して作成しています。

## [Unreleased]

- （現時点なし）

## [0.1.0] - 2026-03-22

初回公開リリース。日本株自動売買システム「KabuSys」のコア機能を提供します。
主にデータ前処理（research → features）、シグナル生成、バックテスト、ポートフォリオシミュレータ、
環境設定周りのユーティリティを実装しています。

### Added

- パッケージ基礎
  - src/kabusys/__init__.py
    - パッケージ名・バージョン定義（__version__ = "0.1.0"）。
    - パブリックモジュール群を __all__ に定義（"data", "strategy", "execution", "monitoring"）。

- 設定/環境変数管理
  - src/kabusys/config.py
    - .env/.env.local をプロジェクトルート（.git または pyproject.toml）から自動読み込みする機能を実装。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサは以下の特徴を持つ:
      - export KEY=val 形式に対応
      - シングル・ダブルクォートされた値のバックスラッシュエスケープを考慮した解析
      - クォートなし値のインラインコメント（#）処理（直前が空白/タブの場合のみコメント扱い）
      - 読み込み時の上書き制御（.env は既存環境に上書きせず、.env.local は上書き）
      - OS 環境変数を保護する機能
    - Settings クラスを提供し、アプリで使う主要設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, データベースパス等）を property ベースで取得可能。
    - KABUSYS_ENV と LOG_LEVEL の値検証（許容値以外は ValueError を送出）。

- 研究/ファクター計算
  - src/kabusys/research/factor_research.py
    - モメンタムファクター（mom_1m, mom_3m, mom_6m, ma200_dev）を計算する calc_momentum() を実装。
      - 200日移動平均の計算はウィンドウ内の行数チェックを行い、データ不足時は None を返す。
    - ボラティリティ／流動性ファクター（atr_20, atr_pct, avg_turnover, volume_ratio）を計算する calc_volatility() を実装。
      - true range の NULL 伝播を適切に扱う設計。
    - バリューファクター（per, roe）を計算する calc_value() を実装。
      - raw_financials の target_date 以前の最新レコード取得ロジックを実装。
  - src/kabusys/research/feature_exploration.py
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=[1,5,21]) を実装（LEAD を使った一括取得）。
    - スピアマンの IC（calc_ic）実装（ランク付け、ties は平均ランクで処理）。
    - ファクターの統計サマリー（factor_summary）と rank ユーティリティを実装。
    - pandas 等の外部依存なしで標準ライブラリ + DuckDB を想定した実装。
  - research パッケージの __all__ に主要関数をエクスポート。

- 特徴量エンジニアリング（features テーブル生成）
  - src/kabusys/strategy/feature_engineering.py
    - build_features(conn, target_date)
      - research モジュールの calc_momentum / calc_volatility / calc_value を呼び出し生ファクターを取得。
      - 株価・流動性によるユニバースフィルタ（最低株価 _MIN_PRICE = 300 円、20日平均売買代金 _MIN_TURNOVER = 5億円）を適用。
      - 数値ファクターの Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）と ±3 でクリップ（外れ値抑制）。
      - features テーブルに対して日付単位で DELETE→INSERT を行うことで冪等的に書き込み（トランザクションを使用）。
      - 当日欠損や休場日対応のため target_date 以前の最新価格参照ロジックを備える。

- シグナル生成
  - src/kabusys/strategy/signal_generator.py
    - generate_signals(conn, target_date, threshold=0.60, weights=None)
      - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを算出。
      - コンポーネントはシグモイド変換等で [0,1] に正規化。
      - weights の入力検証とデフォルト値による補完、合計再スケーリングを実装（不正値は無視）。
      - Bear レジーム検知: ai_scores の regime_score の平均が負なら BUY を抑制（サンプル数閾値あり）。
      - BUY は threshold（デフォルト 0.60）を超える銘柄を採用、SELL はストップロス（-8%）／スコア低下で判定。
      - 欠損コンポーネントは中立値 0.5 で補完して不当な降格を防止。
      - signals テーブルへ日付単位の置換（トランザクション＋バルク挿入）。
      - SELL 優先ポリシー（SELL 対象は BUY から除外）。

- バックテストフレームワーク
  - src/kabusys/backtest/simulator.py
    - PortfolioSimulator クラスを実装:
      - 初期現金、positions、cost_basis、履歴（DailySnapshot）と約定履歴（TradeRecord）を保持。
      - execute_orders(): SELL を先に処理、BUY は資金に応じて株数を切り捨てで計算、BUY の場合は手数料を考慮して再計算。
      - SELL は保有全量をクローズ（部分利確／部分損切りは未対応）。
      - mark_to_market(): 終値で時価評価、終値欠損時は 0 と評価してログ出力。
  - src/kabusys/backtest/metrics.py
    - calc_metrics(history, trades) および個別の内部指標計算関数（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio）を実装。
    - 売却の realized_pnl を用いた指標算出。
  - src/kabusys/backtest/engine.py
    - run_backtest(conn, start_date, end_date, ...) を実装:
      - 本番 DB からインメモリ DuckDB へ必要テーブルをフィルタコピーする _build_backtest_conn()（signals/positions を汚さないため）。
      - 日次ループ: 前日シグナルを始値で約定 → positions を書き戻し → 終値で時価評価 → generate_signals で翌日シグナル生成 → 発注リストを組成して次日へ。
      - 取引日に必要な始値/終値の取得ユーティリティ (_fetch_open_prices / _fetch_close_prices) を提供。
      - positions の書き戻し（_write_positions）を実装し generate_signals の SELL 判定と連携。
    - バックテスト結果を BacktestResult(history, trades, metrics) として返却。

- パッケージ公開 API
  - strategy.__init__.py に build_features, generate_signals をエクスポート。
  - backtest.__init__.py で run_backtest / BacktestResult / DailySnapshot / TradeRecord / BacktestMetrics をエクスポート。
  - research.__init__.py で主要研究用関数をエクスポート。

### Changed

- （初版のため、過去の変更は無し）

### Fixed

- （初版のため、修正履歴は無し）

### Removed

- （初版のため、削除は無し）

### Security

- 環境変数からトークン等を取得する設計になっており、.env/.env.local の自動読み込み挙動はプロジェクトルート検出と保護セットにより OS 環境変数を上書きしないよう配慮されています。
- シークレット管理の運用（.env の除外・権限管理）はユーザ側で注意が必要です（.env.example の利用を推奨）。

### Known limitations / TODO（実装上の注意点）

- signal_generator のエグジット条件の一部（トレーリングストップ、時間決済）は未実装。これらは positions テーブルに peak_price / entry_date 等を入手可能にする必要があります（コード内に注記あり）。
- execution 層（発注 API 連携）はこのリポジトリ内で直接依存していない（戦略層は発注 API に依存しない設計）。実運用では execution 層の実装が別途必要です。
- features テーブルに avg_turnover は保存されない設計（ユニバースフィルタ専用に一時利用）。
- バックテストは DuckDB を用いる設計のため、特定の環境では DuckDB のバージョン差異に注意が必要。
- 一部のユーティリティ（kabusys.data.stats.zscore_normalize や data/schema 等）は外部ファイルに依存する（今回のコードベースで参照はあるが実装ファイルは提示されていない可能性があるため、実行環境での整備が必要）。

---

（以上）