# Changelog

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

最新版: 0.1.0 — 2026-04-19

## [0.1.0] - 2026-04-19

リリース初版。日本株自動売買システム KabuSys の主要コンポーネントとユーティリティを実装・追加しました。

### 追加
- 全体
  - パッケージ初期版を追加。バージョンは `__version__ = "0.1.0"`。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - 起動時にプロセス優先度を "high" に設定。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と完全分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ監視を実装。
    - 起動時に停止フラグが立っている場合は起動せず終了するロジックを追加。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値は警告してデフォルトにフォールバック）。
    - 監視は KABUSYS_ENV に関わらず本番用 `sqlite_path` を使用（監視 DB は共通管理）。
    - 停止フラグファイル検出でループを終了、例外はログ出力して次ポーリングに継続。

- 設定管理
  - config: 環境変数/.env の読み込みおよび Settings クラスを実装。
    - 自動 .env 読み込み: プロジェクトルート（.git または pyproject.toml）を基準に `.env` → `.env.local` の順で読み込み。OS 環境変数は保護して上書きを制御。
    - .env パーサは `export KEY=val` フォーマット、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等をサポート。
    - Settings プロパティ群（J-Quants / kabu API / LINE / DB パス / 監視閾値 / システムフラグ等）を提供。`PAPER_FILL_MODE` の妥当性チェック、`KABUSYS_ENV` / `LOG_LEVEL` の検証などを実装。
    - `settings` の単一インスタンスをエクスポート。

  - config_setup: .env を対話式に生成・更新するウィザード CLI を追加。
    - 各設定項目の説明付きプロンプト、既存 .env の読み込みと Enter による既存値の再利用、シークレット入力のマスク表示、保存確認とファイル書き込みを実装。

  - validate_config: 起動前設定検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL の値検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在確認と（PyYAML があれば）パース検証、本番 (live) 向け追加ガード（LINE通知、kill flag 動作）を実装。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ログまわり
  - utils/logging_setup: 統一ログ設定ユーティリティを追加。
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次ローテーション、30日分保持）を設定。
    - ログレベル・ログディレクトリの解決順を実装（引数 > 環境変数 > デフォルト）。
    - ログディレクトリ作成失敗時はファイル出力をスキップし、コンソール出力のみにフォールバック。
    - 既存ハンドラをクリアして二重設定を防止。

- プロセス優先度 & CPU affinity
  - utils/process_priority: psutil を使ってプラットフォーム差分を吸収するユーティリティを追加。
    - set_process_priority(level): Windows / POSIX(nice) 両対応。権限不足等は警告してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数にプロセスをピン留め（権限不足等は警告してスキップ）。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder:
    - select_candidates: スコア降順で候補選定（タイブレーク: signal_rank 昇順）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率で配分。全スコアが 0 の場合は等金額配分にフォールバックして警告。
  - portfolio/risk_adjustment:
    - apply_sector_cap: セクター集中制限（既存ポジションのセクター比率 >= max_sector_pct の場合、そのセクターを候補から除外）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数 ("bull"/"neutral"/"bear") と未知レジームのフォールバック（1.0）を実装。未知レジーム時に警告ログ。
  - portfolio/position_sizing:
    - calc_position_sizes: 資金配分アルゴリズムを実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）で丸め、1銘柄上限や aggregate cap（available_cash）に基づく縮小処理を実装。
    - aggregate 縮小時は切り捨てによる端数を fractional 残差順に lot 単位で追加配分するアルゴリズムを実装（再現性確保のため tie-break に code を使用）。
    - price 欠損や価格 0 のケースはスキップして安全に処理。

- リサーチ（ファクター計算）
  - research/factor_research: モメンタム等ファクター計算の枠組みを実装（DuckDB 接続を受け取り prices_daily / raw_financials を参照）。モメンタム（1M/3M/6M）、MA200 乖離、ATR/VOL/Liquidity の設計方針と定義を含む（実装の一部がファイル末尾で切れているが基盤を追加）。

- ツール
  - tools/paper_verification_report: Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率 / 注文成功率 / 送信率 / レイテンシ（平均・最大・P95）等を算出し、閾値に基づく PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタの WHERE 句生成、DB パス解決（--db / 環境変数 / デフォルト）を実装。
    - 対象テーブルが存在しない場合は例外を捕捉して N/A や 0 で安全に表示。

### 変更（設計上の決定）
- 監視（run_monitoring）は KABUSYS_ENV に依存せず常に本番の monitoring 用 sqlite_path を使用する方針を採用（監視データは環境に依存しない中央管理）。
- ログ出力は stdout を標準出力に使用する（cron / Task Scheduler でのリダイレクトを想定）。

### 修正（堅牢性 / エラーハンドリング）
- .env パース処理でクォート内のバックスラッシュエスケープとインラインコメント処理を適切に扱うよう改善し、誤ったパースを防止。
- logging_setup: ログディレクトリ作成失敗時にアプリケーションが例外で停止しないようフォールバック処理を追加。
- process_priority / set_cpu_affinity: 権限不足や未サポート環境での例外をキャッチして警告ログを出すようにして、安全にスキップする実装。
- run_monitoring / run_execution: 停止フラグ (data/stop_requested.flag) を検知してグレースフルに停止するロジックを追加。ループ内の check_once() 等で例外が起きてもログ出力して次サイクルに継続する実装。

### 既知の制限 / TODO
- position_sizing: price が欠損（0.0）の場合、エクスポージャーや発注量が過少見積もられる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する旨コメントを残しています。
- research/factor_research の一部実装がファイル末尾で切れており、完全な関数実装・テストが必要。
- 一部のコンポーネント（ExecutionEngine、SystemMonitor、BrokerClient 等）は本リリースでの参照実装として呼び出し側に組込まれていますが、その内部実装や例外ハンドリングの詳細は別途テストが必要です。

---

以上が初版の主な変更点です。ドキュメントやユーティリティ（config_setup、validate_config、paper_verification_report）を通じて、開発・検証・本番運用の流れを意識した基盤を整えています。今後のリリースではテスト、監視アラート、さらなる安定化・チューニング、欠損データへのフォールバック実装などを予定しています。