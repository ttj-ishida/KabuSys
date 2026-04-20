# Changelog

すべての変更は Keep a Changelog 準拠で記載しています。  
このプロジェクトの初期リリースを記録しています。

## [0.1.0] - 2026-04-20

### 追加 (Added)
- 基本パッケージとバージョン情報を追加
  - パッケージのバージョンを `__version__ = "0.1.0"` として定義 (src/kabusys/__init__.py)。

- 起動スクリプト / デーモン類
  - 実行エンジン起動スクリプトを追加 (src/kabusys/run_execution.py)。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用の SQLite（`data/paper_trading.db` や環境変数で上書き可）を使用し、MockBrokerClient を利用して本番 DB と分離して実行。
    - プロセス優先度を高く設定し（set_process_priority）、ExecutionEngine をスレッドで起動。停止は data/stop_requested.flag によるポーリングで検知して安全停止する。
    - ExecutionEngine 起動前に監視テーブルの初期化を行う（init_monitoring_db）。
    - ブローカーファクトリ、OrderRepository、OrderManager、RiskManager、Reconciler 等の組み立てと設定（RiskConfig デフォルト値など）を行う。
  - システム監視ループ起動スクリプトを追加 (src/kabusys/run_monitoring.py)。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して監視データを記録。
    - プロセス優先度を高に設定、stop フラグ検出でループを終了、例外時もログ出力して次のポーリングへ継続。

- 設定 / 環境周り
  - 環境変数・設定管理クラスを追加 (src/kabusys/config.py)。
    - `.env` の自動読み込み（プロジェクトルート検出: .git または pyproject.toml を基準）機能を実装。`.env` / `.env.local` の読み込み順序と上書きルールを明確化。
    - `.env` パーサは export プレフィックス、クォート文字列、エスケープ、インラインコメント等に対応する堅牢なパーサを実装。
    - Settings クラスに多数のプロパティを提供（J-Quants token、kabu API パスワード、DB パス、paper_trading 用 DB、PID / kill flag パス、各種閾値、KABUSYS_ENV 検証、LOG_LEVEL 検証、PAPER_FILL_MODE 検証など）。
    - Paper Trading 用の `paper_sqlite_path` と `paper_fill_mode` の取り扱いを明確化（有効値チェックを実装）。

  - 環境設定ウィザードの CLI を追加 (src/kabusys/config_setup.py)。
    - 対話式で .env の初期作成・更新が可能。シークレット項目はマスク表示、選択肢・デフォルト値の提示、保存確認などを実装。
    - 出力される .env はテンプレートヘッダを含み、Git にコミットしない注意書きを挿入。

  - 設定検証 CLI を追加 (src/kabusys/validate_config.py)。
    - 必須環境変数の存在確認、KABUSYS_ENV の妥当性チェック、LOG_LEVEL のチェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・YAML パースチェック（PyYAML 未インストール時は警告でスキップ）。
    - `--strict` オプションで警告を失敗扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - ログ設定ユーティリティを追加 (src/kabusys/utils/logging_setup.py)。
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保持）を設定。
    - ログディレクトリ自動作成、作成失敗時はファイルハンドラをスキップしてコンソールログにフォールバック。
    - ログレベル・ログディレクトリの決定ロジック（引数 > 環境変数 > デフォルト）。
  - プロセス優先度 / CPU affinity ユーティリティを追加 (src/kabusys/utils/process_priority.py)。
    - Windows / POSIX の差分を吸収して優先度設定（high/normal/low）を行う。アクセス権限エラーなどは警告でスキップ。
    - CPU affinity を先頭 N コアに固定する機能も提供。

- ポートフォリオ構築関連（純粋関数群）
  - 候補選定・配分重み計算モジュールを追加 (src/kabusys/portfolio/portfolio_builder.py)。
    - select_candidates: スコア降順、タイブレークロジックを実装。
    - calc_equal_weights / calc_score_weights: 等金額配分・スコア比率配分（スコア合計が 0 の場合は等配分へフォールバック）。
  - セクター集中制限・レジーム乗数モジュールを追加 (src/kabusys/portfolio/risk_adjustment.py)。
    - apply_sector_cap: 現有ポジションからセクター別エクスポージャを計算し、上限超過セクターの新規候補を除外。unknown セクターは除外しない挙動。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームは警告を出して 1.0 でフォールバック。
  - 株数決定・リスク制限・単元丸めロジックを追加 (src/kabusys/portfolio/position_sizing.py)。
    - allocation_method に基づく発注株数算出（risk_based / equal / score）。
    - 単元株（lot_size）での丸め、1銘柄上限・aggregate cap のスケーリング、cost_buffer を使った保守的見積もり、残差処理による追加配分ロジック等を実装。
  - portfolio パッケージの __init__ を整備して主要関数をエクスポート。

- 研究・ファクター計算
  - ファクター計算モジュール（Momentum 等）のスケルトンを追加 (src/kabusys/research/factor_research.py)。
    - Momentum のための定数（1M/3M/6M、MA200、ATR など）を定義。DuckDB 接続を受けて prices_daily / raw_financials を参照する設計方針を明記。
    - （注）ファイルの末尾で計算ロジックの実装が続く設計になっている（現状一部実装）。

- ツール: Paper Trading 検証レポート
  - 検証レポート生成スクリプトを追加 (src/kabusys/tools/paper_verification_report.py)。
    - Paper Trading の SQLite DB から稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、P95 レイテンシ等を集計してレポートを出力。
    - 基準値（稼働率 99%・fill 90%・send 95%・P95 latency 200 ms）と PASS/FAIL 判定ロジックを実装。
    - 日付フィルタ（--from / --to）、DB パスの指定（環境変数または --db）をサポート。

### 変更 (Changed)
- （初期リリースのため該当なし）

### 修正 (Fixed)
- （初期リリースのため該当なし）

### 削除 (Removed)
- （初期リリースのため該当なし）

### セキュリティ (Security)
- （初期リリースのため該当なし）

注:
- 本 CHANGELOG はソースコードの実装内容から推測して作成しています。実際の仕様や将来の変更に伴い記述は更新されます。