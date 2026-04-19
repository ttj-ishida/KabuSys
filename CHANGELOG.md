# Changelog

すべての notable な変更点を Keep a Changelog の形式で日本語で記載します。  
このログは与えられたコードベースの内容から推測して作成しています（実装上のコメントや TODO、デフォルト値、CLI ヘルプなどを根拠に記載）。

最新版: 0.1.0 (初版)

## [Unreleased]

- （現時点で未リリースの変更はありません。次バージョンで追加予定の注意点は下部の「既知の制限 / TODO」に記載しています）

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 全体
  - パッケージ初版リリース。日本株自動売買システム「KabuSys」の基本ユーティリティ・実行スクリプト群を提供。

- 設定・起動
  - Settings クラス（kabusys.config）を実装：
    - 環境変数経由の設定取得を統一的に管理（例: KABUSYS_ENV, LOG_LEVEL, DUCKDB_PATH, SQLITE_PATH, PAPER_FILL_MODE 等）。
    - 必須変数取得用の _require() を提供（未設定時に明示的なエラーを送出）。
    - env 判定用の is_live / is_paper / is_dev プロパティを提供。
  - .env 自動読み込み機能を追加：
    - プロジェクトルート（.git または pyproject.toml を探索）を基準に .env / .env.local を自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env の行パーサは export 文やクォート、インラインコメントなどに堅牢に対応。
  - 対話式設定ウィザード（kabusys.config_setup）を追加：
    - .env の生成・更新を支援する CLI。主要な設定項目（環境、API トークン、DB パス、ログレベル、Kill Switch 設定等）を対話形式で入力可能。
  - 設定検証 CLI（kabusys.validate_config）を追加：
    - 必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスや config/*.yaml の存在・パースチェックを行う。
    - --strict モードで警告を fail 扱いにできる。

- 実行・監視ランナー
  - 実行エンジン起動スクリプト（kabusys.run_execution）を追加：
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを生成。OrderRepository / OrderManager / RiskManager / Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）と PID 管理（data/execution.pid）に対応。停止フラグ検知で安全停止処理を実行。
    - RiskManager にデフォルト設定を注入（max_position_pct 等）。initial_portfolio_value を broker.get_available_cash() から取得。
  - 監視ループ起動スクリプト（kabusys.run_monitoring）を追加：
    - SystemMonitor の poll ループを起動。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関わらず production 用 sqlite_path を使用する（Settings.sqlite_path）。
    - stop flag による終了、例外発生時にはログ出力して次ループへ継続。

- ロギング・プロセス制御
  - 共通ロギング設定ユーティリティ（kabusys.utils.logging_setup）を追加：
    - stdout 出力（StreamHandler）と日次ローテートのファイル出力（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ（デフォルト logs/）を自動作成。ファイルローテーションは最大 30 日分保持。
    - LOG_LEVEL / LOG_DIR / 引数による柔軟な設定解決。
  - プロセス優先度・CPU affinity ユーティリティ（kabusys.utils.process_priority）を追加：
    - Windows/Linux/macOS の差異を吸収してプロセス優先度（high/normal/low）を設定。CPU affinity を最初 N コアに固定する機能も提供。
    - 実行スクリプトは起動時に set_process_priority("high") を呼び出し高優先度に設定する。

- ポートフォリオ構築（純関数群）
  - portfolio モジュールを実装（kabusys.portfolio）：
    - portfolio_builder: select_candidates, calc_equal_weights, calc_score_weights を提供（シグナルのソート、等金額/スコア加重配分）。
    - risk_adjustment: apply_sector_cap（セクター集中制限、"unknown" セクターは制限を適用しない）、calc_regime_multiplier（regime に応じた乗数: bull/neutral/bear）。
    - position_sizing: calc_position_sizes（allocation_method: "risk_based" / "equal" / "score" に対応）、単元株（lot_size）で丸め、aggregate cap によるスケールダウンと端数配分ロジックを実装。
    - 各関数は DB に依存せずメモリ内で純関数として動作。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py を追加：
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から集計して検証レポートを生成。
    - 指標: 稼働率（uptime_pct）、注文成功率（fill_rate）、送信率（send_rate）、API レイテンシ（avg/max/P95）など。
    - デフォルトの合格基準（閾値）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - CLI オプション: --from / --to（日付フィルタ）、--db（DB パス上書き）。

- リサーチ / ファクター計算（着手）
  - research/factor_research モジュールを追加（ファクター計算の基盤）：
    - Momentum / Value / Volatility / Liquidity の計算方針を定義。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを算出する設計。
    - モメンタム計算（calc_momentum）を実装し始めている（ただし一部未完）。

### 変更 (Changed)
- （初版なので既存コードからの変更履歴は無し）

### 修正 (Fixed)
- （初版なのでバグ修正履歴は無し）

### 既知の制限 / TODO
- research/factor_research.calc_momentum の実装は途中で切れている（コード末尾が不完全）。完全実装が必要。
- position_sizing / apply_sector_cap の一部で「価格が欠損（0.0）の場合にエクスポージャーが過少見積りされる」旨の TODO コメントあり。前日終値や取得原価によるフォールバック価格の導入が検討事項。
- 将来的に単元株（lot_size）を銘柄ごとに扱うための設計拡張（stocks マスタに lot_size を持たせる等）が予定されている。
- logging_setup はログディレクトリ作成に失敗した場合にファイル出力をスキップするが、その場合の運用手順（権限やディレクトリの手動作成など）はドキュメント化が必要。
- validate_config は config/*.yaml の検査に PyYAML を利用するが、PyYAML 未導入時は検証をスキップして警告する挙動。CI 等では依存を明示することを推奨。

### セキュリティ (Security)
- 環境変数の取り扱いについて:
  - JQUANTS_REFRESH_TOKEN および KABU_API_PASSWORD は必須であり、Settings._require により未設定時に起動不可となる。これらは絶対に .env を Git 管理下に含めないことを README 等で強調することを推奨。
  - config_setup で生成される .env ヘッダに「.env は絶対に Git にコミットしないこと」と明記。

---

参考: パッケージ内部で使用される主要な環境変数・デフォルト値（抜粋）
- KABUSYS_ENV: development / paper_trading / live（デフォルト: development）
- LOG_LEVEL: INFO（デフォルト）
- DUCKDB_PATH: data/kabusys.duckdb
- SQLITE_PATH: data/monitoring.db
- PAPER_TRADING_SQLITE_PATH: data/paper_trading.db
- MONITOR_POLL_INTERVAL: 60（run_monitoring のポーリング間隔）
- PAPER_FILL_MODE: instant | partial | never | reject（デフォルト: instant）
- KILL_FLAG_CLEAR_ON_START: 0/1（本番で 1 は危険）

もし本 CHANGELOG をリリースノートや README に反映するなら、上の「既知の制限 / TODO」を Issue として登録し、research モジュールの未完部分や価格フォールバックなどを優先対応事項として扱うことをお勧めします。