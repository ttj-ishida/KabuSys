CHANGELOG
=========

すべての重要な変更はここに記載します。  
このファイルは「Keep a Changelog」フォーマットに従っています。  

なお、このリポジトリの初期バージョンとして以下を記載します。

[0.1.0] - 2026-03-22
-------------------

Added
- パッケージ初期リリース (kabusys 0.1.0)
  - パッケージ構成:
    - kabusys.config: 環境変数 / .env 管理（自動ロード機能を備えた Settings クラス）
      - プロジェクトルート自動検出（.git または pyproject.toml を基準、CWD 非依存）。
      - .env / .env.local 読み込み（.env.local は .env 上書き、OS 環境変数は保護）。
      - .env パーサ:
        - export KEY=val 形式対応
        - シングル/ダブルクォート内のバックスラッシュエスケープ対応
        - インラインコメント扱いの判定（クォート外かつ '#' の直前が空白/タブの場合）
      - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - 必須キー未設定時は _require() が ValueError を送出する安全設計。
      - Settings が提供する主なプロパティ: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV / LOG_LEVEL 判定ユーティリティ（妥当性検査含む）。
  - strategy:
    - feature_engineering.build_features(conn, target_date)
      - research 側の生ファクター (momentum/volatility/value) を統合し、ユニバースフィルタ（最低株価、平均売買代金）を適用。
      - 指定列を Z スコア正規化し ±3 でクリップ後、features テーブルへ日付単位で UPSERT（DELETE + bulk INSERT、トランザクションで原子性確保）。
      - DuckDB を用いた SQL/Python ハイブリッド実装。
    - signal_generator.generate_signals(conn, target_date, threshold, weights)
      - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
      - final_score を重み付き合算（デフォルト重みは StrategyModel.md に準拠）。
      - Bear レジーム検出（AI レジームスコアの平均が負かつサンプル数閾値あり）時は BUY を抑制。
      - エグジット判定（ストップロス -8% / final_score の閾値割れ）、SELL は優先処理。
      - signals テーブルへ日付単位で置換（トランザクションで原子性確保）。
      - weights 入力は検証され、既知キーのみ受け付け、合計が 1 でない場合は再スケール。
  - research:
    - factor_research:
      - calc_momentum(conn, target_date): mom_1m/3m/6m、ma200_dev（200日データ不足時は None）。
      - calc_volatility(conn, target_date): ATR(20)、atr_pct、avg_turnover、volume_ratio（部分窓対応、NULL 伝播の制御）。
      - calc_value(conn, target_date): target_date 以前の最新財務データと株価から PER / ROE を計算（EPS=0 や欠損は None）。
    - feature_exploration:
      - calc_forward_returns(conn, target_date, horizons): 複数ホライズンの将来リターンを一括取得。
      - calc_ic(factor_records, forward_records, factor_col, return_col): スピアマンρ（ランク相関）を計算（有効レコード 3 件未満は None）。
      - factor_summary(records, columns): count/mean/std/min/max/median を計算。
      - rank(values): 平均ランク付け（同順位は平均ランク、round(v, 12) で ties 検出の安定化）。
    - research パッケージは外部ライブラリに依存せず、DuckDB のみで動作するよう設計。
  - backtest:
    - engine.run_backtest(conn, start_date, end_date, ...)
      - 本番 DuckDB から必要テーブルを部分コピーしてインメモリ DuckDB を構築（signals/positions を汚染しない）。
      - 日次ループでシグナルの約定（PortfolioSimulator）→ positions 書き戻し → 時価評価 → generate_signals 生成 の順に実行。
      - get_trading_days による営業日列挙に準拠したシミュレーション。
    - simulator.PortfolioSimulator
      - 擬似約定モデル（先に SELL、次に BUY）、スリッページと手数料を適用。
      - BUY は alloc/始値から約定株数を算出、手数料込みで資金不足時は再計算。
      - SELL は保有全量をクローズ（部分利確/部分損切りは未サポート）。
      - mark_to_market で DailySnapshot を記録（終値欠損時は 0 評価し WARNING）。
      - TradeRecord / DailySnapshot のデータ構造を提供。
    - metrics.calc_metrics(history, trades)
      - CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、Total Trades を計算するユーティリティ。
  - パッケージ公開 API（__all__）を整備:
    - kabusys.strategy: build_features, generate_signals
    - kabusys.research: calc_momentum, calc_volatility, calc_value, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank
    - kabusys.backtest: run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics

Changed
- （初回リリースのため「変更」はありません）

Fixed
- （初回リリースのため「修正」はありません）

Known issues / Notes / Limitations
- signal_generator/_generate_sell_signals:
  - トレーリングストップや時間決済（60 営業日超）等の一部エグジット条件は未実装。これらは positions テーブルに peak_price / entry_date を保持する拡張が必要。
- feature_engineering / research:
  - Z スコア正規化処理は kabusys.data.stats.zscore_normalize に依存（data モジュールの存在が前提）。
- バックテスト:
  - インメモリコピー時に各テーブルのスキーマ互換とデータ型変換に注意（異常があるとコピーをスキップして警告）。
- PortfolioSimulator:
  - BUY 時の割付 (alloc) は均等分配や max_position_pct に依存する実装例があるが、ポジションサイジング戦略のカスタマイズが必要な場合は上書き可能。
- 環境変数パーサ:
  - 非標準的な .env 形式（複雑な複数行クォート等）には未対応の可能性あり。基本的な .env/.env.local の形式に最適化。
- エラー処理:
  - DB トランザクション内での例外時は ROLLBACK を試みるが、ROLLBACK 自体が失敗した場合は warning ログを出力して再度例外を投げる設計。

Compatibility / Migration notes
- 0.1.0 は初回リリースのため後方互換問題はなし。今後のリリースで public API（関数名／引数／DB スキーマ等）を変更する場合は CHANGELOG に明記します。

Security
- .env 自動ロードは OS 環境変数を保護する仕組み（protected set）を取り入れており、.env による意図しない上書きを防止。
- KABUSYS_DISABLE_AUTO_ENV_LOAD によりテスト等で自動読み込みを明示的に無効化可能。

参考 / 設計ドキュメント
- 各モジュールはコード中の docstring や StrategyModel.md / BacktestFramework.md 等の設計資料を参照して実装されています（リポジトリに同梱されている想定）。

今後の予定（例）
- エグジット条件の追加（トレーリングストップ・時間決済）。
- features / ai_scores を用いた学習済みモデルの外部投入インターフェース強化。
- 部分利確 / 部分損切りをサポートする約定ロジックの追加。
- 単体テスト・統合テストの充実（特に DB コピー / トランザクション周り）。

---