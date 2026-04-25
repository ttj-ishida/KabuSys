Changelog
=========
すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。  
各リリースには主要な追加（Added）、変更（Changed）、修正（Fixed）等を記載します。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-25
-------------------

Added
- 基本パッケージ初期実装を追加。
  - kabusys パッケージのバージョンを 0.1.0 に設定。
- 起動スクリプトを追加。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能、停止用フラグファイル（data/stop_requested.flag）を検知して安全に終了。Monitoring は環境にかかわらず本番 sqlite_path を使用。
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。KABUSYS_ENV=paper_trading 時に MockBrokerClient と専用 SQLite（data/paper_trading.db）を使用し本番 DB と分離。停止フラグ・PID ファイル管理を実装。
- 設定・環境管理機能を追加。
  - config.py: .env 自動読み込み（.env, .env.local、OS 環境変数の保護）、プロジェクトルート検出ロジック、export KEY= 形式・引用文字列・インラインコメント対応の .env パーサー、Settings クラスに各種設定プロパティ（DB パス、PID パス、閾値、PAPER_FILL_MODE の検証など）を実装。
  - config_setup.py: 対話式ウィザードで .env を初期作成/更新する CLI を追加。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数・KABUSYS_ENV・ログレベル・DB パス・config/*.yaml の存在とパース（PyYAML の有無を考慮）・本番環境向けガードを実施。--strict オプションで警告を FAIL 扱いにできる。
- ロギング・プロセス管理ユーティリティを追加。
  - utils/logging_setup.py: stdout への StreamHandler と日次ローテーションされるファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定するユーティリティを追加。ログディレクトリの解決順、既存ハンドラのクリア、ファイル作成失敗時のフォールバック動作を実装。デフォルト保管日数 30 日。
  - utils/process_priority.py: psutil を利用したクロスプラットフォームのプロセス優先度設定（Windows / POSIX 対応）および CPU affinity 固定ユーティリティを追加。失敗時は警告を出して安全にスキップ。
- ポートフォリオ構築関連の純粋関数群を追加（DB 参照なし、メモリ内計算）。
  - portfolio/portfolio_builder.py: シグナルから候補選定（スコア降順・タイブレーク）、等金額・スコア加重の重み計算（全スコアが 0 の場合のフォールバック）を実装。
  - portfolio/risk_adjustment.py: セクター集中上限の適用（既存ポジションのセクター露出計算、売却予定銘柄の除外対応）、市場レジームに応じた投下資金乗数（bull/neutral/bear）を追加。未知レジーム時のフォールバックとログ警告あり。
  - portfolio/position_sizing.py: allocation_method（risk_based / equal / score）に基づく株数算出ロジックを実装。単元株（lot_size）丸め、1 銘柄上限・最大投下率、手数料/スリッページ見積り（cost_buffer）を考慮した aggregate cap スケーリング、スケーリング後の端数配分ロジックを実装。
- 解析・運用支援ツールを追加。
  - tools/paper_verification_report.py: Paper Trading 用検証レポートを生成する CLI を追加（期間指定可能）。稼働率・注文成功率・送信率・P95 レイテンシ等を計算し PASS/FAIL 判定を出力。P95 計算、閾値定義、DB が存在しない場合のエラーメッセージなどを実装。
- 研究用ファクター計算モジュール（部分実装）を追加。
  - research/factor_research.py: Momentum / Value / Volatility / Liquidity などの計算方針と定数を実装。DuckDB 接続を受け取り prices_daily / raw_financials を参照する設計。

Changed
- 一貫したログ設定インターフェースを採用し、全起動スクリプトから setup_logging を呼び出すように統一。
- run_monitoring/run_execution で起動直後にプロセス優先度を "high" に設定するフローを採用（set_process_priority の利用）。
- .env 読み込みの優先順位を明示（OS 環境変数 > .env.local > .env）。OS 環境変数を保護するための protected セットを導入。

Fixed
- .env パースでの引用文字列・エスケープ・インラインコメントの扱いを改善し、より堅牢に読み込めるように修正。
- ログディレクトリ作成に失敗した場合でもプロセスが継続するようにフォールバック処理を実装（ファイルハンドラ無効化・コンソール出力継続）。
- process_priority/set_cpu_affinity でアクセス権限や未対応環境による例外発生時の挙動を安全にハンドリング（警告ログでスキップ）。

Notes / Known limitations
- portfolio.position_sizing の price が欠損（0.0）の場合、現在は簡易にスキップしているためエクスポージャーが過少評価される可能性がある。将来的に前日終値や取得原価などのフォールバックを検討（TODO コメントあり）。
- research/factor_research.py はファイル末尾で未完の関数定義（scaffold）等が含まれるため、完全なファクター計算の実装は今後の作業が必要。
- config_setup の対話式ウィザードは端末入力に依存するため、非対話環境では利用できない（CI などでは .env を直接設定することを推奨）。

開発者向け補足
- 環境変数検証ツール（kabusys.validate_config）は --strict モードを提供し、警告を FAIL として扱うことでデプロイ前の厳格チェックを支援します。
- Paper Trading と本番 DB は明確に分離しているため、ペーパートレードでの検証が本番データに影響を与えない設計です。

----- 
この CHANGELOG はコードベースの実装内容から推測して作成しています。実際の変更履歴やリリースノートはリポジトリのコミット履歴やリリース方針に合わせて調整してください。