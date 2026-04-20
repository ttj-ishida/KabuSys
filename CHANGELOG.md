# Changelog

すべての重要な変更点を記録します。本ファイルは「Keep a Changelog」形式に準拠します。
語彙はコードベースから推測して作成しています。

フォーマット:
- Unreleased: 次のリリースに向けた変更（現時点では空）
- 各バージョン: そのバージョンで導入・変更された主な機能・修正点

---

## [Unreleased]

---

## [0.1.0] - 2026-04-20

### Added
- 基本アプリケーション骨格を実装
  - パッケージ情報: `kabusys.__version__ = "0.1.0"`
- 起動スクリプト
  - `src/kabusys/run_execution.py`
    - ExecutionEngine を起動する CLI スクリプト。
    - KABUSYS_ENV に応じて Paper Trading 用の専用 SQLite DB (デフォルト: `data/paper_trading.db`) を使用する分離設計。
    - 起動時にプロセス優先度を高く設定する処理を追加（`utils.process_priority.set_process_priority` を利用）。
    - 起動・終了のための停止フラグ (`data/stop_requested.flag`) と PID ファイル管理を実装。
    - スレッドで実行エンジンをデーモン実行し、停止フラグによる安全停止をサポート。
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor のポーリングループ起動スクリプト。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 SQLite パスを使用する設計。
    - 停止フラグの検知、例外ハンドリング、リソースクローズ処理を実装。
- 設定管理・初期化
  - `src/kabusys/config.py`
    - `.env` 自動読み込み機能（プロジェクトルート検出: `.git` または `pyproject.toml`）。
    - `.env` と `.env.local` の優先順位（OS 環境変数を上書きしない保護機構）。
    - 複雑な .env 行のパース対応（`export ` プレフィックス、クオート内のエスケープ、コメント処理など）。
    - 各種設定プロパティを提供（J-Quants / kabu API / DB パス / paper trading 設定 / 監視閾値 / 起動環境判定など）。
    - `Settings` クラス経由で安全に設定値へアクセスできるインターフェースを提供。
- 設定関連 CLI
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで `.env` を作成・更新するツール。
    - 多数の設定項目定義（環境種別、API トークン、DB パス、ログレベル、Kill Switch 設定など）。
    - 既存 `.env` 読み込み、入力補助、シークレットマスク表示、保存確認までのフローを提供。
  - `src/kabusys/validate_config.py`
    - 起動前に `.env` と `config/*.yaml` の整合性を検証する CLI。
    - 必須・任意環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリチェックを実装。
    - PyYAML が存在すれば YAML のパース検証も実行。`--strict` で警告も失敗扱いにできる。
- ロギング・プロセス管理ユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - アプリ共通のログ初期化処理を提供。
    - stdout 出力の StreamHandler と日次ローテーションの TimedRotatingFileHandler（30 日分保持）をルートロガーに設定。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続する堅牢性。
    - LOG_LEVEL / LOG_DIR / 引数での上書き対応。
  - `src/kabusys/utils/process_priority.py`
    - Windows / POSIX（Linux/Mac 等）の差を吸収してプロセス優先度設定を提供。
    - CPU affinity 設定関数 `set_cpu_affinity` を実装（利用可能なコア数より多い指定は全コア使用へフォールバック）。
    - 権限不足等でも安全に失敗を ログ警告で処理。
- ポートフォリオ構築モジュール（純粋関数群）
  - `src/kabusys/portfolio/portfolio_builder.py`
    - 候補銘柄選定 (`select_candidates`) と重み計算（等配分 `calc_equal_weights`、スコア加重 `calc_score_weights`）。
    - score が全て 0 の場合のフォールバック（等配分）を警告付きで実装。
  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中制限を適用する `apply_sector_cap` を実装（既存保有評価、売却予定の除外、unknown セクターの扱いなど）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier` を提供（bull/neutral/bear をサポート、未知値はフォールバック）。
  - `src/kabusys/portfolio/position_sizing.py`
    - ポジションサイズ計算 `calc_position_sizes` を実装（risk_based / equal / score の配分方式、lot サイズ丸め、per-stock および aggregate キャップ、スケーリングロジック、cost_buffer 考慮）。
    - スケールダウン時の端数処理（lot 単位での再配分）により再現性と安全弁を確保。
  - `src/kabusys/portfolio/__init__.py` にて主要関数をエクスポート。
- Paper Trading 検証ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 用 SQLite DB を解析して検証レポートを生成する CLI。
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシなど。
    - 各種閾値（稼働率99%、fill 90%、send 95%、P95 <= 200ms）に基づく PASS/FAIL 判定を出力。
    - 日付フィルタ、db パス上書きオプションをサポート。
- Research（ファクター計算）モジュール（実装途中）
  - `src/kabusys/research/factor_research.py`
    - Momentum / Value / Volatility / Liquidity の計算方針と定数を定義。
    - DuckDB を用いた prices_daily/raw_financials 参照の方針。
    - モメンタム計算関数の実装を開始（ファイル末尾で途中まで記述）。

### Changed
- なし（初版リリース）

### Fixed
- なし（初版リリース）

### Removed
- なし

### Notes / Design decisions
- 環境変数自動読み込みはデフォルトで有効（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
- `.env` の自動ロードはプロジェクトルートが特定できた場合のみ行い、CWD に依存しない実装。
- 監視・実行プロセスは停止フラグファイルを使った外部制御（ファイルベースの Kill Switch）を採用。
- Paper Trading と Live（本番）の DB は明確に分離する設計（Paper は専用 sqlite）。

---

今後の予定（想定）
- ExecutionEngine / SystemMonitor 本体のより詳細な実装・テスト
- research モジュールの完全実装（ファクター計算の SQL 実装）
- strategy / execution の追加ユニットテスト・統合テスト
- ドキュメント・運用手順の充実化

---

（注）本 CHANGELOG は提示されたソースコードからの推測に基づいて作成しています。実際の変更履歴やリリースノートは開発履歴に基づいて追記してください。