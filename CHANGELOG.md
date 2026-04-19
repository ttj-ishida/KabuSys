# Changelog

すべての重要な変更は Keep a Changelog の仕様に従って記載します。  
変更履歴は主にコードベースから推測して記述しています。

## [0.1.0] - 2026-04-19

### 追加
- 初期リリース。
- 実行用エントリスクリプトを追加:
  - run_execution.py — ExecutionEngine 起動スクリプト。  
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading 用 SQLite（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient を利用して本番 DB と分離。
    - ブローカークライアント生成を BrokerClientFactory に委譲。
    - ExecutionEngine を別スレッドで実行し、data/execution.pid に PID を書き込む仕組み（停止フラグ検知で engine.stop() を呼ぶ）。
    - RiskManager の既定値（max_position_pct=0.20, max_utilization=0.80, rate_limit_per_sec=5, circuit_breaker_errors=10 等）を組み込み。
  - run_monitoring.py — SystemMonitor ポーリングループ起動スクリプト。  
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を使用（監視テーブルの初期化を保証）。
    - 停止フラグ（data/stop_requested.flag）検知で安全にループを終了。
- 環境設定関連ツールを追加:
  - config_setup.py — .env を対話式に作成/更新するウィザード。主要キーやデフォルトが定義され、秘匿項目はマスクして表示。保存時にテンプレート形式で .env を書き出す。
  - validate_config.py — 起動前設定検証 CLI。必須環境変数や config/*.yaml の存在・パースチェック、KABUSYS_ENV のガードなどを行い、--strict で警告を失敗扱いにできる。
- 設定/環境読み込み基盤:
  - config.py に Settings クラスを実装。.env 自動ロード機能（プロジェクトルート検出に .git / pyproject.toml を使用）と堅牢な .env パーサ（引用符・エスケープ・inline コメント等に対応）を実装。
  - Settings による各種設定プロパティ（duckdb/sqlite/paper_sqlite パス、pid/kill flag、閾値、env/log_level 判定、paper_fill_mode 等）を提供。
- ロギング/プロセス制御ユーティリティ:
  - utils/logging_setup.py — 共通ログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保存）をルートロガーへ設定。LOG_DIR / LOG_LEVEL の解決順をサポートし、ディレクトリ作成失敗時は安全にフォールバック。
  - utils/process_priority.py — プロセス優先度（high/normal/low）設定と CPU affinity 固定機能を追加。Windows / POSIX の差分を吸収し、権限不足等は警告でスキップ。
- ポートフォリオ構築モジュール（純粋関数群）を追加:
  - portfolio/portfolio_builder.py:
    - select_candidates: スコア降順・タイブレークで候補選定。
    - calc_equal_weights, calc_score_weights: 等分配・スコア重み配分。スコアが全て 0 の場合は等配分へフォールバック。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（既存ポジションに基づくフィルタリング）。"unknown" セクターは制限を適用しない。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた資金乗数を提供（未知値は警告のうえ 1.0 フォールバック）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応。単元株（lot_size）丸め、per-position と aggregate のキャップ、コストバッファ考慮、available_cash によるスケールダウンロジックを実装。
- Paper Trading 検証ツール:
  - tools/paper_verification_report.py — Paper Trading の検証レポート生成スクリプトを追加。  
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、レイテンシ（P95）を集計し PASS/FAIL 判定（閾値: 稼働率 99%, 成功率 90%, 送信率 95%, P95 レイテンシ 200 ms）。
    - コマンドライン引数 --from / --to / --db と環境変数 PAPER_TRADING_SQLITE_PATH をサポート。
- research パッケージにファクター計算モジュールの骨格を追加:
  - research/factor_research.py に Momentum 等の指標計算ロジック（設計方針、定数、calc_momentum の実装着手）を追加（DuckDB を用いた prices_daily / raw_financials 参照を想定）。

### 変更
- パッケージ初期化:
  - kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" と公開モジュール一覧を追加。
- DB 接続の取り回しを統一:
  - run_execution と run_monitoring で duckdb / sqlite 接続を利用するように統一（監視テーブル存在確認のための init_monitoring_db 呼び出しを追加）。
- ログ設定のデフォルトを明確化:
  - ログ出力は stdout を用いる設計（cron 等からのリダイレクトを想定）、ログローテーションと保持日数（30日）をデフォルトに設定。

### 修正（バグ修正・耐障害性向上）
- 環境変数パーシングの堅牢化:
  - export プレフィックス、引用符内のバックスラッシュエスケープ、インラインコメントの取り扱いなどに対応し、.env の読み込みミスを軽減。
- process_priority / set_cpu_affinity での例外処理強化:
  - 権限不足・未実装 API 等で発生するエラーを捕捉し、警告ログを出して処理継続するように改善。
- run_monitoring のポーリングループでの例外耐性を強化:
  - monitor.check_once() が例外を投げても監視ループ全体が停止しないように logger.exception でログ化して続行。
- config_setup/validate_config の UX 改善:
  - config_setup の対話時にシークレット値はマスク表示、既存 .env の読み込みと Enter による再利用をサポート。validate_config は PyYAML 未インストール時に YAML 検証をスキップして警告を出す。

### 既知の制限・注意点
- research/factor_research.py の一部関数は実装途中（ファイル末尾が切れている）であり、完全なファクター計算パイプラインは未完成。DuckDB テーブル構成に依存するため、実運用前にテーブルスキーマの確認が必要。
- position_sizing の価格フォールバック（価格欠損時の扱い）は TODO コメントを残しており、欠損価格があると過小見積りとなる可能性あり。
- run_monitoring は監視用 DB に常に本番 sqlite_path を使う設計のため、テスト用途では意図せず本番 DB にアクセスしないよう注意が必要。

### セキュリティ
- シークレット項目（J-Quants トークン、kabu API パスワード、LINE トークンなど）は .env に平文で保存する設計。`.env` の Git へのコミットを絶対に避ける旨を config_setup のヘッダに明記。
- 実行前に validate_config.py で本番環境向けの警告（LINE 通知未設定や Kill Switch 設定等）を確認することを推奨。

---

将来的なリリースでは、research モジュールの完成、単体テスト・統合テストの整備、銘柄ごとの lot_size 対応や価格フォールバックの実装などを予定しています。