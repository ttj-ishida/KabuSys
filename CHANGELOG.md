# CHANGELOG

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/

## [0.1.0] - 2026-04-25

### Added
- 初回リリース。KabuSys の基本的な実行/設定/ポートフォリオ/ユーティリティ群を追加。
- 実行スクリプト
  - `run_execution.py` — ExecutionEngine 起動用スクリプトを追加。  
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、Paper Trading は専用 SQLite（デフォルト: `data/paper_trading.db`）に記録して本番 DB と分離。
    - 実行時にプロセス優先度を "high" に設定し、PID ファイル管理と停止フラグ (`data/stop_requested.flag`) による安全停止をサポート。
  - `run_monitoring.py` — SystemMonitor ポーリングループ起動スクリプトを追加。  
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
    - Monitoring は環境に関わらず本番の `sqlite_path` を使用する設計。
    - 停止フラグ検知と例外のロギングを備え、DuckDB/SQLite のクローズ処理を確実に行う。
- 設定関連 CLI
  - `config_setup.py` — 対話式ウィザードで `.env` の初期作成・更新を支援。秘密項目はマスク表示し、保存前に確認を行う。
  - `validate_config.py` — `.env` と `config/*.yaml` の起動前検証ツールを追加。`--strict` オプションで警告を FAIL 扱いにできる。
- 環境設定読み込み/検証
  - `config.py` に Settings クラスを追加。環境変数のラップ、デフォルト値、バリデーション（`KABUSYS_ENV`、`LOG_LEVEL` 等）を提供。
  - 自動 `.env` ロード機構を実装（優先度: OS 環境変数 > `.env.local` > `.env`）。プロジェクトルート検出は `.git` または `pyproject.toml` を基準。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - `.env` パーサを強化（`export KEY=val` サポート、クォート内エスケープ、インラインコメント処理など）。
  - `PAPER_FILL_MODE` のバリデーション（有効値: `instant|partial|never|reject`）を実装。
  - `KILL_FLAG_CLEAR_ON_START` 等の監視関連設定を Settings から取得可能に。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - `portfolio.portfolio_builder`
    - 候補選定 (`select_candidates`)、等金額配分 (`calc_equal_weights`)、スコア加重配分 (`calc_score_weights`) を実装。スコア全てが 0 の場合は警告を出して等配分にフォールバック。
  - `portfolio.risk_adjustment`
    - セクター集中制限適用 (`apply_sector_cap`) と市場レジームに応じた投下比率乗数 (`calc_regime_multiplier`) を実装。未知レジームはフォールバックで 1.0。
  - `portfolio.position_sizing`
    - 株数決定ロジック (`calc_position_sizes`) を実装。`allocation_method` に `risk_based` / `equal` / `score` をサポートし、単元株（lot）丸め、per-stock 上限、aggregate cap（利用可能現金に合わせたスケールダウン）や cost_buffer を考慮するロジックを実装。
  - `portfolio/__init__.py` で主要関数をエクスポート。
- リサーチ/ファクター計算
  - `research.factor_research` の骨組みを追加（モメンタム、移動平均乖離、ATR、流動性等を想定）。DuckDB 接続を受け取り `prices_daily` 等に基づく計算を行う設計。
- ツール
  - `tools.paper_verification_report.py` — Paper Trading の検証レポート生成スクリプトを追加。  
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、API レイテンシ (avg/max/P95) 等を集計。
    - デフォルトの合格基準を実装（例: 稼働率 >= 99%、Fill >= 90%、Send >= 95%、P95 <= 200 ms）。
    - 日付フィルタ（--from/--to）、DB パス引数（--db）をサポート。
- ユーティリティ
  - `utils.logging_setup` — 統一ロギング設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（既定 logs/、30 日保持）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして警告表示。
    - ログレベル解決順: 引数 > 環境変数 `LOG_LEVEL` > デフォルト `"INFO"`。
    - stdout を使用することで cron/task scheduler からの扱いを容易に。
  - `utils.process_priority` — プロセス優先度・CPU affinity 設定ユーティリティを追加。  
    - Windows/Linux/macOS（POSIX）差分を吸収。`set_process_priority("high"|"normal"|"low")`、`set_cpu_affinity(n)` を提供。権限不足などは警告でフォールバック。

### Changed
- ログの標準出力を stdout に統一（cron 等からのリダイレクト運用を考慮）。
- `.env` 書き出しテンプレート（`config_setup.py`）に各種キー・セクションを整理して追加。

### Fixed
- `.env` ファイル読み込みでのエラー時に警告を出して処理を継続する挙動を実装（I/O エラーで強制終了しない）。
- `run_execution.py` と `run_monitoring.py` の終了時に SQLite / DuckDB 接続を確実にクローズするように修正（finally ブロックで確実にクローズ）。
- `calc_score_weights` で全スコアが 0 の場合に 0 除算や不正な重みを返さないよう等金額配分にフォールバックして警告を出す。

### Removed
- （無し）

### Security
- （無し）

---

メモ/移行手順
- .env は決してリポジトリにコミットしないでください（`config_setup.py` のヘッダにも注記あり）。
- 自動 `.env` ロードを無効化するには `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定してください（テスト用途など）。
- 本番運用時は `KABUSYS_ENV=live` を設定した上で `validate_config.py` によるチェックを推奨します（`--strict` で警告も失敗扱いにできます）。
- Paper Trading と本番 DB は分離されています。Paper Trading の DB パスは `PAPER_TRADING_SQLITE_PATH` で上書きできます。

--- 

（この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートとして使用する場合は、必要に応じて担当者による追記・調整を行ってください。）