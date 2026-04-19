Keep a Changelog に準拠した形式で、コードベースから推測した変更履歴を日本語で作成しました。

CHANGELOG.md
-------------

All notable changes to this project will be documented in this file.

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-19
初回リリース（推定）。以下の機能・モジュールを実装。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを src/kabusys/__init__.py の __version__ = "0.1.0" として定義。

- 設定管理
  - 環境変数・.env ファイルを自動読み込みする設定モジュールを追加（src/kabusys/config.py）。
    - プロジェクトルート検出（.git または pyproject.toml による）。
    - .env / .env.local の読み込み順序、OS 環境変数の保護（protected）に対応。
    - export KEY=val、クォート文字列やエスケープ、行内コメントの考慮など堅牢なパース実装。
    - Settings クラスにより各種設定（J-Quants、kabu API、DB パス、Paper Trading 関連、監視閾値、環境種別等）をプロパティとして取得可能。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。

- 設定支援ツール
  - インタラクティブ .env 作成/更新ウィザード（src/kabusys/config_setup.py）を追加。
    - シークレット入力のマスク、選択肢・デフォルト、既存値の再利用、.env の書き込み機能を提供。
    - .env を生成する際にコミットしない旨を明記するヘッダを付与。

- 設定検証 CLI
  - 起動前に .env と config/*.yaml の妥当性を検証する CLI（src/kabusys/validate_config.py）を追加。
    - 必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の妥当性確認、DB パスや config ファイル存在確認、ライブ環境向けのガードチェック等を実行。
    - --strict オプションで警告をエラー扱いにできる。

- 実行系エントリポイント
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
    - プロセス優先度を高（High）に設定して起動。
    - KABUSYS_ENV=paper_trading の際は paper_trading 専用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler 組み立て。
    - ExecutionEngine をスレッドで起動し、stop flag (data/stop_requested.flag) に基づく安全停止をサポート。
    - PID ファイルパス指定とクリーンな DB 接続クローズを提供。

- 監視系エントリポイント
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV に関わらず production 相当の sqlite_path を使用する設計（監視データを本番 DB に集約）。
    - 停止フラグ検知によるループ終了、check_once の例外ハンドリング、起動時のプロセス優先度設定を実装。

- ログ / プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
    - コンソール出力（stdout）と日次ローテートファイル（TimedRotatingFileHandler）をルートロガーに設定。
    - LOG_DIR / LOG_LEVEL の解決順、ログディレクトリ自動作成、ファイル作成失敗時はコンソールのみへフォールバック。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分吸収（psutil 経由）、nice 値設定、CPU affinity 設定、権限不足時は警告でスキップ。

- ポートフォリオ構築モジュール（純粋関数群）
  - 銘柄選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレーク）、等金額 / スコア重み計算（スコア全0の場合は等分にフォールバック）。
  - セクター制約・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有比率に基づくセクター除外、unknown セクターはスキップ）、calc_regime_multiplier（bull/neutral/bear マップ、未知は警告でフォールバック）。
  - ポジションサイズ算出（src/kabusys/portfolio/position_sizing.py）
    - allocation_method に応じた株数算出（risk_based / equal / score）、lot_size 単位丸め、max_position_pct / max_utilization / cost_buffer を考慮した aggregate cap スケーリングロジック、スケーリング後の残差配分アルゴリズムを実装。

- 研究・ファクター計算枠組み
  - ファクター計算モジュール（src/kabusys/research/factor_research.py）を追加（設計・定数・モジュール説明あり）。
    - Momentum / Value / Volatility / Liquidity の計算方針を定義。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計。
    - モメンタム計算関数（calc_momentum）の実装開始（ファイル末尾で途中まで実装が見える）。

- ツール
  - Paper Trading の検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
    - 稼働率・注文成功率・送信率・レイテンシ (avg/max/P95) 等を集計し、PASS/FAIL 判定を出力。
    - P95 計算、日付フィルタ、DB パス解決（コマンドラインオプション / 環境変数 / デフォルト）に対応。

### 変更 (Changed)
- 環境変数/設定の取り扱いを強化
  - .env のパースロジックを強化し、クォート内のバックスラッシュエスケープや inline コメント規則を明確化。
  - .env.local を .env の上書きとして読み込む処理を採用（OS 環境変数は保護）。

- ロギングのデフォルト動作
  - stdout を StreamHandler に使用（stderr ではない）、cron 等からのリダイレクトに配慮。
  - ファイルハンドラは日次ローテーション（30 日分保持）。

- 実行フローの安全性向上
  - run_execution / run_monitoring で起動直後にプロセス優先度を設定。
  - 停止フラグ (data/stop_requested.flag) による停止の共通仕様を採用。

### 修正 (Fixed)
- 不正な MONITOR_POLL_INTERVAL の扱い
  - 0 以下や数値以外の値が指定された場合にデフォルトにフォールバックし、警告ログを出力するように変更（run_monitoring.py）。

- 環境ロードにおけるファイル読み込み障害
  - .env ファイル読み込み失敗時に警告（warnings.warn）を出してスキップする実装により起動失敗を防止（config._load_env_file）。

- 実行停止時のリソース解放
  - DB 接続（sqlite3 / duckdb）を finally ブロックで確実にクローズするようにしてリソース漏洩を防止（run_execution.py / run_monitoring.py）。

### 注意点 / 既知の制限 (Known issues)
- factor_research.py は設計と一部関数実装（モメンタム計算の途中）まで記述があるが、ファイル末端で途中になっている箇所が確認されるため完全実装は要確認。
- position_sizing や apply_sector_cap において、価格情報が欠損（0.0）だとエクスポージャーや算出結果が過少/過大評価される可能性があり、将来的に前日終値等のフォールバックを検討する旨の TODO コメントが残されている。
- PyYAML がインストールされていない場合は config/*.yaml のパース検証がスキップされる（validate_config.py）。

### セキュリティ (Security)
- .env ファイルの生成ヘッダに「.env を絶対に Git にコミットしないこと」を明記。
- シークレット扱いの設定はウィザードでマスク表示するが、書き出し時は平文で .env に保存されるため、運用時はファイルアクセス権管理を推奨。

---

今後の提案（所見）
- factor_research の未完部分を完成させ、ユニットテストを追加する。
- position_sizing の lot_size を銘柄別にサポートする拡張（stocks マスタ参照）を実装する。
- run_monitoring/run_execution の監視・再起動戦略（Supervisor/ systemd 連携等）をドキュメント化する。
- PyYAML 依存に対する要件・インストール手順を README に追記する。

（以上、コード内容から推測してまとめました。必要であれば項目の追記・修正・英語版作成も対応します。）