CHANGELOG
=========

フォーマット: Keep a Changelog 準拠（日本語）

Unreleased
----------
- 小規模内部改善・ドキュメントの整理（将来リリース予定）
  - テストカバレッジや静的解析に基づく微修正を予定。
  - 既存ユーティリティのエラーハンドリングを強化予定（ログの一貫化、例外メッセージの改善など）。

[0.1.0] - 2026-04-17
-------------------
Added
- 基本機能の初期実装（初回公開）。
  - 全体パッケージ: kabusys パッケージの骨格実装。__version__ = 0.1.0。
  - 設定管理:
    - Settings クラスを実装し、環境変数/.env/.env.local からの設定読み込みをサポート。
    - 自動 .env ロードはプロジェクトルート検出（.git または pyproject.toml）に基づき実行。KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化対応。
    - .env パーサを実装（export 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの取り扱い）。
    - 各種設定プロパティ（DBパス、PID/kill フラグパス、閾値、ログレベル、環境種別判定など）を提供。
    - PAPER_FILL_MODE の値検証を実装（instant/partial/never/reject）。
  - 実行エンジン:
    - run_execution スクリプトを実装。ExecutionEngine の起動フローを整備。
    - paper_trading 環境では MockBrokerClient を利用し、Paper 専用 SQLite（data/paper_trading.db）へ完全分離して記録。
    - ExecutionEngine 起動前の停止フラグ検査、スレッドでの実行、停止フラグ検知時の安全な停止処理（engine.stop()）を実装。
    - 実行プロセス用 PID ファイル管理と上限タイムアウトでのスレッド join を採用。
    - risk_manager のデフォルト構成を定義（max_position_pct 等）し、初期ポートフォリオ値をブローカーの利用可能資金から初期化。
  - 監視プロセス:
    - run_monitoring スクリプトを実装。SystemMonitor のポーリングループを起動。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔上書き（デフォルト 60 秒）。不正値時にフォールバックする検証ロジックを追加。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化（init_monitoring_db）。
    - 停止フラグファイル（data/stop_requested.flag）の存在検知による安全終了を実装。
  - ユーティリティ:
    - process_priority モジュールを実装。Windows/POSIX の差分を吸収してプロセス優先度（high/normal/low）を設定。
    - set_cpu_affinity による CPU コア固定機能を提供（アクセス権限が無い場合は警告でスキップ）。
  - ポートフォリオ構築:
    - portfolio モジュール群を実装（選定・重み付け・リスク調整・ポジションサイズ計算）。
    - select_candidates: スコア降順かつ signal_rank によるタイブレークで候補を選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア加重配分（スコア全0 の場合は等配分にフォールバック）。
    - apply_sector_cap: セクター集中制限を適用し、既存ポジションのセクター比率に基づき当該セクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム (bull/neutral/bear) に応じた投下倍率を返す。未知レジームは 1.0 でフォールバック（警告ログ）。
    - calc_position_sizes: allocation_method("risk_based","equal","score") に基づく株数計算。単元株（lot_size）丸め、per-position / aggregate cap、cost_buffer を考慮したスケーリングロジックを実装。
  - 研究・リサーチ:
    - research パッケージにファクター・研究用関数を実装。
    - factor_research: calc_momentum, calc_volatility, calc_value — DuckDB の prices_daily/raw_financials を参照してモメンタム・ボラティリティ・バリュー系ファクターを計算。
    - feature_exploration: calc_forward_returns（将来リターン）、calc_ic（Spearmanランク相関）、factor_summary（基本統計量）、rank（同順位に対して平均ランクを付与）を実装。
    - 実装方針として DuckDB 接続を受け取り標準ライブラリのみで計算（pandas 等非依存）を採用。
  - AI ニューススコアリング:
    - ai.news_nlp モジュールを実装（OpenAI API を利用したニュースセンチメント解析）。
    - ニュース時間ウィンドウ（JST基準）を定め、それに基づき raw_news を銘柄毎に集約して最大文字数・記事数でトリム。
    - バッチ送信（最大 20 銘柄／回）、JSON Mode 出力のバリデーション、スコアを ±1.0 にクリップ、部分成功時のテーブル更新戦略（削除→挿入を対象コードに限定）などの設計を採用。
    - API キー未設定時は例外を投げるバリデーションを実装。
  - ツール:
    - tools.paper_verification_report スクリプトを追加。paper_trading DB を解析して稼働率・注文成功率・送信率・レイテンシ（P95 等）を算出し、PASS/FAIL 判定（閾値はコード内に定義）を標準出力に表示。
    - P95 計算、日付フィルタ、DB 存在チェック、SQL の OperationalError に対するフォールバックを実装。
  - DB:
    - DuckDB 接続サポートを導入（duckdb 接続オブジェクトを各所で受け取る設計）。
    - 監視/Execution 起動時に init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。
  - ロギング:
    - 各モジュールで情報・デバッグ・警告ログを追加し、起動環境や主要イベント（起動・停止・例外）を出力。

Changed
- N/A（初回リリースのため、変更履歴はなし）。

Fixed
- N/A（初回リリースのため、修正履歴はなし）。

Deprecated
- なし

Removed
- なし

Security
- OpenAI API キー未設定時の早期エラーを導入（news_nlp）。機密キーは環境変数または明示引数で供給する必要あり。

Notes / Implementation details
- .env 読み込みは既存 OS 環境変数を保護する仕組み（protected set）を採用。`.env.local` は OS 環境変数を上書きするが、OS 側で既にセットされているキーは上書きしない。
- prices_daily / raw_financials 等の時系列処理は DuckDB のウィンドウ関数を多用して効率化を図っている。ホライズン計算ではカレンダーバッファを設けることで週末/祝日を吸収。
- いくつかの箇所に TODO コメント（例: price フォールバック、lot_size の銘柄別対応）が残っており、将来的な拡張余地を示唆。
- 実行時の優先度設定・CPU affinity 設定は権限が不足する環境では警告ログを出して安全にスキップする設計。

Contributing
- バグ報告・機能要望は Issue を立ててください。PR は small, focused, and well-tested を推奨します。

ライセンス
- リポジトリ内のライセンスファイル（存在する場合）を参照してください。