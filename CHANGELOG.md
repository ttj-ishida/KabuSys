KEEP A CHANGELOG
=================

すべての変更はセマンティックバージョニングに従います。  
このファイルは Keep a Changelog の形式に準拠しています。

Unreleased
---------

（無し）

0.1.0 - 2026-03-26
-----------------

Added
- 初回リリース（ライブラリバージョン: 0.1.0）。
- パッケージのエントリポイント:
  - kabusys.__version__ = "0.1.0"
  - パブリック API エクスポート: data, strategy, execution, monitoring（実装状況は下記参照）
- 設定・環境変数管理:
  - 自動 .env 読み込み機能を搭載（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定のみ）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能（テスト用途）。
  - .env パーサ実装: export プレフィックス、クォート文字列、エスケープ、行内コメント処理などに対応。
  - Settings クラスを提供し、以下のプロパティで型付きに環境変数へアクセス:
    - jquants_refresh_token (JQUANTS_REFRESH_TOKEN 必須)
    - kabu_api_password (KABU_API_PASSWORD 必須)
    - kabu_api_base_url (デフォルト: http://localhost:18080/kabusapi)
    - slack_bot_token / slack_channel_id (必須)
    - duckdb_path / sqlite_path（Path を返す、デフォルト値あり）
    - env / log_level / is_live / is_paper / is_dev（検証済み値、無効値は例外）
- ポートフォリオ構築（kabusys.portfolio）:
  - portfolio_builder:
    - select_candidates: スコア降順・タイブレーク（signal_rank）で候補選定
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコア 0 の場合は等金額にフォールバック）
  - position_sizing:
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") による発注株数算出
    - リスク基準、損切り率、単元丸め、per-stock 上限、aggregate cap（available_cash）考慮
    - cost_buffer を用いた保守的コスト見積りとスケールダウン（端数処理で lot 単位の再配分）
  - risk_adjustment:
    - apply_sector_cap: セクター集中度が上限を超える場合に新規候補を除外（"unknown" は除外対象外）
    - calc_regime_multiplier: market レジーム ("bull" / "neutral" / "bear") に応じた投下資金乗数（既定値: 1.0 / 0.7 / 0.3、未知レジームはフォールバック）
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）:
  - build_features(conn: DuckDB, target_date: date): research で計算した生ファクターをマージ → ユニバースフィルタ（価格・流動性） → Z スコア正規化 → ±3 でクリップ → features テーブルへ日付単位で置換（トランザクション）
  - ユニバース基準: 株価 >= 300 円、20 日平均売買代金 >= 5 億円
- シグナル生成（kabusys.strategy.signal_generator）:
  - generate_signals(conn: DuckDB, target_date: date, threshold=0.60, weights=None)
    - features と ai_scores を結合して momentum/value/volatility/liquidity/news を計算
    - コンポーネント欠損は中立 0.5 で補完、重みのバリデーションと正規化を実施
    - Bear レジーム検知時は BUY シグナルを抑制
    - BUY/SELL を分離して signals テーブルへ日付単位で置換（トランザクション）
    - 売り判定ロジック（stop_loss, score_drop）を実装
- リサーチ（kabusys.research）:
  - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を元に各ファクターを計算（純粋関数、DuckDB SQL ベース）
  - calc_forward_returns: 将来リターン（複数ホライズン）を一括取得
  - calc_ic: スピアマン ρ（ランク相関）計算
  - factor_summary: 基本統計量（count, mean, std, min, max, median）
  - rank: 同順位は平均ランクを返す実装（丸めで ties の検出精度向上）
  - zscore_normalize の再エクスポート
  - 設計思想: pandas 等に依存せず標準ライブラリ + DuckDB で完結
- バックテスト（kabusys.backtest）:
  - metrics:
    - calc_metrics/BacktestMetrics: CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades を計算
  - simulator:
    - DailySnapshot / TradeRecord dataclass
    - PortfolioSimulator: メモリ内での擬似約定・ポートフォリオ状態管理
      - execute_orders: SELL 先行 → BUY 後処理、スリッページ・手数料モデル、約定記録の保持
      - BUY は単元丸め等の取り扱いを考慮（lot_size パラメータ）
- 実装上の耐障害性:
  - DuckDB への書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で原子性を確保。ROLLBACK に失敗した場合の warning ログを出力。
  - 多くの関数で入力検証・ログ警告を備え、不正・欠損データに対して安全にフォールバックする実装。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Known notes / Limitations / TODOs
- strategy.signal_generator:
  - Trailing stop（peak_price ベース）や時間決済（保有 60 営業日超）などの追加エグジット条件は未実装。positions テーブルに peak_price / entry_date が必要。
- portfolio.risk_adjustment.apply_sector_cap:
  - price_map に価格欠損（0.0）がある場合にエクスポージャーが過少見積りされうる旨を TODO コメントで記載。将来的に前日終値や取得原価でのフォールバックを検討。
- portfolio.position_sizing:
  - 単元サイズは現状全銘柄共通の lot_size パラメータ。将来的に銘柄別 lot_map を受け取る設計へ拡張予定（TODO コメントあり）。
- execution パッケージ:
  - src/kabusys/execution/__init__.py は存在するが、外部 API 連携等の実装は含まれていない（スケルトン）。
- monitoring:
  - パッケージの __all__ に "monitoring" が含まれるが、該当モジュールはこのリリース中に未実装またはスケルトンのままの可能性あり。
- 一部のロジックはコメントや TODO を含み、将来的な機能追加・堅牢化を想定している。
- signal_generator.generate_signals は features が空の場合に BUY を生成せず SELL 判定のみ実施する挙動となる（ログ出力あり）。

Security
- （このリリースで特記すべきセキュリティ脆弱性はなし）

その他
- ライブラリは「DB 接続は外部から注入（DuckDB 接続）」という設計を採用しており、IO/外部 API のモック化・ユニットテストが容易。
- ロギングに注力しており、警告やデバッグメッセージで運用時の診断性を向上。

開発者向けヒント
- 自動 .env 読み込みを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください（テスト実行時に便利です）。
- DuckDB 接続を渡して build_features / generate_signals / research 関数を利用します。これらはトランザクションや日付単位の置換を行うため、実行前にテーブルスキーマが適切に用意されていることを確認してください。