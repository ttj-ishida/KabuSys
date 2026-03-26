# Changelog

すべての重要な変更点をこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」仕様に従っています。詳細: https://keepachangelog.com/ja/1.0.0/

最新更新日: 2026-03-26

## [Unreleased]
- 今後の変更やマイナーバージョンで追加予定の改善点をここに記載します。

---

## [0.1.0] - 2026-03-26
最初の公開リリース。日本株自動売買システム「KabuSys」のコア機能を実装しました。以下の主要サブシステムを含みます。

### Added
- パッケージ基礎
  - パッケージ初期化 `kabusys.__init__` を追加。バージョン情報と公開 API を定義。
- 設定管理
  - `kabusys.config`:
    - .env/.env.local および環境変数（OS環境）からの設定自動読み込み機能を実装。
    - プロジェクトルート（.git または pyproject.toml）を基準に .env を探索（CWD に依存しない）。
    - .env のパース器を実装（コメント・クォート・export 形式対応、保護キー対応）。
    - 自動ロードを無効化するためのフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 必須環境変数取得用の `Settings` クラスを提供（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID）。
    - 環境/ログレベルのバリデーション（development/paper_trading/live と DEBUG/INFO/...）。
- ポートフォリオ構築
  - `kabusys.portfolio.portfolio_builder`:
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank でタイブレーク）。
    - 等金額配分 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等金額にフォールバック、警告を出力）。
  - `kabusys.portfolio.risk_adjustment`:
    - セクター集中制限 `apply_sector_cap`（既存保有をセクター別に集計し上限超過セクターの候補を除外）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear をマップ、未知のレジームはフォールバックして警告）。
  - `kabusys.portfolio.position_sizing`:
    - 各銘柄の発注株数算出 `calc_position_sizes`（risk_based, equal, score の割当方式、単元丸め、per-stock/max aggregate cap, cost_buffer を考慮したスケーリング）。
    - lot_size と cost_buffer による保守的見積りと端数処理（残差配分ロジック）を実装。
- 戦略（Feature / Signal）
  - `kabusys.strategy.feature_engineering`:
    - 研究モジュールの生ファクターを取得し、ユニバースフィルタ（最低株価・最低売買代金）を適用、Zスコア正規化（±3 でクリップ）して `features` テーブルへ UPSERT（トランザクションで原子性確保）。
    - DuckDB を利用して prices_daily / raw_financials からデータ取得。
  - `kabusys.strategy.signal_generator`:
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算し最終スコアを算出。
    - レジーム（Bear）判定に応じて BUY シグナルを抑制。
    - BUY（閾値以上）および SELL（ストップロス・スコア低下）シグナルの生成と `signals` テーブルへの日次置換（冪等）。
    - ユーザ提供の weights のバリデーション・正規化ロジックを実装。
- 研究ツール（Research）
  - `kabusys.research.factor_research`:
    - Momentum / Volatility / Value ファクター算出関数（mom_1m/3m/6m, ma200_dev, atr_20/atr_pct, avg_turnover, per/roe 等）。
    - DuckDB SQL ベースで、営業日を考慮したウィンドウ計算を実装。
  - `kabusys.research.feature_exploration`:
    - 将来リターン計算（任意ホライズン）、IC（Spearman ρ）計算、ファクター統計サマリー、ランク関数を提供。
    - pandas 等に依存せず純粋な標準ライブラリ実装。
- バックテスト
  - `kabusys.backtest.simulator`:
    - メモリのみのポートフォリオシミュレータ（DailySnapshot, TradeRecord を定義）。
    - SELL を先に処理してから BUY を約定、スリッページと手数料モデルを適用。SELL は保有全量クローズ（部分利確非対応）。
  - `kabusys.backtest.metrics`:
    - CAGR, Sharpe, Max Drawdown, Win Rate, Payoff Ratio, total_trades を計算するユーティリティ。
    - 入力は DailySnapshot / TradeRecord のリストのみ（DB 参照なし）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）

### Deprecated
- （初版のため該当なし）

### Removed
- （初版のため該当なし）

### Security
- 環境変数や .env の取り扱いに注意。必須トークン・パスワードは `Settings` を通じて取得し、.env には機密情報を保存する際に適切な権限管理を推奨。

### Notes / Known limitations
- .env 読み込みの挙動:
  - OS 環境変数が優先され、.env による上書きを防ぐために protected キーを保持。
  - `.env.local` は `.env` の上に上書きで読み込まれる。
  - 自動読み込みを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定。
- 欠損データの取り扱い:
  - 価格欠損や財務データ欠損時は明示的にスキップまたは None を返す実装が多く、安全寄りに設計されています（例: price がない銘柄は position sizing/sell 判定をスキップ）。
  - `apply_sector_cap` は sector が "unknown" の場合に制限を適用しないため、銘柄マスタ整備が推奨されます。
- 売却ロジック:
  - 現時点では SELL は保有全量をクローズする実装。トレーリングストップや時間決済は未実装（コメントで TODO 記載）。
- position_sizing の制約:
  - 現在は全銘柄共通の lot_size を想定（将来的に銘柄別拡張を予定）。
  - price が 0 または None の場合は該当銘柄をスキップ。
- Simulator の既知挙動:
  - `PortfolioSimulator.execute_orders` のデフォルト lot_size=1（後方互換）。日本株では通常 100 を渡すことを想定。
- レジーム乗数:
  - 未知のレジームが渡された場合は警告を出し multiplier=1.0 でフォールバック。

### Migration / Upgrade notes
- 本バージョンが初回リリースのため、特別な移行手順はありませんが、環境変数の設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）と DuckDB の prices_daily / raw_financials / features / ai_scores / positions など必要テーブルの準備が必要です。
- .env.example を参考に .env を作成してください（Settings._require が未設定時に ValueError を送出します）。

---

貢献・バグ報告・機能要望は issue を作成してください。今後のリリースでは以下を優先して対応予定です:
- 銘柄ごとの lot_size マスタ対応
- 価格フォールバック（前日終値や取得原価など）を利用した exposure 計算の堅牢化
- トレーリングストップや時間決済の SELL 条件追加
- 追加のテストとドキュメント整備

以上。