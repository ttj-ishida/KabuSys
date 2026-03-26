# Changelog

すべての注目すべき変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。

なお本 CHANGELOG は与えられたコードベースから推測して作成した初期リリース記録です。

## [Unreleased]


## [0.1.0] - 2026-03-26

### Added
- パッケージ初期リリース: kabusys（日本株自動売買システム）を公開。
  - パッケージメタ:
    - バージョン: 0.1.0（src/kabusys/__init__.py）
    - 主要サブパッケージをエクスポート: data, strategy, execution, monitoring

- 環境設定・ロード機能（src/kabusys/config.py）
  - .env ファイルおよび OS 環境変数から設定を読み込む自動ロード機能を実装。
  - プロジェクトルート判定: __file__ を起点に .git または pyproject.toml を探索してプロジェクトルートを特定。
  - .env のパースロジック:
    - 空行／コメント行、export プレフィックス、シングル／ダブルクォート（バックスラッシュエスケープ対応）、インラインコメント処理などに対応。
  - 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定のみ）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
  - Settings クラスを提供:
    - 必須設定の取得と未設定時の例外 (_require)
    - J-Quants / kabuステーション / Slack / DB パス等の設定プロパティ（デフォルト値を含む）
    - KABUSYS_ENV と LOG_LEVEL の妥当性チェック（許容値を列挙）
    - is_live/is_paper/is_dev のユーティリティプロパティ

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定・重み計算（portfolio_builder.py）
    - select_candidates: スコア降順（同点は signal_rank でタイブレーク）で上位 N を選択
    - calc_equal_weights: 等金額配分
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック + WARNING）
  - リスク調整（risk_adjustment.py）
    - apply_sector_cap: セクター集中制限（既存保有時価を考慮、売却予定銘柄を除外可能、"unknown" セクターは制限対象外）
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマップ、未知レジームはフォールバックと警告）
  - ポジションサイジング（position_sizing.py）
    - calc_position_sizes: allocation_method に応じた株数決定
      - risk_based（リスク許容率・損切り率に基づく）
      - equal / score（重みベースの配分）
    - lot_size 単位で丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）を考慮
    - cost_buffer を用いた手数料/スリッページの保守的見積りとスケーリング、残差分を lot_size 単位で配分
    - ログ出力による不備（価格欠損等）の扱い

- ストラテジー（src/kabusys/strategy/*）
  - 特徴量作成（feature_engineering.py）
    - research モジュールで計算した生ファクターを取り込み、ユニバースフィルタ（株価・流動性）を適用
    - 指定カラムを Z スコア正規化（外れ値は ±3 でクリップ）
    - DuckDB を用いて features テーブルへ日付単位の置換（冪等）で書き込み
    - ルックアヘッドバイアス回避のため target_date 時点のデータのみを使用
  - シグナル生成（signal_generator.py）
    - features と ai_scores を統合し、momentum/value/volatility/liquidity/news コンポーネントで最終スコアを計算
    - コンポーネントの欠損値は中立 0.5 で補完
    - AI スコア（未登録時は中立）とレジーム判定（Bear 検知時は BUY を抑制）
    - BUY: threshold（デフォルト 0.60）を超えた銘柄にランク付けして生成（SELL 優先ポリシーあり）
    - SELL: ストップロス（-8%）およびスコア低下条件に基づくエグジット判定
    - DuckDB を使った signals テーブルへの日付単位置換（トランザクション管理）
    - weights の入力検証とデフォルト合成・正規化ロジック（不正値は警告でスキップ）

- リサーチ（src/kabusys/research/*）
  - ファクター計算（factor_research.py）
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（データ不足は None）
    - calc_volatility: ATR(20), atr_pct, 20 日平均売買代金、出来高比率
    - calc_value: raw_financials からの EPS/ROE を用いた PER/ROE 計算（最新レコードを使用）
    - DuckDB SQL を主体に実装し、外部ライブラリ（pandas 等）に依存しない設計
  - 特徴量探索（feature_exploration.py）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括取得
    - calc_ic: スピアマン（ランク）による IC 計算（有効レコードが3件未満は None）
    - factor_summary / rank: 基本統計量・ランク変換ユーティリティ

- バックテスト（src/kabusys/backtest/*）
  - PortfolioSimulator（simulator.py）
    - DailySnapshot / TradeRecord のデータモデル
    - 擬似約定ロジック（SELL を先に処理して全量クローズ、BUY は指定株数で約定）
    - スリッページ率／手数料率を反映した約定価格・手数料計算（詳細実装の継続を示唆）
  - メトリクス計算（metrics.py）
    - CAGR, Sharpe Ratio（無リスク=0）, Max Drawdown, Win Rate, Payoff Ratio, Total Trades を計算する関数群
    - 入力はメモリ内の DailySnapshot/TradeRecord のリストのみ（DB 参照なし）

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Notes / TODOs（コード中にコメントとして存在する主な今後の拡張点）
- position_sizing: 銘柄別 lot_size を扱うための拡張（stocks マスタの導入）
- risk_adjustment.apply_sector_cap: 価格欠損時のフォールバック価格（前日終値や取得原価）の検討
- signal_generator._generate_sell_signals: トレーリングストップや時間決済は positions テーブルに peak_price / entry_date が追加されれば実装予定
- DuckDB を用いる設計のため、実行前に適切なテーブルスキーマ（prices_daily, features, ai_scores, positions, signals, raw_financials 等）の準備が必要

---

これはコードベースから推測して作成した CHANGELOG です。追加の変更履歴（コミットごとの詳細、バグ修正やマイナー変更）は実リポジトリのコミットログに基づいて更新してください。