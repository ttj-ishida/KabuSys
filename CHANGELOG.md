# Keep a Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠します。

なお本 CHANGELOG は提示されたコードベースの内容から機能・制約を推測して作成した初版の変更履歴です。

## [0.1.0] - 2026-03-26

初回リリース — 基本的な自動売買・リサーチ・バックテスト機能を実装。

### 追加 (Added)
- パッケージのメタ情報
  - kabusys パッケージ初版（__version__ = "0.1.0"）。
  - パッケージのエクスポート: data, strategy, execution, monitoring（execution/monitoring はプレースホルダ含む）。

- 環境設定管理 (kabusys.config)
  - .env/.env.local の自動読み込み（プロジェクトルート探索: .git または pyproject.toml を基準）。
  - 読み込み制御: KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パース機能:
    - コメント・export 形式のサポート。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理。
    - インラインコメント処理（クォート無しの値では前の空白で # をコメントと判定）。
  - protected な OS 環境変数を維持する読み込みロジック（.env.local は override）。
  - Settings クラス: 必須環境変数取得用のヘルパーと既定値、検証ロジックを提供。
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID など必須設定。
    - KABUSYS_ENV（development / paper_trading / live）と LOG_LEVEL の検証。
    - データベースパス設定（DUCKDB_PATH, SQLITE_PATH）を Path として取得。

- ポートフォリオ構築 (kabusys.portfolio)
  - 銘柄選定・配分ロジック (portfolio_builder)
    - select_candidates: スコア降順ソート＋タイブレーク（score 降順、同点は signal_rank 昇順）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額にフォールバック、警告ログ）。
  - リスク調整 (risk_adjustment)
    - apply_sector_cap: セクター集中制限。既存保有比率が閾値を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull=1.0, neutral=0.7, bear=0.3）、未知レジームはフォールバックで 1.0（警告ログ）。
  - ポジションサイジング (position_sizing)
    - calc_position_sizes: allocation_method に応じた株数決定:
      - risk_based: リスク率、損切り率から個別ターゲット株数を算出。
      - equal / score: ポートフォリオ比率（weight）に基づく株数算出。
    - lot_size（単元）を考慮した切り捨て、_max_per_stock による1銘柄上限の考慮。
    - aggregate cap: 全銘柄合計コストが available_cash を超える場合のスケーリング。コスト見積りに cost_buffer（スリッページ・手数料想定）を使用し、残余キャッシュで端数を lot 単位で再配分するロジックを実装。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features: research モジュールから取得した生ファクターを統合・ユニバースフィルタ・Z スコア正規化・±3でクリップし、features テーブルへ日付単位の置換（トランザクション）で保存。
  - ユニバース基準: 最低株価（300円）、20日平均売買代金（5億円）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals:
    - features と ai_scores を組み合わせてコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - コンポーネントはシグモイド変換等で [0,1] に縮約し、欠損は中立 0.5 で補完。
    - final_score を重み付けして算出。デフォルト重みは StrategyModel.md の仕様に準拠（momentum 0.40 等）。ユーザ渡し weights の検証・補完・再スケールを実装。
    - Bear レジーム検出時は BUY シグナルを抑制（ai_scores の regime_score 平均で判定、サンプル数不足時は Bear と判定しない）。
    - SELL（エグジット）ルール実装:
      - ストップロス（終値対平均取得単価 -8% 以下）。
      - スコア低下（final_score < threshold）。
      - SELL は BUY より優先して扱い、signals テーブルへ日付単位の置換で保存。
    - DuckDB を用いた features / ai_scores / positions / prices_daily の参照。

- リサーチ機能 (kabusys.research)
  - factor_research:
    - calc_momentum: 1/3/6 ヶ月リターン、MA200 乖離率（200日データ不足時は None）。
    - calc_volatility: 20日 ATR / close（atr_pct）、avg_turnover、volume_ratio。
    - calc_value: latest 財務データ（raw_financials）と株価を組み合わせた PER/ROE 計算（EPS=0 等は None）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）計算。
    - rank / factor_summary: ランク付け・統計要約ユーティリティ。

- バックテスト (kabusys.backtest)
  - simulator:
    - PortfolioSimulator: メモリ上でのポートフォリオ状態管理、約定シミュレーション。
    - DailySnapshot / TradeRecord の定義。
    - execute_orders: SELL を先、BUY を後に処理。スリッページ・手数料率を考慮して約定をシミュレート。SELL は現状「保有全量クローズ」。
  - metrics:
    - calc_metrics: 履歴とトレードから CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio、総トレード数を算出。
    - それぞれの内部ロジックを実装（年次化、営業日換算、等）。

### 変更 (Changed)
- （初版のため履歴上の変更はなし。内部実装の設計注記や TODO をコード内に記載。）

### 修正 (Fixed)
- （初版のため無し）

### 既知の制約・未実装項目 (Known issues / TODO)
- execution パッケージおよび monitoring パッケージはプレースホルダまたは未実装の機能を含む（外部ブローカー接続/実取引ラッパーは未実装）。
- position_sizing の将来的拡張として銘柄別の lot_size（単元）に対応する TODO がある（現状は一律 lot_size）。
- apply_sector_cap の価格欠損（price_map に 0.0 や未設定がある場合）によるエクスポージャー低估のリスクがコメントで指摘されている。フォールバック価格（前日終値や取得原価）を使う拡張が検討されている。
- signal_generator の SELL に関する追加ルール（トレーリングストップ、時間決済）は positions テーブルに peak_price / entry_date 等の情報が追加されない限り未実装。
- calc_regime_multiplier は未知レジームでログ警告を出して 1.0 にフォールバックする挙動がある（運用方針に応じた調整が必要）。
- PortfolioSimulator の BUY 処理（部分約定／部分利確）は現在未サポート。SELL は全量クローズのみ。
- データ前処理・欠損値の扱いは保守的に None を採用している箇所が多く、運用時には logging とデータ品質監視が必要。
- 外部参照: data.stats.zscore_normalize 等の一部ユーティリティは本ログに含まれない外部モジュールに依存している（実装が別ファイルに存在する想定）。

### セキュリティ (Security)
- 必要なシークレット（API トークン等）は環境変数経由での管理を想定。.env の自動読み込みは OS の環境変数を保護する仕組み（protected set）を採用。
- ただし .env/.env.local の扱いに注意（git 管理下に置かない等）。

---

今後のリリースで予定している改善案（例）
- execution 層: 実ブローカー（kabuステーション等）との接続ラッパー実装。
- monitoring: Slack 通知・メトリクス収集の実装。
- position_sizing の銘柄別単元対応・手数料モデル改良。
- signal_generator のルール拡張（トレーリングストップ、保持期間の管理）と更なるリスク制御。
- テストカバレッジ追加（ユニットテスト・統合テスト）および CI 設定。

（本 CHANGELOG はコードから推測して作成しています。実際のコミット履歴が存在する場合はそちらを優先して編集してください。）