CHANGELOG
=========

すべての重要な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠します。
タグ付けは SemVer を想定します。

Unreleased
----------

- 予定/検討中
  - 銘柄ごとの単元株（lot_size）をマスタから読み込む対応（現在はグローバルな lot_size=100 固定）
  - sector_exposure の price 欠損時フォールバック（前日終値や取得原価など）の導入
  - psutil が未インストールの場合のフォールバックや依存軽量化
  - 監視（monitoring）を環境ごとの DB を使うオプション化（現状は監視は常に本番 sqlite_path を使用）
  - テスト・CI の充実、ドキュメントの追加

[0.1.0] - 2026-04-18
-------------------

Added
- 初回公開（ライブラリバージョン: 0.1.0）。
- 実行・運用向けエントリポイント
  - run_execution.py: ExecutionEngine 起動用スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は専用のペーパートレード DB（デフォルト: data/paper_trading.db）を使用し、MockBrokerClient 経由で発注を模擬。
    - 実行用 PID ファイル管理、停止フラグ（data/stop_requested.flag）による安全停止、バックグラウンドスレッドでのセッション実行を実装。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker 等）を含む組み立てを提供。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止フラグ検知でループを終了、KeyboardInterrupt による終了処理をサポート。
    - 監視用 DB 初期化（init_monitoring_db）および DuckDB 接続を確立。
    - 起動時にプロセス優先度を "high" に設定するフックを追加。

- 設定管理
  - config.py: 環境変数の読み込み・管理モジュールを追加。  
    - プロジェクトルート（.git または pyproject.toml）から自動的に .env/.env.local を読み込み（自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどをサポート。
    - Settings クラスを提供し、必要な設定（J-Quants, kabu API, DB パス, 監視閾値等）をプロパティ経由で取得・検証。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証を実装。
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。
    - 秘密値マスク表示、既存 .env の読み込み、書式化された .env 出力を提供。
    - .env を Git にコミットしない旨の注意文を含むテンプレート出力。

- 設定検証ツール
  - validate_config.py: 起動前チェック用 CLI を追加。
    - 必須・任意の環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの存在確認（親ディレクトリ有無の警告）を実装。
    - config/*.yaml の存在チェックおよび PyYAML がある場合はパース検証を実行。PyYAML 未インストール時は警告を出力。
    - --strict モードで警告をエラー扱いにできる。

- ポートフォリオ構築（純粋関数群）
  - portfolio.portfolio_builder: 候補選定、等金額配分、スコア加重配分を実装（select_candidates, calc_equal_weights, calc_score_weights）。
    - スコア合計が 0 の場合は等分配にフォールバックし警告を出す。
  - portfolio.risk_adjustment: セクター集中制限とレジーム乗数を実装（apply_sector_cap, calc_regime_multiplier）。
    - 未知のレジームはフォールバック（1.0）し警告を出力。
    - セクター "unknown" は上限適用対象外。
  - portfolio.position_sizing: 発注株数計算を実装（calc_position_sizes）。  
    - allocation_method="risk_based"/"equal"/"score" をサポート。
    - 単元株（lot_size）で丸め、ポジション上限・投下資金上限・手数料等のバッファを考慮したスケーリングロジックを含む。
    - aggregate cap 超過時のスケーリングと残差処理（優先度に基づく追加配分）を実装。

- リサーチ / ファクター計算
  - research.factor_research: DuckDB を利用したモメンタム・ボラティリティ等のファクター計算関数を追加（calc_momentum, calc_volatility 等）。
    - prices_daily テーブルを前提とし、MA200、1/3/6 ヶ月リターン、ATR、出来高関連指標を計算。
    - 欠損データに対する NULL ハンドリングを実装。

- ツール
  - tools.paper_verification_report: Paper Trading の検証レポートを生成する CLI を追加。  
    - 稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（平均・最大・P95）を計算し、PASS/FAIL 判定（閾値はソース上に定義）を出力。
    - 日付レンジ指定（--from/--to）および DB パス指定（--db）に対応。

- ユーティリティ
  - utils.process_priority: プロセス優先度設定と CPU affinity を跨プラットフォームで実行するユーティリティを追加（set_process_priority, set_cpu_affinity）。  
    - Windows / POSIX（Linux, macOS, FreeBSD）向けに分岐実装。
    - 許可エラーや未サポート環境では警告を出してスキップする安全設計。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- なし

Removed
- なし

Security
- 重要: .env ファイルは決してリポジトリにコミットしないよう README／生成スクリプトに明記している。

Notes / Known issues
- position_sizing: 銘柄ごとの lot_size をサポートしておらず、将来的な拡張を検討中（TODO コメントあり）。
- apply_sector_cap: price_map に欠損（0.0）があるとエクスポージャーが過少見積りとなり、意図せずブロックが回避される可能性がある。フォールバック価格の導入を検討する必要あり（TODO コメントあり）。
- process_priority は psutil に依存する。psutil 未導入環境では ImportError が発生する可能性がある（今後の改善対象）。
- 監視モジュールは現状、KABUSYS_ENV に関わらず Settings.sqlite_path（本番想定）を使用する仕様になっているため、ペーパートレードの監視を本番 DB と完全に分離したい場合は注意が必要。

開発者向けメモ
- パーサーと設定ロードはプロジェクトルートを .git / pyproject.toml で探索するため、パッケージ配布後も想定どおり動作する設計。
- validate_config は PyYAML の有無で挙動を分岐するため、YAML 検証を有効にするには PyYAML をインストールすること。
- 各 CLI は直接実行可能（python -m kabusys.<module>）を意図している。

--- 
（この CHANGELOG はコード内のドキュメント・コメント、CLI 仕様、定義済み定数、TODO コメント等から推測して作成しています。実際の変更履歴やリリースノートと差異がある場合は、差分に基づき適宜更新してください。）