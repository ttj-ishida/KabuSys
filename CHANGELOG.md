CHANGELOG
=========

すべての重要な変更をここに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

注意: 以下の変更点は、提示されたコードベースの内容から推測して作成しています。
実際のコミット履歴に基づくものではありません。

Unreleased
----------

- 既知の改善点 / TODO
  - research/factor_research.calc_momentum の実装が途中で切れており未完成。ファクター計算モジュールの追加実装が必要。
  - portfolio/risk_adjustment.apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられる旨の TODO コメントあり。前日終値や取得原価などのフォールバック価格を用いる改善が検討中。
  - portfolio/position_sizing: 将来的に銘柄ごとの lot_size をサポートする設計（stocks マスタに lot_size を持たせる等）の拡張案あり。
  - utils/logging_setup: ログディレクトリ作成失敗時はファイル出力をスキップする実装になっているが、運用上の通知や再試行ポリシーの改善が可能。
  - utils/process_priority: 未対応 OS の扱いや権限不足時の挙動はログ警告でスキップする設計。より詳細なエラー報告やフォールバック戦略の追加が想定される。
  - validate_config: PyYAML 未インストール時に YAML 検証をスキップする動作になっている。CI/デプロイ環境での厳格なチェックを行うためのオプション追加が考えられる。

0.1.0 - 2026-04-19
------------------

Added
- 基本アプリケーションパッケージ
  - kabusys パッケージの初期リリース相当。バージョンは src/kabusys/__init__.py にて "0.1.0" と定義。

- 環境設定・検証関連
  - config.py: .env 自動ロード機能（プロジェクトルート検出、.env / .env.local の読み込み順序、保護された OS 環境変数の扱い）。
    - .env ファイルパースの細かい仕様（export 形式、クォート内のバックスラッシュエスケープ、インラインコメントの扱い）を実装。
    - Settings クラスにより環境変数を型付きプロパティで取得（J-Quants / kabu API / DB パス / PID・kill flag /閾値等）。
    - KABUSYS_ENV, LOG_LEVEL 等の値検証（妥当性チェックと明確なエラーメッセージ）。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI。
    - シークレット入力（マスク表示）、選択肢、デフォルト値をサポート。
    - .env の読み取り・上書き用ユーティリティを提供。
  - validate_config.py: 起動前の設定検証 CLI。
    - 必須環境変数の存在チェック、KABUSYS_ENV や LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース確認（PyYAML があればパース検証）。
    - --strict オプションで警告も失敗として扱う機能。

- 実行・監視エントリポイント
  - run_execution.py: ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading 時は専用 SQLite（PAPER_TRADING_SQLITE_PATH）を使用して本番 DB と分離。
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/OrderManager/Reconciler/RiskManager を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）に基づく安全停止処理。
    - プロセス優先度を "high" に設定するユーティリティ呼び出し。
  - run_monitoring.py: SystemMonitor ポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒）。不正値はデフォルトにフォールバックし警告出力。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計（monitoring DB を一貫して参照）。
    - stop フラグ検出・KeyboardInterrupt ハンドリング・例外発生時のロギングとループ継続処理を実装。

- ロギング・プロセスユーティリティ
  - utils/logging_setup.py: ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション）を設定するユーティリティ。
    - 既存ハンドラをクリーンアップして二重設定を防止。
    - ログレベル・ログディレクトリの解決順を定義（引数 > 環境変数 > デフォルト）。
    - ファイルハンドラ作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py: クロスプラットフォームなプロセス優先度設定と CPU affinity 設定。
    - Windows / POSIX(nice) を吸収し、権限不足や未対応環境では警告を出してスキップ。

- ポートフォリオ構築・リスク管理
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア降順選択（タイブレーク: signal_rank）。
    - calc_equal_weights / calc_score_weights: 等配分およびスコア加重配分（スコア合計が 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中を防ぐため既存ポジション比率に基づいて新規候補を除外するロジック（unknown セクターは除外されない）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づいて銘柄ごとの発注株数を計算。
    - aggregate cap（available_cash）を超える場合はスケールダウンし、lot_size 単位で端数処理を行う保守的な割当ロジックを実装。
    - 手数料/スリッページ考慮の cost_buffer パラメータを導入。

- Paper Trading ツール
  - tools/paper_verification_report.py:
    - Paper Trading（data/paper_trading.db）用の検証レポート生成 CLI。
    - 稼働率（uptime）、注文成功率（fill_rate）、送信率、レイテンシ（avg/max/P95）、リスク却下数を集計。
    - 基準値（稼働率 99%、fill 90%、send 95%、P95 <= 200 ms）に基づく PASS/FAIL 判定出力。

- research
  - research/factor_research.py: ファクター計算モジュールの骨組み（モメンタム / MA / ATR / Value / Liquidity 等の設計方針と定数を定義）。DuckDB 接続を受け取り SQL+Python で計算する設計。注: calc_momentum は途中で切れており実装継続が必要。

- その他
  - monitoring/monitoring_db の初期化呼び出し（init_monitoring_db）を実行時に冪等に行うことでテーブル存在を保証。
  - パッケージ public API（kabusys.portfolio.*）を __all__ でエクスポート。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。ただし以下の実装上の堅牢性確保が行われている:
  - logging_setup が既存ハンドラをクリアして二重出力を防止。
  - run_monitoring の MONITOR_POLL_INTERVAL パースで不正値を検出した際にデフォルトへフォールバックし警告出力。
  - run_execution/run_monitoring での停止フラグ検出により安全にプロセスを停止可能。

Removed
- 該当なし。

Security
- 環境変数読み込みではシークレット項目（J-Quants リフレッシュトークン、kabu API パスワード等）を扱うが、.env を Git にコミットしないよう注意書きを出力する等の基本的注意を促している。シークレット管理の外部化（Vault 等）は今後の検討事項。

Notes / 運用上の注意
- .env 自動ロードはプロジェクトルートが検出できない場合スキップされるため、パッケージ配布後や CWD が異なる環境では明示的に環境変数を設定する必要あり。
- Paper Trading 用 DB と本番 monitoring DB は明確に分離されているが、運用時は環境変数（PAPER_TRADING_SQLITE_PATH / SQLITE_PATH）を誤設定しないよう注意。
- 実行スクリプトは stop フラグファイル（data/stop_requested.flag）により外部から停止指示を受ける設計。デプロイ時の監視・外部制御ポリシーに合わせて利用すること。

--- 

以上。必要であれば各ファイルごとのより詳細な変更点（関数シグネチャ、引数説明、既知の制約等）を追記できます。どの粒度で記載したいか教えてください。