CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-04-18
-------------------

Added
- 初回リリース（0.1.0）。以下の主要機能・モジュールを追加しました。
  - 起動スクリプト
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能。停止はプロジェクトルート/data/stop_requested.flag を監視して行う。
    - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite（デフォルト: data/paper_trading.db）を使用し、本番 DB と分離。実行はデーモンスレッドで行い、停止フラグで安全にシャットダウン可能。
  - 設定・環境管理
    - config.py: 環境変数と設定の取得クラス Settings を実装。自動的にプロジェクトルートの .env/.env.local を読み込む（無効化フラグあり）。.env のパースは export プレフィックス、クォート、エスケープ、インラインコメント等に対応。
    - config_setup.py: 対話式 .env 作成ウィザードを追加。シークレット項目は表示マスク、保存テンプレートを生成。
    - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在・パース等を検証。--strict モードで警告を FAIL 扱いにできる。
  - ログ・プロセス制御ユーティリティ
    - utils/logging_setup.py: StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定する共通ロガーを実装。ログディレクトリ作成に失敗した場合はコンソールのみで動作。
    - utils/process_priority.py: Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）と CPU affinity を設定するユーティリティを実装。権限不足などエラー時は警告してスキップ。
  - ポートフォリオ構築ライブラリ（純粋関数群）
    - portfolio/portfolio_builder.py: 候補選定（スコア順）、等金額配分、スコア重み付けを実装。スコア全てが 0 の場合は等配分へフォールバック。
    - portfolio/risk_adjustment.py: セクター集中上限を適用する apply_sector_cap、および市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装（"bull"/"neutral"/"bear" をサポート）。
    - portfolio/position_sizing.py: position サイズ算出ロジックを実装。risk_based / equal / score の割当方式、単元株（lot_size）丸め、aggregate cap スケーリング、cost_buffer（手数料・スリッページ想定）を考慮。
  - ツール
    - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。システム稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均/最大/P95）を集計し、閾値に基づく PASS/FAIL を判定。P95 計算、日付フィルタ、DB パス引数対応を実装。
  - 研究用モジュール（骨格）
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨格を追加。Momentum/Value/Volatility/Liquidity 系ファクターを計画。（実装は続行中）
  - パッケージ情報
    - __init__.py: パッケージ名とバージョン __version__ = "0.1.0" を追加。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数や .env の取り扱いでシークレットをマスク表示する仕組みを導入（config_setup の対話表示など）。ただし .env ファイルは絶対に Git にコミットしない旨の注意文を追加。

Notes / 補足
- DB 関連: 監視用 monitoring は環境に関わらず settings.sqlite_path（デフォルト data/monitoring.db）を使用し、実行エンジンは paper_trading 時に paper_sqlite_path（デフォルト data/paper_trading.db）へ切り替えることでデータ分離を実現しています。
- ログ: コンソール出力は stdout を利用する設計です（cron やスケジューラでの扱いを考慮）。
- 環境読み込み: デフォルトでプロジェクトルートの .env と .env.local を読み込みますが、KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化できます。
- validate_config の YAML 検証は PyYAML が存在しない場合はスキップされ、警告が出ます。

開発上の今後の課題（TODO）
- research/factor_research.py の完全実装（各ファクター算出ロジックの完成）。
- position_sizing の価格欠損時フォールバック（現在は price がない場合はスキップする注記あり）。
- 単体テスト・統合テストの追加（特に position sizing / risk adjustments / execution の停止動作など）。
- Paper Trading の MockBroker 実装詳細と検証シナリオの整備。

--- 

参考: 本 CHANGELOG は、リポジトリの現状コードベース（2026-04-18 時点）から推測して作成しています。