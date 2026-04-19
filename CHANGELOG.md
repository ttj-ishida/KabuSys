# CHANGELOG

すべての注目すべき変更を日付順に記録します。本ファイルは Keep a Changelog の書式に準拠します。

## [0.1.0] - 2026-04-19
初期リリース。KabuSys のコア機能と運用ユーティリティを実装しました。

### 追加 (Added)
- 実行/監視用エントリポイント
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。プロセス優先度の設定、SQLite/DuckDB 接続、Broker 客のファクトリ生成、OrderManager/RiskManager/Reconciler 組み立て、スレッドでのエンジン実行、停止フラグ（data/stop_requested.flag）による安全終了を実装。
    - KABUSYS_ENV が `paper_trading` の場合は専用の paper_trading DB（data/paper_trading.db）を使用して本番 DB と分離する挙動を実装。
    - 実行時 PID ファイルの取り扱い（data/execution.pid を想定）。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグ検出でループ終了。Monitoring は環境にかかわらず本番 sqlite_path を使用する仕様を明記。
- 設定管理・支援ツール
  - config.py
    - .env の自動読み込み（プロジェクトルート検出ロジック付き）と Settings クラスを提供。各種環境変数の取得/検証ロジック（PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL など）を実装。
  - config_setup.py
    - インタラクティブな .env ウィザードを追加。既存 .env 読み込み、シークレット項目のマスク表示、選択肢付き入力、保存機能を提供。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パース検証、本番環境向けの追加ガードを実装。--strict モードで警告を FAIL 扱いに可能。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - 統一ログ設定ユーティリティを追加。StreamHandler（stdout）と日次ローテーションファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。LOG_DIR/LOG_LEVEL の解決順を実装し、ログディレクトリ作成失敗時はファイル出力をスキップして継続する挙動。
  - utils/process_priority.py
    - プラットフォーム差分を吸収するプロセス優先度設定と CPU affinity 設定を実装。Windows/Linux/macOS に対応し、権限不足や未対応 OS の場合は安全にスキップして警告を出力。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア重み配分 (calc_score_weights) を実装。スコア全体が 0 の場合は等金額へフォールバック。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (apply_sector_cap)、市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装。unknown セクターの扱い、レジームマップ（bull/neutral/bear）などを定義。
  - portfolio/position_sizing.py
    - 株数決定ロジック（risk_based / equal / score）を実装。単元株（lot_size）丸め、1 銘柄上限・アグリゲートキャップ、コストバッファ考慮のスケーリングと余剰分配アルゴリズムを実装。
- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB を用いたモメンタム / MA200 / ATR / 流動性等のファクター計算モジュールの骨子を追加（prices_daily / raw_financials テーブル参照の設計）。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用 SQLite を解析して稼働率、注文成功率・送信率、リスク却下数、レイテンシ（平均・最大・P95）を集計し PASS/FAIL 判定するレポートスクリプトを追加。閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200 ms）を定義。日付フィルタ対応、P95 計算、SQL のフォールバック（テーブル未存在時）を実装。
- パッケージメタ
  - __init__.py によるバージョン定義 (__version__ = "0.1.0") と主要サブパッケージの __all__ 宣言。

### 変更 (Changed)
- （初期リリースのため主要な新規追加のみ。既存ライブラリ依存の扱いと挙動を明記）
  - SQLite / DuckDB を両方採用：ランタイムで SQLite（主に状態・ログ）と DuckDB（分析・研究）を併用する設計に統一。
  - ロギング: stdout をデフォルトのストリームにし、cron 等でリダイレクトしやすい挙動に変更。

### 修正 (Fixed)
- N/A（初期リリース）

### 既知の問題 / 注意事項 (Known issues / Notes)
- research/factor_research.py は実装途中の箇所が含まれている（ファイル末尾が切れている／実装継続の余地あり）。
- apply_sector_cap:
  - price が欠損（0.0）の場合、エクスポージャーが過小に計算される旨の TODO コメントあり。将来的に前日終値などのフォールバックを検討。
- position_sizing:
  - 銘柄ごとに異なる単元株数（lot_size）に対応していない（将来的に拡張予定）。
- process_priority / set_cpu_affinity:
  - 権限不足や未対応プラットフォームでは設定がスキップされる。ログに警告が出力されるので運用者は確認のこと。
- .env の自動読み込み:
  - プロジェクトルートが特定できない場合は自動ロードをスキップする（テストや配布環境での挙動に注意）。
- セキュリティ注意:
  - .env は絶対に Git にコミットしないこと（config_setup に注記あり）。

### 今後の予定 / TODO (Planned)
- factor_research の未実装部分の完成（ファクター集計ロジックの実装とテスト）。
- ポートフォリオ単元株数を銘柄別にサポートする（stocks マスタの導入）。
- モニタリング・アラートの LINE 通知実装（現状は環境変数および検証ロジックのみ）。
- ロギング周りの更なる堅牢化（ファイルハンドラ作成失敗時の詳細なリカバリ）。

---

この CHANGELOG はソースコードの内容から推測して作成しています。実際のコミット履歴と照合して必要に応じて調整してください。