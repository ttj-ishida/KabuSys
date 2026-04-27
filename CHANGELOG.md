CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従い、日本語で記載しています。

フォーマット:
- 変更は "Added / Changed / Fixed / Security / Deprecated / Removed" のセクションに分類しています。
- 各項目はコードベースの内容から推測して記載しています（実装ファイル: src/kabusys/...）。

Unreleased
----------
- 現在未リリースの変更はありません。

[0.1.0] - 2026-04-27
-------------------

Added
- 初期リリースを追加。
  - パッケージバージョンは src/kabusys/__init__.py の __version__ = "0.1.0"。
- 実行エントリポイント / デーモン起動スクリプトを追加。
  - run_monitoring.py: SystemMonitor のポーリングループ。MONITOR_POLL_INTERVAL（秒）でポーリング間隔を上書き可能（デフォルト 60 秒）。停止は data/stop_requested.flag で検出。監視は環境に関係なく本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、data/paper_trading.db を専用 DB として利用。起動時に総資産（現金＋保有評価額）を計算し、ExecutionEngine をスレッドで実行。停止フラグ検知で安全に停止。
  - run_pre_market_report.py: Pre-Market Report 生成 CLI。--save / --json オプション対応。
- 環境設定関連 CLI / ユーティリティを追加。
  - config_setup.py: 対話式 .env 作成・更新ウィザード（項目定義・既存値の読み込み・保存機能）。
  - validate_config.py: 設定検証 CLI（.env と config/*.yaml の存在・形式・重要な環境変数等を検査）。--strict オプションで警告も失敗扱いにできる。
- 設定管理モジュールを追加。
  - config.py: プロジェクトルート検出に基づく自動 .env ロード（.env → .env.local、OS 環境変数優先）。KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能。.env パースは export 形式、クォート、エスケープ、インラインコメントを考慮。
  - Settings クラス: J-Quants、kabuステーション、LINE、DB パス、PID / Kill flag、閾値類（CPU/MEM/DISK）や環境（development/paper_trading/live）、ログレベル等のプロパティを提供。paper_trading 用の paper_sqlite_path、paper_fill_mode の検証ロジックを含む。
- リスク設定読み込みと検証を追加（run_execution 内）。
  - YAML(risk_config.yaml) の読み込みと、max_position_pct / max_utilization / max_drawdown 等の妥当性チェック（範囲チェック・型変換）。読み込み失敗やキー欠落時には明確な例外を送出。
- データベース関連の初期化・接続処理。
  - sqlite3（監視・注文履歴）および duckdb（分析）接続の使用。監視用 DB スキーマ初期化関数 init_monitoring_db を呼び出して冪等に監視テーブルを保証。
- 報告・レポート生成機能を追加。
  - operations/pre_market_report.py: Pre-Market Report のレポートデータモデル・判定ロジック（READY / READY_WITH_WARNINGS / BLOCKED）、フォーマッター（CLI / JSON / Markdown）および保存ロジックを提供。
  - operations/night_batch_report.py: 夜間バッチ（Night Batch）用のレポート生成、判定ロジック、フォーマッター（CLI / JSON / Markdown）および保存ロジックを提供。必須ジョブリスト（MANDATORY_JOBS）に基づく判定、警告生成ロジックを実装。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト（期間指定オプション --from/--to、DB パスの指定）。稼働率、注文成功率、送信率、P95 レイテンシ等の集計と PASS/FAIL 判定ロジックを実装。
- 実行時ユーティリティを追加。
  - プロセス優先度設定 (set_process_priority) を起動直後に適用（"high"）。
  - PID ファイル・停止フラグ (stop_requested.flag) の取り扱いを各実行スクリプトで採用。
- その他ユーティリティ・ヘルパー
  - 日付フィルター作成、P95 計算、数値フォーマット関数、dataclass ベースのレポート構造などを実装。

Changed
- 監視 DB のアクセス方針: run_monitoring は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計になっていることを明示（監視データは本番 DB を参照）。
- .env 読み込みの優先度と保護:
  - OS 環境変数を保護しつつ .env/.env.local を読み込む。.env.local は override=True（ただし OS 環境変数は protected なので上書き不可）。
- Paper Trading の DB 分離:
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用する。これによりペーパートレードデータは本番 DB と完全分離される。
- ログ出力と CLI の振る舞い:
  - run_pre_market_report は --json 時に保存先メッセージを stderr に出力する等、JSON ストリームを汚染しない配慮を追加。

Fixed
- .env パースの堅牢化:
  - _parse_env_line がクォート文字・バックスラッシュエスケープ・インラインコメント・export プレフィックスに対応し、より安全に .env を読み込めるようになった。
- run_monitoring の MONITOR_POLL_INTERVAL の不正値ハンドリング:
  - 環境変数が不正（数値変換失敗や 0 以下）な場合は警告ログを出してデフォルト（60 秒）にフォールバックする仕様を実装。
- YAML 読み込みのエラーハンドリング強化:
  - risk_config.yaml の読み込み・パース・必須キー欠落時に分かりやすい例外 / ログを出すように改良。

Security
- 特に本リリースで追加されたセキュリティ関連の修正や脆弱性修正はありません。ただし以下の注意点をドキュメント化:
  - .env ファイルは絶対に Git にコミットしないこと（config_setup が警告コメントを挿入）。
  - 本番環境（KABUSYS_ENV=live）では KILL_FLAG_CLEAR_ON_START を 0 にすることを推奨（validate_config で警告）。

Deprecated
- なし。

Removed
- なし。

補足（運用メモ）
- 自動 .env 読み込み:
  - デフォルトでプロジェクトルート（.git または pyproject.toml があるディレクトリ）を起点に .env/.env.local を読み込みます。テスト等で自動ロードを抑制したい場合は環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- Kill / Stop の扱い:
  - 複数スクリプトで data/stop_requested.flag を用いて安全にプロセスを終了する仕組みを採用しています。実際の運用では stop フラグの設置・解除運用を明確にしてください。
- Paper Trading 検証:
  - tools/paper_verification_report.py により、過去期間の稼働率やレイテンシ等を集計して PASS/FAIL 判定ができます。P95 計算や閾値はスクリプト内の定数で定義されています（必要に応じて調整してください）。

---

この CHANGELOG はコードベースから推測して作成しています。実際のリリースノートとして採用する場合は、差分やコミット履歴を参照して内容を精査・補足してください。