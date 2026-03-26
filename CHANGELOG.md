CHANGELOG
=========

すべての利害関係者向けの変更履歴を Keep a Changelog の形式に準拠して日本語で記載します。

注: 本リリースはパッケージ内部実装から推測して作成した初版のリリースノートです（ソースコード中の __version__ = "0.1.0" に基づく）。

[0.1.0] - 2026-03-26
--------------------

Added（追加）
- パッケージ基盤
  - kabusys パッケージ初期実装を追加。パッケージメタ情報（src/kabusys/__init__.py）でバージョンを "0.1.0" に設定し、主要サブパッケージを __all__ で公開（data, strategy, execution, monitoring）。

- 環境設定
  - 環境変数 / .env 管理モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を起点に探索）。
    - .env / .env.local の自動読み込みを実装（読み込み順: OS 環境 > .env.local > .env）。自動ロードを無効化するための環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
    - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュによるエスケープ、コメント処理の扱いなど）。
    - protected パラメータで OS 環境変数を上書きから保護する仕組みを用意。
    - Settings クラスを追加し、主要設定をプロパティとして取得可能に（J-Quants / kabuステーション / Slack / DB パス / 環境モード・ログレベル検証など）。
    - 設定値検証: KABUSYS_ENV（development / paper_trading / live のみ許容）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL のみ許容）。未設定の必須項目は ValueError を発生させる _require を提供。

- ポートフォリオ構築（portfolio）
  - 銘柄選定・重み計算モジュール（portfolio_builder）を追加。
    - select_candidates: score 降順、同点は signal_rank 昇順で上位 N を返す。
    - calc_equal_weights / calc_score_weights: 等金額配分とスコア加重配分を実装。全スコアが 0 の場合は等分配にフォールバック（warning を出力）。
  - リスク調整モジュール（risk_adjustment）を追加。
    - apply_sector_cap: セクター毎の既存エクスポージャーを計算し max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: market レジームに対する投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）。未知レジームはログを出して 1.0 にフォールバック。
  - ポジションサイジング（position_sizing）を追加。
    - allocation_method (= "risk_based" / "equal" / "score") に基づく株数算出。
    - risk_based: 許容リスク率と stop_loss_pct からベース株数を計算。
    - equal/score: 重みと max_utilization を用いた配分、per-position 上限（max_position_pct）を適用。
    - lot_size 単位で丸め（将来の銘柄別 lot_map 拡張を想定）。
    - aggregate cap：総投下金額が available_cash を超えた場合のスケーリング実装。cost_buffer（スリッページ・手数料見積り）を考慮した保守的な見積り、端数再配分アルゴリズムを実装。

- 戦略（strategy）
  - 特徴量エンジニアリング（feature_engineering）を追加。
    - research モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価300円、20日平均売買代金 5 億円）を適用。
    - 指定カラムを Z スコア正規化し ±3 でクリップ。DuckDB に対して日付単位での置換（DELETE + INSERT）をトランザクションで実行し冪等性を確保。
  - シグナル生成（signal_generator）を追加。
    - features と ai_scores を統合して各種コンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - sigmoid による 0..1 変換、欠損コンポーネントは中立 0.5 で補完。
    - 最終スコア final_score を計算し閾値超過で BUY を生成。Bear レジーム（AI の regime_score 平均が負かつサンプル数閾値以上）では BUY を抑制。
    - SELL（エグジット）判定を実装（stop_loss: -8% 以内、final_score の閾値割れ）。features に存在しない保有銘柄は score=0 と見なして SELL の対象とする（警告ログ）。
    - signals テーブルへの日付単位置換をトランザクションで実装（冪等）。

- リサーチ（research）
  - factor_research を追加（momentum / volatility / value のファクター計算）。
    - calc_momentum: 1m/3m/6m リターン、200 日 MA 乖離率（データ不足時は None）。
    - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - calc_value: raw_financials からの最新財務データ結合（PER/ROE）。
  - 特徴量評価ユーティリティ（feature_exploration）を追加。
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得。
    - calc_ic: Spearman（ランク相関）による IC 計算（同順位は平均ランク処理、サンプル不足時は None）。
    - factor_summary / rank: 基本統計量とランク変換ユーティリティを実装。
  - すべて DuckDB と標準ライブラリのみで完結する設計（pandas 非依存）。

- バックテスト（backtest）
  - ポートフォリオシミュレータ（simulator）を追加。
    - DailySnapshot / TradeRecord の dataclass 定義。
    - execute_orders: SELL を先に処理して全量クローズ、BUY を後処理。スリッページ（BUY +、SELL −）・手数料モデルを反映。lot_size を考慮した約定動作。
    - TradeRecord に realized_pnl を保持（SELL 時）。
  - メトリクス計算（metrics）を追加。
    - CAGR, Sharpe Ratio（無リスク金利=0 を仮定）, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算する API を提供。

Changed（変更）
- なし（初回リリースのため過去変更履歴無し）。

Fixed（修正）
- なし（初回リリースのため過去修正無し）。

Deprecated（非推奨）
- なし。

Removed（削除）
- なし。

Security（セキュリティ）
- .env ファイル読み込みに失敗した場合は warnings.warn を出して処理を継続（致命的失敗を避ける設計）。ただし、必須環境変数が未設定の場合は Settings._require が ValueError を投げるため、実行時に適切な環境変数管理が必要。

Notes / Limitations（備考 / 既知の制約）
- apply_sector_cap は price_map に欠損（0.0）があるとセクターエクスポージャーを過少見積もる可能性がある旨の TODO を注釈として残している（将来的に前日終値や取得原価でのフォールバックを想定）。
- position_sizing の lot_size は現状グローバル固定（将来的に銘柄別 lot_map に拡張予定）。
- signal_generator のトレーリングストップや時間決済（60 営業日超過）は未実装（positions テーブルの追加入力が必要）。
- feature_engineering と generate_signals は target_date 時点のデータのみを使用することでルックアヘッドバイアスを回避する設計だが、上流データ（prices_daily / raw_financials / ai_scores 等）が正しく整備されていることが前提。
- Backtest: SELL は現状「全量クローズ」方式で、部分利確/部分損切りには対応していない。

ログ / 例外ハンドリング
- 多くの箇所で logging モジュールを利用して情報・警告・デバッグを出力。DB トランザクションでは例外発生時に ROLLBACK を試み、失敗した場合は warning を出力してから例外を再送出する設計。

今後の検討事項（ソース内の TODO）
- position_sizing: 銘柄別 lot_size (lot_map) のサポート
- risk_adjustment: price 欠損時のフォールバック価格採用
- signal_generator: トレーリングストップ、時間決済の実装
- simulator: 部分利確/部分損切りや部分約定の挙動拡張

ライセンス・導入方法などはリポジトリの README / pyproject.toml を参照してください。