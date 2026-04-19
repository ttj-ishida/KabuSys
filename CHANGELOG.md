# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠します。日付はこのリリース時点（2026-04-19）を使用しています。

## [Unreleased]

- 小さな改善やドキュメント注釈、ログ出力修正などが将来的に追加される予定です。

---

## [0.1.0] - 2026-04-19

初回公開リリース。日本株自動売買システム「KabuSys」の基礎機能を実装しました。以下はコードベースから推測してまとめた主な追加・変更点です。

### Added（追加）
- コアパッケージ初期構成を追加
  - パッケージバージョン: `__version__ = "0.1.0"`（src/kabusys/__init__.py）
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループ開始スクリプトを追加（MONITOR_POLL_INTERVAL でポーリング間隔上書き可能、停止フラグによる終了）。（src/kabusys/run_monitoring.py）
  - run_execution: ExecutionEngine 起動スクリプトを追加。`KABUSYS_ENV=paper_trading` の場合は MockBroker を使用して paper DB に完全分離で記録。（src/kabusys/run_execution.py）
- 設定・環境管理
  - Settings クラスを追加し、環境変数から各種設定を取得（DBパス、API トークン、環境種別、閾値等）。（src/kabusys/config.py）
  - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml ベース）を探索して `.env` / `.env.local` を読み込む（自動ロードは環境変数で無効化可能）。柔軟な行パース（export 形式、クォート、エスケープ、インラインコメント対応）を実装。
  - config_setup: 対話式ウィザードで .env を作成/更新する CLI を追加。（src/kabusys/config_setup.py）
  - validate_config: 起動前の設定検証 CLI を追加。必須環境変数の未設定チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリチェック、config/*.yaml の存在確認（PyYAML がインストールされていればパース検証）を実装。`--strict` オプションで警告を失敗扱いに可能。（src/kabusys/validate_config.py）
- 監視・運用
  - 監視 DB 初期化ユーティリティ呼び出し（init_monitoring_db を監視・実行の起動時に実行して監視テーブルの存在を保証）。
  - 停止フラグ / kill スイッチや PID ファイルの取り扱いを実装（起動/停止時の安全機構）。
- データベース接続
  - SQLite（監視・paper_trading 用）と DuckDB（分析用）の接続処理を組み込み。
- ロギング・運用ユーティリティ
  - setup_logging: stdout へ StreamHandler を出力し、日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を追加。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールログのみで継続するフォールバックを実装。（src/kabusys/utils/logging_setup.py）
  - process_priority: Windows / POSIX を吸収してプロセス優先度（nice / Windows priority class）および CPU affinity を設定するユーティリティを追加。権限不足や未対応環境では警告を出してスキップ。（src/kabusys/utils/process_priority.py）
- ポートフォリオ構築モジュール（純粋関数群）
  - portfolio_builder: シグナルから候補選定（スコア降順、タイブレークルール）と重み計算（等金額・スコア加重）を実装。（src/kabusys/portfolio/portfolio_builder.py）
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターは制限の対象外とする挙動を明示。（src/kabusys/portfolio/risk_adjustment.py）
  - position_sizing: 各銘柄の発注株数計算を実装（allocation_method: "risk_based" / "equal" / "score"）。単元株（lot_size）に丸め、aggregate cap によるスケーリング、cost_buffer を考慮した保守的見積りを行うロジックを実装。（src/kabusys/portfolio/position_sizing.py）
  - portfolio パッケージのエクスポートを追加。（src/kabusys/portfolio/__init__.py）
- ツール
  - paper_verification_report: ペーパートレード DB から稼働率・注文成功率・送信率・レイテンシ（P95含む）等を集計して PASS/FAIL 判定のレポートを生成する CLI を追加。閾値はソース中に定義（稼働率 99%、成功率 90% 等）。P95 計算ユーティリティを含む。（src/kabusys/tools/paper_verification_report.py）
- リサーチ基盤（骨格）
  - factor_research: DuckDB 接続を受けて定量ファクター（Momentum/Value/Volatility/Liquidity）を計算する設計を開始。関数や定数を定義。（src/kabusys/research/factor_research.py）

### Changed（変更）
- .env の読み込み優先度と保護ポリシーを明確化
  - OS 環境変数 > .env.local > .env の順でロード。既存の OS 環境変数は保護（上書きされない）。（src/kabusys/config.py）
- ログ出力の一貫化
  - 全起動スクリプトで setup_logging を呼び出す想定により、ログの統一フォーマット・ローテーション実装を適用。（複数ファイル）

### Fixed（修正）
- 環境パースの堅牢化
  - .env の parse 実装で export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメントの取り扱いを改善。（src/kabusys/config.py）
- ポーリング間隔の耐性改善
  - MONITOR_POLL_INTERVAL が不正（非数値や 0 以下）の場合にデフォルト（60秒）へフォールバックし、警告ログを出力するようにした。（src/kabusys/run_monitoring.py）
- ファイル/ディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成に失敗した場合でもコンソールログのみで継続するように変更。（src/kabusys/utils/logging_setup.py）
- クロスプラットフォームの優先度設定で例外発生時に警告を出して処理を継続するようにした。（src/kabusys/utils/process_priority.py）

### Notes（注意 / 既知の制約・TODO）
- position_sizing: 価格が欠損（0.0）の場合のフォールバック価格が未実装。TODO コメントあり（前日終値や取得原価のフォールバックを検討）。このため価格欠損時は一部の銘柄がスキップされる可能性があります。（src/kabusys/portfolio/position_sizing.py, risk_adjustment.py）
- factor_research モジュールは実装途中のファイル末尾切れが見られる（未完）。本格的なファクター計算は今後の追加実装を想定。（src/kabusys/research/factor_research.py）
- run_monitoring は説明にある通り「Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用」する設計です。意図的な動作なので運用時に混同しないよう注意してください。（src/kabusys/run_monitoring.py）
- calc_regime_multiplier は未知のレジーム値に対してフォールバック（1.0）を行い、警告を出力します。（src/kabusys/portfolio/risk_adjustment.py）
- validate_config の YAML 検証は PyYAML がインストールされていない場合はスキップされ、警告を出します。（src/kabusys/validate_config.py）

### Security（セキュリティ）
- .env ファイルは機密情報を含むため「絶対に Git にコミットしないこと」を生成ウィザードに明記しています（config_setup の出力ヘッダ）。（src/kabusys/config_setup.py）

---

開発者向けメモ：
- 起動スクリプトはそれぞれ内部で set_process_priority を最初に呼び出すことで実行プロセスの優先度を上げる設計になっています。環境や権限によっては警告が出るため、CI やコンテナ環境での挙動確認を推奨します。
- Paper Trading 周りは本番 DB と明確に分離されるよう設計されています（PAPER_TRADING_SQLITE_PATH / settings.is_paper 判定）。
- ログは stdout にも出るため、システム起動時に外部ログ集約（systemd/journald やコンテナのログ収集）との相性を意識して設定してください。

もし CHANGELOG に特に強調したい点（例: 破壊的変更、移行手順、リリースノートに載せるスクリーンショットやコマンド例）があれば教えてください。必要に応じて追記・整形します。