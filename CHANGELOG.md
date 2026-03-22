CHANGELOG
=========

すべての重要な変更点はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

なお、本CHANGELOGは提供されたコードベースの内容から推測して作成した初回リリース向けの要約です。

[Unreleased]
-------------

- 今後の予定 / 既知の改善点・未実装事項（参考）
  - エグジット条件: トレーリングストップや保有期間による時間決済の実装（コード内で未実装である旨のコメントあり）。
  - バリュー指標: PBR・配当利回りなどの追加計算は現バージョンでは未実装。
  - execution / monitoring パッケージの実装（パッケージは __all__ に含まれるが実装ファイルは空）。
  - AI ニューススコアやレジーム判定の学習・更新フロー（現状は ai_scores テーブル読み込みとシグモイド補完のみ）。
  - テスト用の追加ユニットテスト・統合テストの整備。

[0.1.0] - 2026-03-22
--------------------

Added
- パッケージ基盤
  - kabusys パッケージ初期バージョンを追加。バージョンは 0.1.0。
  - public API を想定したパッケージレイアウト（data, strategy, execution, monitoring を __all__ に含む）。

- 環境設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む自動ローダを実装。
    - プロジェクトルートの自動検出（.git または pyproject.toml を基準）。
    - .env と .env.local の読み込み順序（OS 環境変数を保護、.env.local は上書き可）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - .env のパース機能を実装（export プレフィックス、クォート文字列、インラインコメント処理、エスケープ対応）。
  - Settings クラスを提供し、主要設定値をプロパティで参照可能にした。
    - J-Quants / kabuAPI / Slack / DB パスなどの必須 / 既定値の管理。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値のチェック）。
    - duckdb/sqlite のパスの Path オブジェクト化。

- 研究用ファクター計算 (kabusys.research)
  - factor_research モジュール: 定量ファクターの計算を実装。
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離率（データ不足時は None）。
    - calc_volatility: 20日 ATR、ATR 比率（atr_pct）、20日平均売買代金、volume_ratio。
    - calc_value: EPS を用いた PER、ROE（raw_financials から target_date 以前の最新値）。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターン計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）計算。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）。
    - rank: 同順位を平均ランクで扱うランク付けユーティリティ。
  - すべて DuckDB 接続を受け取り prices_daily / raw_financials を参照する実装で、外部ライブラリに依存しない設計。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features を実装:
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 指定カラムを Z スコア正規化（zscore_normalize を利用）、±3 でクリップ。
    - features テーブルへ日付単位で UPSERT（DELETE + INSERT）を行い、トランザクションにより原子性を確保。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals を実装:
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントスコアを計算。
    - コンポーネント欠損値は中立値（0.5）で補完。
    - 重み（デフォルト値は StrategyModel に準拠）を受け付け、検証・正規化を行う。
    - Bear レジーム判定（ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）により BUY を抑制。
    - BUY（閾値デフォルト 0.60）/SELL（ストップロス -8% / スコア低下）を生成。
    - signals テーブルへ日付単位の置換（DELETE + INSERT）で書き込み、冪等性を確保。
    - SELL 優先ポリシー（SELL 対象は BUY から除外しランクを再付与）。

- バックテストフレームワーク (kabusys.backtest)
  - simulator モジュール:
    - PortfolioSimulator を実装。メモリ内で現金・ポジション・平均取得単価を管理。
    - 約定ロジック（execute_orders）を実装: SELL を先に処理、BUY は配分（alloc）に基づく株数計算、スリッページ・手数料の適用。
    - mark_to_market により DailySnapshot を記録。
    - TradeRecord / DailySnapshot のデータ構造を提供。
  - metrics モジュール:
    - バックテスト評価指標の計算（CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total trades）。
  - engine モジュール:
    - run_backtest を実装。実DB からバックテスト用インメモリ DuckDB へデータコピーして日次ループを実行。
    - _build_backtest_conn: 必要テーブル（prices_daily, features, ai_scores, market_regime, market_calendar）を日付フィルタ付きでコピー。
    - 日次の価格取得・positions 書き戻し・シグナル生成呼び出し・発注（ポジションサイジング）処理を統合。
    - 既存の generate_signals と統合してシミュレーションを実行。

- 共通・ユーティリティ
  - DuckDB を前提とした SQL 実装と、トランザクションを用いた原子操作による冪等性確保。
  - ロギングを各モジュールに導入し、警告やデバッグ情報を適切に出力。
  - 外部依存を極力抑えた設計（標準ライブラリ + duckdb 想定）。

Changed
- 新規初版のため該当なし。

Fixed
- 新規初版のため該当なし。

Removed
- 新規初版のため該当なし。

Security
- 新規初版のため該当なし。

Notes / Known limitations
- positions テーブルに peak_price / entry_date 等が存在しないため、トレーリングストップや保持期間ベースの時間決済は未実装（コード中に明記）。
- ai_scores が空の場合、ニューススコアは中立（0.5）に補完される。AI スコア周りの学習・更新フローは本実装外。
- execution / monitoring の実装が未完のため、本番での発注・監視は別途実装が必要。
- .env 読み込みはプロジェクトルート検出に依存する。パッケージ配布後は KABUSYS_DISABLE_AUTO_ENV_LOAD を使うか明示的に環境を設定することを推奨。
- 一部の SQL は DuckDB 固有のウィンドウ関数や ROW_NUMBER を利用しているため、他RDBMS への移植時は見直しが必要。

作者・貢献者
- 本CHANGELOG は提供されたソースコードの内容から推測して作成されています（自動生成ではなく手作業の要約）。

---