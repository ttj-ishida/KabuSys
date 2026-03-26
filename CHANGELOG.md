# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠して記載しています。

## [0.1.0] - 2026-03-26

### 追加
- 新規パッケージ kabusys を初期リリース。
  - パッケージバージョンは __version__ = "0.1.0"。
  - 公開モジュール: data, strategy, execution, monitoring（execution は空の初期モジュール）。

- 設定・環境変数管理 (kabusys.config)
  - プロジェクトルート検出: __file__ を起点に親ディレクトリから .git または pyproject.toml を探索してプロジェクトルートを決定するユーティリティを実装。
  - .env 自動ロード機能:
    - 読み込み優先順位: OS環境変数 > .env.local > .env
    - .env/.env.local のロード時に OS 環境変数は保護（protected）され、.env.local は既存環境変数の上書きが可能。
    - 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサーの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - インラインコメントの解釈ロジック（クォートなしでは直前が空白/タブの場合に '#' をコメントとみなす）。
  - Settings クラスを提供し、主要設定値をプロパティ経由で取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は必須 (未設定時は ValueError を送出)。
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, LOG_LEVEL, KABUSYS_ENV にデフォルト値とバリデーションを実装。
    - env/log_level の有効値チェックと is_live/is_paper/is_dev のヘルパーを提供。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank によるブレーク）で上位 N 件を選択。
    - calc_equal_weights: 等金額配分の重み付け。
    - calc_score_weights: スコアに比例した重み付け。全銘柄スコアが 0 の場合は等金額配分にフォールバック（WARNING を出力）。
  - position_sizing:
    - calc_position_sizes: 配分法に応じて発注株数を計算。サポートする allocation_method:
      - "risk_based": risk_pct と stop_loss_pct に基づくロット計算（ポジション上限や単元株丸めを適用）。
      - "equal"/"score": weights を用いた資金配分。
    - aggregate cap（全銘柄合計が available_cash を超える場合のスケーリング）に対応。cost_buffer により手数料・スリッページ分の保守見積りを行い、整数 lot_size 単位で切り捨て／再配分するロジックを実装。
    - lot_size（単元株）や max_position_pct / max_utilization 等のパラメータを受け取り調整可能。
    - price 欠損や price <= 0 の銘柄はスキップする安全処理。
    - 将来的な拡張 TODO: 銘柄別 lot_map を受け取る設計を想定。
  - risk_adjustment:
    - apply_sector_cap: セクター集中制限。既存保有のセクター別時価を計算し、指定比率を超えるセクターの新規候補を除外（"unknown" セクターは制限適用除外）。
      - 当日売却予定銘柄をエクスポージャー計算から除外するオプション対応。
      - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる旨の注意コメント。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を返す。未知のレジームは 1.0 にフォールバックし警告を出力。

- 特徴量計算・戦略 (kabusys.strategy)
  - feature_engineering.build_features:
    - research モジュール（calc_momentum / calc_volatility / calc_value）から生ファクターを取得。
    - ユニバースフィルタ（最低株価・最低平均売買代金）を適用。
    - 数値ファクターを z-score 正規化（kabusys.data.stats.zscore_normalize を利用）し ±3 でクリップ。
    - features テーブルへ日付単位の UPSERT（トランザクションで置換）を行い冪等性を保証。
    - 欠損データや休場日の扱いに配慮した実装。
  - signal_generator.generate_signals:
    - features と ai_scores を結合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - final_score を重み付きで算出（デフォルト重みを提供、ユーザ指定 weights の検証と再スケーリングを実施）。
    - Bear レジーム検知時は BUY シグナルを抑制（判定は ai_scores の regime_score 平均が負かつサンプル数閾値を満たす場合）。
    - BUY シグナル閾値（デフォルト 0.60）を超える銘柄を BUY として出力。
    - SELL シグナル（エグジット）はストップロス（終値/avg_price - 1 < -8%）および final_score が閾値未満のケースを実装。SELL は BUY より優先して扱う。
    - signals テーブルへ日付単位で置換（トランザクションで原子性を保証）。
    - 欠損時の挙動: features に存在しない保有銘柄は score=0.0 と見なし SELL 判定の対象にする（警告ログあり）；価格が取得できない場合は SELL 判定処理をスキップして警告を出す。

- 研究用ユーティリティ (kabusys.research)
  - factor_research:
    - calc_momentum, calc_volatility, calc_value を実装。DuckDB を利用した SQL ベースのファクター計算（各種窓関数とウィンドウ集計を活用）。
    - 欠損データやウィンドウ不足時の None 返却など安全な設計。
  - feature_exploration:
    - calc_forward_returns: target_date から指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（有効レコードが 3 未満の場合は None）。
    - factor_summary: カラムごとの count/mean/std/min/max/median を計算する統計サマリ機能。
    - rank: 同順位は平均ランクで処理するランク化ユーティリティを提供。
  - research パッケージの __all__ で主要関数を公開。

- バックテスト (kabusys.backtest)
  - metrics.calc_metrics: DailySnapshot と TradeRecord から各種メトリクス（CAGR、Sharpe、Max Drawdown、Win Rate、Payoff Ratio、total_trades）を計算。
  - simulator.PortfolioSimulator:
    - 日次スナップショット管理、擬似約定ロジックを実装。
    - execute_orders: SELL を先に処理し全量クローズ、次に BUY を処理するフロー。スリッページ（BUY は +、SELL は -）と手数料を考慮した約定価格計算の想定（実装中）。
    - TradeRecord / DailySnapshot の dataclass を定義。
    - メモリ内での状態管理、history/trades の蓄積。
    - 注意: BUY/SELL の詳細ロジックはファイル末尾で補完される想定（ソースが途中で切れている箇所あり）。

### 変更
- なし（初回リリース）。

### 既知の制限・注意点
- .env のインラインコメントはクォート有無で振る舞いが異なる。クォートありの場合はクォート閉じまでを値として扱い、その後の # は無視される。クォート無しでは '#' の直前が空白/タブであればコメントと判定する。特殊な .env 書式を使う場合は挙動に注意。
- config はプロジェクトルートの検出に失敗した場合（.git / pyproject.toml が見つからない場合）自動環境読み込みをスキップする。
- apply_sector_cap: price_map に price が欠損（0.0）だとエクスポージャーが過少見積りされ、セクターブロックが適切に機能しない可能性がある。将来的なフォールバック価格の導入を検討中。
- calc_regime_multiplier: 未知のレジームは 1.0 にフォールバックし警告を出す。
- calc_position_sizes:
  - 現状 lot_size は全銘柄共通での処理。将来的に銘柄別単元のサポートを想定している（TODO）。
  - price <= 0 や price 欠損時は当該銘柄をスキップ。
- generate_signals:
  - AI スコア未登録の銘柄はニューススコアを中立（0.5）で補完。
  - weights に無効な値や未知のキーが含まれる場合は警告して無視し、合計が 1.0 になるよう再スケールする。
  - Bear 判定は ai_scores の regime_score を利用し、サンプル数閾値（デフォルト 3）未満では Bear とみなさない。
- バックテストシミュレータ:
  - SELL は現時点で「保有全量をクローズする」実装（部分利確や部分損切りは非対応）。
  - ソース末尾が途中で切れているため、BUY 約定の細部動作や手数料計算の最終仕様はリポジトリの続きに依存する。

### 既知の TODO / 今後の改善点
- position_sizing: 銘柄別 lot_size を受け取る設計への拡張。
- apply_sector_cap: price 欠損時のフォールバック価格（前日終値や取得原価）を用いたより堅牢なエクスポージャー算出。
- signal_generator: 現在未実装のエグジット条件（トレーリングストップ、時間決済）対応には positions テーブルに peak_price / entry_date が必要。
- simulator: 部分約定や手数料・スリッページモデルの完成、レポート出力機能の強化。

### 破壊的変更
- なし（初回リリースのため）。

### セキュリティ
- なし（初回リリース）。

---

開発に関する詳細実装意図や設計ドキュメントへの参照は各ファイルの docstring / コメントに記載しています。必要があれば CHANGELOG に更に詳細な項目（バグ修正・内部改善など）を追記します。