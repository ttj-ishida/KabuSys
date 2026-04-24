# Changelog

すべての注目すべき変更点をこのファイルに記録します。本項目は Keep a Changelog の形式に準拠します。  
リリースや機能の追加・修正はここに日本語で要約しています。

フォーマットの約束:
- Unreleased: 今後の変更（現時点では空）
- 各リリースには日付（YYYY-MM-DD）を付与

## [Unreleased]

---

## [0.1.0] - 2026-04-24

初回リリース。以下の主要機能・ユーティリティ・改善を含みます。

### Added（追加）
- コアライブラリの初期実装（KabuSys: 日本株自動売買システムの骨格）
  - パッケージエントリポイントバージョン設定: __version__ = "0.1.0"
- 環境設定/管理
  - Settings クラスによる環境変数ラッパー（J-Quants, kabuステーション, LINE, DBパス, 監視閾値等）
  - .env の自動読み込み機能（プロジェクトルートを自動検出して .env → .env.local の順で読み込み）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化オプション
  - .env の解析強化:
    - export プレフィックス対応（`export KEY=val`）
    - シングル/ダブルクォート内のバックスラッシュエスケープ対応
    - 非クォート値におけるインラインコメント処理（直前が空白/タブの場合のみ）
- 対話式設定ウィザード
  - config_setup.py: .env の対話的生成・更新ウィザード（シークレット入力や選択肢サポート）
  - .env 書き出しテンプレートの追加（書式と注意書き）
- 設定検証ツール
  - validate_config.py: 起動前検証 CLI
    - 必須環境変数チェック（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）
    - KABUSYS_ENV / LOG_LEVEL の妥当性チェック
    - DB パスの親ディレクトリ存在チェック
    - config/*.yaml の存在と（PyYAML があれば）パース検証
    - --strict オプション（警告を FAIL 扱いにして exit(1)）
- 起動スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用し、MockBrokerClient を利用（本番 DB と分離）
    - エンジンを別スレッドで実行、停止フラグ（data/stop_requested.flag）検知で安全停止
    - PID ファイル管理（data/execution.pid）
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
    - 監視は環境にかかわらず本番 sqlite_path を使用（監視用 DB 初期化を保証）
    - 停止フラグ（data/stop_requested.flag）検知でループ終了
- ロギング / プロセス制御ユーティリティ
  - utils.logging_setup.setup_logging
    - コンソール (stdout) と TimedRotatingFileHandler（日次・30日保持）をルートロガーへ設定
    - ログディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソールのみで継続
    - LOG_LEVEL / LOG_DIR の解決順を実装
  - utils.process_priority
    - プラットフォーム差分を吸収してプロセス優先度設定（"high" / "normal" / "low"）
    - CPU affinity 設定ユーティリティ（最初 N コアにピン固定）
    - 実行開始時に run_* スクリプトが優先度を "high" に設定
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder
    - select_candidates: スコア降順で候補選定（signal_rank でタイブレーク）
    - calc_equal_weights / calc_score_weights（スコア全0 の場合は等分配へフォールバック）
  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中上限を超える場合に新規候補を除外（"unknown" セクターは除外対象外）
    - calc_regime_multiplier: market レジームに応じた投下資金乗数（bull/neutral/bear）
  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score に対応した発注株数計算
    - lot_size による丸め、max_position_pct や aggregate cap、cost_buffer を考慮したスケーリングロジック
    - 余剰キャッシュを用いた小数部分の分配アルゴリズム（再現性を保つソート順）
- Paper Trading 検証ツール
  - tools.paper_verification_report: ペーパートレード DB を解析してレポート出力
    - 稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出
    - デフォルト閾値: 稼働率 99.0%, 成立率 90.0%, 送信率 95.0%, P95 レイテンシ 200 ms
    - DB パスはコマンドライン (--db) / 環境変数 PAPER_TRADING_SQLITE_PATH / デフォルトの順で解決

### Changed（変更）
- 設定読み込みの優先順位を明確化（OS 環境 > .env.local > .env）
- run_execution/run_monitoring の起動フロー:
  - 先にプロセス優先度を "high" にセットしてから諸々の初期化を行うよう統一
  - SQLite / DuckDB 接続確保と監視テーブル初期化を起動時に行う（init_monitoring_db を呼び出し、冪等性を確保）
- ログ出力先の標準化: アプリ名に応じたファイル名（logs/<app_name>.log）を採用

### Fixed（修正）
- .env のパースで以下をサポートし、不正な読み込みを低減:
  - export プレフィックス、クォート文字列内のエスケープ、インラインコメントの扱い
- 設定検証ツールで PyYAML 未インストール時に YAML 検証をスキップして警告を出すように改善

### Known issues / Notes（注意点・既知の問題）
- research.factor_research.calc_momentum の実装が途中で切れている（ファイル末尾に未完成の箇所あり）。計算ロジックの続き実装が必要。
- apply_sector_cap 内の価格欠損 (price == 0.0) によるエクスポージャー過小見積り問題は TODO コメントで指摘されており、将来的にフォールバック価格（前日終値等）の導入を検討。
- プロセス優先度 / CPU affinity の設定は OS に依存し、権限不足や未サポート環境では警告を出してスキップする設計になっている（失敗は致命的でない）。
- run_monitoring は明示的に「監視は本番 sqlite_path を使用する」設計になっているため、開発環境で別 DB を使いたい場合は注意が必要。

### Removed（削除）
- 該当なし（初回リリース）

### Security（セキュリティ）
- .env の自動生成テンプレートに「.env は絶対に Git にコミットしないこと」を明記
- シークレット項目はウィザードでマスク表示を行うが、保存先はプレーンテキスト .env のため運用時の管理を推奨

---

今後の予定（例）
- research モジュールのファクター計算の完成（calc_momentum の続き、その他ファクター）
- テスト追加（ユニットテスト / CI）
- broker/engine 周りの詳細実装と paper_trading の挙動検証
- price フォールバック戦略の導入（apply_sector_cap の精度向上）

もし特定の変更点をより詳細に記載したい、別バージョン履歴を分けたい等の希望があれば教えてください。