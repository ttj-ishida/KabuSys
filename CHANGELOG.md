# Changelog

すべての注目すべき変更をここに記録します。  
このファイルは "Keep a Changelog" の形式に準拠しています。

全般:
- リリースバージョンはパッケージ内の __version__ に合わせて 0.1.0 としています（2026-04-17）。

## [0.1.0] - 2026-04-17

### Added
- 基本 CLI / 起動スクリプトを追加
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止はリポジトリルート下 data/stop_requested.flag によるフラグ検知で行う。monitoring は環境にかかわらず本番 sqlite_path を使用する。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可）を使用し、MockBrokerClient を利用して本番 DB と分離する。停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を扱う。
- 環境設定・管理機能
  - config.py: 環境変数読み込みと Settings クラスを実装。自動でプロジェクトルート（.git または pyproject.toml）を探索し `.env` / `.env.local` を読み込む（OS 環境変数は保護）。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動読み込みを無効化可能。複数の設定プロパティ（DB パス、paper_trading 用パス、監視閾値、KABUSYS_ENV/LOG_LEVEL 判定等）を提供。
  - config_setup.py: 対話式ウィザードで .env を作成／更新する CLI を追加。シークレットのマスク表示、選択肢・デフォルト値対応、保存確認を実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数の存在確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリチェック、config/*.yaml の有無・（PyYAML があれば）パース検証、および本番用ガードチェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の確認）を実装。--strict オプションあり。
- ポートフォリオ構築ライブラリ（純関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank でタイブレークして上位 N 件を選択。
    - calc_equal_weights: 等金額配分（1/N）を計算。
    - calc_score_weights: スコア加重配分を計算。全スコアが 0 の場合は等金額配分にフォールバックし警告を出す。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクターごとの既存保有比率が閾値を超える場合に新規候補を除外するロジックを実装（"unknown" セクターは制限を適用しない）。当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告を出して 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じた株数算出。損切り率・リスク率・単元株（lot_size）丸め・1銘柄上限・aggregate cap（available_cash によるスケーリング）・cost_buffer を考慮。価格欠損時のスキップやスケールダウン時の端数処理（lot 単位での再配分）を実装。
- ユーティリティ
  - utils/process_priority.py: プロセス優先度設定と CPU affinity 設定を提供。Windows と POSIX 系を吸収し、psutil ベースで優先度（high/normal/low）と set_cpu_affinity を実装。権限不足や未対応環境では警告を出して安全にフォールバック。
- 研究（リサーチ）機能
  - research/factor_research.py: DuckDB 接続を受け取り価格テーブルから定量ファクターを算出するための基盤（モメンタム、ボラティリティ等）。calc_momentum, calc_volatility を実装（営業日ベースの窓、MA200 や ATR 等）。（注: ファイルは部分的に実装済み）
- レポートツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite DB を読み、稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を集計して検証レポートを出力。閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200 ms）に基づいた PASS/FAIL 判定を行う。コマンドラインで期間指定（--from / --to）と DB パス指定（--db）が可能。
- パッケージ初期化
  - src/kabusys/__init__.py: パッケージヘッダと __version__ を設定（0.1.0）。__all__ に主要サブパッケージを公開。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Implementation details
- .env パーサは export KEY=val 形式、クォート文字列内のバックスラッシュエスケープ、インラインコメント等に対応。既存の OS 環境変数は保護され、.env.local は .env の上書きとして扱われる。
- validate_config は PyYAML 未導入時に YAML 検証をスキップして警告を出すよう安全に実装。
- run_monitoring と run_execution は起動直後にプロセス優先度を "high" に設定する呼び出しを行う（set_process_priority）。
- run_execution は紙トレード時に環境を完全分離（専用 SQLite）して本番 DB を汚染しない設計。
- position_sizing の aggregate cap は cost_buffer（スリッページ・手数料見積り）を考慮した保守的見積りを行い、利用可能資金を超えた場合は比率スケーリングと lot 単位での再配分を行う。

### Security
- .env ファイルに関して、config_setup が生成した .env を Git にコミットしない旨の注記を出力するなど、秘密情報管理の注意喚起を含む。

---

今後の予定（例）
- research/factor_research の残り実装（ファイルの続きを完成）
- 単体テストおよび CI 設定の追加
- 個別銘柄ごとの lot_size サポート（stocks マスタを用いた拡張）
- 更なるログ出力の強化とメトリクス集約（Prometheus 等）

（必要があれば、この CHANGELOG を細分化してコミット単位や機能別により詳細な項目を追加します。）