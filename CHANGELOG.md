# Changelog

すべての変更は Keep a Changelog のガイドラインに従って記載しています。  
フォーマット: https://keepachangelog.com/（日本語補足）

## [0.1.0] - 2026-04-19

初回リリース。日本株自動売買システムのコアユーティリティ群・起動スクリプト・ポートフォリオ構築ロジック・開発支援ツールを追加。

### 追加 (Added)
- パッケージ基盤
  - src/kabusys/__init__.py
    - パッケージバージョンを `__version__ = "0.1.0"` として追加。

- 設定管理
  - src/kabusys/config.py
    - .env 自動読み込み機能（プロジェクトルートの検出: .git / pyproject.toml）。
    - .env/.env.local の読み込み順、OS 環境変数の保護（上書き禁止）。
    - .env 行パーサ実装（export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメントの扱いをサポート）。
    - Settings クラスで各種設定値をプロパティ経由で提供（J-Quants / kabuステーション / DB パス / paper_trading 切替 / 監視閾値 等）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等のバリデーション）。

  - src/kabusys/config_setup.py
    - 対話式 .env ウィザード（.env の初期作成・更新支援）。
    - シークレット項目はマスク表示、選択肢チェック、.env ファイルの整形・出力。
    - .env を Git にコミットしない旨の注意書き自動出力。

  - src/kabusys/validate_config.py
    - 起動前設定検証 CLI（必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML 利用時）等の検査）。
    - 本番環境（live）向けの追加ガード（LINE 通知設定や Kill Switch の設定確認）。
    - --strict オプションで警告を失敗扱いにできる。

- 起動スクリプト / 実行制御
  - src/kabusys/run_monitoring.py
    - SystemMonitor の起動ループ実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き（デフォルト 60 秒、範囲チェックとフォールバック）。
    - 監視 DB は環境にかかわらず本番 sqlite_path を使用する設計。
    - 停止フラグファイル (data/stop_requested.flag) 検出で graceful shutdown。
    - DuckDB との接続確立および監視テーブル初期化。

  - src/kabusys/run_execution.py
    - ExecutionEngine 起動スクリプト。
    - KABUSYS_ENV=paper_trading の場合は専用の paper_sqlite_path を使用（本番 DB と分離）。
    - BrokerClientFactory によるブローカークライアント生成（環境に応じた Mock/実ブローカーの切替を想定）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てとセッションスレッド運用。
    - 停止フラグに応じた停止処理、PID ファイル管理（pidFile を Engine に渡す）。

- ロギング / プロセス管理ユーティリティ
  - src/kabusys/utils/logging_setup.py
    - 統一的ログ設定ユーティリティ。
    - stdout の StreamHandler と日次ローテーションの TimedRotatingFileHandler（logs/<app_name>.log、30日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR 環境変数や関数引数による上書き対応。
    - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで動作継続。

  - src/kabusys/utils/process_priority.py
    - プラットフォーム非依存のプロセス優先度設定ユーティリティ（Windows の priority class / POSIX の nice を吸収）。
    - set_process_priority(level: "high"|"normal"|"low") 実装（アクセス権限不足時は警告でスキップ）。
    - set_cpu_affinity(cpu_count: int | None) 実装（利用可能コア数、権限不足等の例外処理あり）。

- ポートフォリオ構築（純粋関数群）
  - src/kabusys/portfolio/portfolio_builder.py
    - select_candidates: スコア降順 + タイブレークルールで候補抽出。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア合計0で等配分へフォールバック）。

  - src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中を抑えるための候補フィルタ（既存保有時価を計算、unknown セクターは上限非適用）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をマッピング、未知レジームはフォールバックと警告）。

  - src/kabusys/portfolio/position_sizing.py
    - calc_position_sizes: 各銘柄の発注株数算出（allocation_method='risk_based' / 'equal' / 'score' をサポート）。
    - risk_based: 損切り幅・リスク許容率からベース株数を計算、lot_size（単元株）丸め、per-stock 上限と aggregate cap（available_cash）によるスケーリング実装。
    - aggregate cap のスケールダウン時に残差処理を行い、lot 単位で追加配分を行うロジックを実装。
    - cost_buffer による手数料/スリッページ見積り反映、価格欠損時のスキップ・ログ出力。

  - src/kabusys/portfolio/__init__.py
    - 上記関数をパッケージ API として公開。

- 研究 / ツール
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールのスケルトンとモメンタム計算ロジックの導入（DuckDB 経由で prices_daily / raw_financials テーブルを参照する設計）。
    - モメンタム（1M/3M/6M）、MA200 乖離、ATR、出来高指標等を想定した定数と関数雛形を追加（実装は一部）。
    - 設計方針: DuckDB SQL + Python、外部 API 非依存、結果は (date, code) キーの dict リストで返す。

  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成 CLI。
    - PAPER_TRADING_SQLITE_PATH（または --db）から DB を読み、稼働率（uptime）、注文成功率（fill rate）、送信率、P95 レイテンシ等を集計。
    - 基準値（uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms）に基づく PASS/FAIL 判定。
    - 日付フィルタ（--from / --to）対応。空データやテーブル欠損時の堅牢なハンドリング。

- その他
  - src/kabusys/utils/__init__.py, src/kabusys/tools/__init__.py を追加（パッケージ初期化）。

### 変更 (Changed)
- なし（初回公開のため参照なし）。

### 修正 (Fixed)
- なし（初回公開のため参照なし）。

### 注意点 / 既知の制約 (Known issues)
- config.py の自動 .env 読み込みはプロジェクトルート検出に依存する（.git / pyproject.toml）。配布後にプロジェクトルートが見つからない場合は自動ロードをスキップする。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使用する設計のため、paper_trading 環境での監視用 DB 分離が必要な場合は設定変更が必要。
- 一部モジュール（research/factor_research.py）は実装途中（ファイル末尾が途中で切れている）であり、完全なファクター計算ロジックは今後の作業を予定。
- process_priority / set_cpu_affinity の呼び出しは権限やプラットフォームに依存し、失敗した場合は警告でスキップする設計。

---

今後の予定（例）
- factor_research の完全実装（Momentum、Volatility、Value、Liquidity 等の集計と正規化）。
- ExecutionEngine / BrokerClient の単体テスト強化、モッククライアント挿入の明示化。
- モニタリング・アラート（LINE 通知等）連携の拡充。
- ドキュメント（PortfolioConstruction.md 等）と自動テストの追加。

もし CHANGELOG に特定の追加項目（公開日や細かい実装差分）を追記したい場合は、知らせてください。必要に応じて日付やカテゴリを調整します。