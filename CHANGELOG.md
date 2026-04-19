Keep a Changelog
=================
すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

[0.1.0] - 2026-04-19
-------------------

Added
- 基本アプリケーションおよび初期実装を追加（初回リリース相当）。
  - 実行・監視エントリポイント
    - run_execution.py: ExecutionEngine 起動ロジック、プロセス優先度設定、スレッドでのエンジン実行、停止フラグ検出、paper_trading 用に専用 SQLite を使用する分離（data/paper_trading.db を想定）。
    - run_monitoring.py: SystemMonitor のポーリングループ起動、MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能、停止フラグ検知で安全終了。監視は環境に関係なく本番 sqlite_path を使用する旨を明記。
  - 設定管理
    - config.py: Settings クラスを導入。環境変数/.env（.env.local）の自動読み込み、.env パーサー（export 形式、クォート・エスケープ、インラインコメント対応）、必須変数チェックユーティリティ、各種設定プロパティ（DBパス、KABUSYS_ENV 判定、paper_trading 切替、しきい値等）。
    - config_setup.py: .env 作成・更新の対話ウィザード（シークレット入力マスク、選択肢、デフォルト、保存テンプレート）。
    - validate_config.py: 起動前の設定検証 CLI を追加（必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック、KABUSYS_ENV=live 時の追加警告）。--strict モードで警告を FAIL 扱いに可能。
  - ポートフォリオ構築（純粋関数群）
    - portfolio.portfolio_builder: 候補選定（スコア降順、タイブレークルール）、等金額配分、スコア加重配分（スコアが全て 0 の場合は等金額にフォールバック）。
    - portfolio.risk_adjustment: セクター集中制限を適用する apply_sector_cap、レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知レジームはフォールバックと警告）。
    - portfolio.position_sizing: position size 計算（risk_based / equal / score の割当方式、単元株（lot）丸め、max position / aggregate cap / cost_buffer によるスケーリングと端数配分ロジック）。
  - ユーティリティ
    - utils/logging_setup.py: 統一ログ設定ユーティリティを追加（コンソール stdout と日次ローテーションファイルハンドラ、既存ハンドラのクリア、LOG_DIR/LOG_LEVEL の解決）。
    - utils/process_priority.py: クロスプラットフォーム（Windows / POSIX）でのプロセス優先度設定と CPU affinity 設定ユーティリティ。権限不足等の失敗を警告で処理。
  - 分析・検証ツール
    - tools/paper_verification_report.py: Paper Trading の検証レポート生成スクリプトを追加。稼働率・注文成功率（Fill/Send）・リスク却下数・API レイテンシ（平均・最大・P95）などを算出し PASS/FAIL 判定を出力。しきい値はファイル内定義で容易に調整可能。
  - 研究用モジュール（骨格）
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加（モメンタム、MA200乖離、ATR、出来高指標など、DuckDB 接続を受ける設計）。（注: ファイル末尾に続きあり／一部実装中）
  - パッケージ情報
    - __init__.py にバージョン 0.1.0 を定義。

Changed
- n/a（初回リリースのため既存動作からの変更履歴はなし）。

Fixed
- n/a（初回実装。既知のエラーハンドリングを追加：DB/ファイル作成失敗や権限エラー時にログ/警告で継続する実装）。

Notes / Implementation details
- 設計方針として、ポートフォリオ・リスク調整・ポジションサイズ計算は副作用のない純粋関数として実装され、DB 非依存でユニットテストが容易な構成にしています。
- run_execution は paper_trading 環境を本番 DB から完全分離し、paper_trading 用 SQLite（PAPER_TRADING_SQLITE_PATH）を用いることで実運用と検証を切り分けています。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用するよう明示的に設計されています（監視は本番インスタンスを前提とするため）。
- .env の自動読み込みはプロジェクトルート（.git または pyproject.toml）を基準に行い、環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって無効化可能です。
- ログは標準出力（stdout）に出す設計で、ファイル出力に失敗した場合もコンソール出力で運用継続できるよう配慮しています。
- process_priority と set_cpu_affinity は権限不足や未サポート環境で安全にスキップされ、詳細はログに出力されます。
- config_setup の対話ウィザードはシークレットのマスク表示や既存 .env の取り込みをサポートし、.env のテンプレートを書き出します。
- validate_config は PyYAML が無い場合に YAML 検証をスキップし、存在チェックと説明メッセージを提供します。

Known limitations / TODO
- research/factor_research.py はファクター計算の骨格を含みますが、ファイル末尾で途中のように見える箇所があり、完全実装が必要です。
- position_sizing の price フォールバック（前日終値・取得原価など）や銘柄別 lot_size のサポートは今後の拡張対象。
- apply_sector_cap の価格欠損時（price=0.0）に露出が過小評価される可能性があり、フォールバック価格の導入を検討中。
- モニタリング・Execution の停止制御はファイルベースのフラグを使用しているため、より堅牢なプロセス管理（PID/シグナル連携等）を将来的に検討。

Security
- 環境変数や .env に機密情報（API トークン等）を含める設計のため、.env は絶対に Git にコミットしない旨をテンプレートとドキュメントで明記しています。

[Unreleased]
- 今後の作業候補（優先度順）
  - research/factor_research の完全実装とテスト
  - ExecutionEngine / Broker クライアントの統合テスト・モック強化
  - config/*.yaml のスキーマ検証を追加（PyYAML が無くてもパッケージが必須である旨の指示）
  - 単体テストと CI 設定の追加
  - ファイルベースの停止フラグを置き換えるより堅牢な制御インターフェース（systemd, supervisor, signal handling 等）

-----