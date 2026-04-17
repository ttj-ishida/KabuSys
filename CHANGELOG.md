CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

（現時点では未リリースの変更はありません）

[0.1.0] - 2026-04-17
-------------------

Added
- 初期リリース: KabuSys のコアユーティリティ、実行スクリプト、ポートフォリオ構築、ファクター計算、設定管理ツール、監視/検証ツールを追加。
  - パッケージバージョンを設定: src/kabusys/__init__.py の __version__ = "0.1.0".
- 実行/監視エントリポイント
  - run_execution: 実取引 / ペーパートレードを切り替え可能な ExecutionEngine 起動スクリプトを追加。ペーパートレード時は専用 SQLite（PAPER_TRADING_SQLITE_PATH, デフォルト data/paper_trading.db）を使用し、本番 DB と完全に分離する実装。起動時にプロセス優先度を上げ、停止フラグ（data/stop_requested.flag）や実行用 PID ファイルの取り扱いを実装。参照: src/kabusys/run_execution.py。
  - run_monitoring: SystemMonitor のポーリングループを提供。MONITOR_POLL_INTERVAL 環境変数（デフォルト 60 秒）で間隔を上書き可能。監視は環境にかかわらず本番 sqlite_path を使用する仕様。参照: src/kabusys/run_monitoring.py。
- 設定 / 環境管理
  - Settings クラス: 環境変数の取得・検証を集中管理（KABUSYS_ENV, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。環境判定やデフォルト値、簡易バリデーションを実装。参照: src/kabusys/config.py。
  - 自動 .env 読み込み: プロジェクトルート（.git か pyproject.toml）を探索し、.env/.env.local を自動読み込み（OS 環境変数優先）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env パーサー: export 形式、引用符内のエスケープ、インラインコメントの扱い等に対応する堅牢なパーサーを実装。
  - config_setup: 対話式ウィザードで .env を作成/更新する CLI を追加（src/kabusys/config_setup.py）。秘密項目はマスク表示。テンプレートヘッダの自動出力あり。
  - validate_config: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検査、DB パスの親ディレクトリ存在チェック、PyYAML がある場合は YAML のパース検証を行う。--strict で警告を失敗扱いにできる。参照: src/kabusys/validate_config.py。
- ポートフォリオ構築（純粋関数群、DB 非依存）
  - portfolio_builder: 候補選定（select_candidates）、等分配（calc_equal_weights）、スコア加重（calc_score_weights, スコアが全て 0 の場合は等配分にフォールバック）。参照: src/kabusys/portfolio/portfolio_builder.py。
  - risk_adjustment: セクター集中制限（apply_sector_cap。unknown セクターは制限対象外）、市場レジームに基づく投下資金乗数（calc_regime_multiplier。bull/neutral/bear のマッピングと未知値のフォールバック）を実装。参照: src/kabusys/portfolio/risk_adjustment.py。
  - position_sizing: allocation_method（"risk_based" / "equal" / "score"）に基づく株数算出。単元株（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケーリング）、cost_buffer（手数料・スリッページの見積り）を考慮したスケールダウンと端数処理を実装。参照: src/kabusys/portfolio/position_sizing.py。
  - portfolio パッケージとしてエクスポートを整備（src/kabusys/portfolio/__init__.py）。
- ファクター計算（研究用）
  - factor_research: DuckDB 接続を受けてモメンタム（1M/3M/6M、MA200 乖離）・ボラティリティ（ATR20、平均売買代金、出来高比率）等を SQL + Python で計算する関数を実装。営業日ベースのウィンドウやデータ不足時の None 扱いなどを考慮。参照: src/kabusys/research/factor_research.py。
- ユーティリティ
  - process_priority: クロスプラットフォームでプロセス優先度（high/normal/low）と CPU affinity 設定を試みるユーティリティを追加。Windows／POSIX（Linux/Mac/FreeBSD）に対応し、権限不足や未サポート環境では警告を出してスキップする安全設計。参照: src/kabusys/utils/process_priority.py。
- モニタリング / 検証ツール
  - monitoring_db 初期化呼び出しを各起動スクリプトが行う（init_monitoring_db を使用）して監視用テーブルの存在を保証。
  - tools/paper_verification_report: ペーパートレード向けの検証レポート生成スクリプトを追加。稼働率、注文成功率（fill）、送信率（send）、P95 レイテンシ等の集計・閾値判定を行い PASS/FAIL 判定を出力。CLI 引数 --from/--to/--db をサポート。参照: src/kabusys/tools/paper_verification_report.py。

Changed
- なし（初期リリースのため変更履歴はなし）

Fixed
- なし（初期リリース）

Notes / Implementation details
- .env 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は既存の OS 環境変数を上書きしない）。
- Settings による環境値取得は堅牢なバリデーションを行い、無効値は ValueError を発生させる仕組み（例: PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV の許容値チェック等）。
- run_execution は起動時に既に停止フラグが存在する場合は起動せず終了する安全対策を実装。
- run_monitoring は停止フラグ検知、例外時のログ出力と次ポーリングまでの待機、KeyboardInterrupt のハンドリングを実装。
- position_sizing のスケーリングロジックは lot_size 単位での再配分を行い、残余キャッシュで fractional 残差が大きい順に追加配分するアルゴリズムを用いている（再現性のため二次キーにコードを使用）。

Breaking Changes
- なし

Acknowledgements / Next steps
- 本リリースはコア機能の初期実装に相当します。今後の改善候補:
  - ポートフォリオ構築の lot_size を銘柄別にサポートする（現在はグローバル固定）。
  - position_sizing の価格フォールバック（前日終値や取得原価）を改善して欠損時の過少評価を防ぐ。
  - factor_research の追加ファクターやパフォーマンス最適化、DuckDB クエリの堅牢化。
  - モニタリングのアラート送信（LINE 等）連携、より詳細な監視メトリクス収集。

----- End of changelog -----