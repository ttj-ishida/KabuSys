# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載します。  
初回リリース（v0.1.0）はコードベースから推測してまとめた内容です。

## [0.1.0] - 2026-03-26

### Added
- パッケージ初期リリース: kabusys（日本株自動売買システム）を公開。
  - パッケージメタ情報: __version__ = "0.1.0"、主要サブパッケージを __all__ で公開 (data, strategy, execution, monitoring)。
- 環境設定管理モジュール（kabusys.config）
  - .env / .env.local ファイルの自動読み込み機能（プロジェクトルートは .git または pyproject.toml により検出）。
  - 読み込みを無効化するための環境変数フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - .env パーサの強化:
    - export KEY=val 形式対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応。
    - クォートなし値の行末コメント解析（# の直前が空白/tab の場合はコメント扱い）。
  - Settings クラスにより環境変数をプロパティで取得:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須値チェック（未設定時に ValueError を送出）。
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH 等の既定値サポート。
    - KABUSYS_ENV / LOG_LEVEL の入力検証（許容値集合を持つ）。
    - is_live / is_paper / is_dev 等のユーティリティプロパティ。
- ポートフォリオ構築モジュール（kabusys.portfolio）
  - 候補選定:
    - select_candidates: スコア降順、同点時は signal_rank 昇順で上位 N を選択。
  - 重み計算:
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（合計が 0 の場合は等金額へのフォールバックと WARNING）。
  - リスク調整:
    - apply_sector_cap: セクター毎の既存エクスポージャーを計算し、最大比率 (デフォルト 30%) を超えるセクターの新規候補を除外（unknown セクターは除外対象外）。売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム ("bull","neutral","bear") に応じた投下資金乗数を返す（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームはフォールバックで 1.0 を返し WARNING を出力。
  - ポジションサイズ決定:
    - calc_position_sizes: allocation_method ("risk_based","equal","score") に対応。リスクベースでは risk_pct, stop_loss_pct を利用して株数を算出。単元株（lot_size）丸め、per-stock 上限・aggregate cap（available_cash）に対するスケーリング、cost_buffer を用いた保守的見積り、残差処理（fractional remainder に基づく lot 単位での追加配分）を実装。
- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - build_features: research の生ファクター (momentum, volatility, value) を取得し、ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5億円）を適用、選択した数値ファクターを Z スコア正規化・±3 でクリップし、features テーブルへ日付単位で置換（トランザクションにより冪等性を保証）。
  - DuckDB を用いた SQL 経由の価格取得・バルク挿入を実装。
- シグナル生成（kabusys.strategy.signal_generator）
  - generate_signals: features / ai_scores / positions テーブルを参照して各銘柄の component スコア（momentum/value/volatility/liquidity/news）を計算、重み付き合算により final_score を算出。BUY 閾値はデフォルト 0.60。
  - AI ニューススコアを統合（未登録時は中立補完）。
  - レジーム判定: ai_scores の regime_score 平均が負でかつサンプル数が十分な場合 Bear と判定し BUY を抑制。
  - SELL（エグジット）判定:
    - ストップロス: 終値/avg_price - 1 < -8% の場合即時 SELL。
    - スコア低下: final_score が閾値未満の場合 SELL。
    - features に存在しない保有銘柄は final_score=0 として SELL 判定対象に（警告ログあり）。
    - 一部未実装の条件（トレーリングストップ、時間決済）は TODO として明記。
  - signals テーブルへ日付単位で置換（トランザクション＋バルク挿入）。
  - 入力 weights のバリデーション・正規化機能を実装（未知キーや負値、非数値は無視、合計が 1 にスケール）。
- リサーチ機能（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）:
    - calc_momentum（1/3/6 ヶ月リターン、200 日移動平均乖離）。
    - calc_volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比）。
    - calc_value（PER, ROE の計算: raw_financials の最新財務を prices_daily と組み合わせ）。
  - 特徴量探索（kabusys.research.feature_exploration）:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
    - calc_ic: スピアマン順位相関（IC）を計算（有効レコードが 3 未満なら None）。
    - factor_summary: 各ファクター列の基本統計量（count, mean, std, min, max, median）計算。
    - rank: 同順位は平均ランクとする安定ランク変換（丸めで ties 検出の堅牢化）。
  - zscore_normalize を公開 API として再エクスポート。
- バックテスト（kabusys.backtest）
  - metrics: バックテスト評価指標計算（CAGR, Sharpe, MaxDrawdown, WinRate, PayoffRatio, total_trades）。
  - simulator: PortfolioSimulator 実装。
    - 日次スナップショット（DailySnapshot）と約定レコード（TradeRecord）を定義。
    - execute_orders: SELL を先に、BUY を後で処理。SELL は保有全量をクローズ（部分利確・部分損切り非対応）。
    - スリッページ（BUY:+、SELL:-）および手数料モデル（commission_rate）に基づく約定価格・手数料計算を想定（実装の続きあり）。

### Changed
- なし（初回リリースのため変更履歴は無し）。

### Fixed
- なし（初回リリースのため修正履歴は無し）。

### Removed
- なし。

### Security
- なし。

### Notes / Known limitations
- .env 自動ロードはプロジェクトルートが検出できない環境ではスキップされる。テスト環境などで明示的に無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定可能。
- apply_sector_cap:
  - price_map に価格が欠損（0.0）だとエクスポージャーが過小評価される可能性がある旨の TODO コメントあり（将来的に前日終値や取得原価でフォールバックすることが想定されている）。
  - "unknown" セクターはセクター上限の適用対象外。
- generate_signals:
  - Bear レジームでは BUY シグナルを抑制する設計。Bear 相場で BUY が発生しないことは仕様（StrategyModel.md に準拠）。
  - 未実装のエグジット条件（トレーリングストップ、時間決済）が存在。
- calc_position_sizes:
  - 単元株 lot_size は現状グローバルに一律で適用（将来的に銘柄毎の lot_map への拡張が想定されている）。
  - aggregate スケーリング時の再配分ロジックは lot_size 単位での追加を行い、再現性のため安定したソートを使用。
- バックテストシミュレータ:
  - SELL は現状「全量クローズ」のみ対応。部分利確や複雑な注文タイプは未対応。
- データベース操作は DuckDB を利用。各種 upsert 処理は日付単位の DELETE→INSERT のトランザクションで実装されており、例外時には ROLLBACK を試み、失敗をログ出力する実装となっている。

---

この CHANGELOG は提供されたソースコードから仕様・実装の意図を推測して作成しています。追加のコミット履歴や変更履歴がある場合は、それに基づいて更新してください。