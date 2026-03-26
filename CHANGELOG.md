# Changelog

すべての重要な変更は Keep a Changelog の方針に従って記載します。  
このプロジェクトはセマンティックバージョニングを採用しています。

フォーマット:
- 追加: 新機能や新規公開 API
- 変更: 既存機能の重要な変更
- 修正: バグ修正
- 注意事項: 既知の制約・未実装点や移行時の注意

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-26

Added
- 基本パッケージを初期リリース
  - パッケージ名: kabusys、バージョン 0.1.0
  - メイン公開 API: kabusys.settings（設定）、kabusys.portfolio、kabusys.strategy、kabusys.research、kabusys.backtest

- 環境設定 / ロード機能
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動で読み込む機能を実装
    - 自動読み込みはプロジェクトルート（.git または pyproject.toml を探索）を起点に行われるため、CWD に依存しない実装
    - .env.local は .env を上書き（override）する優先順位
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能
  - .env パーサは以下に対応
    - export KEY=val 形式
    - シングル/ダブルクォート内のバックスラッシュエスケープ
    - コメント（#）の扱い（クォート内は無視、クォート外は直前が空白/タブのときのみコメント視）
  - Settings クラスで主要な設定値をプロパティとして公開
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトあり）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH（デフォルト path）
    - KABUSYS_ENV（development / paper_trading / live 検証）および LOG_LEVEL 検証
    - is_live / is_paper / is_dev のフラグプロパティ

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder
    - select_candidates: BUY シグナルをスコア降順で選択（同点時は signal_rank でタイブレーク）
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコア0.0 の場合は等金額にフォールバックし WARNING を出力）
  - position_sizing
    - calc_position_sizes: allocation_method に応じた株数計算
      - risk_based（リスクベース）・equal・score に対応
      - 単元（lot_size）丸め、単銘柄上限（max_position_pct）、aggregate cap（available_cash）でスケールダウン
      - cost_buffer により手数料/スリッページを保守的に見積もる
      - スケールダウン時は残差（fractional）を lot_size 単位で再配分するロジックを実装
      - 将来的な拡張点として銘柄別 lot_size のサポートを想定（TODO を記載）
  - risk_adjustment
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター比率が閾値を超える場合は当該セクターの新規候補を除外）
      - sell_codes により当日売却予定銘柄をエクスポージャー計算から除外可能
      - "unknown" セクターは上限適用対象外（除外しない）
      - 価格欠損時の影響について注意喚起（TODO: フォールバック価格の検討）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull=1.0 / neutral=0.7 / bear=0.3、未知レジームは 1.0 にフォールバック）

- 戦略（kabusys.strategy）
  - feature_engineering
    - research モジュールの生ファクターを統合して features テーブルへ保存する処理を実装
    - ユニバースフィルタ（最低株価、最低平均売買代金）を実装
    - Z スコア正規化（kabusys.data.stats.zscore_normalize を利用）と ±3 クリップ
    - DuckDB を使った日付単位の置換（DELETE + bulk INSERT）で冪等に features を更新
  - signal_generator
    - features と ai_scores を統合して final_score を計算し BUY/SELL シグナルを生成
      - momentum / value / volatility / liquidity / news のコンポーネントを算出
      - AI スコアが未登録のときは中立（0.5）で補完
      - レジームが Bear の場合は BUY を抑制（Bear 判定は ai_scores の regime_score 平均で判定、サンプル数の下限あり）
      - SELL ルール（ストップロス、スコア低下）を実装（トレーリングストップ等は未実装）
    - weights の入力検証（未知キー・非数値の除外、合計が 1 でない場合のリスケール）
    - signals テーブルへの日付単位置換で冪等性を確保

- リサーチ（kabusys.research）
  - factor_research
    - calc_momentum / calc_volatility / calc_value を実装（prices_daily / raw_financials のみ参照）
      - momentum: 1M/3M/6M、MA200 乖離（データ不足時は None）
      - volatility: ATR20、ATR pct、20日平均売買代金、出来高比率
      - value: PER（EPS が 0/欠損なら None）、ROE（raw_financials の最新レコード参照）
  - feature_exploration
    - calc_forward_returns: 指定ホライズンの将来リターンを一括取得（SQL で LEAD を利用）
    - calc_ic: スピアマンランク相関（ランク計算は同順位を平均ランクで処理、最小サンプル数検査）
    - factor_summary: 基本統計量（count/mean/std/min/max/median）

- バックテスト（kabusys.backtest）
  - simulator
    - DailySnapshot, TradeRecord の dataclass を公開
    - PortfolioSimulator によりメモリ内での疑似約定を実装
      - SELL を先に処理（保有全量クローズ、部分利確非対応）
      - BUY は指示された株数を約定（スリッページ率・手数料率考慮）
      - history/trades を保持
      - trading_day, lot_size 等の引数を受け付ける
      - 注意: 一部のロジックは単元や部分約定に依存するため実運用時のパラメータ調整が必要
  - metrics
    - calc_metrics: CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティ

- モジュール構成とエクスポート
  - 各サブパッケージ（portfolio, strategy, research, backtest）は公開関数・クラスを __all__ で明示的にエクスポート
  - パッケージルートで主要モジュール群を import 可能

Changed
- 初期リリースのため、特別な「変更」はなし（今後のバージョンで API の安定化を予定）

Fixed
- 初期リリースのため、特別な「修正」はなし

注意事項 / 既知の制約
- 環境変数の必須チェックは Settings._require により ValueError を投げる。CI/テストでは KABUSYS_DISABLE_AUTO_ENV_LOAD の利用を推奨
- position_sizing:
  - price が欠損（None または <=0）の銘柄はスキップされる
  - lot_size は現在グローバル固定（将来的に銘柄別単元対応の拡張を想定）
- risk_adjustment.apply_sector_cap:
  - sector_map に存在しないコードは "unknown" と見なされ、セクターキャップの対象外（意図的挙動）
  - price_map が欠損の場合、エクスポージャーが過小評価される可能性あり（将来的に価格フォールバックを検討）
- strategy.signal_generator:
  - SELL の一部条件（トレーリングストップ、時間決済）は未実装（positions テーブルに peak_price や entry_date の保存が必要）
  - Bear 相場判定は ai_scores に依存。ai_scores 未登録やサンプル不足時は Bear とみなさない
- backtest.simulator:
  - SELL は全量クローズのみ。部分利確・部分損切りは未対応
- duckdb を前提とした SQL 実装になっている（features / prices_daily / raw_financials / ai_scores / positions / signals テーブルが前提）
- 研究モジュールは標準ライブラリのみで実装しており pandas 等には依存しない設計

開発上のメモ（今後の改善候補）
- .env 処理のフォールバック価格導入（前日終値や取得原価）によるエクスポージャー計算の堅牢化
- position_sizing の銘柄別 lot_size 対応
- signal_generator の追加エグジット条件（トレーリングストップ、時間決済）実装
- execution モジュール（API連携）や monitoring 周りの実装強化

署名
- 初期実装：内部開発チーム（コードコメント／モジュール実装より推測）

---  
参考: 本 CHANGELOG はソースコードの構成・コメントから推測して作成しています。実際のリリースノートにはコミット履歴や PR の要約を反映させてください。