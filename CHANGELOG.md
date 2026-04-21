# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-21

リリース初版。日本株自動売買フレームワーク「KabuSys」の基本機能を実装しました。
主に環境設定、実行・監視ランナー、ポートフォリオ構築、実行エンジン周辺のユーティリティと検証ツールを含みます。

### 追加 (Added)
- コアメタ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_execution: ExecutionEngine 起動用エントリポイントを実装（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用 SQLite を使用して本番 DB と完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成。
    - ExecutionEngine を別スレッドで実行し、stop フラグ検出で安全停止。
    - PID ファイル管理（data/execution.pid）をサポート。
  - run_monitoring: SystemMonitor のポーリングループ起動スクリプトを実装（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計。

- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）。
    - .env 自動読み込み（プロジェクトルートの .env / .env.local、環境変数優先）。
    - 多数のプロパティ（J-Quants / kabu API / DB パス / 監視閾値 / 環境種別 等）を提供。
    - env, log_level, PAPER_FILL_MODE などのバリデーションを実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化対応。
  - .env ファイルの安全性・使用方法に関する注意を含む（config_setup 参照）。

- 環境設定支援ツール
  - 対話型設定ウィザード（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を支援（シークレット入力のマスク、デフォルト表示、選択肢サポート）。
    - 生成される .env にコミットしない旨の警告を含むテンプレート出力。
  - 設定検証 CLI（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パースチェック（PyYAML がない場合はスキップの警告）。
    - --strict オプションで警告を FAIL として扱うモードを提供。

- ポートフォリオ構築ライブラリ（pure function）
  - portfolio モジュール（src/kabusys/portfolio/*）
    - 候補選定: select_candidates（スコア降順、同点タイブレーク）。
    - 重み計算: calc_equal_weights, calc_score_weights（スコアが全て 0 の場合は等配分にフォールバック）。
    - セクター集中制限: apply_sector_cap（既存保有のセクター露出を計算し、上限超過セクターの新規候補を除外）。unknown セクターは上限適用対象外。
    - レジーム乗数: calc_regime_multiplier（"bull"/"neutral"/"bear" に対応し、未知レジームは警告の上 1.0 にフォールバック）。
    - 株数決定: calc_position_sizes（risk_based / equal / score の各方式、単元株丸め、aggregate cap スケーリング、cost_buffer を考慮）。
  - portfolio/__init__.py で上記関数を公開。

- ユーティリティ
  - logging_setup（src/kabusys/utils/logging_setup.py）
    - stdout (StreamHandler) と 日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - 重複ハンドラ排除、ログディレクトリ作成失敗時のフォールバック、ログレベル解決ロジックを実装。
    - stdout を標準出力に使う設計（cron 等でのリダイレクトを考慮）。
  - process_priority（src/kabusys/utils/process_priority.py）
    - Windows / POSIX の差分を吸収してカレントプロセスの優先度を設定。
    - CPU affinity を最初の N コアにピン留めするユーティリティを実装。
    - 権限不足や未対応 OS でのフォールバック処理を行う。
  - tools.paper_verification_report（src/kabusys/tools/paper_verification_report.py）
    - ペーパートレード DB から稼働率、注文成功率、送信率、レイテンシ等を集計してレポートを出力する CLI。
    - P95 計算、閾値に基づく PASS/FAIL の判定を実装。--from / --to / --db の引数をサポート。

- 研究用モジュール（下地）
  - research.factor_research の骨組みを追加（src/kabusys/research/factor_research.py）。
    - モメンタム、MA200 乖離、ATR、出来高等の計算方針と定数を定義。DuckDB を用いたファクター計算を想定。
    - （注）ファイル末尾で関数実装が一部未完（今後の実装予定）。

### 変更 (Changed)
- logging の挙動
  - ルートロガーの既存ハンドラを明示的に flush/close してから削除するように変更。初期化を複数回呼んでもハンドラの重複が起きないように設計（logging_setup）。
- .env ロード順
  - OS 環境変数 > .env.local > .env の順で読み込む仕様を明確化（src/kabusys/config.py）。既存の OS 環境変数は保護される（上書き除外）。
- run_monitoring のデータベース接続方針
  - 監視モジュールは KABUSYS_ENV に関わらず常に本番用 sqlite_path を使用する挙動を明確化（設計選択）。

### 修正 (Fixed)
- .env パーサの堅牢化（src/kabusys/config.py）
  - export プレフィクス、シングル／ダブルクォート、バックスラッシュエスケープ、行内コメントの扱いを正しくパースするように実装。
  - 無効行（空行、コメント、キー無し等）は無視される。
- ログディレクトリ作成失敗時の動作安定化（logging_setup）
  - 作成に失敗した場合はファイルハンドラ作成をスキップし、標準出力のみで継続するように改善。
- process_priority の例外ハンドリング強化
  - psutil による権限エラーや未実装メソッドの例外を捕捉し、警告ログを出して処理を続行するように改善。
- calc_score_weights のフォールバック
  - 全銘柄のスコア合計が 0 の場合に等金額配分へフォールバックし、warning ログを出力するように修正。
- calc_position_sizes のスケーリングロジック
  - aggregate cap 超過時のスケールダウンロジックと lot_size による丸め処理を導入。残余キャッシュで端数を再配分するアルゴリズムを実装。

### 注意点 (Notes)
- run_execution は paper_trading モード時に DB を分離しますが、run_monitoring は監視用 DB に production sqlite_path を使用するため、paper_trading 実行時の監視データの扱いに注意してください（設計として監視は本番 DB を参照する仕様）。
- research.factor_research は設計ドキュメントに基づく下地を実装済みですが、関数実装の一部が未完です。DuckDB のテーブルスキーマ（prices_daily / raw_financials）を前提としています。

### 既知の制限 (Known issues)
- research/factor_research.py の実装未完（モメンタム関数の途中でファイルが終了）。ファクター計算の詳細実装は今後追加予定。
- 一部外部ライブラリ（psutil, duckdb, PyYAML など）に依存。環境によってはインストールが必要。

---

将来のリリースでは、引き続き以下を予定しています:
- research.factor_research の完全実装（各ファクターの SQL/Python 実装と単体テスト）
- ExecutionEngine / BrokerClient 実装の詳細（モック・実ブローカー双方の振る舞いの検証）
- モニタリング・アラート（LINE 通知等）の追加機能
- 単体テストと CI ワークフローの整備

もし差分や追加で強調したい変更点があればお知らせください。