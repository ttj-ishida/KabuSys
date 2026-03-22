# Changelog

すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

次の内容は提供されたコードベースから推測して作成した初期リリースの変更履歴です。

## [0.1.0] - 2026-03-22

### Added
- パッケージ基盤
  - パッケージのバージョンを `__version__ = "0.1.0"` として追加。
  - トップレベルのエクスポートに `data`, `strategy`, `execution`, `monitoring` を追加。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動ロードする仕組みを実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を起点に探索して特定（CWD に依存しない実装）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードを無効化するフラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート（テストなどで使用可能）。
  - .env のパース処理を実装（コメント対応、export KEY=val 形式、シングル/ダブルクォートのエスケープ処理など）。
  - .env 読み込み時に OS 環境変数を保護する仕組み（protected set）を実装。`.env.local` は既存 OS 環境変数以外を上書き可能とするオプションをサポート。
  - Settings クラスを実装して、アプリケーション設定をプロパティで提供（J-Quants / kabu API / Slack / DB パス等）。
    - 必須値未設定時は `_require()` により ValueError を送出して明示的に失敗する挙動。
    - `KABUSYS_ENV` / `LOG_LEVEL` の検証（許容値外は ValueError）。
    - `is_live`, `is_paper`, `is_dev` のブール補助プロパティを追加。
    - デフォルトの DB パス（DuckDB / SQLite）や kabu API base URL のデフォルト値を定義。

- 研究用モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - Momentum（1M/3M/6M リターン、200 日移動平均乖離率）を計算する `calc_momentum()` を追加。
    - Volatility（20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率）を計算する `calc_volatility()` を追加。
    - Value（PER, ROE）を計算する `calc_value()` を追加。`raw_financials` の target_date 以前の最新レコードを参照。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算 `calc_forward_returns()`（複数ホライズン対応、返却値は fwd_<hd>d）。
    - IC（Spearman の ρ）計算 `calc_ic()`（ランク相関によるファクター評価）。
    - 基本統計量を返す `factor_summary()`。
    - 同順位の平均ランクを扱う `rank()` ユーティリティ。
  - research パッケージの __all__ に主要関数をエクスポート。

- 特徴量エンジニアリング（kabusys.strategy.feature_engineering）
  - 研究環境からの生ファクターを統合・正規化して `features` テーブルに UPSERT する `build_features()` を実装。
    - calc_momentum / calc_volatility / calc_value から原始ファクターを取得してマージ。
    - ユニバースフィルタ（最低株価 300 円、20 日平均売買代金 >= 5 億円）を適用。
    - 指定カラムに対する Z スコア正規化（正規化ユーティリティは kabusys.data.stats の zscore_normalize を利用）と ±3 でクリップ。
    - 日付単位で DELETE→INSERT のトランザクション処理により冪等に書き込み（ロールバック処理を考慮）。
    - 価格欠損や数値非有限値に対する取り扱いが実装されている。

- シグナル生成（kabusys.strategy.signal_generator）
  - 正規化済みの features と ai_scores を統合し、各銘柄の最終スコア（final_score）を算出して BUY/SELL シグナルを生成する `generate_signals()` を実装。
    - コンポーネントスコア（momentum, value, volatility, liquidity, news）を計算するユーティリティを実装（シグモイド変換、平均化、PER の逆数スケーリング等）。
    - デフォルト重み、閾値（デフォルト閾値 0.60）、ストップロス（-8%）など StrategyModel に由来する定数を採用。
    - AI レジームスコアの平均を用いた Bear レジーム検知を実装（サンプル不足時は Bear と判定しない）。
    - BUY は閾値超過かつ Bear レジームでない場合に生成。SELL はポジションのストップロス／スコア低下で生成。
    - SELL 優先ポリシー（SELL 対象を BUY から除外し、BUY のランクは再付番）。
    - 日付単位で signals テーブルを置換（トランザクション + バルク挿入で原子性保証）する実装。
    - 重み辞書の検証と正規化、無効値の警告ログ出力を実装。

- バックテストフレームワーク（kabusys.backtest）
  - ポートフォリオシミュレータ（kabusys.backtest.simulator）
    - メモリ内でポジション / cost basis / cash / history / trades を管理する `PortfolioSimulator` を実装。
    - 約定ロジック（BUY/SELL）を実装：始値ベースの約定、スリッページ・手数料の適用、BUY のシェア計算（切り捨て）、SELL は保有全量クローズ。
    - `mark_to_market()` により終値で時価評価し DailySnapshot を記録。終値欠損時の警告と 0 評価の挙動を定義。
    - TradeRecord / DailySnapshot のデータモデル（dataclass）を定義。
  - メトリクス計算（kabusys.backtest.metrics）
    - CAGR、Sharpe、Max Drawdown、勝率、Payoff Ratio、合計取引数を計算する `calc_metrics()` と内部実装を追加。
    - 各指標の数式と境界条件（データ不足時の 0.0 返却等）を明示。
  - バックテストエンジン（kabusys.backtest.engine）
    - 本番 DB からインメモリ DuckDB へ必要データをコピーしてバックテスト用接続を構築する `_build_backtest_conn()` を実装（signals/positions を汚染しない）。
    - 日次ループでのシミュレーション手順を `run_backtest()` に実装（open 約定 → positions 書き戻し → mark_to_market → generate_signals → ポジションサイジング → 次日約定）。
    - DuckDB 上のデータの期間フィルタリングコピー（prices_daily, features, ai_scores, market_regime）や market_calendar の全件コピーを実装。
    - 日付単位の signals 読み取り／positions 書き込み補助関数を実装。
    - デフォルトパラメータ（初期資金 10,000,000 円、スリッページ 0.1%、手数料率 0.055%、1 銘柄最大 20%）を定義。

- API 統合
  - strategy パッケージの __all__ に `build_features`, `generate_signals` を追加。
  - backtest パッケージの __all__ に `run_backtest`, `BacktestResult`, `DailySnapshot`, `TradeRecord`, `BacktestMetrics` を追加。

- 設計上の注意点・安全対策（ドキュメント的実装）
  - ルックアヘッドバイアスを防ぐため、target_date 時点のデータのみを使用するポリシーを各モジュールで徹底。
  - DB 書き込み時は日付単位で DELETE→INSERT を行い、トランザクションとロールバックで原子性を担保。
  - 外部 API（発注 API / 本番口座）にはアクセスしない設計（研究・バックテストでの安全性向上）。
  - pandas などの外部ライブラリに依存しない実装方針（標準ライブラリ + duckdb を基本に実装）。

### Changed
- 初回リリースのため該当なし。

### Fixed
- 初回リリースのため該当なし。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

### Security
- 初回リリースのため該当なし。

### Notes / Known limitations / TODO
- 未実装の exit 条件がコード内にコメントで明記されている：
  - トレーリングストップ（peak_price を positions に保存する必要あり）。
  - 時間決済（保有 60 営業日超過）など。
- execution パッケージは空のまま（発注実装は未提供）。実運用の発注ロジックは別途実装が必要。
- monitoring パッケージの実装は提供されていない（トップレベルに含まれているが実体はない）。
- ai_scores の取り扱いは存在するが、AI スコア計算フロー自体はこのコードには含まれていない（外部プロセスでの生成を想定）。
- zscore_normalize 等のユーティリティは `kabusys.data.stats` に依存しているが、その実装は本スナップショットからは読み取れないため、利用時に該当モジュールが必要。
- .env パーサは多くのケースをカバーするが、極端なコーナーケースの動作は要検証（複雑なエスケープや行継続など）。
- バックテストにおける営業日取得や calendar 管理は `kabusys.data.calendar_management.get_trading_days` に依存。該当実装の正確性が前提。

もし特定のリリースノートの詳細を追加したい、あるいは「Unreleased」や今後の変更候補セクションを追加したい場合はお知らせください。