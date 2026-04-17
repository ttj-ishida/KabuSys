# Changelog

すべての重要な変更をここに記録します。フォーマットは「Keep a Changelog」に準拠します。  
リリース日はコードから推測した日付を記載しています。

## [0.1.0] - 2026-04-17 (初回リリース)

### 追加 (Added)
- 初回リリースとして主要機能群を実装。
- 実行・監視関連スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用 DB を分離し、BrokerClientFactory によるブローカークライアント生成、RiskManager / OrderManager / Reconciler を組み立ててエンジンを別スレッドで実行する。停止フラグ（data/stop_requested.flag）および PID ファイルの扱いを実装。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は環境に関わらず本番 sqlite_path を使用する仕様。
- 設定関連ツール
  - config_setup.py: 対話式 .env ウィザードを実装（.env の初期作成・更新を支援）。秘密値のマスク表示、選択肢サポート、保存プレビューを提供。
  - validate_config.py: .env と config/*.yaml の事前検証 CLI を追加。必須環境変数チェック、パスの存在チェック、YAML パース（PyYAML が存在する場合）や本番環境向けの追加ガードを実装。--strict モード対応。
- 環境・設定管理
  - config.py: Settings クラスを追加し、アプリケーション設定（環境変数）を一元管理。自動でプロジェクトルートの .env / .env.local を読み込む機能（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。.env のパース処理は export プレフィックス・クォート・エスケープ・インラインコメントに対応。
  - 各種設定プロパティを提供（J-Quants, kabuAPI, LINE, DuckDB/SQLite パス, paper_trading 用パス, 監視しきい値等）。
- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder.py: 候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights, calc_score_weights）を実装。
  - risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた投下資金乗数（calc_regime_multiplier）を実装。
  - position_sizing.py: 株数決定ロジック（risk_based / equal / score の allocation_method、単元株丸め、aggregate cap スケーリング、cost_buffer 考慮）を実装。
  - 上記をまとめたパッケージエクスポートを提供。
- ユーティリティ
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定と CPU affinity 設定ユーティリティを追加。Windows と POSIX 系を吸収し、権限不足等は警告でスキップ。
- 研究用モジュール
  - research/factor_research.py: DuckDB を利用したファクター計算モジュールを追加（Momentum、Volatility、Liquidity 等）。calc_momentum / calc_volatility 等の関数を実装し、prices_daily テーブルを参照して計算。
- ツール
  - tools/paper_verification_report.py: Paper Trading 用の検証レポート生成スクリプトを追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを算出し PASS/FAIL 判定を出力。閾値はソース内定義で可読。
- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" として設定。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- .env パーサーの堅牢化
  - export KEY=val 形式、シングル/ダブルクォートでのバックスラッシュエスケープ、インラインコメントの扱い、未定義行のスキップ等に対応し、より現実的な .env フォーマットを正しく読み込むようにした。
- DB 初期化の冪等性確保
  - run_execution/run_monitoring 起動時に init_monitoring_db を呼び出して監視テーブルが存在することを保証（存在しても安全に呼べる実装配慮）。

### 非推奨 (Deprecated)
- （初回リリースのため該当なし）

### 削除 (Removed)
- （初回リリースのため該当なし）

### セキュリティ (Security)
- （このリリースで特筆すべきセキュリティ修正は無し。ただし .env は絶対にリポジトリにコミットしないことをドキュメントとウィザードで強調。）

---

備考・運用メモ
- モニタリングは本番 sqlite_path を参照する設計（KABUSYS_ENV に依らず）。ペーパートレード時は run_execution が paper_sqlite_path（デフォルト data/paper_trading.db）を使用して本番 DB と分離するため、運用時は環境変数の設定を確認してください。
- プロセス優先度設定や CPU affinity は権限やプラットフォームに依存するため、失敗時はログに警告を出してスキップします。
- validate_config と config_setup を併用することで、起動前に設定ミスを検出・修正できます。
- 今後の予定: 銘柄ごとの lot_size 対応、価格フォールバック（前日終値など）によるエクスポージャー評価改善、さらに詳細なファクター群の追加。

以上。