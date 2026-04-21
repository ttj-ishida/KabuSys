# Changelog

すべての重要な変更はこのファイルに記録します。本ドキュメントは「Keep a Changelog」形式に準拠します。  
バージョン番号はソース内の `kabusys.__version__` に合わせて管理しています（現行: 0.1.0）。

## [Unreleased]

（現時点では未リリースの変更はありません）

## [0.1.0] - 初期リリース
最初の公開リリース。システム全体のコア機能・ユーティリティ・CLI を含みます。

### 追加 (Added)
- 基本のパッケージ/モジュールを実装
  - kabusys パッケージ本体とバージョン定義（src/kabusys/__init__.py）
- 環境設定・管理
  - Settings クラスによる環境変数ラッパーの実装（src/kabusys/config.py）
    - 自動でプロジェクトルートの `.env` / `.env.local` を読み込む機能（KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化可）
    - 必須・任意設定、環境種別（development/paper_trading/live）、各種デフォルト値を提供
    - PAPER_FILL_MODE のバリデーション（instant/partial/never/reject）
    - paper_trading 用 DB パスの分離（paper_sqlite_path）
  - 対話式環境設定ウィザード CLI（python -m kabusys.config_setup）を追加
    - .env の読み書き、既存値の再利用、シークレットマスク表示（src/kabusys/config_setup.py）
  - 設定検証 CLI（python -m kabusys.validate_config）を追加
    - 必須環境変数チェック、KABUSYS_ENV / LOG_LEVEL 検証、DB パスの親ディレクトリ有無チェック、config/*.yaml 存在・YAML パース検証（PyYAML 未導入時は警告）など（src/kabusys/validate_config.py）
- 実行/監視ランナー
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）
    - KABUSYS_ENV=paper_trading 時に専用の paper_trading DB を使用して本番 DB から分離
    - BrokerClientFactory を用いたブローカークライアント生成、OrderRepository/RiskManager/Reconciler/ExecutionEngine の組み立てと実行スレッド化
    - data/execution.pid 管理、stop フラグ検知による安全停止
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）
    - MONITOR_POLL_INTERVAL 環境変数によるポーリング間隔上書き（デフォルト 60 秒）
    - 監視は環境に関係なく本番 sqlite_path を参照し初期化（監視テーブル保証）
    - stop フラグによるループ終了、例外ログ出力と次ポーリング続行
- 分析・検証ツール
  - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）
    - 指定期間の稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力
    - CLI オプション: --from / --to / --db、環境変数 PAPER_TRADING_SQLITE_PATH をサポート
- ポートフォリオ構築ライブラリ（純粋関数群）
  - 候補選定と重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates, calc_equal_weights, calc_score_weights
  - セクター分散制御とレジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap, calc_regime_multiplier（regime に応じた乗数: bull/neutral/bear）
  - ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の配分方式、単元株（lot_size）への丸め、aggregate cap とスケーリングロジック、コストバッファ考慮
  - portfolio パッケージのエクスポート設定（src/kabusys/portfolio/__init__.py）
- ロギング・プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）
    - stdout StreamHandler と 日次ローテートファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定
    - ログディレクトリ作成に失敗した場合はファイル出力をスキップしてコンソールのみで継続
    - LOG_LEVEL / LOG_DIR の解決順を実装
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）
    - Windows / POSIX 差分を吸収して nice/priority を設定、失敗時は警告でスキップ
    - set_cpu_affinity による先頭 N コアへの固定サポート
- 研究用ファクター計算（雛形）
  - DuckDB を使うファクター計算モジュールの雛形（src/kabusys/research/factor_research.py）
    - モメンタム/MA/ATR 等の定数・スキャンレンジ定義（計算ロジックの実装は途中）

### 変更 (Changed)
- なし（初回リリース）

### 修正 (Fixed)
- なし（初回リリース）

### 既知の制限・注意点 (Notes / Known issues)
- config/config_setup 等で生成される .env は絶対に Git にはコミットしないことを README や開発手順に明記する必要あり（config_setup.py 内コメントにも記載）。
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合にエクスポージャーや投資額が過少見積りされる可能性があり、将来的に前日終値や取得原価でのフォールバックを検討する TODO コメントあり。
  - lot_size は現状グローバル固定（将来的には銘柄別対応想定）。
- process_priority / set_cpu_affinity:
  - 権限不足や未対応 OS では設定がスキップされる（ログに警告を出す）。
- Paper Trading 検証レポート:
  - 対象 DB のスキーマ不整合やテーブル欠如時は sqlite3.OperationalError を捕捉して N/A を出力する設計。
- research/factor_research.py は一部実装が途中（コメント末尾で切れている）ため完全なファクター計算ロジックは未完成。

### セキュリティ (Security)
- シークレット値（J-Quants トークン / kabu API パスワード）は .env に保存する設計だが、リポジトリにコミットしない運用が必須。config_setup でも注意喚起を出力。

---

今後の予定:
- factor_research の完成、DuckDB ベースの実データ処理パイプライン構築
- ExecutionEngine / Broker のモックと統合テスト整備
- 銘柄ごとの lot_size マスタ統合、価格フォールバックロジック実装
- 監視・アラート（LINE 通知）フローの充実化

（必要に応じてリリース日や詳細なコミット参照を追加してください）