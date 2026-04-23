CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」規約に準拠しています。

フォーマット:
- Unreleased: 今後の変更（空欄）
- 各バージョンは日付付きで記載

Unreleased
----------

（なし）

[0.1.0] - 2026-04-23
-------------------

Added
- 初期リリースを追加。
- 全体
  - パッケージ初期バージョンを 0.1.0 に設定。
  - プロジェクトルート検出ロジックを実装（.git または pyproject.toml を探索）。
  - .env 自動ロード機能を実装（.env / .env.local を OS 環境変数を保護しつつ読み込み）。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動読み込みを無効化可能。
  - Settings クラスを実装し、環境変数の取得・簡易検証（KABUSYS_ENV・LOG_LEVEL 等）や便利プロパティ（duckdb/sqlite パス、paper_trading 判定など）を提供。
- 実行・監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用し、本番 DB と分離。停止フラグ（data/stop_requested.flag）検出機構と実行 PID 管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。Monitoring は環境に依らず本番 sqlite_path を使用する設計。
- 設定関連 CLI
  - config_setup.py: 対話式ウィザードで .env を初期作成／更新する CLI を追加。秘密値はマスク表示、既存 .env の読み込み・再利用対応、保存確認を実装。
  - validate_config.py: 起動前設定検証用 CLI を追加。必須環境変数やパス、config/*.yaml の存在・パースチェック（PyYAML があれば内容検証を実行）、KABUSYS_ENV=live 時の追加注意チェック、--strict モードを実装。
- ロギング
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次、30 日分保持）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。
- プロセス制御ユーティリティ
  - utils/process_priority.py: プラットフォームに依らないプロセス優先度設定（high/normal/low）を実装。Windows / POSIX(nice) の差分吸収。CPU affinity 設定関数 set_cpu_affinity を提供。権限不足等の例外は警告にフォールバック。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定（スコア降順）、等金額配分、スコア重み配分（全スコア 0 の場合等金額にフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに基づく資金乗数（calc_regime_multiplier）を実装。unknown セクターの扱い、未知レジームのフォールバック挙動を定義。
  - portfolio/position_sizing.py: 株数決定ロジック（allocation_method: risk_based / equal / score）を実装。単元株（lot_size）丸め、1 銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）、cost_buffer による保守的コスト見積り、残差に基づく端数処理を反映。
  - portfolio/__init__.py: 上記機能を公開 API としてまとめてエクスポート。
- ツール
  - tools/paper_verification_report.py: ペーパートレード結果検証レポート生成ツールを追加。指定期間（--from/--to）で system_status / trade_logs / risk_logs 等を集計して稼働率、注文成功率、送信率、P95 レイテンシなどを算出し PASS/FAIL 判定（閾値はソース内で定義）するレポートを出力。DB パスはコマンド引数、環境変数（PAPER_TRADING_SQLITE_PATH）、デフォルトの順に解決。
- 監視・実行関連基盤
  - monitoring.monitoring_db.init_monitoring_db の呼出しを導入し、監視テーブルの存在を保証（冪等）。
  - execution 側で BrokerClientFactory を利用し、paper_trading 時は MockBrokerClient を用いる設計（実装は別モジュール）。
- 研究（ファクター）基盤（未完）
  - research/factor_research.py を追加。モメンタム等のファクター計算を行う設計に着手（DuckDB 接続を受け prices_daily / raw_financials を参照する想定）。一部実装（定数等）を含むが、ファイル末尾で処理が途中で切れている（今後拡張の余地あり）。

Changed
- 初期リリースのため、変更履歴はなし。

Fixed
- 初期リリースのため、修正履歴はなし。

Notes / 実装上の注意
- .env パーサはクォート内のバックスラッシュエスケープやインラインコメント処理を考慮した手作り実装。複雑なケースでは想定外の挙動になる可能性があるため注意。
- Settings.paper_fill_mode は許容値（instant / partial / never / reject）を検証し、不正値なら ValueError を送出する。
- run_monitoring の MONITOR_POLL_INTERVAL は不正値（非整数や 0 以下）であればデフォルト（60 秒）にフォールバックして警告を出す。
- ロギングは stdout を使用する設計（cron 等で stdout/stderr を一本化しやすくするため）。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で動作しない場合、警告を出してスキップする。
- paper_verification_report の閾値（稼働率/成功率/レイテンシ等）はソース内定数で定義されており、必要に応じて調整可能。

今後の予定（例）
- factor_research の完全実装（calc_momentum 等の完成）。
- ExecutionEngine / BrokerClient の詳細実装と単体テスト強化。
- YAML 設定ファイルのスキーマ検証導入（validate_config の拡張）。
- e2e テストと CI の追加。

-----