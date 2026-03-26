Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
このプロジェクトはセマンティックバージョニングに従います。

フォーマット
----------
各リリースは次のカテゴリで整理しています: Added, Changed, Fixed, Removed, Deprecated, Security。

Unreleased
----------
- （ここには次のリリースで予定している変更点を記載してください）
  - 例: 銘柄別の lot_size マップ対応、部分利確・トレーリングストップの実装、execution 層の具備化 など。

[0.1.0] - 2026-03-26
--------------------

Added
- 基本パッケージ初版を追加
  - パッケージ名: kabusys、バージョン: 0.1.0
  - 公開 API（__all__）: data, strategy, execution, monitoring（execution/monitoring の中身は順次拡張予定）
- 環境設定管理モジュールを追加（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml で探索）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能
  - _parse_env_line による export/クォート/コメントの堅牢なパース
  - 必須環境変数取得ヘルパー _require と Settings クラス（J-Quants / kabu / Slack / DB パス / ログレベル等）
  - env 値・log_level のバリデーション（development/paper_trading/live 等を検証）
- ポートフォリオ構築機能（kabusys.portfolio）
  - 銘柄選定 / 重み計算（portfolio_builder）
    - select_candidates: スコア降順 + signal_rank によるタイブレークで候補選定
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分（全スコア0の際は等配分へフォールバック）
  - リスク調整（risk_adjustment）
    - apply_sector_cap: セクター集中上限チェック（当日売却予定銘柄はエクスポージャー計算から除外、"unknown" セクターは上限不適用）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear マッピング + 未知レジームはフォールバック）
  - ポジションサイズ決定（position_sizing）
    - allocation_method に応じた発注株数計算（"risk_based" / "equal" / "score"）
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash によるスケールダウン）、cost_buffer による保守見積り
    - aggregate scale-down 時に fractional remainder に基づき lot 単位で再配分するロジック
    - TODO: 将来的に銘柄別 lot_size マップへ拡張可能な設計注記
- 戦略（strategy）モジュール
  - 特徴量エンジニアリング（feature_engineering）
    - research 側で算出した生ファクターを取り込み、ユニバースフィルタ（価格/流動性）、Zスコア正規化、±3 クリップを行い features テーブルへ UPSERT（DuckDB）
    - ユニバース最低基準: 最低株価 300 円、20 日平均売買代金 5 億円
  - シグナル生成（signal_generator）
    - features と ai_scores を統合して final_score を計算（momentum/value/volatility/liquidity/news の重み付け）
    - Bear レジーム検知時は BUY シグナルを抑制
    - BUY は閾値超過により生成、SELL はストップロス（-8%）・スコア低下で判定。SELL 優先ポリシーで BUY から除外
    - weights のバリデーション・フォールバック・再スケーリング処理を実装
    - DB 操作は日付単位の置換（DELETE → INSERT）で冪等性と原子性を担保
    - 未登録 AI スコアは中立補完、features 欠損保有銘柄は score=0 として SELL 判定を行う挙動を明記
- リサーチ（research）モジュール
  - ファクター計算（factor_research）
    - momentum: 1M/3M/6M リターン、200 日 MA 乖離（データ不足時は None）
    - volatility: 20 日 ATR / atr_pct、20 日平均売買代金、volume_ratio
    - value: raw_financials から EPS/ROE を取得し PER を算出（EPS=0 の場合は None）
    - DuckDB による SQL ベース実装で prices_daily / raw_financials を利用
  - 特徴量探索（feature_exploration）
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターン計算（営業日ベース）
    - calc_ic: スピアマンランク相関（IC）計算（有効レコードが 3 件未満なら None）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）
    - rank: 同順位は平均ランクで処理（round による安定化）
  - zscore_normalize を data.stats から再公開
- バックテスト（backtest）
  - ポートフォリオシミュレータ（simulator）
    - DailySnapshot / TradeRecord の dataclass 定義
    - execute_orders: SELL を先に処理してから BUY（SELL は保有全量クローズ、部分利確非対応）
    - スリッページ率・手数料率を考慮した約定処理の枠組み（現状の実装は基本ロジックの一部まで）
  - メトリクス計算（metrics）
    - CAGR, Sharpe (無リスク=0), Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティを追加

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Removed
- （初版のため該当なし）

Known issues / Notes
- execution パッケージは __init__.py は存在するが、発注 API への具体的な実装は今後追加予定
- monitoring モジュールは __all__ に含まれるが、具体的実装は未提供（今後追加予定）
- position_sizing の価格欠損（price が 0.0）の場合、_max_per_stock やエクスポージャー計算が過少評価になる注記あり。将来的に前日終値や取得原価をフォールバックする予定
- signal_generator の未実装/未完全な exit 条件:
  - トレーリングストップや時間決済（60 営業日超）は positions テーブルに peak_price / entry_date 等の情報が必要で現在未実装
- calc_regime_multiplier は未知レジームで 1.0 をフォールバックしログを出力
- テスト・CI による検証が推奨（特に DB クエリ / 日付依存処理 / 数値の端ケース）

作者・貢献
- 初期実装・仕様実装（機能群は PortfolioConstruction.md, StrategyModel.md, BacktestFramework.md 等の設計文書に基づくことがコメントで明記されています）

ライセンス
- リポジトリ内のライセンスファイルに従ってください（本 CHANGELOG にはライセンス情報を含めていません）。

（以降のリリースはここに日付付きで追記してください）