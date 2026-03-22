Keep a Changelog
================

すべての重要な変更はこのファイルに記録します。

フォーマット: https://keepachangelog.com/ja/1.0.0/ に準拠しています。

Unreleased
----------

（次のリリースに向けた変更はここに記載します）

[0.1.0] - 2026-03-22
-------------------

初期公開リリース。

### 追加 (Added)

- パッケージ基盤
  - パッケージメタ情報を追加（kabusys.__version__ = "0.1.0"）。トップレベルで data / strategy / execution / monitoring を公開。
- 環境設定 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml を探索して特定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート。
  - 柔軟な .env パーサ実装（export 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理）。
  - Settings クラスを提供し、以下の環境変数をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（未設定時は ValueError を送出）
    - KABUSYS_ENV（development / paper_trading / live の検証）および LOG_LEVEL（検証）
    - データベースパスのデフォルト: DUCKDB_PATH="data/kabusys.duckdb", SQLITE_PATH="data/monitoring.db"
- 戦略（feature engineering / signal）
  - feature_engineering.build_features: research モジュールで計算した生ファクターをマージし、ユニバースフィルタ（最低株価300円、20日平均売買代金5億円）を適用、指定カラムを Z スコア正規化して ±3 にクリップし、features テーブルへ日付単位で置換（トランザクション + バルク挿入で原子性を保証）。
  - signal_generator.generate_signals: features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出、重み付け合算により final_score を計算して BUY/SELL シグナルを生成。Bear レジームで BUY を抑制。SELL はストップロス（-8%）およびスコア低下で判定。signals テーブルへ日付単位で置換。
  - デフォルトの重み・閾値を実装（例: momentum 0.40, default threshold 0.60）。weights 引数は検証・正規化される（合計が 1.0 に再スケール）。
- 研究モジュール（research）
  - factor_research: calc_momentum / calc_volatility / calc_value を実装。prices_daily / raw_financials を参照して、モメンタム（1m/3m/6m、MA200乖離）、ATR・相対ATR、出来高比率、平均売買代金、PER/ROE 等を計算。
  - feature_exploration: calc_forward_returns（複数ホライズンの将来リターンを一括取得）、calc_ic（スピアマンのランク相関で IC を計算）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。外部ライブラリに依存せずに実装。
  - いずれの関数も DuckDB 接続を受け取り SQL ベースで効率的に取得。
- バックテストフレームワーク（backtest）
  - PortfolioSimulator（simulator）: BUY / SELL の擬似約定、スリッページ・手数料計算、平均取得単価の管理、mark_to_market による日次スナップショット記録、TradeRecord の収集を実装。SELL は保有全量クローズ（部分利確非対応）。
  - metrics: バックテスト評価指標を計算（CAGR、Sharpe、最大ドローダウン、勝率、Payoff Ratio、総トレード数）。
  - engine.run_backtest: 本番 DuckDB から必要テーブルをインメモリ DB にコピーして日次ループを実行する処理を実装。シグナル生成（generate_signals）との連携、positions の書き戻し、約定（前日シグナルを当日始値で約定）、ポジションサイジングのためのユーティリティ関数を提供。
  - DB 操作において、features/signals/positions 等は「日付単位の置換（DELETE+INSERT）」で冪等性と原子性を確保。
- DuckDB を中心としたデータ操作
  - 各モジュールで DuckDB クエリを直接使用し、集計、ウィンドウ関数、LEAD/LAG、移動平均等を適切に利用。
- ロギング
  - 各所で詳細なログ（debug/info/warning）を出力して問題発見を容易に。

### 変更 (Changed)

- 初版リリースのため該当なし。

### 修正 (Fixed)

- 初版リリースのため該当なし。

### 削除 (Removed)

- 初版リリースのため該当なし。

既知の制限 / 未実装事項
-----------------------

- signal_generator のエグジット条件に関して、ドキュメントにある一部の条件（トレーリングストップ、保有期間による決済）は未実装（positions テーブルに peak_price / entry_date の保存が必要）。
- feature_engineering ではユニバースフィルタに avg_turnover を使用するが、features テーブル自体には avg_turnover を保存しない（フィルタ用のみ）。
- バックテストのポジションサイジングはシンプルな実装（BUY は均等割り当て等）で、より高度なリスク管理・部分約定や複雑な手仕舞いロジックは未実装。
- 一部機能は ai_scores / market_regime / market_calendar 等のテーブルやデータ整備を前提としている。これらが存在しない場合は警告が出たり、該当処理がスキップされる。

互換性と移行メモ
-----------------

- このリリースは初期公開版です。後方互換性の破壊となる変更は将来のマイナー/メジャーリリースで明示的に記載します。

開発者向けメモ
--------------

- データベースへはトランザクション + executemany によるバルク挿入で更新を行い、日付単位での「DELETE → INSERT」により冪等性（idempotency）を確保しているため、複数回実行しても同じ状態が作られることを前提としている。
- 環境変数の必須チェックは Settings のプロパティ経由で行われるため、外部から直接 os.environ を参照しているコードは Settings に移行すると良い。
- research モジュールは外部依存を持たない設計のため、軽量に実行可能。

----- 

（以後の変更はこのファイルの Unreleased セクションに追記してください）