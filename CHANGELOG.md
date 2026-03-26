CHANGELOG
=========

すべての注目すべき変更点はこのファイルに記載します。  
フォーマットは "Keep a Changelog" に準拠します。  
リリースは SemVer に従います。

[0.1.0] - 2026-03-26
-------------------

Added
- 初回リリース。以下の主要機能・モジュールを実装・公開しました。
  - パッケージ情報
    - kabusys.__version__ = "0.1.0"
    - パッケージ公開 API を __all__ で定義（data, strategy, execution, monitoring など）。
  - 設定 / 環境変数管理 (kabusys.config)
    - .env ファイルの自動読み込み機能（プロジェクトルートを .git または pyproject.toml で探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。テスト等のため KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env パーサ実装:
      - export KEY=val 形式対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - インラインコメントの扱い（クォート外かつ '#' の直前がスペース/タブの場合にコメントと判断）
    - Settings クラス（settings インスタンス）:
      - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID の必須取得ヘルパー
      - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH のデフォルト値
      - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL のバリデーション
      - is_live / is_paper / is_dev のユーティリティプロパティ
  - ポートフォリオ構築 (kabusys.portfolio)
    - portfolio_builder:
      - select_candidates: スコア降順で候補選定（同点は signal_rank でブレーク）
      - calc_equal_weights: 等金額配分
      - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分へフォールバックし WARNING を出力）
    - position_sizing:
      - calc_position_sizes: allocation_method に応じた発注株数計算を実装
        - risk_based: リスク率・ストップロスを用いた株数計算
        - equal / score: weight に基づく株数算出
      - 単元株（lot_size）丸め、max_position_pct による per-stock 上限、aggregate cap（available_cash）によるスケールダウン、cost_buffer による保守的見積り、残差配分ロジック実装
      - 将来的な拡張用に銘柄別 lot_size への注記（TODO）
    - risk_adjustment:
      - apply_sector_cap: 既存保有のセクター集中をチェックし、上限を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）
      - calc_regime_multiplier: market regime に応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）と未知レジームのフォールバック
  - ストラテジー（特徴量作成・シグナル生成） (kabusys.strategy)
    - feature_engineering.build_features:
      - research モジュールの calc_momentum / calc_volatility / calc_value を組み合わせて features 作成
      - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）
      - 指定列の Z スコア正規化（±3 にクリップ）、DuckDB の features テーブルへ日付単位で置換（トランザクションで冪等性保証）
    - signal_generator.generate_signals:
      - features テーブルと ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
      - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完
      - デフォルト重みセット、ユーザ指定重みの検証と正規化
      - Bear レジーム検知時は BUY シグナル抑制（ai_scores の regime_score 平均で判定）
      - BUY（閾値デフォルト 0.60）および SELL（ストップロス・スコア低下）の生成、signals テーブルへ日付単位で置換（トランザクションで冪等性保証）
      - SELL 優先ポリシー（SELL 対象は BUY から除外）
  - リサーチユーティリティ (kabusys.research)
    - factor_research: calc_momentum / calc_volatility / calc_value を DuckDB ベースで実装
    - feature_exploration:
      - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターン計算（1クエリ）
      - calc_ic: スピアマンのランク相関（IC）計算
      - factor_summary: 基本統計量（count/mean/std/min/max/median）
      - rank: 同順位は平均ランク扱い（浮動小数丸めで ties 検出の安定化）
  - バックテスト (kabusys.backtest)
    - simulator:
      - DailySnapshot, TradeRecord のデータクラス
      - PortfolioSimulator: 擬似約定処理（SELL を先に処理し全量クローズ、BUY は指定株数で約定）、スリッページ・手数料モデル、履歴とトレード記録保持
    - metrics:
      - calc_metrics: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算する関数群を提供

Changed
- N/A（初回リリースのため過去変更はなし）

Fixed
- N/A（初回リリース）

Removed
- N/A

Security
- N/A

Notes / Known limitations
- apply_sector_cap: price_map に price が欠損（0.0）の場合、エクスポージャーが過小評価されブロックが回避される可能性があります。将来的に前日終値や取得原価をフォールバックに使う検討予定。
- signal_generator のトレーリングストップや時間決済（保有60営業日超など）は未実装。positions テーブルに peak_price / entry_date が必要。
- position_sizing は現状単一の lot_size（全銘柄共通）を想定。銘柄別単元対応は TODO。
- calc_score_weights は全スコアが 0 の場合に等配分へフォールバックし logger.warning を出力する仕様。
- research / strategy / execution 層は DB（DuckDB）テーブル構造や外部データ（prices_daily, raw_financials, features, ai_scores, positions, signals）に依存します。運用前にスキーマとデータ整備が必要です。
- generate_signals は ai_scores が不足する場合を考慮しているが、regime 判定には最小サンプル数を要する（_BEAR_MIN_SAMPLES = 3）。

Migration notes
- 既存の環境では .env 自動読み込みによりローカルの .env / .env.local が意図せず読み込まれる場合があります。必要に応じて KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- 設定名（環境変数）は Settings クラスのプロパティ名とは異なる場合があります（例: jquants_refresh_token → JQUANTS_REFRESH_TOKEN）。README や .env.example を参照してください。

Compatibility
- Python 3.10+ を想定（型アノテーションに Union 短縮形や型ヒントを使用）。
- DuckDB を利用する API が含まれます。DuckDB の互換性を満たす環境で動作します。

Future TODOs / Roadmap（抜粋）
- 銘柄別 lot_size のサポート（stocks マスタからの読み込み）
- apply_sector_cap の価格フォールバック実装（前日終値等）
- signal_generator にトレーリングストップ・時間決済の実装（positions テーブル拡張）
- execution 層の実装（kabuapi / 実口座連携）と監視（monitoring）モジュールの充実
- テストカバレッジの整備と CI 設定

--- 

（注）この CHANGELOG は提供されたコードベースから推測して作成しています。実際の変更履歴やリリース日付はリポジトリ運用者の記録に合わせて調整してください。