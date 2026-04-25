CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを採用します。

## [0.1.0] - 2026-04-25

### 追加 (Added)
- 基本リリース: KabuSys v0.1.0 を初版公開。
- 実行スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。プロセス優先度を起動時に "high" に設定。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 専用 SQLite（data/paper_trading.db、環境変数で上書き可）を使用し、本番 DB と完全に分離して発注のモック処理が可能。
    - BrokerClientFactory を利用してブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立て、ExecutionEngine を別スレッドで実行する監視ロジックを実装。
    - data/execution.pid を PID ファイルとして使用し、data/stop_requested.flag により外部から安全に停止できる仕組みを実装。

  - run_monitoring.py
    - SystemMonitor ポーリングループ起動スクリプトを追加。起動時にプロセス優先度を "high" に設定。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値や 0 以下はデフォルトにフォールバックして警告を出力。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する挙動（監視用 DB の一貫性確保）。
    - stop flag (data/stop_requested.flag) を検知してループを終了する安全停止機構を実装。

- 設定関連
  - config.py
    - プロジェクトルートの検出 (_find_project_root) を実装し、.env/.env.local の自動読み込み機構を導入（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースロジックを強化（export KEY=val 形式対応、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いの改善）。
    - Settings クラスを導入し、環境変数のプロパティアクセス・型変換・バリデーションを提供。
    - 設定項目を多く追加・整備（DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PAPER_FILL_MODE の検証、PID/kill flag 関連、CPU/MEM/DISK 閾値、env/log_level 判定ユーティリティ等）。

  - config_setup.py
    - 対話式ウィザードで .env を生成・更新する CLI を追加。秘密項目のマスク表示、選択肢・デフォルトのサポート、.env テンプレートの書き出しを提供。
    - .env に関する注意書き（Git へコミットしないこと）を同梱。

  - validate_config.py
    - 起動前に環境変数や config/*.yaml の設定不備を検出する検証 CLI を追加。
    - 必須／任意環境変数チェック、KABUSYS_ENV／LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、YAML ファイルの存在・パース検証（PyYAML 未インストール時は警告）等を実装。
    - --strict モードを追加（警告も失敗扱いで exit(1)）。

- ユーティリティ
  - utils/logging_setup.py
    - 統一的なログ設定ユーティリティを追加。stdout への StreamHandler と日次ローテーション（TimedRotatingFileHandler）を組み合わせて root ロガーを設定。既存ハンドラをクリアして二重設定を防止。
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップし、コンソール出力のみで継続。

  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定機能を追加（Windows/Linux/macOS 等を吸収）。psutil を用いて nice 値や優先度クラスを設定。CPU affinity 設定用の set_cpu_affinity を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にフォールバック。

- ポートフォリオ構築モジュール（純粋関数群）
  - kabusys.portfolio
    - portfolio_builder.py
      - select_candidates（スコア降順、タイブレーク時に signal_rank）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等金額へフォールバック）を実装。
    - risk_adjustment.py
      - apply_sector_cap（既存ポジションによるセクター集中制限を適用し、新規候補を除外）、calc_regime_multiplier（regime に応じた資金乗数を返す。unknown は警告して 1.0 フォールバック）を実装。
    - position_sizing.py
      - calc_position_sizes を実装。allocation_method に応じて risk_based / equal / score をサポート。
      - 単元株（lot_size）丸め、per-stock 上限(max_position_pct)、aggregate cap（available_cash）超過時のスケーリングおよび残差に基づく再配分ロジックを実装。cost_buffer により手数料／スリッページを保守的に見積もる。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite データベースから稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）などを集計してレポート出力する CLI を追加。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義し PASS/FAIL を出力。テーブルが存在しない場合は安全に N/A 扱いで処理。

- research/factor_research.py（骨格）
  - DuckDB を使ったファクター計算モジュールを追加（Momentum, Value, Volatility, Liquidity 計算の方針を実装予定）。calc_momentum の実装開始（スキャン日数定数等を定義）。

### 変更 (Changed)
- ロギング
  - 全体で logging の初期化を統一するユーティリティを導入し、起動スクリプトは setup_logging を呼ぶよう変更。デフォルトで stdout を使用するため cron 等でのリダイレクトに適するようにした。
- DB 接続
  - 監視系（monitoring）は KABUSYS_ENV に依存せず production sqlite_path を使用する方針に明確化（監視情報の一貫性維持）。
  - run_execution は paper_trading 環境では paper_sqlite_path を使用するようにして本番 DB との分離を強化。
- .env 読み込み順序
  - 自動ロード優先順位を OS 環境変数 > .env.local > .env に変更（既存 OS 環境変数を保護）。.env.local は .env を上書き可能。
- エラーハンドリング
  - run_monitoring の polling loop 内で monitor.check_once() が例外を投げてもログに exception を残して次回ポーリングへ継続するようにした（監視の頑健化）。
  - run_execution はエンジンスレッド実行中に停止フラグを検知した場合に engine.stop() を呼んで安全停止するフローを追加。

### 修正 (Fixed)
- MONITOR_POLL_INTERVAL のパースで不正値（非整数や 0/負数）が与えられた場合に ValueError を避けるためデフォルトへフォールバックし、警告ログを出力するようにした（run_monitoring）。
- logging_setup: 既存ハンドラの flush/close を試みてから削除するようにして、ハンドラ二重登録やハンドラリークを防止。
- process_priority: 未対応プラットフォームや権限不足時に例外で停止させず警告ログを出してスキップするよう改善。

### ドキュメント・注意事項 (Notes)
- .env ファイルは機密情報を含むため絶対に Git 等にコミットしないこと（config_setup のヘッダに注意文あり）。
- validate_config により本番環境（KABUSYS_ENV=live）では LINE 通知設定や kill flag の自動クリア設定を重点的にチェックするため、運用前に必ず検証を推奨。
- Paper Trading と本番（live）は DB を分離する設計のため、paper_trading 実行時でも誤って本番 DB を更新しないことを保証する構成になっている。
- position_sizing の現状実装は単元株（lot_size）を全銘柄共通で扱う。将来的に銘柄別 lot_size を導入する余地あり（TODO コメントあり）。
- research モジュールはファクター計算の方針と一部実装を含むが、完全実装・テストについては継続作業が必要。

---

今後のリリースでは以下を予定しています:
- research/factor_research の完全実装とテストカバレッジ追加
- 戻り値・エラーケースのユニットテスト強化
- 実行エンジンの運転ログ・メトリクスの拡張（可観測性向上）
- 銘柄別 lot_size 対応などポートフォリオモジュールの細部改善

(終)