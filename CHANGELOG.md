CHANGELOG
=========

この CHANGELOG は "Keep a Changelog" の形式に準拠しています。  
コードの内容から推測して記載しています（実際の変更履歴が存在する場合は差異が生じる可能性があります）。

フォーマットの説明:
- Added: 新機能・新規追加
- Changed: 既存機能の変更・振る舞いの更新
- Fixed: バグ修正（推測）
- Removed: 削除（該当なしの場合は記載しません）

[0.1.0] - 2026-04-24
--------------------

Added
- 基本アプリケーション構成と起動スクリプトを追加
  - 実行エンジン起動スクリプト (src/kabusys/run_execution.py)
  - 監視ループ起動スクリプト (src/kabusys/run_monitoring.py)
  - モジュールエントリポイントや __version__ を追加 (src/kabusys/__init__.py)
- 環境設定・管理関連
  - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）
    - DB パス、API トークン、環境種別、ログレベル、監視しきい値等のプロパティを提供
    - PAPER_FILL_MODE, PAPER_TRADING_SQLITE_PATH など Paper Trading 向け設定をサポート
  - 自動 .env ロード機能を追加（プロジェクトルート判定、.env / .env.local 読み込みを実施）
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードの無効化が可能
  - .env ファイル読み書き・対話式ウィザードを追加（src/kabusys/config_setup.py）
    - .env の初期作成・更新を対話式で実施可能
    - シークレット値のマスク表示、デフォルト・選択肢対応などを実装
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML 必須）など
    - --strict モードで警告を失敗扱いにするオプションを提供
- ログ関連ユーティリティを追加（src/kabusys/utils/logging_setup.py）
  - stdout 出力（StreamHandler）と日次ローテートファイル出力（TimedRotatingFileHandler）をルートロガーに設定
  - ログ出力先ディレクトリ自動作成、環境変数/引数による上書き対応、失敗時のフォールバック挙動を実装
- プロセス制御ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - プロセス優先度（high/normal/low）設定を Windows/Linux/macOS 向けに抽象化
  - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装
  - 権限不足や未対応 OS の場合は安全にスキップするフォールバックを実装
- Execution / Monitoring の実装上の統合
  - ExecutionEngine 用の組み立てロジック（BrokerClientFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等の利用）を追加（src/kabusys/run_execution.py）
    - Paper Trading 環境時は専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離
  - Monitoring は本番 sqlite_path を環境に関係なく使用（src/kabusys/run_monitoring.py）
    - 簡易な停止フラグ（data/stop_requested.flag）検知によりループを終了
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）
- ポートフォリオ構築の純粋関数群を追加（src/kabusys/portfolio/**）
  - 候補選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）
  - セクター集中制限（apply_sector_cap）とレジームに基づく乗数（calc_regime_multiplier）
  - 位置サイズ算出（calc_position_sizes） — リスクベース、等配分、スコア配分、単元株丸め、aggregate cap の縮小ロジック等を実装
- 研究（リサーチ）モジュール（部分実装）を追加（src/kabusys/research/factor_research.py）
  - Momentum / MA200 等を計算する設計（DuckDB 経由で prices_daily 等を参照する設計方針）
  - P95 計算など分析ユーティリティを実装（paper_verification_report で利用するロジックと整合）
- Paper Trading 検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）
  - SQLite（Paper Trading DB）から各種指標（稼働率、注文成功率、送信率、レイテンシ P95 等）を集計して標準出力レポートを生成
  - デフォルト閾値（稼働率 99%、成功率 90%、送信率 95%、P95 レイテンシ 200ms）に基づき PASS/FAIL を判定
  - コマンドライン引数 --from / --to / --db を提供

Changed
- 監視と実行のデータベース取り扱いを明確化
  - 監視プロセスは環境（KABUSYS_ENV）に関係なく Settings.sqlite_path（本番監視 DB）を使用するようになっている（src/kabusys/run_monitoring.py）
  - 実行プロセスは settings.is_paper の判定により paper_sqlite_path を使用する（src/kabusys/run_execution.py）
- .env パースの堅牢化（src/kabusys/config.py）
  - export KEY=val 形式のサポート、シングル/ダブルクォート内部のバックスラッシュエスケープ処理、インラインコメント処理を追加
  - .env.local を .env の上から上書き（OS 環境変数は保護）する優先順位を実装
- ログ設定の動作安定化（src/kabusys/utils/logging_setup.py）
  - 既存ハンドラの flush/close と除去を行い二重登録を防止
  - stdout を使うことで Task Scheduler / cron とのリダイレクト運用を考慮
- プロセス優先度設定は権限不足や未対応環境の場合に警告を出してスキップするよう変更（src/kabusys/utils/process_priority.py）

Fixed (推測)
- 監視・実行スクリプトの終了処理で DB コネクションが確実にクローズされるように try/finally を使用して安全性を向上（src/kabusys/run_monitoring.py, src/kabusys/run_execution.py）
- Paper レポートの P95 算出や NULL 値時の出力が N/A となるようフォールバックを追加（src/kabusys/tools/paper_verification_report.py）

Potential breaking changes / 注意点
- Monitoring の挙動: run_monitoring は KABUSYS_ENV にかかわらず settings.sqlite_path（本番用の監視 DB）を使用するため、paper_trading 環境で混在させたくない場合は設定に注意してください。（src/kabusys/run_monitoring.py）
- 自動 .env ロード: プロジェクトルートが検出できない場合は自動読み込みがスキップされます。自動ロードを無効にしたい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定してください。（src/kabusys/config.py）
- プロセス優先度・CPU affinity の設定は環境依存（OS 権限）で失敗する可能性があり、その場合は警告が出て処理は継続します。

開発メモ / 実装上の注記（コードからの推測）
- 多くの関数は外部 API や本番資金に直接アクセスしない純粋関数として設計されており、ユニットテストが容易（ポートフォリオ構築・位置サイズ計算等）。
- DuckDB を分析用 DB として統合しており、リサーチコードは DuckDB 接続を受けて SQL と Python を組み合わせて計算する設計。
- ExecutionEngine 周りは BrokerClientFactory を介して実際のまたはモックのブローカークライアントを注入することで paper_trading と live の切り替えを容易にしている。
- .env の書き出しウィザードは .env を Git 管理しないことを明記している（セキュリティ配慮）。

今後の改善候補（コードから推測）
- price の欠損時のフォールバック（前日終値など）を position_sizing/apply_sector_cap に導入（現在は TODO コメントあり）
- 銘柄ごとの単元（lot_size）をマスタで持たせる設計への拡張
- factor_research の完全実装とユニットテスト充実
- ログ設定のテストカバレッジ、ファイルハンドラ作成失敗時のより詳細なロギング

脚注
- ここに記載した変更点は、提供されたソースコードから推測してまとめたものです。実際のコミット履歴や意図とは異なる可能性があります。実際の変更履歴として利用する場合は、リポジトリの git ログ等と照合してください。