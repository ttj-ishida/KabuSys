CHANGELOG
=========

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

現在のバージョン: 0.1.0

Unreleased
----------

（なし）

0.1.0 - 初回リリース
--------------------

追加 (Added)
- 基本アーキテクチャと主要コンポーネントを実装。
  - 実行エンジン / 監視ループ用のエントリスクリプトを追加
    - run_execution.py: ExecutionEngine を起動する CLI。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB と MockBroker を使用。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 設定関連ユーティリティ
    - config.py: 環境変数読み込み・抽象化 Settings クラス（.env/.env.local 自動ロード、各種 path/閾値/フラグのプロパティ）。
    - config_setup.py: 対話式ウィザードで .env を初期作成・更新する CLI。
    - validate_config.py: .env と config/*.yaml の整合性チェック用 CLI（--strict オプションで警告を失敗扱いに可能）。
- ポートフォリオ構築関連（純粋関数）
  - portfolio/portfolio_builder.py: 候補選定（スコア順）・等分配 / スコア加重配分の実装。
  - portfolio/position_sizing.py: 株数決定ロジック（risk_based / equal / score、単元株丸め、aggregate cap によるスケーリング、コストバッファ考慮）。
  - portfolio/risk_adjustment.py: セクター集中制限の適用、マーケットレジームに基づく投下資金乗数。
- 実行時ユーティリティ
  - utils/process_priority.py: Windows/Linux/macOS の差を吸収したプロセス優先度設定と CPU affinity 設定ユーティリティ。
- 監視・分析関連
  - monitoring 側の DB 初期化ユーティリティ呼び出しを実装（run_monitoring/run_execution が監視テーブルの存在を保証）。
  - tools/paper_verification_report.py: ペーパートレード用検証レポート生成スクリプト（稼働率・注文成功率・送信率・レイテンシ P95 等を計算）。コマンドライン引数 --from/--to/--db に対応。
- 研究用モジュール
  - research/factor_research.py: DuckDB を用いたファクター計算（モメンタム、ボラティリティ等の基盤実装）。prices_daily/raw_financials を参照して結果を返す設計。
- パッケージ初期化
  - __init__.py にバージョン（0.1.0）と主要パッケージエクスポート定義を追加。

変更 (Changed)
- .env 読み込み/パースの堅牢化（config._parse_env_line）
  - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、コメントの取り扱い改善などを実装。
  - _load_env_file に protected 引数を導入し OS 環境変数が .env によって誤って上書きされないよう保護。
  - 自動ロード順序は OS 環境変数 > .env.local > .env（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- Settings による設定検証の明確化
  - KABUSYS_ENV / LOG_LEVEL の許容値チェック、紙取引用 DB / PID/kill flag 等のプロパティを提供。
  - PAPER_FILL_MODE の有効値を明確化（instant / partial / never / reject）。
- monitor 実行時の設計決定
  - run_monitoring は KABUSYS_ENV に依らず「本番 sqlite_path（Settings.sqlite_path）」を監視 DB に使用するよう明示（設計上の注意点）。
- run_execution のデータ分離
  - paper_trading 実行時は settings.paper_sqlite_path（デフォルト data/paper_trading.db）を使用し本番 DB と分離。
- ProcessPriority 実装で psutil のプラットフォーム差分を吸収。未対応 OS や権限不足時は警告を出して処理をスキップ。

修正 (Fixed)
- run_execution/run_monitoring の停止方法をファイルベースで統一（data/stop_requested.flag を監視して安全に終了）。
- .env 書き出しテンプレートの改善（config_setup._write_env）。.env の注意書きを追加（Git へのコミット禁止）。
- paper_verification_report の統計処理でデータ欠損時に例外を回避する耐性を追加（テーブルがない／空でもエラーにならないようにフォールバック）。

パフォーマンス (Performance)
- position_sizing の aggregate cap スケーリングで再現性を確保するため残差処理（小数端数を lot 単位で分配）を実装。大口スケーリング時の安定性を向上。

セキュリティ (Security)
- config_setup においてシークレット項目は入力時にマスク表示を行う UI を実装（ファイルには平文で保存されるため、.env の取扱いに注意喚起を記載）。
- Settings._require による必須環境変数未設定時の明示的なエラー報告を追加。

注記 (Notes)
- run_monitoring は MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。0 や負値を渡した場合はデフォルト（60 秒）にフォールバックして警告が出ます。
- run_execution は Engine を別スレッドで実行し、停止フラグ検知で engine.stop() を呼び安全終了を試みます。PID ファイル・停止フラグ等の運用手順に従ってください。
- research/factor_research のクエリは DuckDB の存在を前提としており、prices_daily/raw_financials のスキーマに依存します。環境によってはデータ準備が必要です。
- validate_config は PyYAML が未インストールの場合、YAML パース検証をスキップして警告を出します。

将来検討 (Future)
- position_sizing: 銘柄別の lot_size を stocks マスタで持たせる拡張（現在は全銘柄共通で lot_size を仮定）。
- apply_sector_cap の price 欠損時のフォールバック（前日終値や取得原価など）対応。
- run_monitoring/run_execution のより細かい監視・メトリクス収集（Prometheus 等）や外部アラート連携。

--- 

作成者注:
- 上記はソースコードの内容から推測してまとめた初期リリース向けの CHANGELOG です。実際のリリースノート作成時は、コミット履歴やリリースポリシーに合わせて調整してください。