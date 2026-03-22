# Changelog

すべての重要な変更は Keep a Changelog の指針に従って記載しています。  
リリースはセマンティックバージョニングに従います。

## [Unreleased]
- （なし）

## [0.1.0] - 2026-03-22

### 追加 (Added)
- パッケージ初期リリース: kabusys（日本株自動売買システム）のコアモジュールを追加。
  - バージョン情報: kabusys.__version__ = "0.1.0"

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを追加。
  - 自動ロード機能:
    - プロジェクトルートは .git または pyproject.toml を起点に探索（cwd に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用）。
    - .env 読み込み時、既存 OS 環境変数を protected として上書き防止。
  - .env パース機能を強化:
    - export KEY=VAL 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応、コメント処理（インラインコメントの特別扱い）。
  - 必須設定取得用の _require() を提供（未設定時は ValueError を送出）。
  - 設定項目（プロパティ）を提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - データベースパス: DUCKDB_PATH, SQLITE_PATH（Path 型で展開）
    - 実行環境: KABUSYS_ENV（"development" / "paper_trading" / "live" の検証）
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- 戦略: 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - research 側で算出した生ファクターを統合して features テーブルへ書き込む build_features(conn, target_date) を追加。
  - 処理内容:
    - calc_momentum / calc_volatility / calc_value を用いたファクター取得
    - ユニバースフィルタ（最低株価、20日平均売買代金）適用
    - Z スコア正規化（指定カラム）、±3 でクリップ
    - 日付単位の置換（DELETE→INSERT）による冪等な書き込みとトランザクション制御
  - トランザクション失敗時はロールバックを試行し、失敗ログを出力。

- 戦略: シグナル生成 (kabusys.strategy.signal_generator)
  - features と ai_scores を統合し、final_score を計算して BUY/SELL シグナルを生成する generate_signals(conn, target_date, threshold, weights) を追加。
  - 実装の要点:
    - コンポーネントスコア（momentum/value/volatility/liquidity/news）の計算（シグモイド変換や逆転など）
    - 欠損コンポーネントは中立値 0.5 で補完
    - 重み (weights) の妥当性チェック・フォールバック（デフォルト重みは StrategyModel に基づく）
    - Bear レジーム検知（ai_scores の regime_score 平均が負であれば BUY を抑制）
    - SELL 条件（ストップロス、スコア低下）を実装
    - signals テーブルへの日付単位の置換（冪等）を実施
    - ログ出力（情報・警告・デバッグ）

- research モジュール (kabusys.research)
  - 研究用ユーティリティを追加:
    - calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照するファクター計算）
    - calc_forward_returns(conn, target_date, horizons)（複数ホライズンの将来リターンを一クエリで取得）
    - calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman のランク相関 IC 計算）
    - factor_summary(records, columns)（基本統計量算出）
    - rank(values)（同順位を平均ランクにするランク関数）
  - 実装方針: DuckDB を主体に SQL + Python、外部ライブラリに依存しない実装。

- バックテストフレームワーク (kabusys.backtest)
  - ポートフォリオシミュレータ (PortfolioSimulator) を実装:
    - 約定ロジック（スリッページ、手数料を考慮）、BUY は割当額に基づく整数株数の発注、SELL は保有全量クローズ
    - TradeRecord / DailySnapshot のデータ構造
    - mark_to_market による日次スナップショット記録
  - metrics モジュール:
    - calc_metrics(history, trades) により BacktestMetrics（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades）を算出
    - 内部計算関数は年次化・分散・引数検証を含む
  - バックテストエンジン (run_backtest):
    - 本番 DB からインメモリ DuckDB へ必要テーブルをコピーする _build_backtest_conn を実装（signals/positions を汚さない）
    - 日次ループ: 前日シグナルを当日始値で約定、positions テーブル書き戻し、時価評価、generate_signals を用いた翌日シグナル生成、ポジションサイジングと発注の流れ
    - get_trading_days を利用して営業日ベースで実行
    - 実行結果を BacktestResult(history, trades, metrics) として返却

- データスキーマ／操作の実装方針
  - DuckDB を利用した SQL 主導の集計・ウィンドウ関数活用（LEAD/LAG/AVG OVER 等）
  - DB 書き込みは基本的に日付単位で削除→挿入による置換を採用して冪等性を保証
  - トランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を担保

### 変更 (Changed)
- 初回リリースのため、後方互換性に配慮した安全なデフォルト設定と入力検証を導入（weights の正規化、KABUSYS_ENV/LOG_LEVEL のバリデーションなど）。

### 既知の制限 / 未実装 (Notable limitations)
- シグナル生成のエグジット条件について未実装の機能が明記されています:
  - トレーリングストップ（直近最高値から -10%）や時間決済（保有 60 営業日超過）は未実装。positions テーブルに peak_price / entry_date の追加が必要。
- PortfolioSimulator の BUY は部分利確・部分損切りには未対応（SELL は保有全量をクローズする設計）。
- research モジュールは外部ライブラリ（pandas 等）に依存せず実装しているため、大規模データでの操作は手作業での最適化が必要な場合がある。
- market_calendar のコピーは例外発生時にスキップされうる（警告ログが出力される）。

### 修正 (Fixed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （該当なし）

---

注:
- ドキュメント内で参照される仕様（StrategyModel.md、BacktestFramework.md、Market/Strategy ドキュメント等）は実装方針の根拠として参照されています。実際の運用に際しては .env.example に基づく秘密情報の管理、DuckDB ファイルのバックアップ、テスト環境での KABUSYS_DISABLE_AUTO_ENV_LOAD の活用を推奨します。