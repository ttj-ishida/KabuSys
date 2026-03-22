CHANGELOG
=========

すべての変更は「Keep a Changelog」フォーマットに従い、下位互換性を重視します。
リリースノートは主にコードベースから推測した機能追加・設計方針・実装上の注意点を記載しています。

2026-03-22 — 0.1.0
------------------

Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__init__ にバージョン "0.1.0" と公開 API を定義。
- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local の自動読み込みを実装。読み込み優先順位は OS 環境変数 > .env.local > .env。
  - プロジェクトルートの探索は __file__ を起点に .git または pyproject.toml を探索する方式を採用（CWD に依存しない）。
  - .env パーサ実装: export 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントルールなどに対応。
  - 自動読み込みを無効化するためのフラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供（テスト向け）。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パスなどの必須・デフォルト設定をプロパティ経由で取得。
    - 必須キー未設定時は ValueError を送出する _require 実装。
    - KABUSYS_ENV の検証（development / paper_trading / live のみ許容）。
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - duckdb/sqlite のパスに対するデフォルト値と Path 変換を実装。
- 研究用ファクター計算 (kabusys.research.factor_research)
  - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離率の計算を提供。データ不足時は None を返す設計。
  - calc_volatility: 20日 ATR / 相対 ATR (atr_pct) / 20日平均売買代金 / 出来高比率を計算。
  - calc_value: raw_financials から直近の財務データを取得して PER / ROE を計算（EPS が無効な場合は PER を None に）。
  - DuckDB 上で SQL を中心に実装。営業日ベースの窓処理とカレンダーバッファを用いたスキャン範囲最適化。
- 研究支援ユーティリティ (kabusys.research.feature_exploration)
  - calc_forward_returns: 指定日から複数ホライゾン（デフォルト [1,5,21]）の将来リターンを一括取得する実装。
  - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算する実装。サンプル不足時は None。
  - rank / factor_summary: ランク付け（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）計算。
  - 実装は外部ライブラリ非依存（標準ライブラリのみ）。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features: research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価300円、20日平均売買代金5億円）を適用。
  - 数値ファクターを Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
  - features テーブルへの日付単位 UPSERT（削除→挿入）により冪等性と原子性を確保（トランザクション利用）。
- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals: features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算して final_score を生成。
  - デフォルト重みを提供（momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）とし、ユーザ指定の weights を検証・補完・再スケール。
  - AI スコア（ai_score）をシグモイド変換してニューススコアに利用。未登録は中立（0.5）で補完。
  - Bear レジーム判定: ai_scores の regime_score の平均が負（かつサンプル数閾値を満たす）場合に BUY シグナルを抑制。
  - SELL（エグジット）判定: ストップロス（終値/avg_price - 1 <= -8%）と final_score の閾値割れを実装。保有銘柄の価格欠損時は判定をスキップ（警告ログ）。
  - signals テーブルへの日付単位置換（トランザクション）で冪等性を担保。
- バックテストフレームワーク (kabusys.backtest)
  - PortfolioSimulator: メモリ内で約定処理・ポジション管理・時価評価を行うシミュレータを実装。SELL 先行 → BUY 後処理、全量クローズポリシー、スリッページ・手数料モデルをサポート。
  - DailySnapshot / TradeRecord のデータ構造を定義。
  - run_backtest: 本番 DB からインメモリ DuckDB へ必要テーブルを日付範囲でコピーし、日次ループでシグナル生成 → 約定 → mark_to_market → positions 書込（generate_signals の SELL 判定に必要）というフローでシミュレーションを実行。
  - _build_backtest_conn: date 範囲でテーブルをフィルタしてコピー（market_calendar は全件コピー）し、本番データの汚染を防止。
  - _write_positions/_read_day_signals/_fetch_open_prices/_fetch_close_prices: バックテスト用の入出力ユーティリティを提供。
  - バックテスト実行時の資金配分 (max_position_pct) と allocation 計算ロジックを実装。
- バックテストメトリクス (kabusys.backtest.metrics)
  - CAGR / Sharpe Ratio / Max Drawdown / Win Rate / Payoff Ratio / total_trades を計算する calc_metrics と内部実装を提供。
  - 実装は歴史スナップショットと約定履歴のみを入力とする純粋関数的設計。

Changed
- なし（初回リリースにつき該当なし）

Fixed
- なし（初回リリースにつき該当なし）

Security
- 環境変数ロード時に OS 環境変数を保護するため protected key set を導入し、.env.local の上書き挙動でも OS 環境変数を保護する設計。
- 必須トークン・パスワードは Settings のプロパティで _require により明示的に検出して早期に失敗させることで誤動作を防止。

Notes / 実装上の注意
- ルックアヘッドバイアス回避:
  - research / strategy の関数は target_date 時点までのデータのみを使用する設計。
- 冪等性と原子性:
  - features / signals / positions の書き込みは「date 単位で削除→挿入」を行い、BEGIN/COMMIT/ROLLBACK でトランザクション制御している。
- ログと警告:
  - 価格欠損や異常値時には警告ログを出し、誤ったクローズや過度な降格を防ぐため一部判定をスキップまたは中立補完する実装がある。
- 外部依存の最小化:
  - 研究用ユーティリティは pandas 等に依存せず標準ライブラリ + DuckDB の SQL を中心に実装している。
- 未実装だが想定される拡張点:
  - signal_generator のエグジット条件にトレーリングストップや時間決済（保有期間制限）について記載があるが、現在は未実装（positions テーブルに peak_price / entry_date 等が必要）。

Contributing
- バグ修正・機能追加の提案は issue/PR を送ってください。環境変数の取り扱いや DB 書き込み部分は特に注意してレビューします。

License
- 明記されていないためリポジトリの LICENSE を参照してください。