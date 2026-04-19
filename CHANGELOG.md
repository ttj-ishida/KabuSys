# CHANGELOG

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の形式に従います。  
バージョン番号はパッケージの __version__ （src/kabusys/__init__.py）に合わせています。

## [Unreleased]
（現在なし）

## [0.1.0] - 2026-04-19
初回リリース。

### 追加
- 基本アプリケーション構成
  - パッケージ初期化とバージョン情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。
- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite(DB) を使用して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）検出による安全停止、PID ファイル管理、スレッド実行処理を実装。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番 sqlite_path を使用する設計。
    - 停止フラグ検出でループ終了、例外発生時はログを残して次ループへ継続。
- 設定管理
  - Settings クラスを追加し環境変数・.env を統一的に取得（src/kabusys/config.py）。
    - 自動的にプロジェクトルート（.git または pyproject.toml）を探索して .env/.env.local を読み込む機能。
    - 必須項目取得ヘルパー、環境種別（development / paper_trading / live）や各種パスのプロパティを提供。
    - PAPER_FILL_MODE 等のバリデーションを実装。
  - 対話式設定ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期生成・更新を支援。秘密値のマスク表示、選択肢の提示、保存確認を実装。
- 設定検証 CLI
  - 起動前に .env と config/*.yaml の妥当性をチェックする validate_config CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在チェック、PyYAML があれば YAML のパースチェックを実行。
    - --strict オプションで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - 統一的ロギング設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - ルートロガーのハンドラを再設定（既存ハンドラのクリア）、コンソール(stdout)出力と日次ローテーションファイル出力を組み合わせ。
    - LOG_DIR / LOG_LEVEL の環境変数に対応し、ディレクトリ作成失敗時はファイル出力をフォールバック。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX の差分を吸収して優先度（high/normal/low）を設定。CPU affinity を最初の N コアに固定する関数も提供。
    - 権限不足や未対応プラットフォームでは警告を出して安全にフォールバック。
- ポートフォリオ構築モジュール
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - 候補のスコア降順ソート、等金額配分、スコア加重配分（全スコアが 0 の場合は等配分へフォールバック）。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - 既存保有に基づくセクター別エクスポージャー計算と上限超過セクターの候補除外ロジック。
    - market レジームに応じた投下資金乗数（bull/neutral/bear）と未知レジームでのフォールバック。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の割当方式をサポート。lot_size（単元株）丸め、per-position 上限、aggregate cap（利用可能現金）に基づくスケーリングと残差配分ロジックを実装。
  - 上記モジュールをまとめてエクスポート（src/kabusys/portfolio/__init__.py）。
- Research / 分析
  - ファクター計算モジュールの下地を追加（src/kabusys/research/factor_research.py）。
    - Momentum / MA200 / ATR / Volume 系の定数や calc_momentum のインターフェースと設計方針を実装（実装途中の箇所あり）。
- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - 指定期間の稼働率、注文成功率、送信率、レイテンシ（avg/max/P95）等を集計して PASS/FAIL 判定を出力。
    - DB パスはコマンドライン --db や PAPER_TRADING_SQLITE_PATH 環境変数で指定可能。しきい値はファイル内定数で管理。

### 変更（設計・挙動）
- .env 読み込み
  - .env/.env.local の自動読み込みをプロジェクトルート検出に基づいて行う（CWD に依存しない実装）。
  - export KEY=val 形式、クォート、インラインコメント、エスケープシーケンス等を考慮した堅牢なパーサを実装。
  - OS 環境変数は保護（.env.local の override を行う際にも保護）。
- ログ出力
  - コンソール出力は stdout を使用（cron/Task Scheduler でのリダイレクトを考慮）。
  - 既にハンドラが設定されている場合は一度クリアしてから再設定することで二重出力を防止。
- 監視・実行の DB 接続方針
  - 監視（monitoring）は環境に関係なく Settings.sqlite_path（本番用 path）を使用する設計。
  - 実行（execution）は paper_trading 環境時に paper_sqlite_path を使用し、DB を完全分離する設計（paper trading のログは data/paper_trading.db へ）。
- エラー耐性
  - run_monitoring のポーリング中に check_once() で例外が発生してもループを継続するようにログを残して回復する仕様。
  - 各種設定検証やレポート生成で対象テーブルが存在しない場合は sqlite3.OperationalError を捕捉してデフォルト値で継続。

### 修正（バグ修正、安定化）
- .env パーサ
  - クォート内のバックスラッシュエスケープやインラインコメントの扱いを修正し、より実用的に .env を読み込めるように改善。
- ロギングハンドラ管理
  - 既存ハンドラの flush/close を行ってから削除するように変更し、ハンドラの二重登録やリソースリークの抑制を行う。
- プロセス優先度設定
  - 未対応 OS やアクセス権限不足に対して例外ではなく警告でフォールバックするように修正。

### 注意事項 / 既知の制限
- research.factor_research.calc_momentum は実装途中の箇所（ソースの途中で切れている箇所）があり、完全なファクター計算は今後のリリースで提供予定です。
- apply_sector_cap のエクスポージャ計算は価格が欠損（0.0）の場合に過少評価される可能性があり、将来的にフォールバック価格（前日終値等）を導入予定。
- position_sizing は現状 lot_size を全銘柄共通値として扱う（将来的に銘柄別 lot_size サポートを想定）。
- monitor のポーリング間隔に 0 以下を設定した場合は値が不正としてデフォルトにフォールバックする（time.sleep に渡すと ValueError が発生するため）。

---

貢献・バグ報告は Issue を通じてお願いします。次のリリースでは未実装のファクター実装、単体テスト追加、そしてさらなるドキュメント整備を予定しています。