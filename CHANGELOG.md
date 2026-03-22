# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
リリース日や機能説明はソースコード（src/ 以下）から推測して作成しています。

## [0.1.0] - 2026-03-22

初回リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。
主要なモジュール群（設定管理、ファクター計算・特徴量エンジニアリング、シグナル生成、リサーチ、バックテストフレームワーク、ポートフォリオシミュレータ、評価指標）を含みます。

### Added
- コアパッケージ
  - パッケージメタ情報: kabusys.__version__ = 0.1.0、公開 API の __all__ を定義。

- 設定管理 (kabusys.config)
  - 環境変数/.env 読み込み機能を実装
    - プロジェクトルート（.git または pyproject.toml）を __file__ から探索して自動的に .env/.env.local をロード（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用途）。
    - .env パーサは export 形式、シングル/ダブルクォート、エスケープ、インラインコメントの扱いに対応。
    - OS 環境変数は protected として .env の上書きを防止（.env.local は override=True だが protected は尊重）。
  - Settings クラスを提供
    - 必須変数取得（_require による未設定時 ValueError）
    - J-Quants / kabu API / Slack / DB パス等のプロパティ（デフォルト値・型変換を含む）
    - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）
    - is_live / is_paper / is_dev の便利プロパティ

- 戦略（strategy）
  - 特徴量エンジニアリング (strategy.feature_engineering)
    - research の生ファクターを取り込み、ユニバースフィルタ（最低株価・平均売買代金）を適用
    - 指定カラムを Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）、±3 でクリップ
    - features テーブルへ日付単位で置換（BEGIN/DELETE/INSERT/COMMIT、冪等性・トランザクション保証）
    - 欠損や価格取得不能に配慮したフィルタリング
  - シグナル生成 (strategy.signal_generator)
    - features と ai_scores を統合して各銘柄のコンポーネントスコア（momentum/value/volatility/liquidity/news）を算出
    - コンポーネントはシグモイド変換／補完（欠損は中立値 0.5）を適用
    - 重み指定を受け付け、妥当性検査後に合計が 1 になるよう再スケール
    - Bear レジーム検知（ai_scores の regime_score 平均が負で一定サンプル数以上）
      - Bear 時は BUY シグナル抑制
    - BUY（閾値超）および保有ポジションに対する SELL（ストップロス・スコア低下）を生成
    - signals テーブルへ日付単位で置換（トランザクション + バルク挿入）
    - 不正な重みやデータ欠損に対するログ警告を多数実装

- Research（研究用ユーティリティ）
  - ファクター計算 (research.factor_research)
    - momentum（1M/3M/6M、MA200 乖離率）、volatility（20日 ATR・相対 ATR、20日平均売買代金、出来高比率）、value（PER, ROE）を DuckDB SQL ベースで実装
    - 営業日ベースの窓長を考慮し、スキャン範囲にカレンダーバッファを使用
    - データ不足時の None ハンドリング
  - 特徴量探索 (research.feature_exploration)
    - 将来リターン計算（複数ホライズンを同一クエリで取得）
    - IC（Spearman の ρ）計算（ランク相関、同順位は平均ランク処理）
    - ファクター統計サマリー（count/mean/std/min/max/median）
    - rank ユーティリティ（同順位平均ランク、丸めによる ties 対応）
  - research パブリックエクスポートに必要な関数群を __all__ に公開

- バックテスト（backtest）
  - ポートフォリオシミュレータ (backtest.simulator)
    - PortfolioSimulator クラス（cash, positions, cost_basis, history, trades 管理）
    - 約定ロジック：BUY は指定配分に基づき始値にスリッページ・手数料を適用して約定、SELL は保有全量を始値でクローズ
    - BUY/SELL の処理順序（SELL 優先）と資金再計算（手数料込みで株数調整）
    - mark_to_market で終値評価、価格欠損時に警告して 0 と評価
    - TradeRecord / DailySnapshot のデータ構造を定義
  - バックテストエンジン (backtest.engine)
    - run_backtest を実装：本番 DuckDB からインメモリ DuckDB へ必要データをコピーして日次ループでシミュレーション
    - データコピーはテーブル単位で日付範囲をフィルタしてインサート（prices_daily, features, ai_scores, market_regime など）
    - positions テーブルの書き戻し（generate_signals が参照するため）や signals の読み取りを含むフローを実装
    - ポジションサイジング（max_position_pct などのパラメータを受け取り分配）
  - 評価指標 (backtest.metrics)
    - CAGR, Sharpe Ratio（無リスク金利=0, 年次化標準換算252日）, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算する calc_metrics 実装
    - データ不足（スナップショットやトレード不足）時の安全なデフォルト値（0.0）処理を実装

- 内部実装・運用上の配慮
  - SQL クエリを多用し、DuckDB のウィンドウ関数や LEAD/LAG/AVG を活用してパフォーマンスと正確性を確保
  - features / signals / positions など日付単位で DELETE→INSERT による置換を行い冪等性を担保
  - 各所で例外発生時のトランザクションロールバック処理およびログ出力を実装
  - ロギング（logger）を各モジュールで使用し、情報・警告・デバッグメッセージを出力

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Removed
- （初回リリースのため該当なし）

### Known limitations / Notes
- シグナル生成の SELL 条件でコメントに挙げられている「トレーリングストップ（peak_price）」や「時間決済（保有 60 営業日超過）」は未実装。positions テーブルに peak_price / entry_date 情報が必要。
- PortfolioSimulator の SELL は「保有全量クローズ」しかサポートしておらず、部分利確・部分損切りは未対応。
- calc_value は PER/ROE を実装しているが、PBR や配当利回りは未実装。
- research.feature_exploration は標準ライブラリのみで実装されている（pandas 等には依存していない）。
- 一部の機能は kabusys.data モジュール（例: data.stats.zscore_normalize、data.schema.init_schema、data.calendar_management.get_trading_days）に依存するため、それらのモジュールの存在と互換性が前提。
- バックテストでは本番 DB からのデータコピー中に問題が発生したテーブルはログ警告を出してスキップする（堅牢性優先）。

### Migration / 環境変数
- 本バージョンを運用するために以下の環境変数が必要／利用されます（Settings により取得／検証されます）:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - 任意 / デフォルトあり: KABUSYS_ENV (development|paper_trading|live、デフォルト development), LOG_LEVEL (デフォルト INFO), KABUSYS_DISABLE_AUTO_ENV_LOAD, KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）、DUCKDB_PATH、SQLITE_PATH
- .env の自動読み込みはプロジェクトルート検出に依存するため、配布後やインストールパッケージ環境では KABUSYS_DISABLE_AUTO_ENV_LOAD を使って手動ロードに切り替えることが可能。

---

上記はソースコードに記述された仕様、ログメッセージ、コメントから推測して作成した初回リリースの CHANGELOG です。補足・修正したい点や、実装箇所ごとのより詳細な記載（例: 各関数の入出力サンプルなど）が必要であれば指示してください。