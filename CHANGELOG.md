CHANGELOG.md

すべての注目すべき変更履歴を記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

履歴はリポジトリ内のコード構成・コメントから推測して作成しています。実際のコミット履歴と差異がある場合があります。

Unreleased
---------
- なし

[0.1.0] - 2026-04-20
--------------------
Added
- 初回リリース。KabuSys の基本機能群を追加。
  - 実行スクリプト
    - run_execution.py: ExecutionEngine を起動する CLI スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用の専用 SQLite を利用し（data/paper_trading.db）、MockBrokerClient を利用可能にする。プロセス優先度を High に設定し、停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）をサポート。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。監視は常に本番用の sqlite_path を使用。
  - 設定・環境
    - config.py: 環境変数/ .env 読み込みロジックを実装（.env / .env.local の自動読み込み、OS 環境変数保護、クォート・エスケープ・インラインコメントの取り扱い対応）。Settings クラスで各種設定（DB パス、KABUSYS_ENV、閾値など）を提供。
    - config_setup.py: .env を対話式に生成・更新するウィザード。デフォルト値・選択肢・シークレット入力をサポート。
    - validate_config.py: 起動前に .env と config/*.yaml（存在する場合）の検証を行う CLI。--strict オプションで警告も失敗扱いに可能。
  - ログ・プロセス管理ユーティリティ
    - utils/logging_setup.py: 標準出力（stdout）と日次ローテーションファイルハンドラをルートロガーに設定するユーティリティ。ログディレクトリの自動作成とフォールバック動作を実装。
    - utils/process_priority.py: Windows/Linux/macOS でのプロセス優先度（nice/HIGH_PRIORITY_CLASS）設定と CPU affinity 設定ユーティリティを提供。権限不足時は警告ログを出してスキップ。
  - ポートフォリオ構築モジュール
    - portfolio/portfolio_builder.py: シグナルのソート（スコア降順・タイブレーク）と候補選定、等金額配分 / スコア加重配分の計算を実装。
    - portfolio/position_sizing.py: 各銘柄の株数決定ロジック（risk_based / equal / score）を実装。単元株丸め、最大ポジション比、aggregate cap スケーリング、cost_buffer による保守的見積りを実装。
    - portfolio/risk_adjustment.py: セクター上限の適用（既存保有を考慮して当日売却予定を除外）と市場レジームに応じた乗数（bull/neutral/bear）を実装。未知レジームは警告を出してフォールバック。
    - portfolio/__init__.py: ポートフォリオ関数群をエクスポート。
  - リサーチ（計算）基盤
    - research/factor_research.py: DuckDB を用いたファクター計算の骨子を追加（モメンタム、MA200、ATR、流動性などを想定）。（ファイルは途中まで実装。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計）
  - ツール・レポート
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成ツールを追加。期間指定 (--from / --to) や DB 指定 (--db) をサポート。稼働率、注文成功率、送信率、P95 レイテンシ等を計算し、閾値に基づき PASS/FAIL 判定を出力。デフォルト閾値や P95 算出ロジックを含む。
  - 初期データベース用ユーティリティ
    - monitoring/monitoring_db.py（参照されているが本CHANGELOGでは実装ありと推測）: 監視用テーブル作成関数 init_monitoring_db を利用して起動時に冪等的にテーブル確保。

Changed
- なし（初回公開のため）

Fixed
- なし（初回公開のため）

Deprecated
- なし

Removed
- なし

Security
- なし

Notes / Migration
- 環境変数の自動読み込みはデフォルトで有効。テストや特殊用途で自動ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- .env の読み込みロジックは OS 環境変数を保護（既存キーは上書きしない）しますが、.env.local は override=True として上書きを許可します（ただし OS 環境変数は保護されます）。
- paper_trading モードでは paper_sqlite_path（デフォルト data/paper_trading.db）が使用され、本番の SQLite（SQLITE_PATH）とは分離されます。運用時は誤って本番 DB を上書きしないようご注意ください。
- run_monitoring.py は監視 DB に常に settings.sqlite_path を使用します（環境にかかわらず本番監視 DB を参照する設計）。
- ログはデフォルトで logs/ 以下に出力され、daily ローテーション（30 世代）されます。ログ出力先が作成できない場合はコンソール出力のみで継続します。
- process priority / cpu affinity の設定はプラットフォーム依存のため、権限不足や非対応 OS の場合は警告を出してスキップします。

Known issues / TODO
- portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）時にエクスポージャーが過少見積りされる問題に対するフォールバック処理（前日終値や取得原価のフォールバック）は未実装（TODO コメントあり）。
- research/factor_research.py はファイル末尾で途中（実装未完）となっている可能性あり。DuckDB クエリ実装の続きが必要。
- 一部のモジュール（例: monitoring.system_monitor、execution.Engine 等）はこのスナップショットでは参照されているが実装詳細は別ファイルに依存（実装の有無により動作保証が変わります）。

ライセンスやリモート API の認証情報（J-Quants、kabuステーション、LINE トークン等）は .env に保存し、.env は絶対に Git にコミットしないでください（config_setup のヘッダにも注意書きあり）。

--  
この CHANGELOG はソースコードとそのコメントから推測して作成しています。実際の変更履歴（コミットログ）と差がある場合は、リポジトリの正式な履歴を参照してください。