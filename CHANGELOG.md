CHANGELOG
=========

すべての変更は Keep a Changelog の方針に準拠して記載しています。  
日付はリリース想定日です（コードから推測して記載）。

Unreleased
----------

- なし

[0.1.0] - 2026-04-19
--------------------

Added
- 実行用 / 管理用エントリポイントを追加
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用の paper_trading DB を使用し、MockBrokerClient を利用する設計を反映。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ（data/stop_requested.flag）検知で安全に終了。
- 設定管理とウィザード
  - config.py: 環境変数・設定読み込みロジックを実装。プロジェクトルート自動検出、.env / .env.local の自動ロード（OS 環境変数を保護）や必須パラメータの取得ユーティリティを提供。
  - config_setup.py: .env の対話式作成・更新ウィザードを実装。シークレット項目のマスク表示、デフォルト値、保存テンプレートを提供。
  - validate_config.py: 起動前チェック用 CLI を追加。必須環境変数、KABUSYS_ENV の妥当性、DB パス、config/*.yaml の存在／パース検証、live 環境向けの追加ガードを含む。
- ロギングとプロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定を実装。コンソール（stdout）と日次ローテーションのファイル出力（logs/<app_name>.log）を構成。ログディレクトリ作成失敗時はファイルハンドラをスキップして継続する等の耐障害性を持つ。
  - utils/process_priority.py: プロセス優先度（high/normal/low）と CPU affinity 設定ユーティリティを実装。Windows / POSIX の差分を吸収し、権限不足等の例外は警告でスキップ。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: 候補選定、等配分・スコア加重の重み計算を実装。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio/position_sizing.py: 発注株数算出ロジックを実装（risk_based / equal / score）。単元株（lot_size）丸め、aggregate cap によるスケールダウン、残余配分ロジックを実装。
  - portfolio/risk_adjustment.py: セクター集中制限の除外ロジックと市場レジームに基づく乗数（regime multiplier）を実装。
- 分析・検証ツール
  - tools/paper_verification_report.py: Paper Trading 検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。期間フィルタ／DB パス引数対応。
- リサーチ基盤（開始）
  - research/factor_research.py: モメンタム等のファクター計算モジュールの骨子を追加（DuckDB 接続を受け取り prices_daily / raw_financials を参照する想定）。将来的なファクター計算ロジックのベース。

Changed
- DB/監視に関する挙動の明示化
  - run_monitoring は環境（KABUSYS_ENV）にかかわらず本番用 sqlite_path を使用する仕様に決定（監視は環境に依存しない設計）。
  - run_execution は paper_trading 環境時に paper_sqlite_path を使用し、本番 DB と完全分離するように実装。
- .env 自動ロードの挙動
  - OS 環境変数を保護するために、自動ロード時は既存の OS 環境変数を上書きしない（.env.local は override=True だが protected により OS 変数は保護）。
- ログ出力のデフォルトと解決順を明確化
  - setup_logging にてログレベルとログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。

Fixed
- .env パーシングの堅牢化
  - config._parse_env_line で export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応し、より正確に .env 行を解釈するよう改良。
- DB 初期化の冪等性
  - init_monitoring_db の呼び出しを各起動スクリプトで行い、監視テーブルが存在することを保証（存在すれば何もしない）。
- 例外耐性の向上
  - run_monitoring のポーリングループで monitor.check_once() の例外を捕捉して記録し、次のポーリングに持ち越す設計により監視プロセスが単発エラーで停止しないように。
  - process_priority と CPU affinity の設定で権限不足や未対応 OS を安全に扱うようにし、失敗しても警告ログを出して継続するように。
- ログファイル作成失敗時のフォールバック
  - logging_setup でログディレクトリの作成に失敗した場合、ファイルハンドラ作成をスキップしてコンソール出力のみで継続するように修正（運用時にロギング失敗でプロセスが落ちないように）。

Security
- config_setup に .env テンプレートを出力する際の注意書きを追加（.env を絶対に Git にコミットしないよう明記）。シークレット項目はウィザード中にマスク表示。

Notes / Implementation details（コードから推測）
- run_execution は ExecutionEngine をスレッドで起動し、data/execution.pid に PID を書き込む想定。停止は data/stop_requested.flag の存在検知で行う。
- run_monitoring は duckdb と sqlite の両方に接続し、SystemMonitor に両コネクションを渡す設計。停止フラグと KeyboardInterrupt による安全終了を実装。
- portfolio モジュール群は「純粋関数（副作用なし）」として設計され、単体テストしやすい構造になっている。
- paper_verification_report は SQL を用いて各種統計を集計し、閾値を超えた指標を FAIL としてレポートする（P95 は独自関数で算出）。
- Settings クラスはプロパティベースで環境変数を遅延評価し、妥当性チェック（例: KABUSYS_ENV / LOG_LEVEL / PAPER_FILL_MODE）を行う。

今後の予定（推測）
- research/factor_research のファクター計算関数の実装完了・テスト追加
- ExecutionEngine / SystemMonitor 周りのテスト強化と実運用向けの監視アラート（LINE 連携等）の整備
- 単体テスト・CI 設定の追加

--- 

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノート作成時にはコミットログやリリース方針に合わせて調整してください。