# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
書式は「Keep a Changelog」に準拠しています。

## [0.1.0] - 2026-03-22

### 追加 (Added)
- 初回リリース: KabuSys — 日本株自動売買システムの骨組みを実装。
- パッケージ初期化:
  - src/kabusys/__init__.py に __version__ = "0.1.0" と公開モジュール一覧を追加。

- 環境設定モジュール (src/kabusys/config.py):
  - .env ファイルまたは環境変数から設定を読み込む自動ローダを実装。
  - プロジェクトルート検出: __file__ を基点に .git または pyproject.toml を探索してルートを特定。
  - .env パーサ: export 構文、シングル/ダブルクォート内のエスケープ、インラインコメントの扱い、無効行スキップ等に対応する堅牢なパース処理を実装。
  - .env の読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は protected として上書き防止。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスでアプリ設定をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須チェック。
    - デフォルト値の指定 (例: KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH)。
    - KABUSYS_ENV / LOG_LEVEL の検証（許容値チェック）。
    - is_live / is_paper / is_dev の利便性プロパティ。

- 戦略: 特徴量生成 (src/kabusys/strategy/feature_engineering.py):
  - research モジュールで計算した raw factor を取り込み、ユニバースフィルタ・正規化・クリップを経て features テーブルへ日付単位でUPSERT（DELETE+INSERT をトランザクションで実施）する build_features を実装。
  - ユニバースフィルタ条件: 株価 >= 300 円、20 日平均売買代金 >= 5 億円。
  - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）、±3 でクリップ。
  - 欠損値・非有限値に対する安全な扱い（None に変換等）およびログ出力。

- 戦略: シグナル生成 (src/kabusys/strategy/signal_generator.py):
  - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し、重み付け合算で final_score を算出する generate_signals を実装。
  - デフォルト重みと閾値を採用しつつ、ユーザ提供 weights の検証・正規化（既知キーのみ、非数値や負値は無視、合計が 1.0 になるようリスケール）を実装。
  - Sigmoid による Z スコアの [0,1] 変換、欠損コンポーネントは中立 0.5 で補完。
  - Bear レジーム判定（AI の regime_score の平均が負かつサンプル数閾値以上で判定）による BUY 抑制。
  - SELL 条件（ストップロス -8%／スコア低下）を実装（保有銘柄のエグジット判定）。トレーリングストップや時間決済は未実装（注記あり）。
  - signals テーブルへの日付単位置換（トランザクション＋バルク挿入）を実装。
  - 欠損データや価格欠損時の安全措置（ログ出力・判定スキップ）を追加。

- Research モジュール (src/kabusys/research/*):
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率を SQL ウィンドウ関数で計算。データ不足時の None 処理。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に制御。
    - calc_value: raw_financials から最新の財務データを取得して PER/ROE を計算（EPS が 0/欠損のときの扱い）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（既定: 1,5,21 営業日）について将来リターンを計算する関数を実装。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。サンプル数不足時は None を返す。
    - factor_summary / rank: 基本統計量とランク付けユーティリティを実装。
  - 研究用モジュールは DuckDB と標準ライブラリのみを使用する設計（外部依存を最小限に）。

- バックテスト (src/kabusys/backtest/*):
  - simulator:
    - PortfolioSimulator 実装: BUY/SELL の擬似約定（SELL を先に処理、BUY は残資金に応じて発注）、スリッページ・手数料を適用、平均取得単価の管理、約定履歴 TradeRecord の記録、日次時価評価 DailySnapshot の記録。
    - mark_to_market は終値欠損時に警告を出し 0 評価で続行する堅牢性を実装。
  - metrics:
    - バックテスト評価指標計算（CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、総トレード数）を実装。
  - engine:
    - run_backtest の骨組みを実装。実運用 DB からインメモリ DuckDB に必要データをコピーしてバックテストを実行するワークフローを提供。
    - _build_backtest_conn: date 範囲でテーブルをコピー（prices_daily/features/ai_scores/market_regime など）し、market_calendar を全件コピー。コピー失敗は警告でスキップして堅牢に動作。
    - 日次ループ: 前日シグナルの約定、positions の書き戻し、時価評価、generate_signals の呼び出し、シグナル読み取り→サイジング→次日発注（サイジングの基本ロジックを実装する箇所を含む）。
    - トランザクションや入出力エラーに対する例外処理とログ出力を実装。

- パッケージ公開 (src/kabusys/strategy/__init__.py, src/kabusys/research/__init__.py, src/kabusys/backtest/__init__.py):
  - 主要関数・クラスを __all__ で公開。

### 変更 (Changed)
- 該当なし（初回リリース）。

### 修正 (Fixed)
- 該当なし（初回リリース）。

### 注意 / 既知の制限 (Notes / Known limitations)
- 一部機能は簡略実装／未実装のまま:
  - _generate_sell_signals 内のトレーリングストップや時間決済（保有日数に基づく決済）は未実装（コード中に明示的コメントあり）。
  - calc_value は現バージョンで PBR・配当利回りを未実装。
  - src/kabusys/execution は今バージョンでは空のパッケージ（発注実行層は未実装）。
- research モジュールは外部ライブラリ（pandas 等）に依存しない設計のため、特定の高機能な集計処理は今後改善の余地あり。
- DuckDB のスキーマ初期化関数（kabusys.data.schema.init_schema）や zscore_normalize 等、外部参照されるユーティリティはこの差分に含まれない（別モジュールで実装される前提）。
- 自動 .env 読み込みはプロジェクトルートが検出できない場合はスキップされる。テストや CI では KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することを推奨。

---

今後の予定（例）
- execution 層の実装（kabu API への実注文送信）
- ポジションサイジング詳細・リバランスロジックの拡充
- トレーリングストップ・時間決済などエグジットルールの実装
- ドキュメント・例（運用手順、設定例、DB スキーマ）を追加

（注）この CHANGELOG は提示されたコード内容から推測して作成しています。実際のリリース履歴や変更内容と異なる可能性があります。