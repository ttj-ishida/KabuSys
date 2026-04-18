# Changelog

すべての重要な変更点をこのファイルに記録します。フォーマットは「Keep a Changelog」に準拠し、Semantic Versioning を想定しています。

- 参考: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 開発中の変更点や次回リリースでの予定事項をここに記載してください。

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション構成
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を追加。
  - 公開 API: portfolio モジュールの主要関数をエクスポート（select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier）。

- 環境設定 / 設定管理
  - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml）を探索して `.env` / `.env.local` を読み込み（`KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可）。
  - 高度な .env パーサ実装:
    - `export KEY=val` 形式のサポート、シングル/ダブルクォートのエスケープ処理、インラインコメント処理など。
    - `_load_env_file` により OS 環境変数を保護しつつ上書きや優先読み込みを実現。
  - `Settings` クラスを実装して、環境変数から構成値を安全に取得・検証（例: KABUSYS_ENV、LOG_LEVEL、DB パス、paper trading 関連設定など）。
  - `config_setup.py`：対話式ウィザードで `.env` を作成・更新する CLI を提供（選択肢、デフォルト、シークレット入力対応）。
  - `validate_config.py`：起動前に必須環境変数・パス・YAML ファイル等の存在や値を検証する CLI を提供。`--strict` オプションで警告を失敗扱いにする機能あり。

- 実行・監視ランナー
  - `run_execution.py`：
    - ExecutionEngine の起動エントリポイント。
    - `KABUSYS_ENV=paper_trading` 時は paper 用 SQLite（`PAPER_TRADING_SQLITE_PATH`）を使用し、本番 DB と分離。コメントで MockBrokerClient の使用が示されている。
    - BrokerClientFactory を介したブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler の組立て。
    - `RiskConfig` の既定値を定義（ポジション上限、利用率、レート制限、サーキットブレーカー、ドローダウン等）。初期ポートフォリオ値はブローカーの利用可能現金から取得。
    - エンジンは別スレッドで動作し、プロジェクトルート下の停止フラグ（data/stop_requested.flag）を監視して安全に停止。
    - PID ファイルの取り扱い。
  - `run_monitoring.py`：
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。0 以下の値はデフォルトにフォールバックして警告出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視 DB を固定している点に注意）。
    - 停止フラグ検知・例外のログ化・duckdb 接続と sqlite の初期化を含む。

- ユーティリティ
  - `utils/logging_setup.py`：
    - 統一ログ設定ユーティリティ。STDOUT へ出力する StreamHandler と、日次ローテーション（TimedRotatingFileHandler）でログファイルを出力（デフォルト logs/、30 日保持）。
    - 既存ハンドラをクリーンに置き換える実装、ログディレクトリ作成に失敗した場合のフォールバック（コンソール出力のみ）を考慮。
    - 出力は stdout を使用（cron 等からのリダイレクトを想定）。
  - `utils/process_priority.py`：
    - クロスプラットフォームでプロセス優先度設定を行うユーティリティ（Windows / POSIX 対応）。`set_process_priority` と `set_cpu_affinity` を提供。
    - 権限不足や未サポート環境では警告を出して安全にスキップ。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - `portfolio/portfolio_builder.py`：
    - 候補選定（スコア降順、同点時は signal_rank でタイブレーク）、等金額配分、スコア加重配分（全スコア 0 の場合は等配分にフォールバック）を実装。
  - `portfolio/risk_adjustment.py`：
    - セクター集中制限の適用（既存保有をもとにセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外）。
    - レジーム乗数（bull/neutral/bear に対応、未知レジームはフォールバックで 1.0）を提供。Bear レジームの特性に関する注釈あり。
  - `portfolio/position_sizing.py`：
    - 複数配分方式（risk_based / equal / score）に基づく株数計算を実装。
    - 単元株（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash）に合わせたスケーリング、cost_buffer（手数料/スリッページ見積り）の考慮、余り配分アルゴリズムを実装。
    - price 欠損時のスキップやログ出力を行う。

- リサーチ / ツール
  - `research/factor_research.py`（ファクター計算の骨子を実装）：
    - Momentum / Value / Volatility / Liquidity 等のファクター計算を想定し、DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - （ファイル内に計算定数・モメンタム計算関数などの基盤実装あり。）
  - `tools/paper_verification_report.py`：
    - Paper Trading の検証レポート生成スクリプト。期間フィルタ（--from / --to）、DB パスの指定（--db / 環境変数）に対応。
    - 稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均 / 最大 / P95）などを集計し、閾値に基づいた PASS/FAIL 判定を行う。
    - P95 計算、NULL ハンドリング、テーブル存在時の例外フォールバック等を考慮。

- DB/分析
  - DuckDB と SQLite の併用を前提（duckdb は分析用、sqlite は監視・注文履歴用の軽量 DB）。
  - `monitoring_db.init_monitoring_db` を起動時に呼び出して監視テーブルの存在を保証（冪等）。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Removed
- （初期リリースのため該当なし）

### Security
- 環境変数のシークレットは `.env` に保存する設計を想定（.env を Git にコミットしないことを README/生成ファイルに明記）。
- `config_setup` では機密情報入力時にマスク表示を行う設計。

### Notes / Known limitations / TODO
- 一部実装に TODO コメントあり（例: price が欠損した場合のフォールバック価格の扱い）。
- research モジュール（factor_research.py）は設計方針・骨子を実装しているが、完全なファクター集合の計算・テストは今後の整備が必要。
- 実環境でのプロセス優先度設定や CPU affinity は権限や OS に依存し、失敗時は安全にスキップする挙動。
- Monitoring は環境にかかわらず本番用 sqlite_path を使う点に注意（意図的な設計だが運用ドキュメントで明示推奨）。
- パッケージ全体の動作には外部依存（psutil, duckdb, PyYAML など）がある。validate_config による事前チェックを推奨。

---

変更履歴はコード内容から推測して作成しています。実際のコミット履歴やリリースノートと整合させる場合は、差分や目的に応じて調整してください。