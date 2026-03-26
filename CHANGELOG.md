CHANGELOG
=========

すべての重要な変更点を Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) 準拠の形式で記載します。

現バージョン
------------
- バージョン: 0.1.0
- 日付: 2026-03-26

[0.1.0] - 2026-03-26
--------------------

Added
-----
- パッケージ初期リリース。日本株自動売買システムのコア機能を提供するモジュール群を追加。
- 環境設定読み込み:
  - .env / .env.local の自動読み込み機能を実装（優先度: OS 環境変数 > .env.local > .env）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート（テスト用途）。
  - export KEY=val 形式やクォート・エスケープ、行内コメントの取り扱いに対応するパーサ実装。
  - OS 環境変数を保護する protected オプションを採用し、.env 読み込み時の上書きを制御。
- Settings クラス:
  - 必須環境変数の取得ヘルパー（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
  - デフォルト値: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH。
  - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の値検証（不正値は ValueError）。
  - is_live / is_paper / is_dev ヘルパーを追加。
- ポートフォリオ構築 (kabusys.portfolio):
  - 候補選定: select_candidates（スコア降順、タイブレークに signal_rank を使用）。
  - 重み計算: calc_equal_weights（等金額）、calc_score_weights（スコア加重、全スコアが 0 の場合は等金額にフォールバックして WARNING を出力）。
  - セクター集中リスク: apply_sector_cap（既存ポジションのセクター別時価を算出し、指定比率を超えるセクターの新規候補を除外。unknown セクターは適用除外）。
  - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に対応。未知のレジームは 1.0 でフォールバックし WARNING を出力）。
  - ポジションサイズ決定: calc_position_sizes
    - allocation_method に "risk_based", "equal", "score" をサポート。
    - risk_based: 許容リスク率（risk_pct）と損切り率（stop_loss_pct）に基づく株数算出。
    - equal/score: weight ベースの割付、per-position & aggregate 上限、単元株（lot_size）で丸め。
    - cost_buffer を用いた約定コスト（スリッページ・手数料）保守見積りと aggregate scale-down、および残差の lot 単位での再配分ロジック。
    - portfolio_value × max_position_pct による 1 銘柄上限を適用。
- 特徴量エンジニアリング (kabusys.strategy.feature_engineering):
  - research モジュールから得た生ファクターをマージし、ユニバースフィルタ（株価 >= 300 円、20 日平均売買代金 >= 5 億円）を適用。
  - 指定列を Z スコア正規化し ±3 でクリップ、features テーブルへ冪等的に（target_date 単位で置換）書き込み。
  - DuckDB を用いるデータ処理実装。
- シグナル生成 (kabusys.strategy.signal_generator):
  - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
  - final_score の加重合算（デフォルト重み: momentum 0.40, value 0.20, volatility 0.15, liquidity 0.15, news 0.10）。重みは外部から上書き可能で、合計が 1 に正規化される。
  - AI スコア未登録は中立（0.5）で補完。AI レジームスコアの平均が負かつサンプル数が十分な場合は Bear レジームと判定し BUY 抑制。
  - BUY 判定閾値デフォルト 0.60。SELL 判定はストップロス（-8%）およびスコア低下を実装。
  - signals テーブルへの日付単位置換（トランザクションで原子性を保証）。
- リサーチ機能 (kabusys.research):
  - ファクター計算: calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials を参照し、必要な窓計算を SQL で実行）。
  - 特徴量探索: calc_forward_returns（複数ホライズンの将来リターンを一括取得）、calc_ic（Spearman ランク相関）、factor_summary（基本統計量）と rank ユーティリティ。
  - 外部依存を持たず標準ライブラリ + DuckDB で完結する実装。
- バックテスト (kabusys.backtest):
  - metrics: バックテスト指標を計算するユーティリティ（CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、総トレード数）。
  - simulator: PortfolioSimulator（擬似約定・ポートフォリオ状態管理）
    - TradeRecord / DailySnapshot のデータモデル。
    - 約定モデル: SELL を先に全量クローズ、その後 BUY を処理。スリッページと手数料を適用（BUY はスリッページを加算、SELL は減算する符号ルールを採用）。
    - lot_size を引数に取り、部分約定の単元を指定可能（日本株では 100 を利用想定）。
    - history / trades を内部に保持し metrics 計算に利用可能。

Changed
-------
- 初回リリースにつき変更履歴はなし（新規導入）。

Fixed
-----
- 初回リリースにつき修正履歴はなし。

Deprecated
----------
- 現時点で非推奨 API はなし。

Removed
-------
- 現時点で削除された機能はなし。

Security
--------
- 現時点でセキュリティに関する特別な注記はなし。

注意点・既知の制限 / TODO
------------------------
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過少見積りになり、ブロックが外れる可能性がある旨を注記。将来的には前日終値や取得原価でフォールバックする拡張を検討中。
- sell シグナル（_generate_sell_signals）:
  - トレーリングストップや時間決済（保有 60 営業日超）等の一部ルールは未実装（positions テーブルに peak_price / entry_date 等が必要）。
- position_sizing:
  - lot_size は現状全銘柄共通の想定（デフォルト 100）。将来的に銘柄ごとの lot_map を受け取る拡張を検討中。
- signal_generator:
  - features が空の場合は BUY なしで SELL 判定のみを行う設計。欠損銘柄の final_score 扱いは SELL 判定用に 0.0 と見なす箇所がある（ログ出力あり）。
- config の .env パーサは POSIX シェル互換の一部に対応するが、すべての corner case を網羅しているわけではない。
- DuckDB クエリは target_date を基準としたルックアヘッドバイアス防止設計（target_date 以前のデータのみ使用）。
- 一部の入力検証やロギング（WARNING / DEBUG / INFO）が実装されているため、実運用前にログレベルや環境変数の適切な設定を推奨。

開発メモ
--------
- パッケージバージョンは kabusys.__version__ = "0.1.0" に設定。
- パッケージ公開後は CHANGELOG に Unreleased セクションを追加し、今後の変更を追記してください。