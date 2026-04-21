# Changelog

すべての変更は Keep a Changelog の形式に従って記載しています。  
重要な変更点や新機能をコードベースから推測してまとめました。

フォーマット:
- Unreleased: 今後の変更（現時点では空）
- 各バージョン: 主要な追加・変更・修正点をカテゴリ別に列挙

## [Unreleased]

## [0.1.0] - 2026-04-21

### Added
- 基本アプリケーションパッケージを追加（kabusys）。
  - バージョン定義: `src/kabusys/__init__.py` にて `__version__ = "0.1.0"` を設定。
- 起動スクリプト / デーモン系
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加（`src/kabusys/run_monitoring.py`）。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60秒）。
    - 停止制御はリポジトリ内の `data/stop_requested.flag` ファイルで行う。
    - Monitoring は環境（KABUSYS_ENV）にかかわらず本番用の `sqlite_path` を使用。
  - run_execution: ExecutionEngine 起動スクリプトを追加（`src/kabusys/run_execution.py`）。
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、ペーパートレーディング用 DB（`data/paper_trading.db`）へ記録して本番 DB と分離。
    - デーモンの停止は同様に `data/stop_requested.flag` を参照。PID ファイル管理あり（`data/execution.pid`）。
- 設定管理とツール
  - Settings クラス: 環境変数をラップする設定モジュールを追加（`src/kabusys/config.py`）。
    - .env の自動読み込み機能（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。
    - 自動ロードの無効化フラグ `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 多数のプロパティを提供（J-Quants、kabuAPI、LINE、DB パス、監視しきい値、環境判定等）。
    - Paper Trading 専用設定（`paper_sqlite_path`, `paper_fill_mode`）をサポート。
  - 設定ウィザード CLI: `.env` を対話式に作成・更新するツールを追加（`src/kabusys/config_setup.py`）。
    - シークレット入力、選択肢、既存値の再利用、保存確認などをサポート。
  - 設定検証 CLI: `.env` および `config/*.yaml` を起動前に検証するツールを追加（`src/kabusys/validate_config.py`）。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、DB パス・YAML ファイル存在チェック、Live 環境用追加ガードを実装。
    - `--strict` オプションで警告を失敗扱いにできる。
- ロギング / プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティを追加（`src/kabusys/utils/logging_setup.py`）。
    - stdout への StreamHandler と日次ローテーションの FileHandler（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、既存ハンドラのクリーンアップ、環境変数や引数によるログレベル/出力先制御を実装。
  - プロセス優先度・CPU affinity ユーティリティを追加（`src/kabusys/utils/process_priority.py`）。
    - Windows / POSIX 差分を吸収し "high"/"normal"/"low" の優先度を設定。
    - CPU コア固定（set_cpu_affinity）をサポート。
    - psutil の権限制約や未対応 OS を考慮したフォールバック処理を実装。
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder: 候補選定・重み計算（等分配・スコア加重）を追加（`src/kabusys/portfolio/portfolio_builder.py`）。
  - risk_adjustment: セクター制限（apply_sector_cap）とレジーム乗数（calc_regime_multiplier）を追加（`src/kabusys/portfolio/risk_adjustment.py`）。
    - セクターマップ・現在保有・価格マップを考慮した除外ロジック、レジームに応じた資金乗数を実装。
  - position_sizing: 発注株数算出（リスクベース / 等分配 / スコアベース）、単元株丸め、aggregate cap スケールダウンロジックを追加（`src/kabusys/portfolio/position_sizing.py`）。
    - lot_size（現在 100）で丸め、cost_buffer を見積もりに反映して保守的に計算。
- 研究用モジュール（部分実装）
  - factor_research: DuckDB を用いたファクター計算モジュールを追加（`src/kabusys/research/factor_research.py`）。
    - Momentum（1M/3M/6M リターン、MA200 乖離）、ATR、出来高指標等の計算方針を定義（実装は継続）。
- Paper Trading 検証ツール
  - paper_verification_report: ペーパートレード用 SQLite DB から各種指標（稼働率、注文成功率、レイテンシ等）を集計しレポートを出力する CLI を追加（`src/kabusys/tools/paper_verification_report.py`）。
    - P95 レイテンシ計算、閾値に基づく PASS/FAIL 判定を実装。
    - DB 存在チェック、日付フィルタ、コマンドライン引数対応（--from/--to/--db）。

### Changed
- -- （初回リリースのため大きな既存挙動変更はなし。各モジュールは設計上の注意書き・フォールバックを含む実装となっている）

### Fixed
- -- （初回リリース）

### Security
- 環境変数の自動読み込みは OS 環境変数を保護（protected set）し、既存の OS 環境変数を上書きしない既定の動作を採用。
- `.env` を Git にコミットしない旨を config_setup のヘッダに明示（運用上の注意）。

### Notes / Implementation details / 作業上の注意
- .env パーサは以下をサポート:
  - コメント行、`export KEY=val` 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行内コメント（クォート外かつ直前が空白の場合に認識）等。
- run_monitoring は監視 DB（monitoring.db）を常に本番パスから初期化して使用する設計で、環境にかかわらず同一監視 DB を参照することに注意。
- run_execution は Paper Trading 用 DB を明確に分離しており、paper_trading 環境では本番 DB に影響を与えない。
- process_priority と logging_setup は実行環境の権限制約を考慮し、失敗してもプロセスを継続する安全設計になっている。
- Portfolio / PositionSizing 周りは将来的な拡張（銘柄別 lot_size マスタ、価格フォールバック、より細かな手数料モデル等）を想定した TODO コメントを含む。

---

開発初期の大きな骨格（設定管理、起動スクリプト、ロギング・プロセス制御、ポートフォリオ構築、ペーパートレード検証、研究モジュール雛形）が整った状態です。今後の作業候補として、factor_research の完全実装、ユニットテスト追加、ドキュメント整備（使用例・運用手順）、および運用向けの監視・アラート設定の強化を推奨します。