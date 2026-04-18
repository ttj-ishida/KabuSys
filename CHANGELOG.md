# CHANGELOG

すべての notable な変更はこのファイルに記載します。  
フォーマットは Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠しています。

## [Unreleased]

### Added
- 開発用コマンド／ユーティリティ
  - `python -m kabusys.config_setup` : 対話式に .env を作成／更新するウィザードを追加。
  - `python -m kabusys.validate_config` : .env と config/*.yaml の設定検証 CLI を追加（--strict オプションあり）。
  - `python -m kabusys.tools.paper_verification_report` : ペーパートレード結果の検証レポート生成ツールを追加（期間指定・DBパス指定対応）。
- 起動スクリプト
  - `src/kabusys/run_execution.py` : ExecutionEngine 起動スクリプトを追加。  
    - `KABUSYS_ENV=paper_trading` の場合は MockBrokerClient を使用し、paper_trading 用 SQLite DB（`data/paper_trading.db` または `PAPER_TRADING_SQLITE_PATH`）に記録することで本番 DB と分離する動作をサポート。
    - 起動時にプロセス優先度を高に設定し、stop flag（data/stop_requested.flag）検知で安全に停止する仕組みを備える。
  - `src/kabusys/run_monitoring.py` : SystemMonitor ポーリング起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - Monitoring は環境にかかわらず本番の `sqlite_path` を利用する設計。
- 設定・環境読み込み
  - `src/kabusys/config.py` : Settings クラスを実装。アプリ全体で利用する環境変数プロパティを提供（J-Quants / kabu / LINE / DB / 監視 / システム設定など）。
    - プロジェクトルート検出（.git / pyproject.toml）に基づく自動 .env ロードを追加（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - .env のパースを強化（`export KEY=val`、シングル／ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応）。
    - Paper Trading 関連設定（`PAPER_FILL_MODE`, `PAPER_TRADING_SQLITE_PATH`）を提供。
- ポートフォリオ構築関連（純粋関数群）
  - `kabusys.portfolio` パッケージを追加:
    - portfolio_builder: 候補選定（スコア順）・等重み／スコア加重の重み算出（calc_equal_weights / calc_score_weights / select_candidates）。
    - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた乗数（calc_regime_multiplier）。
    - position_sizing: 発注株数計算（calc_position_sizes） — risk_based / equal / score 方式、単元丸め、aggregate cap のスケーリングを実装。
- ロギング・プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` : stdout ストリームハンドラと日次ローテートのファイルハンドラを統一的に設定するユーティリティ。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで継続。
  - `kabusys.utils.process_priority` : Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定ユーティリティを追加（権限不足時は警告を出してスキップ）。
- モニタリング DB 初期化フック（init_monitoring_db）を run スクリプトから呼ぶことで監視テーブルの存在を保証（冪等）。
- パッケージ初期化にバージョン情報を追加（`__version__ = "0.1.0"`）。

### Changed
- ログ出力の挙動を統一：
  - StreamHandler は stdout を利用（cron 等で stdout/stderr を一本化しやすくするため）。
  - 既存ハンドラを再設定する際に flush/close を行い二重設定を防止。
- .env 読み込みの優先順位を明確化：OS 環境変数 > .env.local > .env。OS 環境変数は保護され、上書きされない。

### Fixed
- .env パーサの堅牢化：
  - クォート内のバックスラッシュエスケープ、`export` プレフィックス、インラインコメントの扱いなどの不正パースを修正。
- ログディレクトリ作成失敗時にプロセスがクラッシュする問題を回避（警告を出してファイルロギングを無効化する）。

### Security
- `.env` を生成する `config_setup` のヘッダに「絶対に Git にコミットしないこと」を明記。

---

## [0.1.0] - 初回リリース（推定）
リポジトリ内の現在コードを基にした初回相当のリリース想定記録。

### Added
- 上記 Unreleased の機能群を初回実装として追加（起動スクリプト、設定管理、検証ツール、ポートフォリオ構築関数群、ロギング／プロセス管理ユーティリティ、paper verification レポート等）。

### Known issues / Notes
- research/factor_research.py が途中で終端しており（ファイル末尾が途中で切れているように見える）、一部のファクター計算処理が未完成。今後の実装・レビューが必要。
- position_sizing.calc_position_sizes における価格欠損時の扱い（price が 0.0 の場合にエクスポージャーが過少見積りされる可能性）に関する TODO コメントあり。将来的に価格フォールバック（前日終値や取得原価）を導入する予定。
- プロセス優先度 / CPU affinity の設定はプラットフォーム依存であり、権限がない場合は警告を出してスキップする挙動。CI や restricted 環境での動作確認を推奨。
- validate_config の YAML 検証は PyYAML 未導入時にスキップされる。CI で厳密検証する場合は PyYAML を依存に含めてください。

---

脚注:
- 本 CHANGELOG は配布されたソースコードから変更点を推測して作成したものです。実際のリリース履歴と異なる場合があります。必要に応じてリリース日やコミットハッシュ等を追記してください。