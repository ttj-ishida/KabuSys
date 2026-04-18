CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従っています。  
安定版リリース／機能概要はコードベースから推測して記載しています。

フォーマット:
- 追加: 新規追加された機能や公開 API
- 変更: 既存挙動の変更（後方互換性に注意）
- 修正: バグ修正や堅牢化
- 注意: 実装上の制限や既知の挙動

[Unreleased]
------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-18
-------------------

追加
- 基本アプリケーションパッケージを初期導入
  - パッケージメタ情報: kabusys/__init__.py に __version__ = "0.1.0"
- 実行エントリスクリプト
  - run_execution.py: ExecutionEngine 起動スクリプト。KABUSYS_ENV に応じて paper_trading 用 DB を分離し、BrokerClientFactory により適切なブローカークライアントを生成。Daemon スレッドでエンジンを実行、停止フラグ (data/stop_requested.flag) を監視して安全停止。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境にかかわらず本番 sqlite_path を使用。
- 設定関連ユーティリティ
  - config.py: 環境変数・.env 自動読み込み、.env パースロジック（export 形式・クォート内のエスケープ・インラインコメント考慮）を実装。Settings クラスを提供（各種環境変数のアクセサ、Paper Trading 用設定を含む）。
  - config_setup.py: 対話式 .env 作成ウィザード（項目定義、既存 .env 読み込み、保存機能）。
  - validate_config.py: 起動前検証 CLI。必須/任意環境変数、DB パス、config/*.yaml の存在/パース（PyYAML あれば検証）や本番（live）向けガードチェックを実装。--strict オプションで警告を FAIL 扱いにできる。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py: 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights)。
  - portfolio/risk_adjustment.py: セクター集中制限適用 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier)。
  - portfolio/position_sizing.py: 発注株数決定ロジック（risk_based / equal / score）、単元株丸め、aggregate cap によるスケールダウン、手数料・スリッページのバッファ考慮。
  - portfolio/__init__.py: 上記関数群の公開インターフェースをエクスポート。
- 実行系サポートコンポーネント（雛形/参照実装）
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティ。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみ継続。
  - utils/process_priority.py: Windows/Linux/macOS でのプロセス優先度設定（nice / Windows priority クラス）および CPU affinity 設定ユーティリティ。権限不足や未対応 OS 時は警告してスキップ。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプト。system_status / trade_logs / risk_logs から稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定を出力。デフォルト DB は data/paper_trading.db、--db 指定や PAPER_TRADING_SQLITE_PATH 環境変数に対応。
- モニタリング DB 初期化フック
  - monitoring.monitoring_db.init_monitoring_db の呼び出しにより、実行時に監視テーブルの存在を保証（冪等）。
- リサーチ（骨組み）
  - research/factor_research.py: ファクター計算モジュールの骨格（モメンタム / MA / ATR / 出来高系の定義と計算方針）。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計（実装途中の関数あり）。

変更
- .env 自動ロードの挙動を明示
  - OS 環境変数が優先され、.env.local は .env の上書きとして適用。KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
- DB/環境分離ポリシー
  - ExecutionEngine は KABUSYS_ENV=paper_trading の場合に専用 paper_trading DB を使用し、本番 DB とのデータ分離を保証。

修正 / 堅牢化
- 環境値の検証とフォールバック
  - MONITOR_POLL_INTERVAL: 環境変数が不正（非整数または <= 0）の場合、警告を出してデフォルト 60 秒にフォールバック。
  - PAPER_FILL_MODE: 想定外の値は ValueError で明示的に拒否し、安全なデフォルト（"instant"）を保持。
  - logging_setup: ログディレクトリ作成失敗時はファイルハンドラ作成をスキップし、コンソール出力を継続するよう堅牢化。
  - process_priority / set_cpu_affinity: 権限不足や未実装 API 呼び出し失敗時に警告ログを出して処理を続行する（例: psutil.AccessDenied 等のハンドリング）。
- run_execution/run_monitoring の安全停止
  - data/stop_requested.flag を検知してループ/エンジンを停止する仕組みを実装。起動前にフラグが立っている場合は起動を中止。
  - run_execution は PID ファイル管理（data/execution.pid）および max join timeout を用いた安全な終了待ち。
- Paper Trading 検証ロジックの分離
  - tools/paper_verification_report は DB が存在しない場合にユーザへ明確にエラーを表示し、誤った DB を参照しないよう保護。
- validate_config の強化
  - 必須環境変数の未設定・プレースホルダ検出・YAML パース失敗の検出と適切なメッセージ出力。KABUSYS_ENV=live の場合の追加警告（LINE 通知未設定や KILL_FLAG_CLEAR_ON_START の危険性）。

注意（既知の制限）
- research/factor_research.py は計算ロジックの骨格があるものの、一部関数（例: calc_momentum の実装途中）や最終出力整形が未完。DuckDB スキーマに依存するため、実用化には prices_daily / raw_financials のスキーマ確認が必要。
- position_sizing の lot_size 現状は全銘柄共通の想定（将来的に銘柄別 lot_map を想定した拡張が必要）。
- apply_sector_cap は "unknown" セクターの取り扱いで上限を適用しない仕様。price が 0.0 のケースは将来的にフォールバック価格導入を検討。
- ログのファイル出力はログディレクトリ作成に成功した場合のみ有効。権限やファイルシステム問題で作成失敗する環境ではコンソール出力のみとなる。

セキュリティ
- .env は生成時に「絶対に Git にコミットしないこと」と明記。secret な項目は対話式 UI でマスクして表示。

今後の検討 / TODO
- research モジュールの完成（ファクター計算の SQL 実装、出力の正規化）
- Strategy / Execution モジュールのテストカバレッジ拡充（特にリスク管理・リコンシリエーション）
- 銘柄別 lot_size のサポート（stocks マスタとの連携）
- より詳細なログローテーション設定やログ送信（外部ログ集約）対応

--- 

注: 本 CHANGELOG は提供されたソースコードから推測して作成しています。実際のリリースノート／履歴はコミット履歴やリリース工程に基づいて調整してください。