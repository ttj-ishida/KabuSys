# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは "Keep a Changelog" に準拠します。  
日付はコミットから推測した現在日付（2026-04-18）を使用しています。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
初回リリース。以下の主要機能・モジュールが追加されました。

### 追加 (Added)
- 起動スクリプト
  - run_execution.py
    - ExecutionEngine を起動する CLI スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は専用の paper_trading DB を使用し、MockBrokerClient を利用することで本番 DB と完全分離。
    - 停止制御用の stop flag（data/stop_requested.flag）検知と PID ファイル管理をサポート。
    - エンジンは別スレッドで実行し、停止フラグ検知で安全に停止する仕組みを実装。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は本番の sqlite_path を環境にかかわらず使用（監視データは本番 DB へ記録）。
    - 停止フラグ検知でループを終了し、KeyboardInterrupt に対応。

- 設定・環境管理
  - config.py
    - 環境変数ラッパー Settings を実装。J-Quants トークン・kabu API・DB パス・監視閾値などをプロパティで取得。
    - プロジェクトルート自動検出（.git / pyproject.toml）に基づく .env 自動読み込み機能を追加（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env のパースは export 形式や引用符、インラインコメントに対応。
  - config_setup.py
    - インタラクティブな .env 作成/更新ウィザードを追加。必須項目・デフォルト値・シークレット入力対応。
    - .env ファイルの安全なテンプレート出力（.env を Git にコミットしない旨のコメントを含む）。
  - validate_config.py
    - 起動前の設定検証 CLI を追加。必須環境変数確認、KABUSYS_ENV/LOG_LEVEL 検証、DB パスや config/*.yaml の存在チェック、live 環境での追加ガード等を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナル選定（スコア降順、タイブレークルール）select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全銘柄スコアが 0 の場合は等金額にフォールバック）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap（既存保有のセクター比率に応じて候補を除外）。
    - レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear をサポート、未知はフォールバック）。
  - portfolio/position_sizing.py
    - 発注株数計算 calc_position_sizes（risk_based / equal / score の配分方式）。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap（利用可能現金に対するスケールダウン）と残差処理を実装。

- ユーティリティ
  - utils/logging_setup.py
    - 共通ログ初期化関数 setup_logging を追加。StreamHandler（stdout）と日次ローテーションの TimedRotatingFileHandler をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決ルールとディレクトリ作成失敗時のフォールバックを実装。
  - utils/process_priority.py
    - クロスプラットフォームでのプロセス優先度設定（Windows の priority class / POSIX の nice）と CPU affinity 設定ユーティリティ。
    - 権限不足時に安全にスキップするよう例外をハンドリング。

- 実行・監視のための DB 初期化フック
  - monitoring.monitoring_db.init_monitoring_db を起動時に呼び出し、監視テーブルの存在を保証（冪等処理）。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - ペーパートレード用 SQLite（デフォルト data/paper_trading.db）から統計を集計し、稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）などを出力するレポート生成スクリプトを追加。
    - 閾値（稼働率 99%、成功率 90% 等）を用いた PASS/FAIL 判定を実装。

- 研究用モジュール（基盤）
  - research/factor_research.py
    - ファクター計算の骨子と定数（Momentum / Value / Volatility / Liquidity）を追加。DuckDB を受け取り prices_daily / raw_financials を参照する設計。

### 変更 (Changed)
- パッケージ初期化
  - __init__.py にバージョン 0.1.0 を設定。

### 修正 (Fixed)
- 環境ファイル読み込み
  - .env パーサーの堅牢化（export プレフィックス、引用符内のエスケープ、インラインコメントの扱い）を実装し、実運用での .env 解析ミスを低減。

### ドキュメント / 注意事項 (Notes)
- .env ファイルは絶対に Git にコミットしないことを .env テンプレートに明示。
- run_monitoring は監視データとして本番 sqlite_path を使用するため、環境に応じた DB 分離が必要な場合は設定を見直してください。
- position_sizing や apply_sector_cap にいくつかの TODO/注意点あり：
  - apply_sector_cap: price が欠損（0.0）の場合にエクスポージャーが過少見積もられるリスクがあるため、将来的に前日終値等のフォールバック実装を検討。
  - position_sizing: 銘柄ごとの lot_size を将来的にマスタで管理する拡張を想定（現在は単一の lot_size を想定）。
- logging_setup はログディレクトリ作成に失敗した場合でもコンソール出力は保証する設計。

### セキュリティ (Security)
- 環境変数の必須項目（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD）は validate_config でチェック。config_setup のテンプレートはシークレット項目をマスクして扱う。
- KABUSYS_ENV=live の場合、LINE 通知設定等の不備に対して警告を出す保護策を実装。

---

今後の改善候補（非網羅）
- per-stock lot_size 対応（stocks マスタの導入）
- apply_sector_cap の price フォールバック実装
- factor_research の完全実装（SQL クエリ／計算ロジックの追加）
- ExecutionEngine / SystemMonitor の単体テスト強化とエラーハンドリングの一層の堅牢化

---
参考: この CHANGELOG はコードベースの内容から推測して作成しています。実際のコミット履歴やリリースポリシーに応じて適宜調整してください。