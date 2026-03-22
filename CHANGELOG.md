# Changelog

すべての重要な変更はこのファイルに記載します。本リポジトリは Keep a Changelog の慣例に従っています。  
安定版リリースはセマンティックバージョニングを採用します。

## [Unreleased]
- （現状なし）

## [0.1.0] - 2026-03-22
初回リリース。日本株自動売買システム "KabuSys" のコア機能を実装。

### Added
- パッケージ初期化
  - パッケージバージョンを `0.1.0` に設定（src/kabusys/__init__.py）。
  - パブリックモジュール一覧を __all__ に定義（data, strategy, execution, monitoring）。

- 設定管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出ロジック（.git または pyproject.toml を探索）を実装し、CWD に依存しない自動ロードを実現。
  - .env / .env.local の優先順位（OS 環境変数 > .env.local > .env）および KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化をサポート。
  - .env パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理を考慮）。
  - 環境変数の必須チェックとプロパティアクセス用 Settings クラスを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）。
  - env 値の検証（KABUSYS_ENV の許容値、LOG_LEVEL の許容値）、パス設定（DUCKDB_PATH, SQLITE_PATH）を実装。

- 戦略（feature engineering / signal generation）
  - 特徴量エンジニアリング（src/kabusys/strategy/feature_engineering.py）
    - research で算出された生ファクター（momentum / volatility / value）を取得し統合。
    - ユニバースフィルタ（最低株価 = 300 円、20 日平均売買代金 >= 5 億円）を実装。
    - 指定カラムの Z スコア正規化と ±3 クリッピングを実行。
    - features テーブルに対して日付単位で置換（DELETE → INSERT）の冪等アップサートを実装。トランザクションで原子性を保証。
  - シグナル生成（src/kabusys/strategy/signal_generator.py）
    - features と ai_scores を統合して各コンポーネントスコア（momentum/value/volatility/liquidity/news）を算出。
    - sigmoind 変換、欠損コンポーネントは中立値（0.5）で補完するロバストなスコアリング。
    - デフォルト重み・しきい値のサポートとユーザ定義 weights の検証・再スケーリング。
    - Bear レジーム検出（AI の regime_score 集計）による BUY シグナル抑制。
    - BUY / SELL シグナルの生成、SELL 優先ポリシー、signals テーブルへの日付単位置換（トランザクション）を実装。
    - ポジションのエグジット判定にストップロス（-8%）とスコア低下を実装。価格欠損時の取り扱いに注意喚起ログを出力。

- Research（src/kabusys/research/）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER, ROE）を DuckDB の prices_daily / raw_financials から計算。
    - データ不足時の None 処理とログ出力。
  - 特徴量探索ユーティリティ（src/kabusys/research/feature_exploration.py）
    - 将来リターン calc_forward_returns（指定ホライズンのリターンを一括取得）。
    - IC（Spearman の ρ）計算 calc_ic と rank / factor_summary を実装。
    - 外部ライブラリに依存しない純 Python 実装（標準ライブラリ + DuckDB）。
  - research パッケージの __all__ を整備。

- バックテストフレームワーク（src/kabusys/backtest/）
  - ポートフォリオシミュレータ（src/kabusys/backtest/simulator.py）
    - DailySnapshot / TradeRecord dataclass。
    - PortfolioSimulator によるメモリ内状態管理、約定ロジック（先に SELL → 次に BUY、スリッページと手数料の適用、保有全量をクローズするシンプル仕様）。
    - mark_to_market による日次評価（終値欠損時は 0 として警告）。
  - メトリクス計算（src/kabusys/backtest/metrics.py）
    - CAGR、シャープレシオ（無リスク=0）、最大ドローダウン、勝率、ペイオフレシオ、総トレード数を計算するユーティリティ。
  - バックテストエンジン（src/kabusys/backtest/engine.py）
    - 本番 DB からインメモリ DuckDB へ必要テーブルを日付範囲でコピーする _build_backtest_conn。
    - 日次ループ（約定 → positions 書き戻し → 時価評価 → signal 生成 → ポジションサイジング → 次日約定シグナル作成）を実装。
    - run_backtest API を提供（初期資金・スリッページ・手数料・最大ポジション割合をパラメータ化）。
    - DB 書き戻し用ユーティリティ（_write_positions）・シグナル読み取り（_read_day_signals）を実装。

- モジュールエクスポートの整備
  - backtest / research / strategy パッケージの __all__ に主要 API を公開。

### Changed
- 初回リリースのため該当なし。

### Fixed
- .env ファイル読み込みでのエラーを警告として扱い、処理継続するようにした（読み込み失敗時の堅牢性向上）。
- トランザクション中に例外が発生した場合、ROLLBACK を試みる処理を導入し、ROLLBACK に失敗した場合は警告ログを出すようにした（feature_engineering, signal_generator, engine の共通パターン）。
- SQL クエリと算出ロジックにおいて、NULL / 非有限値（NaN, Inf）に対する保護を明確化。

### Security
- 特に無し。

### Deprecated
- 初回リリースのため該当なし。

### Removed
- 初回リリースのため該当なし。

---

注意事項 / 必要条件
- 必須環境変数（Settings で必須とされるもの）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらが未設定の場合、Settings の対応プロパティ呼び出しで ValueError が発生します。
- DuckDB スキーマ（以下のテーブル名がコード内で使用されます）:
  - prices_daily, raw_financials, features, ai_scores, positions, signals, market_calendar, market_regime など
  - バックテストは本番 DB から日付範囲でデータをコピーしてインメモリで実行するため、これらのテーブルが想定されるスキーマで存在する必要があります（data/schema 実装に依存）。
- 設計上の方針:
  - ルックアヘッドバイアスを避けるため、各処理は target_date（当該日）時点のデータのみを参照するようになっています。
  - 発注 API（kabu API 等）への直接依存は持たず、execution 層や外部通信は別モジュールで扱う想定です。
  - 依存ライブラリとして DuckDB を使用。その他の外部解析ライブラリ（pandas 等）は依存していません。

もしリリースノートをさらに細分化したい（例えばモジュール別の変更履歴や既知の制限・TODO リストを追加）場合は、どの粒度で記載するかを教えてください。