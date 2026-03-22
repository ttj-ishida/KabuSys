# Changelog

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

※この CHANGELOG はソースコードの内容から推測して作成しています（実際の変更履歴が存在する場合は差異があり得ます）。

---

## [Unreleased]

（現在未リリースの変更はここに記載します）

---

## [0.1.0] - 2026-03-22

最初の公開バージョン。本リリースは日本株自動売買フレームワークのコア機能をまとめた初期実装を含みます。

### Added
- パッケージ基本情報
  - パッケージ名 `kabusys`、バージョン `0.1.0` を定義（`src/kabusys/__init__.py`）。
  - パブリック API として `data`, `strategy`, `execution`, `monitoring` をエクスポート。

- 環境設定管理
  - `.env` および `.env.local` の自動読み込み機能を実装（プロジェクトルートは `.git` または `pyproject.toml` で探索）。自動読み込みを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を使用可能（`src/kabusys/config.py`）。
  - `.env` の行パーサを実装（コメント、`export KEY=value` 形式、クォート文字とバックスラッシュエスケープに対応）。
  - 必須環境変数取得関数 `_require()` と、`Settings` クラスを提供。主な設定項目:
    - J-Quants: `JQUANTS_REFRESH_TOKEN`
    - kabuステーション API: `KABU_API_PASSWORD`, `KABU_API_BASE_URL`（デフォルト: http://localhost:18080/kabusapi）
    - Slack: `SLACK_BOT_TOKEN`, `SLACK_CHANNEL_ID`
    - DB パス: `DUCKDB_PATH`（デフォルト: data/kabusys.duckdb）、`SQLITE_PATH`（デフォルト: data/monitoring.db）
    - 実行環境: `KABUSYS_ENV`（`development`/`paper_trading`/`live`）、`LOG_LEVEL`（`DEBUG`/`INFO`/...）

- 戦略（Strategy）モジュール
  - 特徴量エンジニアリング: `build_features(conn, target_date)` を実装（`src/kabusys/strategy/feature_engineering.py`）。
    - 研究側の生ファクター（momentum/volatility/value）を取得してマージ。
    - ユニバースフィルタ（最低株価 300 円、20日平均売買代金 >= 5 億円）。
    - 指定列を Z スコア正規化し ±3 でクリップ。
    - 日付単位で features テーブルへ冪等的に UPSERT（トランザクション + バルク挿入）。
  - シグナル生成: `generate_signals(conn, target_date, threshold, weights)` を実装（`src/kabusys/strategy/signal_generator.py`）。
    - features と ai_scores を統合してコンポーネントスコア（momentum/value/volatility/liquidity/news）を計算。
    - デフォルト重みは momentum 40%、value 20%、volatility 15%、liquidity 15%、news 10%。
    - BUY 閾値のデフォルトは 0.60。Bear レジーム判定時は BUY を抑制。
    - 保有ポジションに対してストップロス（-8%）やスコア低下で SELL シグナルを発生。
    - signals テーブルへ日付単位の冪等置換。
    - 無効なユーザー重みはログで警告しスキップ、合計が 1.0 でない場合は再スケールして補正。

- リサーチ（Research）モジュール
  - ファクター計算群（`calc_momentum`, `calc_volatility`, `calc_value`）を実装（`src/kabusys/research/factor_research.py`）。
    - Momentum: 1M/3M/6M リターン、200 日移動平均乖離率（200 行未満は None）。
    - Volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率。
    - Value: raw_financials から最新財務を取得して PER / ROE を計算（EPS 欠損は PER=None）。
  - 解析系ユーティリティ（`src/kabusys/research/feature_exploration.py`）:
    - 将来リターン計算 `calc_forward_returns(conn, target_date, horizons=[1,5,21])`（複数ホライズン対応、ホライズンは 1..252）。
    - IC（Spearman ランク相関）計算 `calc_ic(...)`。
    - ファクター統計サマリ `factor_summary(...)` とランク関数 `rank(...)`。
  - Z スコア正規化は `kabusys.data.stats.zscore_normalize` を利用可能にしている（エクスポートされている）。

- バックテスト（Backtest）フレームワーク
  - シミュレータ（`PortfolioSimulator`）を実装（`src/kabusys/backtest/simulator.py`）。
    - BUY/SELL の擬似約定（始値を使用、スリッページ・手数料モデル、SELL は全量クローズ）。
    - 約定履歴 `TradeRecord`、日次スナップショット `DailySnapshot` を記録。
    - `execute_orders`, `mark_to_market` 等を提供。価格欠損時はログとともに安全に扱う。
  - 評価指標計算（`src/kabusys/backtest/metrics.py`）:
    - CAGR、Sharpe（無リスク=0）、Max Drawdown、Win Rate、Payoff Ratio、total_trades を計算。
  - バックテストエンジン `run_backtest(conn, start_date, end_date, ...)` を実装（`src/kabusys/backtest/engine.py`）。
    - 本番 DB からインメモリ DuckDB へ必要テーブルをコピーしてバックテストを実行（signals/positions を汚染しない）。
    - 日次ループ: 前日シグナル約定 → positions 書き戻し → mark-to-market → generate_signals（BT用 conn）→ ポジションサイジング → 次日の約定。
    - デフォルトのパラメータ: initial_cash=10,000,000、slippage_rate=0.001、commission_rate=0.00055、max_position_pct=0.20。

- その他設計上の注意点 / 実装の頑健性
  - 重要な DB 操作はトランザクション（BEGIN/COMMIT/ROLLBACK）で保護され、ROLLBACK 失敗時は警告ログを出力して例外を再送出。
  - 欠損データ（価格・財務・ai_scores 等）に対する保守的な挙動（ログ出力、スコア補完やスキップ）を多数実装。
  - 外部依存を最小化しており、研究用計算は DuckDB + 標準ライブラリで動作することを想定。

### Changed
- 初期リリースのため該当なし。

### Fixed
- 初期リリースのため該当なし。

### Removed
- 初期リリースのため該当なし。

---

注意事項（利用者向けメモ）
- .env 自動ロードはパッケージの __file__ を基準にプロジェクトルートを探索するため、配布後も CWD に依存せず動作する設計です。テスト等で自動ロードを無効にしたい場合は `KABUSYS_DISABLE_AUTO_ENV_LOAD` を設定してください。
- Signal / Features / Positions 等のテーブルスキーマに依存する実装が多く含まれているため、初期化スクリプト（schema の作成）や実データの整備が必要です（`kabusys.data.schema.init_schema` の利用を想定）。
- AI スコアや財務データが欠損している場合は、スコア計算において中立値で補完される箇所があります（不当な降格を防止する設計）。

---

今後の想定追加項目（例）
- 部分利確 / 部分損切りのサポート（現在は SELL=全量）
- トレーリングストップや時間決済の実装（StrategyModel.md に記載の未実装項目）
- より細かな手数料モデルやスリッページモデルの導入
- モデル学習 / AI モジュールと実運用の接続、実行層（execution）の拡充

---