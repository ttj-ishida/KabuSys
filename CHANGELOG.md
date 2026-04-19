Keep a Changelog
=================

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の慣例に準拠しています。

フォーマット
- Unreleased: 今後の変更
- 各リリースは日付付きで記載

Unreleased
---------
- （なし）

[0.1.0] - 2026-04-19
--------------------
Added
- 基本アプリケーション初期リリース。
- 実行用スクリプトを追加:
  - run_execution.py: ExecutionEngine の起動スクリプト。KABUSYS_ENV=paper_trading 時は専用の paper DB を使用し、MockBrokerClient を利用可能にする。スレッド実行・停止フラグ監視・PID ファイル管理を実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止フラグ検知で安全に終了。
- 設定・環境管理:
  - config.py: .env 自動ロード（.env, .env.local）、プロジェクトルート探索、堅牢な .env パース機構、Settings クラスによるプロパティアクセス（各種パス、閾値、モード判定、PAPER_FILL_MODE の検証など）。
  - config_setup.py: 対話式ウィザードで .env を生成/更新する CLI を実装（シークレット入力、既存値の再利用、保存確認）。
  - validate_config.py: 起動前設定検証 CLI。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在/パース検証（PyYAML がある場合）。
- ポートフォリオ構築ライブラリ:
  - portfolio/portfolio_builder.py: 候補選定（スコア降順・タイブレーク）、等金額配分、スコア重み配分（全スコア0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py: セクター集中制限適用（既存ポジションを考慮）、レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear のマッピング、未知レジームはフォールバックと警告）。
  - portfolio/position_sizing.py: 発注株数計算（risk_based / equal / score）、単元株丸め、per-position および aggregate 上限、コストバッファ考慮のスケーリングと残差処理。
  - portfolio/__init__.py で API をエクスポート。
- 監視・実行補助:
  - monitoring.monitoring_db の初期化呼び出し（init_monitoring_db）により監視テーブルの冪等な準備を確保。
  - monitoring.SystemMonitor（run_monitoring から利用）による単回チェック check_once() の呼び出しループを実装（例外を捕捉してログを残し継続）。
- ユーティリティ:
  - utils/logging_setup.py: 一貫したロギング設定ユーティリティ。stdout への StreamHandler と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR / LOG_LEVEL の解決、既存ハンドラのクリア、ファイル出力が失敗した場合のフォールバック対応を実装。
  - utils/process_priority.py: Windows / POSIX を吸収するプロセス優先度設定と CPU affinity 設定。アクセス権限や未サポート環境では警告を出してスキップ。
- 分析 / ツール:
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を解析して Paper Trading の検証レポートを生成するツール。稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均/最大/P95）を算出し PASS/FAIL 判定を出力。日付フィルタ・DB パス指定に対応。
  - research/factor_research.py（骨格実装）: DuckDB を用いたファクター計算モジュール（モメンタム、MA200、ATR、流動性等）を設計。calc_momentum 等の実装開始（DuckDB 接続を受ける設計）。
- パッケージ情報:
  - __init__.py にて __version__ = "0.1.0" を定義。

Changed
- （初期リリースのため該当なし）

Fixed
- ロバストネス向上:
  - MONITOR_POLL_INTERVAL が不正な値の場合にデフォルト値へフォールバックして警告を出す処理を追加（監視ループの異常終了防止）。
  - logging_setup で既存ハンドラを安全に close/flush してから削除することで二重ハンドラ設定を防止。
  - run_monitoring/run_execution で例外や KeyboardInterrupt を捕捉し、必ず DB 接続をクローズするよう finally ブロックで資源解放を保証。
  - config._load_env_file は読み込み失敗時に警告を出して安全に続行。
  - calc_score_weights 全スコア0 の際の等配分フォールバックと警告ログ。
  - calc_position_sizes の aggregate スケーリングで残差処理を行い、lot_size 単位で安定した再分配を行うロジックを導入。

Security
- .env の取り扱いに関する注意喚起を config_setup のヘッダに明記（.env を Git にコミットしないこと）。

Notes / Known limitations
- research/factor_research.py は計算ロジックの一部（calc_momentum の実装途中）や細かい検証が残っているため、ファクター計算の完全実装は今後の作業を要する。
- apply_sector_cap は price_map に欠損（0.0）がある場合にエクスポージャーを過少見積もる可能性があり、将来的にフォールバック価格導入を検討する旨の TODO コメントあり。
- process_priority/set_cpu_affinity はプラットフォームや権限に依存し、失敗した場合は警告を出してスキップする仕様。
- run_execution は BrokerClientFactory や ExecutionEngine の詳細実装に依存。paper_trading と live の切替は Settings による動作判定に依存する。

---

作成された CHANGELOG はコードベースから推測した初期リリース向けのまとめです。実際の変更履歴やコミット履歴がある場合はそれに合わせて日付・カテゴリ・詳細を調整してください。