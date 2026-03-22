# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

リリース日はパッケージ内の __version__ に基づきます。

## [0.1.0] - 2026-03-22

初回公開リリース。日本株の自動売買研究・バックテスト基盤となる以下の主要機能を追加しました。

### 追加 (Added)
- パッケージ基本情報
  - kabusys パッケージ初期化。__version__ = "0.1.0"、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定管理 (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テスト目的）。
  - .env ファイルの行パーサーを実装（コメント行・export プレフィックス・シングル/ダブルクォートとバックスラッシュエスケープに対応、インラインコメント処理の挙動を細かく制御）。
  - 環境変数の保護機構（OS 環境変数を protected として .env の上書きを制御）。
  - Settings クラスを提供し、必要な環境変数取得メソッドを公開:
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN / SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH / SQLITE_PATH（デフォルトパスを提供）
    - KABUSYS_ENV の検証（development, paper_trading, live のみ許可）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー属性: is_live / is_paper / is_dev

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research 側で算出した raw factor を取り込み、ユニバースフィルタ・正規化（Z スコア）・クリップ（±3）を経て features テーブルへ UPSERT（ターゲット日単位で削除→挿入し冪等性を確保）する build_features(conn, target_date) を実装。
  - ユニバースフィルタ: 株価 >= 300 円、20日平均売買代金 >= 5 億円。
  - DuckDB を利用した price の最新参照（target_date 以前の最新価格を使用し休場日欠損に対応）。
  - トランザクション（BEGIN / COMMIT / ROLLBACK）による原子性と、ROLLBACK 失敗時の警告ログ。

- シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合し、各銘柄のコンポーネントスコア（momentum / value / volatility / liquidity / news）を計算、重み付け合算して final_score を算出、BUY/SELL シグナルを生成する generate_signals(conn, target_date, threshold, weights) を実装。
  - デフォルトの重みと閾値:
    - デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10
    - デフォルト BUY 閾値: 0.60
    - ストップロス閾値: -8%（_STOP_LOSS_RATE）
  - weights 引数の検証と補完（未知キー無視、非数値/負値無視、合計が 1.0 になるよう再スケール）。
  - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数が閾値以上のとき）による BUY 抑制。
  - SELL（エグジット）判定:
    - ストップロス（最優先）
    - final_score が閾値未満
    - price 欠損時の判定スキップや features 未登録銘柄を score=0 と扱うなど堅牢性の考慮。
  - signals テーブルへの日付単位置換（トランザクション + バルク挿入で原子性確保）。

- 研究用ユーティリティ (kabusys.research)
  - calc_momentum / calc_volatility / calc_value（factor_research）を実装。prices_daily / raw_financials を参照してモメンタム・ボラティリティ・バリュー系のファクターを返す。
  - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）先までの将来リターンを一括 SQL クエリで取得。
  - calc_ic: スピアマンランク相関（IC）を計算する実装（欠損処理、サンプル数閾値 = 3）。
  - rank: 同順位は平均ランクにするランク付け（浮動小数の丸め対策 round(..., 12) を導入）。
  - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。

- バックテストフレームワーク (kabusys.backtest)
  - PortfolioSimulator: 約定ロジック・ポートフォリオ状態管理を実装（BUY/SELL の約定、平均取得単価管理、スリッページ・手数料適用、SELL は保有全量クローズ、SELL を先に処理）。
    - スリッページ/手数料の適用方法、資金不足時の株数再計算、始値欠損時の警告ロギング。
    - mark_to_market による日次スナップショット記録（終値欠損は 0 評価で警告）。
  - バックテストエンジン run_backtest(conn, start_date, end_date, ...) を実装。
    - 本番 DB からインメモリ DuckDB へ必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar 等）を期間指定でコピーする _build_backtest_conn（init_schema(":memory:") を利用）。
    - 日次ループ: 前日シグナル約定 -> positions 書き戻し -> 時価評価 -> generate_signals 実行 -> signal 読み取り -> 発注（サイジング） のフローを実装。
    - デフォルトパラメータ: initial_cash=10_000_000, slippage_rate=0.001, commission_rate=0.00055, max_position_pct=0.20
  - バックテスト用メトリクス calc_metrics を実装（CAGR, Sharpe, Max Drawdown, Win rate, Payoff ratio, total trades）。

- パブリック API のエクスポート
  - strategy.__init__ で build_features / generate_signals をエクスポート。
  - research.__init__ で主要ユーティリティをエクスポート。
  - backtest.__init__ で run_backtest / BacktestResult / DailySnapshot / TradeRecord / BacktestMetrics をエクスポート。

### 仕様上の設計上の注意・制限 (Notes / Known)
- データベース: DuckDB を前提に実装。prices_daily / features / raw_financials / ai_scores / positions / market_calendar 等のスキーマが前提。
- ルックアヘッドバイアス回避: すべて target_date 時点（またはそれ以前）のデータのみを用いる設計を原則としています。
- 未実装・保留事項（今後の拡張候補としてコード中に注記あり）:
  - トレーリングストップ（positions に peak_price / entry_date が必要）
  - 時間決済（保有 60 営業日超過など）
  - PBR / 配当利回りなどのバリューファクター拡張
- ロバストネス: 欠損データ（価格欠損、財務データ欠損）に対する多くのガードが入っています（警告ログ、判定スキップ、中立値 0.5 補完など）。
- トランザクション処理: features / signals の日付単位置換はトランザクションを使用しますが、例外発生時に ROLLBACK 処理が失敗する場合は警告ログを出します。
- research モジュールは外部ライブラリ（pandas 等）を使わずに標準ライブラリ + DuckDB の SQL で動作するよう意図されています。

### 変更 (Changed)
- 初回リリースにつき該当なし。

### 修正 (Fixed)
- 初回リリースにつき該当なし。

### 削除 (Removed)
- 初回リリースにつき該当なし。

---

今後のリリースでの改善案（例）
- execution 層の実装（kabuステーションとの連携）、monitoring（Slack 通知等）の具体的実装。
- features / signals の並列処理や性能改善（大量銘柄・長期間データでの最適化）。
- より柔軟なポジションサイジング・部分利確対応やトレーリングストップの実装。
- テスト・CI の充実、型アノテーションの強化と mypy 等の導入。

もし特定ファイルや機能についてより詳しい変更点・設計意図の記載を希望する場合は、対象を指定して指示してください。