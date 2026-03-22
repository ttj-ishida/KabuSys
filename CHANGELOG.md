CHANGELOG
=========

すべての注目すべき変更を記録します。これは Keep a Changelog の形式に準拠しています。

0.1.0 - 2026-03-22
-----------------

Added
- 初回リリースとして日本株自動売買システム「KabuSys」を追加。
- パッケージ構成（kabusys）を追加し、以下の主要サブパッケージ／モジュールを実装：
  - kabusys.config
    - .env ファイルおよび環境変数から設定を読み込む自動ロード機能（プロジェクトルートは .git または pyproject.toml を基準に検出）。
    - 独自の .env パーサ（export フォーマット、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD。
    - 必須変数チェック（_require）と Settings クラス（J-Quants / kabu API / Slack / DB パス / 環境・ログ設定）。
    - デフォルトの DB パス（DUCKDB_PATH= data/kabusys.duckdb、SQLITE_PATH= data/monitoring.db）。
  - kabusys.strategy
    - feature_engineering.build_features
      - research 側の生ファクター（momentum, volatility, value）を統合して features テーブルへ日付単位で UPSERT（トランザクション＋バルク挿入で原子性確保）。
      - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 5 億円）を実装。
      - Z スコア正規化（zscore_normalize を利用）、±3 でクリップして外れ値影響を抑制。
      - target_date 時点のデータのみを使用することでルックアヘッドを防止。
    - signal_generator.generate_signals
      - features と ai_scores を統合して最終スコア（final_score）を算出。
      - momentum/value/volatility/liquidity/news のコンポーネントスコアを計算し、デフォルト重みで加重平均。
      - AI レジームスコアに基づく Bear 検知（サンプル数閾値あり）で BUY シグナルを抑制。
      - BUY/SELL のエグジット判定（ストップロス -8% など）、SELL 優先ポリシー、signals テーブルへの日付単位置換（トランザクションで原子性）。
      - weights の入力バリデーション（未知キー・非数値・負値を無視、合計を再スケール）。
  - kabusys.research
    - factor_research（calc_momentum / calc_volatility / calc_value）
      - prices_daily / raw_financials をベースにモメンタム、ボラティリティ、バリュー系ファクターを計算。
      - 移動平均・ATR 等のウィンドウ処理は SQL ウィンドウ関数で実装。データ不足時は None を返す安全設計。
    - feature_exploration（calc_forward_returns / calc_ic / factor_summary / rank）
      - 将来リターンを一括で取得する効率的なクエリ。
      - Spearman（ランク相関）による IC 計算。サンプル不足や同順位処理を考慮。
      - ファクター列の統計サマリー出力。
    - 研究向けユーティリティを __all__ で公開。
  - kabusys.backtest
    - simulator.PortfolioSimulator
      - 擬似約定（始値ベース、スリッページと手数料を適用）、BUY は資金に応じて株数を決定、SELL は保有全量をクローズする単純モデル。
      - mark_to_market により日次スナップショットを記録。
      - TradeRecord / DailySnapshot 型を提供。
    - metrics.calc_metrics（および内部指標計算）
      - CAGR、Sharpe Ratio（無リスク金利=0）、最大ドローダウン、勝率、Payoff Ratio、取引数を計算。
    - engine.run_backtest
      - 本番 DuckDB から必要データをインメモリ DB にコピーして日次シミュレーションを実行（signals/positions を汚染しない）。
      - シミュレータと連携してシグナル約定、positions 書き戻し、評価、翌日シグナル生成を含むフルフローを実装。
      - デフォルトパラメータ（初期資金 10,000,000 円、slippage 0.1%、手数料 0.055%、max_position_pct 20%）を採用。
    - バックテスト用のデータコピーは日付範囲でフィルタして効率化。
- パッケージトップレベルで主な関数/クラスをエクスポート（kabusys.strategy.build_features, generate_signals、backtest.run_backtest 等）。
- DuckDB を中心とした SQL + Python の混在実装でパフォーマンスと透明性を両立。

Changed
- -（初回リリースのため履歴なし）

Fixed
- -（初回リリースのため履歴なし）

Removed
- -（初回リリースのため履歴なし）

Known issues / Notes
- トレーリングストップ・時間決済など一部エグジット条件は未実装（コード内に未実装コメントあり）。positions テーブルに peak_price / entry_date を追加すれば実装可能。
- AI スコアが未登録の場合は中立値（0.5）で補完される仕様。AI スコアの運用により挙動が変化します。
- generate_signals や build_features は特定の DB スキーマ（prices_daily, features, ai_scores, positions, signals, raw_financials, market_calendar など）を前提とするため、スキーマ準備が必要。
- config の自動 .env ロードはプロジェクトルート検出に依存するため、配布方法や実行環境によっては KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境を準備することを推奨。
- research モジュールは外部ライブラリ（pandas 等）に依存せず純粋な標準ライブラリ + duckdb で実装しているため、大規模データや複雑分析では追加の最適化が必要となる場合がある。

Usage highlights（簡単な利用メモ）
- 環境設定: .env に JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等を設定。
- 特徴量生成: duckdb 接続を用意し build_features(conn, target_date) を呼ぶ。
- シグナル生成: generate_signals(conn, target_date, threshold=0.6) を呼ぶと signals テーブルに書き込まれる。
- バックテスト: run_backtest(conn, start_date, end_date) を呼び結果（history, trades, metrics）を受け取る。

今後の予定（例）
- エグジット条件の追加（トレーリングストップ、時間決済）。
- ポジションサイジングの高度化（リスクベース・ボラティリティ調整等）。
- ai_scores の収集/ETL と Slack 通知の統合。