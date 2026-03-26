# CHANGELOG

すべての変更は Keep a Changelog の仕様に準拠して記載しています。  
リリース日はリポジトリの現時点（2026-03-26）を使用しています。

## [Unreleased]

## [0.1.0] - 2026-03-26
初回リリース。日本株向け自動売買フレームワークの基礎機能を提供します。

### 追加
- パッケージ構成
  - kabusys パッケージ初期化（__version__ = 0.1.0）。主要サブパッケージを公開（data, strategy, execution, monitoring）。

- 設定管理（kabusys.config）
  - .env/.env.local ファイルと OS 環境変数から設定を読み込む自動ロードを実装。
    - プロジェクトルートの検出は .git または pyproject.toml を基準に行うため、CWD に依存せず配布後も動作。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動読込無効化サポート（テスト用途）。
  - .env パーサ（クォート付き値、export プレフィックス、インラインコメントの処理、保護された OS 環境変数扱い）を実装。
  - Settings クラスを実装し、必要な環境変数の取得（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や各種検証（KABUSYS_ENV, LOG_LEVEL）を行う。
  - デフォルト値の提供（KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH）および便利なプロパティ（is_live / is_paper / is_dev）。

- ポートフォリオ構築（kabusys.portfolio）
  - 銘柄選定（portfolio_builder.select_candidates）
    - スコア降順、同点時は signal_rank をタイブレークとして最大保有数で切り取る。
  - 重み計算
    - 等金額配分（calc_equal_weights）
    - スコア加重配分（calc_score_weights）：全スコアが 0 の場合は等金額配分にフォールバックし警告を出力。
  - 単元・リスクベースの株数決定（position_sizing.calc_position_sizes）
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - lot_size による丸め処理、1銘柄上限（max_position_pct）、aggregate cap（available_cash）によるスケーリング、cost_buffer による保守的コスト見積の反映。
    - スケーリング時の残差処理は lot 単位で再配分して再現性を確保。
  - リスク調整（risk_adjustment）
    - セクター集中制限（apply_sector_cap）：既存保有比率が閾値を超えるセクターの新規候補を除外。unknown セクターは制限対象外。
    - 市場レジーム乗数（calc_regime_multiplier）："bull"/"neutral"/"bear" をマッピング（1.0/0.7/0.3）、未知レジームは警告後 1.0 にフォールバック。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - research 側で計算した raw ファクターを読み込み、ユニバースフィルタ（最低株価・最低売買代金）、Z スコア正規化、±3 クリップを行い features テーブルへ日付単位で冪等に UPSERT。
  - DuckDB を用いたデータ取得（prices_daily / raw_financials を参照）。
  - ロギングとトランザクション（COMMIT/ROLLBACK）による原子性確保。

- シグナル生成（kabusys.strategy.signal_generator）
  - features と ai_scores を統合し、momentum/value/volatility/liquidity/news のコンポーネントごとにスコアを算出。最終スコア final_score を計算して BUY/SELL シグナルを生成。
  - AI ニューススコアの補完（未登録時は中立 0.5 として扱う）。
  - Bear レジーム検知時の BUY 抑制（ai_scores の regime_score を用いた集計判定）。
  - SELL（エグジット）判定:
    - ストップロス（終値が avg_price より -8% 以下）
    - final_score が閾値未満
    - SELL 判定は BUY より優先し、signals テーブルへ日付単位で冪等に書き込み。
  - weights 入力のバリデーションと正規化（デフォルト重みは仕様に準拠）。

- リサーチ（kabusys.research）
  - ファクター計算（factor_research）
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（20日 ATR、相対 ATR、20日平均売買代金、出来高比）
    - calc_value（PER/ROE の算出、raw_financials の最新報告を参照）
    - DuckDB ベースの SQL 実装、データ不足時の None 処理。
  - 特徴量探索（feature_exploration）
    - 将来リターン計算（calc_forward_returns、複数ホライズン対応）
    - IC（calc_ic：Spearman ランク相関）
    - factor_summary（基本統計量）と rank ユーティリティ
  - zscore_normalize を含む公開 API を提供。

- バックテスト（kabusys.backtest）
  - ポートフォリオシミュレータ（simulator.PortfolioSimulator）
    - 擬似約定モデル：SELL を先に、BUY を後に処理。BUY は指定株数で約定、SELL は保有全量クローズ（部分利確非対応）。
    - スリッページ（符号: BUY +、SELL -）と手数料率を反映した約定価格・手数料計算。
    - 日次スナップショット（DailySnapshot）と取引記録（TradeRecord）を保持。
  - メトリクス計算（metrics.calc_metrics）
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, Total Trades の算出（history / trades のみ参照）。

### 変更
- 初回リリースのため既存バージョンからの変更はありません。

### 修正
- 初回リリースのため修正履歴はありません。

### 既知の制限・注意点
- 設定
  - .env 読み込みはプロジェクトルート検出に失敗した場合はスキップされる。テスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を利用してください。
  - Settings._require は未設定時に ValueError を送出するため、実行時に必須環境変数が設定されていることを確認してください。
- position_sizing / apply_sector_cap
  - price_map における価格欠損（0.0）は過少見積りの原因となり得る旨の TODO コメントあり（将来的にフォールバック価格を導入予定）。
- simulator
  - SELL は全量クローズのみをサポート。部分利確やトレーリングストップ等は未実装。
- strategy.signal_generator
  - 一部のエグジット条件（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の情報が必要であり未実装。
- 依存と設計
  - DuckDB を前提とした SQL 実装のため、DB スキーマ（prices_daily / raw_financials / features / ai_scores / positions / signals 等）が必要。
  - external ライブラリへの依存を抑えた設計（research.feature_exploration は pandas 等に依存しない）。ただし実行環境に duckdb が必要。

### セキュリティ
- .env の読み込みで OS 環境変数を保護する仕組み（protected set）を導入。override フラグや保護キーにより OS 側の値が不意に上書きされないよう配慮。
- .env ファイル読み込み失敗時には警告を出力（例外は送出しない）。

### 破壊的変更
- 初回リリースのため該当なし。

---

今後の予定（例）
- 各銘柄ごとの lot_size を stocks マスタで管理する拡張
- position_sizing の価格フォールバックロジック（前日終値や取得原価の利用）
- simulator の部分利確・トレーリングストップ実装
- strategy の追加エグジット条件（peak_price / entry_date を用いる）  

ご要望があれば、各機能の詳細（API シグネチャ、入出力例、DB スキーマ）に基づくリリースノートをさらに充実させます。