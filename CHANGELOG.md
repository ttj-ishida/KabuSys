# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣例に従って管理します。  

フォーマット:
- Added: 新規追加機能
- Changed: 既存機能の変更
- Fixed: バグ修正や安全性向上
- Deprecated / Removed / Security: 必要時に追記

## [0.1.0] - 2026-04-19
最初の公開リリース。主要サブシステム（実行エンジン、監視、設定管理、ポートフォリオ構築、ユーティリティ、レポート生成など）を含む初期機能群を実装。

### Added
- 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）
  - ExecutionEngine を組み立てて別スレッドで実行する起動ロジックを提供。
  - ブローカークライアントを BrokerClientFactory で生成（paper_trading 環境では MockBroker を想定）。
  - paper_trading 環境では専用 SQLite（data/paper_trading.db）を使用し、本番 DB と分離。
  - 停止フラグ（data/stop_requested.flag）・PID ファイル（data/execution.pid）による安全停止をサポート。
  - duckdb を分析用 DB として接続。

- 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）
  - SystemMonitor を定期的に呼び出すポーリングループを実装。
  - 環境変数 MONITOR_POLL_INTERVAL によりポーリング間隔を上書き可能（デフォルト 60 秒）。
  - 停止フラグ検知で安全にループを抜ける。
  - 監視用 DB 初期化を行う（monitoring テーブル保証）。

- 環境設定管理・自動読み込み（src/kabusys/config.py）
  - .env の自動読み込み機能（プロジェクトルートの検出 .git / pyproject.toml 基準）。
  - エクスポート形式（export KEY=...）や引用符・エスケープ、インラインコメントの取り扱いに対応した .env パーサを実装。
  - 設定値を取得する Settings クラスを提供（DB パス、ログレベル、paper_trading 関連設定等）。
  - PAPER_FILL_MODE のバリデーション、paper_sqlite_path 等の便利プロパティ。

- 設定ウィザード CLI を追加（src/kabusys/config_setup.py）
  - 対話式に .env を作成・更新するウィザードを提供。
  - 各項目の説明、デフォルト、マスク表示（シークレット）を備え、最終確認後に .env を書き出す。

- 設定検証 CLI を追加（src/kabusys/validate_config.py）
  - 必須環境変数の存在チェック、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェックを実施。
  - config/*.yaml の存在確認と（PyYAML があれば）パース検査を行う。
  - KABUSYS_ENV=live に対する追加ガード（LINE トークン未設定や Kill Switch 設定の警告）。
  - --strict オプションで警告を FAIL 扱いにできる。

- Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）
  - ペーパートレード DB から稼働率・注文成功率・送信率・レイテンシ（P95）等の指標を集計し、判定（PASS/FAIL）を出力。
  - 日付フィルタ、DB パス指定オプションをサポート。
  - P95 計算、閾値定義（稼働率 99%、成立率 90% 等）を実装。

- ポートフォリオ構築・リスク管理関連モジュールを実装（src/kabusys/portfolio/*）
  - 銘柄候補選定（select_candidates）、等配分・スコア加重（calc_equal_weights / calc_score_weights）。
  - セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）。
  - ポジションサイズ決定ロジック（calc_position_sizes）：
    - risk_based / equal / score 方式のサポート。
    - 単元株（lot_size）丸め、per-position 上限・aggregate cap（available_cash に基づくスケーリング）、cost_buffer（手数料・スリッページ）考慮。
    - 不足データ時はスキップし、ログ出力で説明。

- ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
  - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler をルートロガーに一括設定。
  - ログディレクトリ作成に失敗した場合はファイル出力を無効化してコンソールのみで継続。
  - ログレベルとログディレクトリの解決順（引数 > 環境変数 > デフォルト）を実装。

- プロセス優先度・CPU affinity ユーティリティを追加（src/kabusys/utils/process_priority.py）
  - Windows / POSIX の差分を吸収する set_process_priority(level) を実装（"high"/"normal"/"low"）。
  - CPU affinity を最初の N コアに固定する set_cpu_affinity(cpu_count) を実装。
  - 権限不足や未対応 OS では警告を出し安全にフォールバック。

- 研究用ファクター計算モジュール（部分実装）を追加（src/kabusys/research/factor_research.py）
  - Momentum / Value / Volatility / Liquidity を計算する設計方針と定数を導入。
  - calc_momentum の骨組み（horizon 定義など）を追加（実装続行の余地あり）。

- パッケージ初期化とバージョン（src/kabusys/__init__.py）
  - __version__ = "0.1.0" を設定。

### Changed
- DB 周りの責任分離
  - 監視（monitoring）は環境に関わらずデフォルト sqlite_path を使用して監視データを記録。
  - 実行エンジンは paper_trading 環境時に paper_sqlite_path を優先して使用（本番データと分離）。

- 停止・Kill の取り扱い
  - 起動スクリプトがプロジェクトルートの data/stop_requested.flag / data/kill.flag を監視し、検出時に安全に停止する設計。
  - Settings に KILL_FLAG_CLEAR_ON_START を追加し、自動クリア挙動を設定可能に。

- .env 自動ロードの安全性向上
  - OS 環境変数を保護する protected 引数を導入し、.env.local の override を適切に制御。

- ロギングの既存ハンドラ処理
  - setup_logging は既存のハンドラを flush/close してから削除し、二重出力を防止するよう変更。

### Fixed
- .env パーサの堅牢化（src/kabusys/config.py）
  - export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの解釈を改善。
  - 不正な行を無視することで .env の柔軟性と安全性を向上。

- 起動時のファイル/ディレクトリ作成失敗時のフォールバック
  - ログディレクトリ作成やファイルハンドラ作成に失敗した場合でも、コンソールログで継続するようにし、起動が致命的に失敗しないように改善。

- Process priority / CPU affinity のエラー耐性
  - psutil による権限不足や未実装 API に対して警告を出して処理をスキップ。例外によりプロセスが落ちないように保護。

- Execution/Monitoring のリソースクリーンアップ
  - 最終処理で sqlite3 / duckdb 接続を確実にクローズするように修正（finally ブロック）。

### Notes / Known limitations
- research/factor_research.py の calc_momentum 実装が途中（コメント部分で終端）。ファクター計算ロジックの継続実装が必要。
- position_sizing は単元株数を全銘柄共通 lot_size で扱う設計（将来的に銘柄別 lot_map へ拡張予定）。
- .env の自動ロードはプロジェクトルートの検出に依存するため、配布後や特定の配置では自動ロードがスキップされる可能性がある（環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
- paper_trading 用 MockBroker の詳細実装は別モジュールに依存（BrokerClientFactory）。

---

今後の予定（例）
- factor_research の完全実装（DuckDB SQL を用いたファクター集計）。
- テスト追加（ユニットテスト・統合テスト）。
- 複数 lot_size 対応や手数料モデルの詳細化。
- モニタリングアラートの外部通知（LINE）連携強化。

もしこの CHANGELOG をより細かく（ファイルごとのコミット単位など）記載したい場合は、コミットログやリリースノートの粒度に合わせて追記します。