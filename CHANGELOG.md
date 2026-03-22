# Changelog

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

## [0.1.0] - 2026-03-22

### 追加 (Added)
- 基本パッケージ初期リリース。
  - パッケージバージョン: 0.1.0（src/kabusys/__init__.py に定義）
  - エクスポート対象: data, strategy, execution, monitoring

- 環境設定管理モジュール (kabusys.config)
  - .env/.env.local の自動読み込み機能（プロジェクトルートを .git または pyproject.toml から検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプション。
  - .env パーサーは以下をサポート:
    - 空行・コメント行（#）の扱い
    - export KEY=val 形式
    - シングル／ダブルクォート、バックスラッシュによるエスケープ
    - インラインコメントの扱い（クォートの有無に応じた処理）
  - OS 環境変数保護（既存の環境変数を protected として扱い .env で上書きしない挙動）。.env.local は override=True（ただし protected は上書き不可）。
  - 必須環境変数取得ヘルパー `_require()` と settings オブジェクトを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_* など）。
  - KABUSYS_ENV の検証（development / paper_trading / live）と LOG_LEVEL の検証。

- 戦略関連
  - 特徴量エンジニアリング (kabusys.strategy.feature_engineering)
    - research モジュールで計算した raw ファクターを正規化・合成して features テーブルへ UPSERT（冪等）する `build_features(conn, target_date)` を提供。
    - ユニバースフィルタ（株価 >= 300 円、20日平均売買代金 >= 5億円）。
    - Z スコア正規化（指定列を対象）、±3 でクリッピング。
    - トランザクション＋バルク挿入による日付単位の置換（atomic）。
  - シグナル生成 (kabusys.strategy.signal_generator)
    - features と ai_scores を統合して銘柄ごとのコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - シグモイド変換、欠損コンポーネントは中立値 0.5 で補完。
    - final_score に基づく BUY シグナル生成（閾値デフォルト 0.60）。Bear レジーム検知時は BUY を抑制。
    - 保有ポジションに対するエグジット判定（ストップロス: -8%、スコア低下によるクローズ）。
    - signals テーブルへの日付単位置換（トランザクション＋バルク挿入で冪等）。
    - 重み指定 (weights) の検証・補完・リスケーリングロジック。

- リサーチ（研究）機能 (kabusys.research)
  - ファクター計算群を公開 (calc_momentum, calc_volatility, calc_value)（duckdb を使った SQL + Python 実装）。
  - 特徴量探索ユーティリティ:
    - 将来リターン計算 `calc_forward_returns(conn, target_date, horizons=[1,5,21])`（複数ホライズン同時取得）。
    - IC（Spearman のランク相関）計算 `calc_ic()`（ランクの tie は平均ランクで処理）。
    - factor_summary（count/mean/std/min/max/median） と rank（同順位は平均ランク）。
  - 設計方針: prices_daily / raw_financials のみ参照し、外部 API には接続しない。

- バックテストフレームワーク (kabusys.backtest)
  - ポートフォリオシミュレータ `PortfolioSimulator`:
    - BUY/SELL の擬似約定（始値・スリッページ・手数料モデル）、SELL は保有全量クローズ。
    - 平均取得単価（cost_basis）管理、トレード履歴 `TradeRecord`、日次スナップショット `DailySnapshot` 管理。
    - mark_to_market で終値評価と履歴記録（終値欠損時は 0 で評価し WARNING ログ）。
  - メトリクス計算 (kabusys.backtest.metrics):
    - CAGR, Sharpe ratio（無リスク金利=0）, max drawdown, win rate, payoff ratio, total trades を計算する `calc_metrics`。
  - バックテストエンジン (kabusys.backtest.engine):
    - run_backtest(conn, start_date, end_date, ...) を提供。実行中は本番 DB から必要データをインメモリ DuckDB にコピーして実行（signals/positions を汚さない）。
    - データコピーは日付範囲でフィルタ（prices_daily, features, ai_scores, market_regime）し、market_calendar は全件コピー。
    - 日次ループ: 前日シグナル約定 → positions 書き戻し → 時価評価 → generate_signals 呼び出し → 発注リスト作成（ポジションサイジング）を実施。
    - バックテスト専用の DB 初期化ヘルパーを利用（init_schema(":memory:") を想定）。

- API とエクスポート
  - strategy パッケージで build_features / generate_signals を公開。
  - research パッケージで calc_momentum / calc_volatility / calc_value / zscore_normalize / calc_forward_returns / calc_ic / factor_summary / rank を公開。
  - backtest パッケージで run_backtest, BacktestResult, DailySnapshot, TradeRecord, BacktestMetrics を公開。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- 環境変数の自動読み込み時に OS 環境変数を意図せず上書きしない保護機構を導入（.env の上書きは protected を除外）。

---

## 既知の制限・注意点（現状の実装から推測）
- 一部のエグジット条件は未実装（トレーリングストップ、時間決済等）。ソースのコメントに実装予定の旨を記載。
- PBR・配当利回りなどのバリューファクターは未実装（calc_value の TODO）。
- research モジュールは pandas 等に依存せず標準ライブラリ＋DuckDB を前提としているため、大量データ処理の最適化は今後の課題。
- バックテスト用データコピー処理は例外発生時に該当テーブルのコピーをスキップして続行する設計（警告ログ出力）。データ欠損により再現性が低下する可能性あり。
- .env パースは多くのケースを扱うが、特殊ケースの完全互換性（すべてのシェル構文やエスケープ）は保証されない。

---

このバージョンは初回の機能実装をまとめたリリースです。以降のリリースでは上記既知の未実装部分の実装、最適化、テスト整備、API の安定化（Breaking change の可否）を行う予定です。