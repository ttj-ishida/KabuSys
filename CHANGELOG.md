CHANGELOG
=========
すべての注目すべき変更履歴はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
リリース日は、コードベースから推測した日付を使用しています。

[Unreleased]
-------------

- なし

[0.1.0] - 2026-04-17
-------------------

Added
- 初期リリース: KabuSys （日本株自動売買システム）パッケージを追加。
  - パッケージバージョン: 0.1.0 (src/kabusys/__init__.py)
- 環境設定 / ロード
  - Settings クラスを導入し、環境変数経由での各種設定を提供（DBパス、APIキー、閾値など）。
  - .env / .env.local の自動ロード機能を実装（プロジェクトルート自動検出、OS 環境変数の保護、KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能）。
  - .env パーサーは export 付き行、クォート、エスケープ、インラインコメント等を堅牢に処理。
  - 各種設定値のバリデーションを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）。
- 実行・監視スクリプト
  - run_execution: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading のときは専用の paper DB を使用（本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て。
    - エンジンは別スレッドで実行、data/stop_requested.flag により安全停止。
    - PID 書き出しサポート（data/execution.pid）。
  - run_monitoring: SystemMonitor 起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視 DB 初期化（init_monitoring_db）、停止フラグ検出でループ終了。
    - 起動時にプロセス優先度を高く設定（set_process_priority を呼び出し）。
- データベース
  - SQLite と DuckDB を併用する設計を採用（sqlite3 / duckdb 接続ラッパーの利用）。
  - 監視テーブル初期化ユーティリティ（init_monitoring_db）を利用して冪等にセットアップ。
- ポートフォリオ構築（純粋関数群）
  - portfolio_builder: シグナル選定（select_candidates）、等金額／スコア加重の重み計算（calc_equal_weights, calc_score_weights）。
  - risk_adjustment: セクター集中制限の適用（apply_sector_cap）、市場レジームに応じた投下資金乗数（calc_regime_multiplier）。
  - position_sizing: 発注株数決定ロジック（calc_position_sizes）。
    - risk_based / equal / score の割当方式をサポート。
    - 単元株（lot_size）丸め、ポジション上限、aggregate cap（利用可能現金に基づくスケーリング）、コストバッファ考慮。
- 研究（Research）モジュール
  - factor_research: モメンタム・ボラティリティ・バリュー系ファクター計算（calc_momentum, calc_volatility, calc_value）。
    - DuckDB の SQL とウィンドウ関数を活用し、営業日ウィンドウ等を考慮した計算を実装。
  - feature_exploration: 将来リターン計算（calc_forward_returns）、IC（calc_ic）、ファクター統計サマリ（factor_summary）、ランク計算ユーティリティ（rank）。
    - 外部依存を最小化（標準ライブラリのみで実装）。
- AI / ニュース解析
  - news_nlp: raw_news を OpenAI（gpt-4o-mini）でスコアリングするモジュールを追加。
    - タイムウィンドウ計算、記事集約、銘柄バッチ送信（最大 20 銘柄/コール）、JSON 出力の厳密検証。
    - リトライ（429/ネットワーク/5xx）に対する指数バックオフ、スコアの ±1.0 クリップ、部分成功時のテーブル更新保護を考慮。
- ユーティリティ
  - process_priority: プロセス優先度設定（set_process_priority）および CPU affinity 固定（set_cpu_affinity）を追加。Windows / POSIX の差分を吸収し、失敗時は警告でスキップ。
- ツール
  - paper_verification_report: Paper Trading 検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを算出し、閾値判定で PASS/FAIL を表示。
    - 日付フィルタ、DB パス引数（--db）/ 環境変数対応、欠損テーブルへの堅牢性を確保。

Changed
- （初回リリースのため該当なし）

Fixed
- .env 読み込み時のエラーを捕捉して警告を出すように（ファイルアクセス失敗を無視して続行）。
- Settings における環境変数の妥当性チェックを導入し、不正値時に明確なエラーメッセージを返す（例: PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL）。
- run_monitoring と run_execution のプロセス優先度設定で失敗しても起動継続するよう例外処理を実装。

Security
- （本リリースでは特にセキュリティ修正の記載なし）

Notes / Implementation details
- DB
  - 監視データはデフォルト data/monitoring.db（Settings.sqlite_path）、paper_trading は data/paper_trading.db（分離）を使用。
  - DuckDB はファクター計算や AI 集約／分析用の高速クエリエンジンとして利用。
- 停止制御
  - data/stop_requested.flag / data/kill.flag 等のフラグファイルにより外部から安全に停止可能。
- ロギング
  - 起動スクリプトは basic logging を INFO レベルで初期化。詳細は Settings.log_level で制御可能。
- フェイルセーフ設計
  - API 失敗や DB テーブル欠如時に例外でプロセス全体を落とさないよう、個別処理単位での例外ハンドリング・フォールバックを多用している。

今後の予定（推測）
- news_nlp の記事取得処理の続き実装（コード末尾が途中で切れている）。
- Broker クライアントや ExecutionEngine の詳細実装・テスト、運用上の監視アラート・集計強化。
- 単元株・手数料モデルの銘柄別対応や、より細かな lot_size マスタ導入。

---

注: 本 CHANGELOG は提供されたソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと完全に一致しない可能性があります。必要であれば、特定のファイル変更点やコミット単位のより詳細なログを想定して追記します。