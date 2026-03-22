# Changelog

すべての注目すべき変更を記録します。フォーマットは "Keep a Changelog" に準拠します。慣例により、最も新しい変更を先頭に記載します。

## [Unreleased]

- （現状なし）

## [0.1.0] - 2026-03-22

Added
- パッケージ初期リリース。
- 基本モジュールを実装:
  - kabusys.config
    - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。実行カレントディレクトリに依存せず自動 .env ロードを行う。
    - .env 自動ロード（優先順: OS 環境変数 > .env.local > .env）。環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサを実装（export KEY=val 形式、シングル／ダブルクォート、エスケープ、インラインコメントの取り扱いに対応）。
    - .env 読み込み時の保護キー機能（OS 環境変数を上書きしない protected ロジック）。
    - 必須環境変数取得用の _require を実装（未設定時は ValueError を送出）。
    - Settings クラスを実装（J-Quants / kabu API / Slack / DB パス / 環境種別 / ログレベル等）。KABUSYS_ENV と LOG_LEVEL の検証を実施。
  - strategy.feature_engineering
    - research で算出した生ファクターをマージ・ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）でフィルタリング。
    - Z スコア正規化（指定カラム）と ±3 でのクリップ処理を実装（zscore_normalize を利用）。
    - features テーブルへの日付単位置換（DELETE + bulk INSERT）で冪等性・原子性を担保（BEGIN / COMMIT / ROLLBACK 対応）。
  - strategy.signal_generator
    - features と ai_scores を統合して final_score を算出するロジックを実装（momentum/value/volatility/liquidity/news の重み付け合算）。
    - デフォルト重み・閾値を実装。ユーザ指定 weights の妥当性検証・正規化（合計が 1.0 にリスケール）を実装。
    - Sigmoid 変換、欠損コンポーネントに対する中立補完 (0.5) を採用。
    - AI の regime_score に基づく Bear 相場判定を実装（サンプル数閾値を設定して過剰判定を回避）。Bear 相場時に BUY シグナルを抑制。
    - エグジット判定（STOP_LOSS: -8%／スコア低下）を実装。positions テーブルと prices_daily 参照で SELL シグナルを生成。
    - signals テーブルへ日付単位置換で書き込み（冪等、トランザクション処理）。
  - research.factor_research
    - prices_daily/raw_financials を参照するファクター計算を実装:
      - Momentum: mom_1m/mom_3m/mom_6m、ma200_dev（200日移動平均乖離）。データ不足時は None を返す。
      - Volatility: 20日 ATR / atr_pct、20日平均売買代金（avg_turnover）、出来高比率。
      - Value: PER（EPS が 0 または欠損時は None）、ROE（最新財務データを target_date 以前から取得）。
    - ウィンドウ・スキャン範囲および NULL 伝播を考慮した設計。
  - research.feature_exploration
    - 将来リターン calc_forward_returns（任意ホライズン、horizons のバリデーション）。
    - スピアマンランク相関（IC）を計算する calc_ic（同順位の平均ランク処理、最小サンプル数チェック）。
    - factor_summary による各ファクターの基本統計量（count/mean/std/min/max/median）。
    - rank 関数での同順位処理と丸め（round(v, 12)）による ties の安定化。
  - backtest
    - simulator（PortfolioSimulator）を実装:
      - BUY/SELL の擬似約定（始値、スリッページ、手数料を考慮）。SELL は保有全量クローズ、BUY は配分（alloc）に基づき株数を計算。
      - 平均取得単価（cost_basis）の更新とトレード記録（TradeRecord）の生成。
      - mark_to_market による日次スナップショット（DailySnapshot）記録。終値欠損時は 0 評価で WARNING を出力。
    - metrics モジュールでバックテスト評価指標を実装:
      - CAGR、Sharpe（無リスク金利=0、252 営業日で年次化）、最大ドローダウン、勝率、ペイオフレシオ、総クローズトレード数。
    - engine.run_backtest を実装:
      - 本番 DB から必要テーブル（prices_daily, features, ai_scores, market_regime 等）をフィルタコピーして in-memory DuckDB を構築（_build_backtest_conn）。
      - 日次ループ: 前日シグナルを当日始値で約定 → positions テーブルへ書き戻し → 終値で時価評価 → generate_signals で翌日シグナル生成 → ポジションサイジングと発注（max_position_pct に基づく配分）。
      - run_backtest の結果として BacktestResult(history, trades, metrics) を返却。

Changed
- N/A（初回リリースのため、過去バージョンからの変更はなし）。

Fixed
- 多数のデータ欠損ケースでの安全処理を追加:
  - .env ファイル読み込み失敗時の警告出力（warnings.warn）。
  - SQL／価格欠損時にシグナル／売買判定をスキップし、ログを残す（generate_signals/_generate_sell_signals、simulator.mark_to_market 等）。
  - トランザクション失敗時に ROLLBACK を試み、失敗ログを残す（feature_engineering.generate / signal_generator.generate_signals）。
  - 重みやパラメータの不正値に対してフォールバック/スキップロジックを導入（weights の検証）。

Deprecated
- N/A

Removed
- N/A

Security
- N/A

Notes / Limitations / TODO
- 一部戦略仕様や機能は意図的に未実装・保留:
  - generate_signals のエグジット条件におけるトレーリングストップ／時間決済は未実装（positions テーブルに peak_price / entry_date が必要）。
  - calc_value で PBR・配当利回りは現バージョンでは未実装。
  - engine._build_backtest_conn はコピー時に例外が発生したテーブルをスキップする（警告ログ）。
- 実行環境:
  - Settings の一部（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_BOT_TOKEN、SLACK_CHANNEL_ID）は必須環境変数として _require によってチェックされ、未設定時は ValueError を投げます。デプロイ前に .env を準備してください。
- その他:
  - データベーススキーマや外部 data モジュール（schema, calendar_management, data.stats 等）は本リリースで前提となっているが、この CHANGELOG では実装済みファイルのみを対象に記載。
  - run_backtest 内の最終的なポジションサイジング周りは、提供コードの末尾が切れているため実装の続き（実際の割当計算と BUY シグナルの alloc 設定）が存在するはずです。実運用前に該当処理の確認を推奨。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートやリリース日、追加・修正内容はリポジトリの Git 履歴またはリリース時の記録に基づいて更新してください。