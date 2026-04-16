# CHANGELOG

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
バージョン履歴はコード内容から推測して作成しています。

## [Unreleased]

### Added
- 環境変数自動ロードの挙動改善
  - プロジェクトルート検出（.git / pyproject.toml）に基づく .env/.env.local の自動読み込みを追加。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
  - .env のパースで `export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理に対応。

- ユーティリティ追加 / 拡張
  - process_priority モジュールに set_cpu_affinity を追加（プロセスの CPU affinity 固定が可能）。
  - set_process_priority のプラットフォーム差分吸収（Windows / POSIX の優先度設定）をより堅牢に実装。

- 監視（Monitoring）関連
  - run_monitoring スクリプトを追加。SystemMonitor のポーリングループを実装。
  - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き機能を追加（デフォルト 60 秒）。
  - 監視は KABUSYS_ENV に関わらず本番 sqlite_path を使用する仕様を明示。

- 実行（Execution）関連
  - run_execution スクリプトを追加。ExecutionEngine をスレッドで起動し、停止フラグ / PID 管理に対応。
  - KABUSYS_ENV=paper_trading 時に MockBrokerClient を使用し専用 SQLite（data/paper_trading.db）へ記録する分離を実装。
  - RiskManager / Reconciler / OrderManager 等の依存コンポーネントを組み合わせた実行フローを実装。

- ポートフォリオ構築（Portfolio）モジュール
  - 銘柄選定・重み計算モジュール（select_candidates / calc_equal_weights / calc_score_weights）を追加。
  - セクター制約・レジーム乗数（apply_sector_cap / calc_regime_multiplier）を追加。
  - 株数決定・リスク制限・単元丸め（calc_position_sizes）を追加。aggregate cap（総投下上限）のスケーリングと余剰分の lot 単位配分ロジックを実装。

- リサーチ（Research）モジュール
  - ファクター計算（calc_momentum / calc_volatility / calc_value）を追加。DuckDB の prices_daily / raw_financials を参照して純粋関数的に計算。
  - 特徴量探索ユーティリティ（calc_forward_returns / calc_ic / factor_summary / rank）を追加。外部ライブラリに依存しない実装。

- AI ニュース NLP
  - raw_news を OpenAI API（gpt-4o-mini）でスコアリングし ai_scores に保存するモジュール（news_nlp）を追加。バッチ処理、トリム、リトライ、レスポンス検証、スコアクリップ等の設計を実装。
  - ニュース収集ウィンドウ計算ユーティリティ（calc_news_window）を追加。

- ツール
  - Paper Trading の検証レポート生成スクリプト（tools/paper_verification_report.py）を追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計・判定するレポートを標準出力に出力。

### Changed
- Settings 周りの堅牢化とバリデーション強化
  - KABUSYS_ENV / LOG_LEVEL の許容値チェックを追加し、不正値時に明確な例外を投げるようにした。
  - PAPER_FILL_MODE の有効値チェックを追加（instant, partial, never, reject）。
  - データベースパス（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH）を Path 型で正規化して扱うように変更。
  - pid/kill flag 等のパス設定を Settings で一元化。

### Fixed
- ファクター・リサーチ計算の堅牢化
  - calc_momentum / calc_volatility においてウィンドウ内のデータ不足時に None を返すよう明確化し、NULL 伝播の扱いを調整。
  - calc_forward_returns: horizons の入力検証（正の整数かつ <=252）を追加し、複数ホライズンをまとめて効率的に取得するクエリに改良。
  - rank 関数: ties（同順位）処理を round(..., 12) による丸めで安定化し、平均ランクでの処理を保証。

- ポートフォリオ・ポジションサイズ算出の修正
  - calc_score_weights: 全スコアが 0.0 の場合に等金額配分へフォールバックし、警告を出力。
  - calc_position_sizes:
    - 単元（lot_size）丸めを確実に行い、価格欠損時のスキップ処理を安定化。
    - aggregate cap を越えた場合のスケーリングで端数処理・余剰キャッシュからの追加配分を実装し、総投下額を available_cash に収めるロジックを改善。
    - price が 0 や未取得の場合の安全弁を明記。

- 環境変数ファイル読み込みの例外ハンドリング改善
  - .env ファイル読み込み失敗時に warnings.warn で通知し、処理を継続するように変更。

- プロセス優先度設定の障害耐性向上
  - psutil の権限エラーや未実装例外時に警告を出力してスキップするようにした。

---

## [0.1.0] - 2026-04-16

初期リリース（推測）。以下の主要機能を実装。

### Added
- コア
  - ExecutionEngine、OrderManager、OrderRepository、Reconciler、RiskManager 等の実行系コンポーネント（発注・リスク管理・再整合化の基盤）。
  - SystemMonitor（監視テーブルの収集・管理）と監視起動スクリプト run_monitoring。
  - Settings 構成管理（.env 自動読み込み、環境変数ラッパー）。
  - プロジェクトバージョン定義 (__version__ = "0.1.0")。

- データ処理 / 研究
  - DuckDB ベースのファクター計算（Momentum / Volatility / Value）。
  - 将来リターン計算、IC 計算、ファクター統計サマリ等の研究ユーティリティ。

- ポートフォリオ
  - 候補選定、重み算出、ポジションサイズ計算、セクター上限・レジーム乗数などのモジュールを実装。

- AI / ツール
  - ニュース NLP スコアリング（OpenAI）および Paper Trading 検証レポート生成ツール。

### Changed
- なし（初期リリース）

### Fixed
- なし（初期リリース）

---

注意事項:
- 上記はコードベースの実装内容から推測した変更履歴です。実際のコミット履歴やリリースノートと差異がある可能性があります。必要であれば、より正確な日付・バージョン分割やコミット単位の記述に合わせて調整できます。