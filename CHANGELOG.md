# CHANGELOG

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。

## [0.1.0] - 2026-04-25
初回リリース。

### 追加
- 実行エントリ・監視エントリ
  - run_execution.py: ExecutionEngine を起動する起動スクリプトを追加。KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用する（data/paper_trading.db、PAPER_TRADING_SQLITE_PATH で上書き可能）。停止フラグ / PID 管理 / スレッド駆動での実行管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用する設計。
- 設定・環境管理
  - config.py: 環境変数ラッパー Settings を実装。.env の自動ロード（プロジェクトルート検出を行い .env/.env.local を順に読み込む）・値検証（KABUSYS_ENV, LOG_LEVEL など）を提供。Paper Trading 用設定（PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH 等）をサポート。
  - config_setup.py: 対話式 .env ウィザードを追加。よく使う設定項目の入力補助、既存 .env の読み込み・更新、保存機能を提供。
  - validate_config.py: 起動前の設定検証 CLI を追加。必須環境変数・パス・config/*.yaml の存在・YAML パース（PyYAML がインストールされている場合）・本番環境向けの安全ガード等をチェック。--strict オプションで警告を失敗扱いにできる。
- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: シグナル選定（select_candidates）と重み計算（calc_equal_weights, calc_score_weights）を実装。
  - portfolio.risk_adjustment: セクター集中制限適用関数 apply_sector_cap と、市況レジームに応じた乗数 calc_regime_multiplier を実装。
  - portfolio.position_sizing: 株数決定ロジック calc_position_sizes を実装（risk_based / equal / score の割当方式、単元株丸め、aggregate cap スケーリング、cost_buffer を考慮）。
  - portfolio パッケージで上記機能をエクスポート。
- ユーティリティ
  - utils.logging_setup: ルートロガーの初期化ユーティリティを追加。コンソール(stdout)出力と日次ローテーションのファイル出力を設定。LOG_DIR/LOG_LEVEL の優先順位に対応し、ファイルハンドラ作成失敗時はコンソール出力のみで継続する。
  - utils.process_priority: プロセス優先度（および CPU affinity）をクロスプラットフォームで設定するユーティリティを追加。Windows/Linux/macOS を考慮し、権限不足等の失敗は警告でスキップ。
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード用 SQLite を参照してシステム安定性、注文成功率、送信率、レイテンシ等を集計・レポート出力するコマンドラインツールを追加。P95 計算・閾値判定に基づく PASS/FAIL 判定を実装。
- リサーチ（部分実装）
  - research.factor_research: Momentum 等のファクター計算モジュールを追加（DuckDB 接続を受け取り prices_daily/raw_financials を参照する設計）。モメンタム計算の設計と定数を整備。※ファイル末尾で実装が未完（トランケートあり）。

### 変更（設計・挙動）
- DB 分離ポリシーを明示
  - 監視（monitoring）データは環境にかかわらず本番 sqlite_path を使用する方針を明記。
  - Execution は paper_trading 環境であれば専用の paper_sqlite_path を使用し、本番 DB と完全分離する設計に。
- ログ挙動
  - ログは標準で stdout に出力するようにし（cron 等からのリダイレクト時に扱いやすくするため）、ファイル出力は日次ローテーションで 30 世代保持。
- 環境変数読み込みの挙動改善
  - .env パーサは export プレフィックス対応、クォート内のエスケープ処理対応、行内コメントの扱い、override/protected オプションなどを実装。OS 環境変数を保護して .env.local で上書き可能にする。

### 修正（バグ修正・堅牢化）
- run_monitoring のポーリング周期取得で不正値対策を実装
  - MONITOR_POLL_INTERVAL が整数でない、または 0 以下のときにデフォルト（60 秒）へフォールバックし、警告を出すようにした（time.sleep に渡す ValueError を防止）。
- process_priority / cpu_affinity のエラー耐性を強化
  - 権限不足や未対応 OS で例外を上げず警告でスキップするようにして起動安定性を向上。
- logging_setup のログディレクトリ作成失敗時のフォールバック
  - ディレクトリ作成に失敗してもコンソール出力で継続し、ユーザーへ警告を出すようにした。
- CLI ツールのエラー耐性（DB スキーマ不在時）
  - paper_verification_report ではテーブルが存在しない場合に安全に N/A や 0 を扱うようにし、OperationalError を捕捉してレポート生成を継続する。

### 既知の問題
- research.factor_research の一部実装がトランケートされており、完全なファクター計算ロジックは未完。今後のリリースで実装を続行予定。
- position_sizing の price フォールバック未実装
  - risk_adjustment.apply_sector_cap 内で price が 0.0 の場合にエクスポージャーが過小見積りされる旨の TODO が残っている。前日終値等のフォールバック実装は将来の改善候補。

### セキュリティ
- 本リリースでは機密情報（API トークン・パスワード）を .env に保存する設計を取っているため、.env を絶対に Git にコミットしないよう README/コメントで注意喚起済み。

---

将来的なリリースでは、research の完了、単体テスト・統合テストの追加、設定検証の拡張（より詳細な config/*.yaml 検証）、および運用上の監視／通知（LINE 等）統合の強化を予定しています。