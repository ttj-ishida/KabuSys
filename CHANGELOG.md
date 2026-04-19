# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記録しています。  
このファイルはコードの内容から推測して作成した初期の変更履歴です（実装コメント・デフォルト値・CLIの使い方等を元にまとめています）。

フォーマット:
- 追加 (Added)
- 変更 (Changed)
- 修正 (Fixed)
- 廃止 (Deprecated)
- 削除 (Removed)
- セキュリティ (Security)
- 既知の問題 / TODO

---

## [Unreleased]

### Added
- 監視用プロセス起動スクリプト `run_monitoring.py` を追加。
  - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はログ警告のうえデフォルトにフォールバック）。
  - 停止フラグ `data/stop_requested.flag` を検知して安全にループを終了。
  - Monitoring は環境にかかわらず本番の sqlite パスを使用する設計。
  - DuckDB への接続を確立し、監視 DB の初期化を行う。
  - 例外発生時はログ出力して次のポーリングに継続する堅牢性を確保。

- 実行エンジン起動スクリプト `run_execution.py` を追加。
  - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、Paper Trading 用 DB（`data/paper_trading.db` など）に完全分離して記録。
  - 停止フラグ / PID ファイルの取り扱い（`data/stop_requested.flag`, `data/execution.pid`）。
  - エンジンを別スレッドで実行し、停止フラグ検知時に安全停止を行う。

- 設定管理モジュール `kabusys.config` を追加。
  - .env を自動的に読み込む仕組み（プロジェクトルート検出: .git または pyproject.toml）。
  - `.env` のパースはシングル/ダブルクォートや `export KEY=...` 形式、インラインコメントを考慮。
  - `Settings` クラスで環境変数をプロパティとして提供（各種デフォルト値、バリデーションを含む）。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化対応。

- 設定ウィザード CLI `kabusys.config_setup` を追加。
  - `.env` の対話式作成・更新ツール。シークレット項目のマスク表示、デフォルト/既存値の再利用、保存確認機能などを提供。
  - 出力テンプレートは `.env` をそのまま書き出す形式。

- 設定検証 CLI `kabusys.validate_config` を追加。
  - 必須環境変数の存在チェック、`KABUSYS_ENV` / `LOG_LEVEL` の妥当性、DB パスの親ディレクトリ存在チェック、`config/*.yaml` の存在と YAML パース（PyYAML がインストールされていない場合は警告）を実行。
  - `--strict` オプションで警告を FAIL 扱いにできる。

- ポートフォリオ構築関連モジュールを追加（純粋関数群）。
  - `kabusys.portfolio.portfolio_builder`
    - 候補選定 `select_candidates`（スコア降順、同点は signal_rank の昇順でタイブレーク）。
    - 等金額配分 `calc_equal_weights`。
    - スコア加重配分 `calc_score_weights`（全スコアが 0 の場合は等配分にフォールバックして警告）。
  - `kabusys.portfolio.risk_adjustment`
    - セクター集中抑制 `apply_sector_cap`（既存ポジションのセクター比率が閾値を超える場合は同セクターの新規候補を除外、"unknown" セクターは除外対象外）。
    - レジーム乗数 `calc_regime_multiplier`（"bull"=1.0、"neutral"=0.7、"bear"=0.3、未知は 1.0 でフォールバック／警告）。
  - `kabusys.portfolio.position_sizing`
    - 発注株数計算 `calc_position_sizes` を実装（allocation_method: "risk_based" / "equal" / "score"）。
    - 単元株（lot_size）での丸め、1 銘柄上限・aggregate cap に基づくスケーリングと残差処理を行う。
    - cost_buffer を加味した保守的なコスト見積り。

- ユーティリティ群を追加。
  - `kabusys.utils.logging_setup`
    - 共通のログ設定ユーティリティ。コンソール (stdout) と日次ローテーションのファイルハンドラ（logs/<app_name>.log）を設定。既存ハンドラをクリアして二重設定を防止。
    - デフォルト 30 日保持、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで動作。
  - `kabusys.utils.process_priority`
    - Windows / POSIX を吸収するプロセス優先度設定。`set_process_priority("high"|"normal"|"low")` と `set_cpu_affinity` を提供。権限不足や未対応 OS の場合は警告してスキップ。

- 解析ツールを追加。
  - `kabusys.tools.paper_verification_report`
    - Paper Trading 用 SQLite DB から稼働率、注文成功率、送信率、P95 レイテンシなどを集計してレポート出力。閾値（稼働率 99% など）による PASS/FAIL 判定を実装。
    - 日付範囲フィルタ、DB パスの CLI 指定／環境変数対応。

- 研究用モジュール `kabusys.research.factor_research` の骨格を追加。
  - モメンタム、ボラティリティ、バリュー等のファクター計算方針と定数を定義。DuckDB 接続経由で prices_daily / raw_financials を参照して計算する想定。

### Changed
- ログ出力の標準を stdout に統一（cron 等で stdout/stderr を一本化する運用を想定）。
- ログレベル・ログディレクトリ・DB 路径など、多くの設定が環境変数経由で上書き可能に（Settings 経由でアクセス）。

### Fixed
- （該当コードベース内では明示的なバグ修正履歴はなし。実装段階での堅牢性向上として前処理・例外ハンドリングを強化。）

### Known issues / TODO
- position_sizing.py:
  - price が欠損（0.0）の場合、エクスポージャーや発注量が過少見積りされてしまう問題がコメントにて指摘。将来的に前日終値や取得原価を使うフォールバックを検討中。
  - 将来的な拡張として、銘柄ごとの単元（lot_size）を stocks マスタに持たせる案あり（現在は全銘柄共通の lot_size を想定）。
- risk_adjustment.calc_regime_multiplier:
  - 未知レジームは 1.0 でフォールバックするが、運用方針に応じた扱いの再検討が必要。
- research.factor_research:
  - モジュール後半が実装途中（ファイルの最後で処理が中断されているように見える）。ファクター計算ロジックの完成が必要。
- validate_config:
  - PyYAML がない場合、YAML 内容検証をスキップして警告を出す仕様（本番デプロイ前に PyYAML の導入を推奨）。
- run_monitoring / run_execution:
  - 停止フラグや PID の取り扱いは実装済みだが、複数プロセス運用時の競合条件や権限周りのテストが必要。
- logging_setup:
  - ログディレクトリ作成に失敗した場合はファイル出力を無効化する仕様。ディスク権限による影響に注意。

---

## [0.1.0] - 2026-04-19

初回リリース想定（コードベースのバージョン: __version__ = "0.1.0"）

### Added
- コア機能の実装（上記 Unreleased に記載の主要機能群を初期実装）。
  - 実行 / 監視スクリプト、設定・ウィザード・検証ツール、ポートフォリオ構築・リスク調整・ポジションサイジング関数、ログ・プロセスユーティリティ、Paper Trading 検証レポート生成ツール、研究用ファクター計算モジュールの骨格。
- デフォルト設定・環境変数のドキュメント（コード内 docstring / comments）。

### Changed
- プロジェクトルート自動検出を実装（.env の自動ロードに利用）。
- ログ設定を統一化（アプリ名ごとの日次ローテーションログを導入）。

### Fixed
- 起動時のプロセス優先度設定やポーリング間隔の不正値処理など、堅牢性に関する基本的なエラーハンドリングを実装。

---

注意:
- この CHANGELOG はコードのコメント・デフォルト値・実装から推測して作成しています。実際のコミット履歴やリリースノートに基づくものではないため、細かな追加・変更点はリポジトリの履歴（git log）と合わせて確認してください。