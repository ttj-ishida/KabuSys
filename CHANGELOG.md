CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に従って記載しています。
このファイルには、リリースごとの機能追加・変更・既知の制限や注意点を日本語でまとめています。

フォーマット:
- Added: 新機能
- Changed: 変更点（互換性に注意）
- Fixed: 修正
- Deprecated: 廃止予定
- Removed: 削除
- Security: セキュリティ関連

Unreleased
----------
（現在なし）

[0.1.0] - 2026-03-26
--------------------
初回リリース — 基本的な戦略研究・シグナル生成・ポートフォリオ構築・バックテスト基盤を実装。

Added
- パッケージ基盤
  - kabusys パッケージを追加。__version__ を "0.1.0" に設定。
  - パッケージ公開 API（__all__）を定義（data, strategy, execution, monitoring）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイル（.env, .env.local）と OS 環境変数からの設定ロード機構を実装。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .git または pyproject.toml を基準にプロジェクトルートを探索するので、CWD に依存しない挙動。
  - シェル形式（export KEY=val）やシングル/ダブルクォート、エスケープ、インラインコメント等を考慮した .env パーサを実装。
  - Settings クラスを提供し、J-Quants / kabu API / Slack / DB パス / 環境種別・ログレベルなどの取得と基本バリデーションを実装。
  - 環境値が未設定の場合に ValueError を投げる _require ユーティリティを実装。

- ポートフォリオ構築 (kabusys.portfolio)
  - 候補選定
    - select_candidates: スコア降順でソートし上位 N を選択。スコア同点は signal_rank でタイブレークするロジック。
  - 重み計算
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比例配分（合計スコアが 0 の場合は等金額へフォールバック）。
  - リスク調整
    - apply_sector_cap: セクター別の既存エクスポージャーを計算し、1セクター上限超過時に同セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（"bull" / "neutral" / "bear"）に応じた投下資金乗数を返す（未知レジームはフォールバックで 1.0）。
  - ポジションサイジング
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に基づく発注株数算出、単元（lot_size）で丸め、per-position と aggregate の上限、cost_buffer による保守的見積りをサポート。available_cash に基づくスケーリング処理（残余の分配は端数優先度で lot 単位で追加）。

- 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
  - build_features: research モジュールの生ファクターを取得しユニバースフィルタ（最低株価・最低平均売買代金）を適用、Z スコア正規化（±3 でクリップ）し features テーブルへ日付単位で置換（トランザクションで原子性を担保）。

- シグナル生成 (kabusys.strategy.signal_generator)
  - generate_signals: features と ai_scores を統合してモメンタム/バリュー/ボラティリティ/流動性/ニュースの最終スコア（final_score）を算出し、閾値超過で BUY シグナル、エグジット条件で SELL シグナルを生成。Bear レジーム時は BUY を抑制。signals テーブルへ日付単位で置換。
  - 売り判定（_generate_sell_signals）:
    - ストップロス判定（終値が avg_price から -8% 以下）
    - final_score が閾値未満でのエグジット
  - 重みのマージ・バリデーション（不正な重みは無視、合計が 1 でなければリスケール）を実装。

- 研究ユーティリティ (kabusys.research)
  - calc_momentum / calc_volatility / calc_value: prices_daily / raw_financials を用いた各種ファクター計算を実装（モメンタム、MA200 乖離、ATR、平均売買代金、PER 等）。
  - calc_forward_returns: 任意ホライズンに対する将来リターンを一括で取得。
  - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
  - factor_summary / rank: 基本統計量とランク付けユーティリティを実装。
  - zscore_normalize を data.stats から利用するための再エクスポート。

- バックテスト (kabusys.backtest)
  - metrics: DailySnapshot / TradeRecord から CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, 総トレード数を計算する BacktestMetrics と calc_metrics を実装。
  - simulator: PortfolioSimulator を実装。メモリ上で約定処理を模擬（SELL を先に処理、部分利確非対応、スリッページ・手数料モデル反映）。TradeRecord / DailySnapshot データ構造を提供。

- ドキュメント・設計ノート
  - 各モジュールに実装方針・参照セクション（StrategyModel.md / PortfolioConstruction.md 等）や未実装項目（TODO）を注記。

Changed
- （該当なし：初期リリース）

Fixed
- .env 読み込みにおいてファイルオープン失敗時に警告を出し安全にスキップするロバストな処理を実装。
- DB トランザクション中のエラー発生時に ROLLBACK を試行し、失敗した場合は警告ログを出すように実装。

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- 設定値の保護: .env ロード時に既存 OS 環境変数を保護する protected キーセット機構を導入（.env の上書きを制御）。

Notes / Known limitations
- position_sizing:
  - lot_size は現状全銘柄共通で扱う（将来的に銘柄別 lot_map に拡張する TODO）。
  - price が欠損（0.0）の場合、_max_per_stock の算出により想定よりエクスポージャーが低く評価される可能性がある（TODO にて対応検討）。
- feature_engineering / signal_generator / research:
  - 外部 API（発注・実口座）への依存は持たない設計。DuckDB のテーブル（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提とする。
  - build_features / generate_signals は target_date 時点のデータのみを用い、ルックアヘッドを避ける前提で実装されている。
- signal_generator:
  - Bear レジーム判定は ai_scores の regime_score に依存。サンプル数が少ない場合は Bear としない（誤判定防止）。
  - SELL の一部条件（トレーリングストップや時間決済）は未実装（positions テーブルに peak_price / entry_date 等の情報が必要）。
- simulator:
  - SELL は現状「保有全量をクローズ」のみ対応。部分利確・部分損切りは未対応。
- エラーハンドリング:
  - DB 操作時にエラーが発生した場合は ROLLBACK を試みるが、Rollback 自体が失敗する可能性がある旨を警告する実装になっている。
- テストと互換性:
  - 環境変数の自動読み込みはテスト目的で無効化できるが、パッケージ配布後の動作確認ではプロジェクトルート検出ロジックに依存する。

Migration / Configuration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings で必須とされ値がないと ValueError を送出します。.env.example を参照して .env を作成してください。
- デフォルト値:
  - KABUSYS_ENV は "development"、LOG_LEVEL は "INFO"、KABU_API_BASE_URL は "http://localhost:18080/kabusapi"、データベースパス等にデフォルトを設定。

開発者向け注記
- コード中に複数の TODO/未実装コメントあり。実運用にあたっては部分利確対応、銘柄別 lot_size、価格フォールバック（前日終値等）の導入、追加のエグジット条件などの実装が推奨されます。
- DuckDB のスキーマ（tables）や外部データ供給の前提（features/ai_scores/prices_daily/raw_financials/positions）を整備してください。

フルチェンジログ
- 初回リリースのため現時点でこれが全ての主要変更です。今後の変更はここに追記します。