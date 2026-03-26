# Keep a Changelog
すべての注目すべき変更点をバージョン別に記録します。  
このファイルは Keep a Changelog の形式に準拠します。  

現在のバージョン: 0.1.0

## [Unreleased]
（現時点の開発中の変更はここへ記載します）

## [0.1.0] - 2026-03-26
初回公開リリース。日本株自動売買システムのコアモジュールをまとめて実装しました。

### 追加
- パッケージ全体
  - kabusys パッケージを導入。__version__ を 0.1.0 に設定。
  - パッケージ公開用の public API を __all__ で整理（data, strategy, execution, monitoring 等を想定）。
- 設定管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定を読み込む Settings クラスを実装。
  - 自動 .env ロード機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロードを無効化可能。
  - .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメント処理）。
  - 環境変数必須チェック用の _require ユーティリティと各種プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* 等）。
  - env 値・LOG_LEVEL の検証（許容値チェック）とヘルパー is_live / is_paper / is_dev を実装。
- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定・配分ロジック（純粋関数）を提供:
    - select_candidates: スコア降順で候補を選択し上位 N を返す。
    - calc_equal_weights: 等金額配分を返す。
    - calc_score_weights: スコア比率に基づく配分。全スコアが 0 の場合は等配分にフォールバック（警告ログ）。
  - リスク調整:
    - apply_sector_cap: セクター集中上限チェック。現在保有のセクター比率が上限を超えている場合、新規候補を除外（unknown セクターは無視）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームはフォールバック）。
  - ポジションサイズ計算:
    - calc_position_sizes: risk_based / equal / score の各割当方式をサポート。単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash）でスケール調整、cost_buffer による保守的見積りを実装。
    - aggregate スケーリング後に端数調整を行い lot_size 単位で再配分するアルゴリズムを実装。
- 戦略（strategy）
  - 特徴量エンジニアリング (feature_engineering.build_features):
    - research モジュールから生ファクターを取得し、ユニバースフィルタ（最低株価・売買代金）適用、Z スコア正規化（±3 クリップ）、features テーブルへの日付単位 UPSERT（トランザクション）を実装。
    - DuckDB を用いたデータ取得処理を実装。
  - シグナル生成 (signal_generator.generate_signals):
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）および final_score を算出。
    - Bear レジーム検出時は BUY シグナルを抑制するロジックを実装。
    - BUY/SELL の生成ルール（閾値、ストップロス、score 低下）を実装し、signals テーブルへ日付単位の置換（トランザクション）を行う。
    - weights の入力検証（不正値スキップ・合計リスケール）を実装。
    - SELL 対象を優先して BUY から除外するポリシーを実装。
- Research
  - ファクター算出モジュール (research.factor_research):
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev 計算（窓・データ不足時は None）。
    - calc_volatility: ATR、相対 ATR (atr_pct)、20日平均売買代金、volume_ratio の計算。
    - calc_value: PER / ROE の算出（raw_financials の最新レコードと prices_daily を組み合わせる）。
  - 探索ユーティリティ (research.feature_exploration):
    - calc_forward_returns: 指定ホライズンに対する将来リターン（複数ホライズン同時取得）。
    - calc_ic: スピアマンのランク相関（IC）計算（レコード結合・サンプル不足時は None）。
    - factor_summary, rank: 基本統計量・ランク付けユーティリティ。
  - zscore_normalize を data.stats から再エクスポートするインターフェースを用意。
- バックテスト (kabusys.backtest)
  - ポートフォリオシミュレータ (simulator.PortfolioSimulator):
    - 仮想約定（SELL 先行、その後 BUY）、スリッページ・手数料考慮、TradeRecord / DailySnapshot のデータ構造を提供。
    - BUY/SELL の処理フロー、単元処理（lot_size）を実装（部分利確非対応などの設計注記あり）。
  - メトリクス計算 (metrics.calc_metrics):
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティを実装。
- 例外処理・ログ
  - 各種処理でのログ出力（info/debug/warning）を整備、トランザクション失敗時の ROLLBACK 試行と警告ログを実装。
  - データ欠損時のスキップやフォールバック（例: features に存在しない保有銘柄は score=0 と見なす等）を明示。

### 変更
- （初回リリースのため該当なし）

### 修正
- .env 読み込みの堅牢化:
  - 存在しないファイルの扱い、ファイル読み取り失敗時の警告発行、既存環境変数の保護機構（protected set）などを実装。
- signal_generator と feature_engineering のトランザクション処理で COMMIT/ROLLBACK の安全な実行を実装。

### 既知の制限 / TODO
- position_sizing.calc_position_sizes:
  - 銘柄別単元株情報（lot_map）未実装。現状は全銘柄共通 lot_size を使用。
- risk_adjustment.apply_sector_cap:
  - price_map に価格が欠損（0.0）ある場合、エクスポージャーが過小評価される可能性がある（将来的に前日終値や取得原価でのフォールバックを検討）。
- signal_generator._generate_sell_signals:
  - トレーリングストップや時間決済（保有 60 営業日超）などは未実装（positions テーブルに peak_price / entry_date が必要）。
- PortfolioSimulator:
  - SELL は全量クローズのみ。部分利確/部分損切りは非対応。
- 一部の箇所で外部データ不在時に WARN を出して判定をスキップする設計になっているため、本番運用時はデータ完全性の担保が必要。
- research モジュールは外部ライブラリ（pandas 等）に依存しない実装だが、データ量が大きい場合のパフォーマンス改善余地あり。

### セキュリティ
- 機密情報（API トークン等）は環境変数から取得する設計。.env 自動ロード時に既存 OS 環境変数は上書きされないよう保護しています。

---

（注）上記はコードベースから推測して作成した CHANGELOG です。実際のリリースノートとして公開する際は、リリース担当者による確認・追記（導入手順、互換性、マイグレーション手順、リスク評価など）を推奨します。