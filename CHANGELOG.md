# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [0.1.0] - 2026-03-26

初回公開リリース。日本株向け自動売買システムのコアライブラリを実装しています。主な機能は設定管理、ポートフォリオ構築、戦略の特徴量／シグナル生成、リサーチユーティリティ、バックテスト用メトリクスとシミュレータなどです。

### 追加 (Added)
- パッケージの基本情報
  - パッケージ名: kabusys、バージョン: 0.1.0（src/kabusys/__init__.py）。
  - 公開 API に data, strategy, execution, monitoring を想定した __all__ を定義。

- 環境変数・設定管理 (src/kabusys/config.py)
  - .env / .env.local 自動ロード機能（プロジェクトルートは .git または pyproject.toml を基準に探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサ実装: export プレフィックス、シングル／ダブルクォート、バックスラッシュエスケープ、コメント処理などに対応。
  - Settings クラスを提供し、J-Quants トークン、kabu API 設定、Slack、DB パス、環境モード（development/paper_trading/live）、ログレベル等をプロパティで取得。
  - 必須環境変数未設定時は ValueError を送出する _require 実装。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - 候補選定: select_candidates — スコア降順＋同点時 signal_rank によるタイブレーク。
  - 重み計算: calc_equal_weights（等配分）、calc_score_weights（スコア比率）。全スコアが 0 の場合は等配分にフォールバックして警告を出す。
  - セクター集中制限: apply_sector_cap — 既存保有のセクター比率が閾値を超える場合に当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
  - レジーム乗数: calc_regime_multiplier — "bull"/"neutral"/"bear" に対する乗数マップ（デフォルト 1.0、未知レジームは警告付きで 1.0 にフォールバック）。
  - ポジションサイズ計算: calc_position_sizes
    - allocation_method に基づく数値化（"risk_based", "equal", "score" をサポート）。
    - risk_based: 許容リスク（risk_pct）と stop_loss_pct からベース株数を算出。
    - equal/score: 重み・max_utilization・max_position_pct に基づく配分。
    - lot_size（単元）による丸め、max_per_stock の適用。
    - aggregate cap（available_cash）を超過した場合はスケーリングし、端数は lot_size 単位で残差を大きい順に再配分。
    - cost_buffer による手数料・スリッページの保守的見積りを考慮。

- 戦略：特徴量エンジニアリング (src/kabusys/strategy/feature_engineering.py)
  - research モジュールの生ファクター（momentum, volatility, value）を取得してマージ。
  - 株価・流動性によるユニバースフィルタ（最低株価 300 円、20日平均売買代金 5 億円）を実装。
  - 指定カラムの Z スコア正規化（kabusys.data.stats.zscore_normalize を使用）および ±3 でクリップ。
  - DuckDB に対して日付単位で冪等に features テーブルへアップサート（トランザクションで原子性保証）。

- 戦略：シグナル生成 (src/kabusys/strategy/signal_generator.py)
  - features と ai_scores を統合して最終スコア（final_score）を計算。
  - コンポーネントスコア（momentum/value/volatility/liquidity/news）の計算ロジックを実装（シグモイド変換、中立値 0.5 による欠損補完など）。
  - デフォルト重みのマージと正規化（不正な値は無視して警告）。
  - Bear レジーム検知時は BUY シグナルを抑制（ai_scores の regime_score を集計して判定）。
  - エグジット判定（ストップロス、score 低下）に基づく SELL シグナル生成。SELL を優先して BUY から除外。
  - signals テーブルへ日付単位の置換（トランザクションで原子性保証）。

- リサーチユーティリティ (src/kabusys/research/)
  - 将来リターン計算: calc_forward_returns（複数ホライズンを同時取得、ホライズン検証あり）。
  - IC（スピアマンのランク相関）計算: calc_ic（欠損/不足サンプル時の取り扱い）。
  - ファクター統計サマリ: factor_summary（count/mean/std/min/max/median）。
  - rank ユーティリティ（同順位は平均ランク）。

- バックテスト (src/kabusys/backtest/)
  - メトリクス計算: calc_metrics を中心に CAGR / Sharpe / MaxDrawdown / WinRate / PayoffRatio / total_trades を計算するユーティリティを実装。
  - ポートフォリオシミュレータ: PortfolioSimulator、DailySnapshot, TradeRecord のデータクラス。
    - execute_orders: SELL を先、BUY を後で処理。スリッページ（BUY:+、SELL:-）・手数料率に対応して約定処理をシミュレート。
    - BUY の単元制御（lot_size）対応。SELL は保有全量をクローズ（現バージョンでは部分利確・部分損切りは未対応）。

### 変更 (Changed)
- （初版につき該当なし）

### 修正 (Fixed)
- （初版につき該当なし）

### 既知の制約 / 未実装 (Known issues / Unimplemented)
- apply_sector_cap の価格欠損時（price_map に 0.0 又は欠損）ではエクスポージャーが過小評価される可能性があり、将来的に前日終値等のフォールバック価格を導入する想定。
- calc_regime_multiplier の bear 用乗数は追加の安全弁であり、生成ロジック上は Bear レジームではそもそも BUY シグナルが生成されない設計（ドキュメントに注記）。
- _generate_sell_signals: トレーリングストップや時間決済（保有日数ベース）は未実装（positions テーブルに peak_price / entry_date フィールドが必要）。
- position_sizing の lot_size は現在全銘柄共通。将来的に銘柄別 lot_map による拡張を計画。
- feature_engineering / signal_generator は DuckDB のテーブル構造（prices_daily, raw_financials, features, ai_scores, positions, signals 等）を前提としているため、利用前にスキーマ準備が必要。
- バックテストの約定ロジックの一部（ファイル末尾の BUY 単元チェック部分）がソース断片で終端している箇所あり（実行系の細部は今後整備予定）。

### セキュリティ (Security)
- （初版につき該当なし）

---

注: 各モジュール内に詳細なログ出力や警告メッセージが実装されており、運用時の診断に役立ちます。今後のリリースでは execution 層の具体的な broker 接続、モニタリング/アラート、テストケース強化、エラーハンドリングの拡充、ドキュメント（PortfolioConstruction.md / StrategyModel.md 等）の整備・参照実装追加を予定しています。

[0.1.0]: https://example.com/compare/v0.0.0...v0.1.0