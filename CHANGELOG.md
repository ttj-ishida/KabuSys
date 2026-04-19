# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従って記載しています。  
このファイルは、与えられたコードベースの内容から推測して作成した初期リリース向けの変更履歴です。

## [Unreleased]
- （現時点のスナップショットでは未リリースの作業は特に明示されていません。将来的な改善点は「既知の問題 / TODO」に記載しています。）

## [0.1.0] - 2026-04-19
初回リリース。KabuSys のコアユーティリティ、実行 / 監視スクリプト、ポートフォリオ構成ロジック、および付随ツール群を導入。

### 追加 (Added)
- コアパッケージ導入
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。
- 起動 / デーモン向けスクリプト
  - run_execution.py: 実行エンジン起動スクリプトを追加。KABUSYS_ENV により paper_trading の場合は専用の MockBrokerClient と paper_trading 用 DB を使用して本番 DB と分離して実行する仕組みを提供。
  - run_monitoring.py: システム監視用ポーリングループを追加。環境変数 `MONITOR_POLL_INTERVAL` で間隔を上書き可能。停止フラグファイルで安全に停止可能。
- 設定管理
  - Settings クラス (src/kabusys/config.py): 環境変数アクセスラッパーを追加。各種デフォルト値・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を提供。
  - .env 自動ロード機能: プロジェクトルート（.git または pyproject.toml を探索）を基準に `.env` / `.env.local` を自動読み込み（ただし環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能）。
- 設定ツール / 検証
  - config_setup.py: 対話式 .env 作成ウィザードを追加（.env の初期作成・更新をサポート）。
  - validate_config.py: 起動前チェック CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在と YAML パース（PyYAML があれば実行）などを検証。`--strict` オプションで警告も失敗扱いにする。
- ロギング / プロセス制御ユーティリティ
  - logging_setup.py: 統一的なロギング設定ユーティリティを追加。StreamHandler（stdout）と日次ローテートの TimedRotatingFileHandler をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップして stdout のみで動作。
  - process_priority.py: プロセス優先度と CPU affinity 設定ユーティリティを追加。Windows / POSIX を吸収しつつアクセス拒否等を許容してフォールバックする実装。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio.portfolio_builder:
    - select_candidates: BUY シグナルのソート・上位 N 選定。
    - calc_equal_weights / calc_score_weights: 配分重み計算（スコア加重はスコア合計 0 の場合に等配分にフォールバック）。
  - portfolio.risk_adjustment:
    - apply_sector_cap: セクター集中上限チェックに基づく候補除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を提供（未知のレジームは警告の上 1.0 でフォールバック）。
  - portfolio.position_sizing:
    - calc_position_sizes: 発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score" 対応）。単元株（lot_size）丸め、1銘柄上限・全体利用上限（aggregate cap）、コストバッファ考慮、スケールダウン時の残差配分アルゴリズムを実装。
- Paper Trading 検証ツール
  - tools.paper_verification_report: Paper Trading 用の検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計し PASS/FAIL 判定を行う。閾値を定義（稼働率 99% など）。
- リサーチ基盤（スキャフォールド）
  - research.factor_research: DuckDB を用いたファクター計算の基礎を実装（モメンタム、MA200 乖離、ATR、出来高指標などを想定）。関数インターフェースと定数が定義されている（実装途中の箇所あり）。

### 変更 (Changed)
- ログ出力先の方針:
  - コンソール出力は stderr ではなく stdout を使用（cron などで stdout/stderr を一本化しやすくするため）。
- DB 接続の取り扱い:
  - 監視(run_monitoring)は KABUSYS_ENV にかかわらず本番 sqlite_path を利用する設計になっている点を明示。
  - 実行(run_execution)は paper_trading モード時に paper_sqlite_path を使用して本番 DB と分離。

### 修正 (Fixed)
- .env パーサーの堅牢化:
  - export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ処理、インラインコメントの扱い、クォートなし時のコメント認識ルールなどを実装し、実運用での .env 記述の幅を広げた。
- ログディレクトリ作成失敗時のフォールバック:
  - ディレクトリ作成に失敗した際、ファイルハンドラをスキップしてコンソール出力のみで継続するようにした（安全に起動できるように）。

### 既知の問題 / TODO
- portfolio/risk_adjustment.apply_sector_cap:
  - price_map に欠損（0.0）がある場合、エクスポージャーが過少見積りされてしまう旨の TODO が残っており、将来的に前日終値や取得原価でのフォールバックを検討する必要あり。
- research.factor_research:
  - ファクター計算モジュールはスキャフォールド状態（コード末尾で未完の箇所が存在）。完全なファクター定義と DuckDB クエリの調整が必要。
- テスト:
  - 単体テスト / 結合テストがこのスナップショットからは見つかっていないため、ユニットテストの整備が推奨される。
- 運用ドキュメント:
  - system_config.yaml 等の config ファイル生成や運用手順は validate_config や config_setup のメッセージで示唆されているが、運用ガイドとしてまとめると導入が容易になる。

---

（この CHANGELOG はコード内容からの推測に基づき作成しています。実際のコミット履歴やリリースノートがある場合は、そちらを優先して差分を反映してください。）