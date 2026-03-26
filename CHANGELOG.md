# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

## [Unreleased]


## [0.1.0] - 2026-03-26

初回リリース。日本株自動売買システム「KabuSys」のコアライブラリを提供します。本バージョンは主に以下の機能群を実装しています（モジュール単位の概要と重要な挙動・制約を含む）。

### 追加 (Added)
- パッケージ基礎
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py）
  - エクスポート: data, strategy, execution, monitoring（将来的な拡張点を示唆）

- 設定・環境変数管理 (src/kabusys/config.py)
  - .env / .env.local 自動読み込み機能を提供（プロジェクトルートは .git または pyproject.toml で探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - .env パーサ:
    - export KEY=val 形式対応
    - シングル・ダブルクォートおよびバックスラッシュエスケープを考慮した解析
    - インラインコメントの取り扱い（クォート有無によりルールが異なる）
  - Settings クラス: アプリケーション設定のアクセスラッパー（J-Quants, kabu API, Slack, DB, 環境種別・ログレベル判定など）
    - 必須環境変数取得時は未設定で ValueError を送出（_require）

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を選出
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコアに比例した配分（全スコアが 0 の場合は等配分にフォールバック）
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合に新規候補を除外（"unknown" セクターは適用除外）
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知レジームは 1.0 でフォールバック）
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた発注株数計算
    - 単位株（lot_size）で丸め、max_position_pct・max_utilization の上限を考慮
    - aggregate cap（available_cash）超過時にスケールダウンし、lot 単位の端数処理で再配分
    - cost_buffer によるコスト保守見積り（スリッページ・手数料）反映

- 戦略: 特徴量とシグナル生成 (src/kabusys/strategy/)
  - feature_engineering.build_features:
    - research モジュールの raw factor 取得（momentum/volatility/value）
    - ユニバースフィルタ（最低株価、平均売買代金）
    - Z スコア正規化（指定カラム）と ±3 でクリップ
    - DuckDB 上の features テーブルへ日付単位で置換（トランザクションで原子性保証）
  - signal_generator.generate_signals:
    - features と ai_scores を統合して final_score を計算（momentum/value/volatility/liquidity/news の重み付け）
    - デフォルトの重み・閾値を実装（重みは入力で上書き可能、検証・正規化あり）
    - Bear レジーム検知時は BUY シグナルを抑制（ai_scores 中の regime_score 平均が負で且つサンプル数足りる場合）
    - エグジット判定（stop_loss / score_drop）による SELL シグナル生成
    - signals テーブルへの日付単位での置換（トランザクションで原子性）

- リサーチユーティリティ (src/kabusys/research/)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value：prices_daily / raw_financials を使った主要ファクター計算
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターン計算（複数ホライズンを一クエリで取得）
    - calc_ic: スピアマンランク相関（Information Coefficient）計算
    - factor_summary: 基本統計量集計（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクで処理するランク化ユーティリティ
  - zscore_normalize をエクスポート

- バックテスト (src/kabusys/backtest/)
  - simulator:
    - PortfolioSimulator: メモリ上での保有・現金管理、約定擬似化
    - DailySnapshot / TradeRecord データクラス
    - execute_orders: SELL を先に処理し全量クローズ、BUY は指定株数で約定。スリッページ・手数料モデルを適用
  - metrics:
    - calc_metrics: cagr, sharpe_ratio, max_drawdown, win_rate, payoff_ratio, total_trades を算出
    - 各内部算出関数を実装（営業日252日年次化等）

### 変更 (Changed)
- 初回リリースのため履歴に変更はありません。

### 修正 (Fixed)
- 初回リリースのため履歴に修正はありません。

### 注意事項 / 既知の制約 (Notes / Known limitations)
- 設定・環境
  - 必須環境変数（例）:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - デフォルトの DB パス: DUCKDB_PATH = data/kabusys.duckdb, SQLITE_PATH = data/monitoring.db
  - KABUSYS_ENV の許容値: development, paper_trading, live
  - LOG_LEVEL は DEBUG/INFO/WARNING/ERROR/CRITICAL

- DB とトランザクション
  - build_features / generate_signals は DuckDB 接続を受け取り、日付単位で DELETE → INSERT のトランザクション置換を行う（冪等）。
  - DuckDB のテーブル構成（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提とする。

- リスク制御・策略上の挙動
  - apply_sector_cap: "unknown" セクターはセクター上限の対象外（意図的）
  - calc_regime_multiplier: 未知レジームは 1.0 でフォールバック（警告ログあり）
  - generate_signals:
    - AI スコア未登録銘柄は中立扱い（news=0.5）
    - features に存在しない保有銘柄は final_score=0.0 と見なして SELL 対象になる場合がある（ログ出力あり）
    - Bear レジームの根拠は ai_scores の regime_score 平均。サンプル不足時は Bear と判定しない

- 未実装 / TODO（コード内コメント）
  - risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合に露出が過少見積りされる問題 — 将来的な価格フォールバックを検討
  - position_sizing: 銘柄別 lot_size マップへの対応は未実装（将来的な拡張を想定）
  - signal_generator の未実装エグジット条件: トレーリングストップ / 時間決済（positions テーブルに peak_price / entry_date が必要）
  - execution パッケージは空のプレースホルダ（実際の発注ロジックは別実装を想定）
  - monitoring モジュールについては参照のみ（実装は別途）

### マイグレーション / 利用時の注意
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後に想定通り動かない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定し明示的に環境を注入してください。
- DuckDB を用いた各種集計・計算はテーブルスキーマに依存します。テーブル構造・カラム名を変更する際は当該モジュール群を確認してください。
- バックテストの年次化等のパラメータ（252 営業日等）は固定値で実装されています。必要に応じて調整してください。

---

以上。今後のリリースでは execution/monitoring の実装、銘柄別単元対応、追加のエグジットロジック（トレーリング等）、およびより高度なリスク管理機能を予定しています。