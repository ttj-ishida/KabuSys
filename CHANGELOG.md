# CHANGELOG

すべての重要な変更を記録します。フォーマットは Keep a Changelog に準拠しています。

注: 以下の履歴は提示されたコードベースの実装内容から推測して作成したものであり、実際のコミット履歴とは異なる場合があります。

## [Unreleased]

- ドキュメント・テスト向けの小さな改善や文言修正を予定。

---

## [0.1.0] - 2026-04-19

初回リリース — 基本的な自動売買フレームワークのコア機能を実装。

### Added
- 実行／監視のエントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）と完全分離して動作する。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番用 sqlite_path を使用する設計。

- 環境設定／検証ツール
  - config_setup.py: 対話式 .env 作成・更新ウィザードを追加（秘密値はマスク表示、.env を上書き保存）。
  - validate_config.py: 起動前検証 CLI を追加（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml 存在チェック、live 環境向けガード等）。--strict オプションで警告を FAIL 扱いにできる。

- 設定管理
  - config.py: .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）、.env パースの堅牢化（export 構文、クォート内エスケープ、インラインコメント処理等）、Settings クラス（各種環境変数の getter / バリデーション）を実装。PAPER_FILL_MODE の有効値検証や env/log level の検証ロジックを含む。

- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等分配/スコア加重の重み計算 (calc_equal_weights / calc_score_weights) を実装。スコア全ゼロ時のフォールバック挙動あり。
  - portfolio/risk_adjustment.py: セクター集中制限の適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。未知レジームのフォールバックやログ出力あり。
  - portfolio/position_sizing.py: 発注株数決定ロジックを実装（risk_based / equal / score 手法対応、単元株丸め、per-position 上限、aggregate cap によるスケールダウン、cost_buffer による保守的見積り、残差処理の再配分アルゴリズム）。lot_size 固定だが将来的拡張を想定した TODO コメントあり。
  - portfolio パッケージのエクスポートを整備。

- ロギング／プロセス制御ユーティリティ
  - utils/logging_setup.py: ルートロガーの一元設定ユーティリティを追加。StreamHandler（stdout）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリ自動作成とフォールバックの挙動を明記（作成失敗時はコンソールのみ）。
  - utils/process_priority.py: Windows/Linux/macOS を透過するプロセス優先度設定（set_process_priority）および CPU affinity 設定（set_cpu_affinity）を実装。アクセス権限不足や未対応 OS の場合は警告を出してスキップ。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite DB から稼働率・注文成功率・送信率・レイテンシ等を集計して人間向けレポートを出力するスクリプトを追加。期間フィルタ、P95 計算、閾値比較（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）に基づく PASS/FAIL 判定を提供。

- 研究（ファクター計算）モジュール（実装開始）
  - research/factor_research.py: DuckDB 接続を用いたファクター計算モジュールの骨組み（モメンタム・MA・ATR 等）を追加。価格テーブル参照により日付基準で多数のファクターを算出する設計。注釈に設計方針・定数を記載（実装途中ファイルの一部が提示）。

### Changed
- ログ出力の標準化
  - ログは stdout に出力するよう統一（cron 等で stdout/stderr をまとめてリダイレクトしやすくするため）。

- 起動スクリプトのプロセス初動
  - run_execution/run_monitoring は起動直後にプロセス優先度を "high" に設定するよう共通化（set_process_priority 呼び出し）。

- DB パス／環境の扱い
  - 実行エンジンは KABUSYS_ENV に応じて paper_trading 用 DB と本番 DB を選択する（分離）。一方、監視は環境にかかわらず本番 sqlite_path を使用することを明記。

### Fixed / Robustness improvements
- .env パーサーの堅牢化（config.py）
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ処理、インラインコメントの扱いなどに対応し、実運用での多様な .env 記述に耐えるよう改善。

- ログディレクトリ作成失敗時のフォールバック（logging_setup.py）
  - ディレクトリ作成失敗時はファイルハンドラをスキップしてコンソールのみで動作するように変更。ハンドラの二重設定を防ぐため既存ハンドラのクローズ/削除処理を追加。

- プロセス優先度設定の例外処理（process_priority.py）
  - 権限不足や未実装メソッドに対して警告を出して処理を継続するように修正し、クロスプラットフォームでの安全性を向上。

- run_monitoring のポーリング間隔設定の堅牢化
  - 環境変数 MONITOR_POLL_INTERVAL の不正値（0、負数、非整数）を検出してデフォルトにフォールバックするログ出力を追加。

- 各種 DB 初期化の防御的実装
  - init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。run_execution は paper_trading モードでも監視テーブルが存在することを保証するために呼び出す。

### Notes / Implementation details
- 多くのモジュールは「外部 API への直接アクセスなし」に設計されており、本番取引ロジックと分析・テスト用ロジックを分離する方針が取られている（例: research は DuckDB の価格テーブルのみ参照、paper_trading では専用 SQLite を使用）。
- 設定自動読み込みは、プロジェクトルート検出に失敗した場合や KABUSYS_DISABLE_AUTO_ENV_LOAD が設定されている場合はスキップされる。
- Portfolio や Position sizing のアルゴリズムはドキュメント（PortfolioConstruction.md, StrategyModel.md 等）に基づく旨の注釈があり、将来的な拡張（銘柄別 lot_size、フォールバック価格など）に備えた TODO コメントが含まれている。
- research/factor_research.py はファイル末尾で実装途上に見える箇所があるため、ファクター計算の完全実装は今後の作業が必要。

### Security
- 初期リリースでは特にセキュリティ修正は記録なし。環境変数にトークン/パスワードを保持するため .env の取り扱い（絶対に Git にコミットしない等）を README に明記することを推奨。

---

将来的にはリリースごとに実際のコミット・チケットに基づいて CHANGELOG を更新してください。必要であれば、各ファイルごとの詳細な変更点や懸念点（例えば position_sizing の価格欠損時の挙動や paper_trading の検証閾値の調整提案など）についても追記できます。必要であればその点も反映して更新します。