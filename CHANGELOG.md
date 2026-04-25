# CHANGELOG

すべての変更は Keep a Changelog（https://keepachangelog.com/ja/1.0.0/）に準拠して記述しています。  
バージョンはセマンティックバージョニングを想定しています。

## [Unreleased]
- なし（現状のリポジトリ状態は v0.1.0 の初期公開相当の機能群を表します）

## [0.1.0] - 初期リリース
リポジトリの初期実装。自動売買システム「KabuSys」のコアユーティリティ、起動スクリプト、ポートフォリオ構築ロジック、設定管理、検証ツールなどを含む。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを定義: __version__ = "0.1.0"（src/kabusys/__init__.py）。

- 起動スクリプト
  - run_execution (src/kabusys/run_execution.py)
    - ExecutionEngine を立ち上げるエントリポイント。プロセス優先度設定、DB接続、ブローカークライアント生成、OrderManager / RiskManager / Reconciler の組み立て、別スレッドでエンジン実行、停止フラグ検出により安全停止。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db 等）を使用して本番 DB と分離。
    - 起動時 pid ファイルの指定と停止フラグ（data/stop_requested.flag）での制御をサポート。

  - run_monitoring (src/kabusys/run_monitoring.py)
    - SystemMonitor のポーリングループ起動スクリプト。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境（KABUSYS_ENV）にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。

- 設定管理・支援ツール
  - Settings クラス (src/kabusys/config.py)
    - 環境変数を高水準に参照するユーティリティ。デフォルト値、バリデーション（KABUSYS_ENV / LOG_LEVEL 等）、パスの Path 変換、paper_trading 用設定などを提供。
    - PAPER_FILL_MODE のバリデーションや paper_sqlite_path、kill/ pid ファイルパス、しきい値（CPU/MEM/DISK）などの getter を実装。
    - 自動 .env ロード機能:
      - プロジェクトルートを .git または pyproject.toml から自動検出し、.env / .env.local をロード（OS 環境変数は保護）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。

  - 環境設定ウィザード (src/kabusys/config_setup.py)
    - 対話式ウィザードで .env を作成・更新する CLI。必須項目（J-Quants、kabu API など）やオプション項目を扱う。既存 .env の読み込み・表示、保存機能を実装。

  - 設定検証 CLI (src/kabusys/validate_config.py)
    - .env と config/*.yaml の事前検証ツール。必須環境変数の存在確認、KABUSYS_ENV / LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在チェック、PyYAML の有無に応じた YAML パース検証、KABUSYS_ENV=live 時の追加ガードチェックを実装。
    - --strict オプションで警告も失敗扱いにできる。

- ロギング & プロセス制御ユーティリティ
  - logging_setup (src/kabusys/utils/logging_setup.py)
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（daily, 30日保持）を設定する共通ユーティリティ。
    - LOG_DIR/LOG_LEVEL の解決順をサポート。既存ハンドラのクリーンアップを行い二重設定を防止。
    - ファイル出力に失敗した場合はコンソールログのみで継続。

  - process_priority (src/kabusys/utils/process_priority.py)
    - Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定するユーティリティ。
    - cpu_affinity 設定関数も提供。権限不足や未対応 OS の場合は警告出力してフォールバック。

- ポートフォリオ構築（純粋関数群）
  - portfolio_builder (src/kabusys/portfolio/portfolio_builder.py)
    - シグナル選定（スコア降順で上位 N）、等金額・スコア重み計算を実装。

  - risk_adjustment (src/kabusys/portfolio/risk_adjustment.py)
    - セクター集中制限を適用する apply_sector_cap と、市場レジームに応じた投下資金乗数 calc_regime_multiplier を実装。
    - 未知レジームは警告を出してフォールバック（1.0）。

  - position_sizing (src/kabusys/portfolio/position_sizing.py)
    - risk_based / equal / score の配分方式に基づく発注株数計算を実装。
    - 単元株（lot_size）丸め、1銘柄上限・aggregate cap、cost_buffer による保守的見積り、スケーリング／端数処理（残余キャッシュでの追加配分）などを実装。
    - 設計上の将来拡張（銘柄ごとの lot_size を持たせる等）に関する TODO コメントあり。

- Paper Trading 検証ツール
  - paper_verification_report (src/kabusys/tools/paper_verification_report.py)
    - ペーパートレード用 SQLite を読み込んで稼働率、注文成功率、送信率、リスク却下数、レイテンシ（平均/最大/P95）を集計・表示するレポート生成 CLI。
    - P95 計算ユーティリティ、各種閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を行う。
    - --from/--to/--db オプションをサポート。

- 研究 / ファクター計算（下地）
  - factor_research (src/kabusys/research/factor_research.py)
    - モメンタム / ボラティリティ / Value / Liquidity の計算方針と定数を定義。DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計方針を提示。
    - calc_momentum 等の実装開始（ファイル途中まで実装）。設計に関する注釈あり。

- その他
  - tools パッケージの雛形 (src/kabusys/tools/__init__.py)。
  - utils パッケージの __init__ を追加（src/kabusys/utils/__init__.py）。
  - monitoring_db 初期化フック等、監視用テーブル初期化を起動スクリプトから確実に呼ぶ実装を追加（init_monitoring_db の使用）。

### 変更 (Changed)
- N/A（初期リリース）

### 修正 (Fixed)
- N/A（初期リリース）

### 既知の制限・注意点 (Notes)
- .env ファイルの自動ロードはプロジェクトルートの自動検出に依存するため、配布後や特殊な配置では自動ロードがスキップされる場合がある。必要なら KABUSYS_DISABLE_AUTO_ENV_LOAD を使い挙動を制御可能。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存し、失敗時は警告を出して無害にフォールバックする実装。
- portfolio/risk_adjustment のセクター時価計算は一部 price が欠損した場合に過少評価する旨の TODO コメントあり（将来的なフォールバック価格の導入予定）。
- factor_research の一部関数は途中実装。ファクター計算は DuckDB のテーブル構造（prices_daily, raw_financials）に依存。

### セキュリティ
- .env は絶対にリポジトリにコミットしない旨が config_setup にて明記。

---

（この CHANGELOG はソースコードの内容から推測して作成しています。実際のリリース履歴や日付、マイナー／パッチの分割はプロジェクト運用ポリシーに従って調整してください。）