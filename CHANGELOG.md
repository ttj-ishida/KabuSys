# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠します。  
このプロジェクトの初回リリースとして、バージョン 0.1.0 に含まれる主な追加・仕様を日本語でまとめます。

## [0.1.0] - 初版リリース (unreleased)
リリース日: 未設定

### 追加 (Added)
- 基本アプリケーション情報
  - パッケージバージョンを定義: src/kabusys/__init__.py にて `__version__ = "0.1.0"` を追加。

- 起動スクリプト / デーモン系
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine を起動するエントリポイントを提供。
    - ストップフラグ (data/stop_requested.flag) の検知、PID ファイル (data/execution.pid) の取り扱い。
    - KABUSYS_ENV が `paper_trading` の場合は paper_trading 用 SQLite（data/paper_trading.db）を使用して本番 DB と完全分離。
    - BrokerClientFactory を通じたブローカークライアントの生成、OrderManager / RiskManager / Reconciler の組み立てを実施。
    - デーモンスレッドで engine.run_session を実行し、停止フラグで安全停止。

  - 監視ポーリング起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを実行。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず production sqlite_path を使用する点に注意（監視データは本番 DB に記録）。
    - 停止フラグ検知・例外耐性・KeyboardInterrupt ハンドリング。

- 環境設定・検証ツール
  - 設定ウィザード CLI: src/kabusys/config_setup.py
    - 対話式で .env を初期作成・更新するウィザードを提供。
    - J-Quants / kabu API / DB パス / ログレベル / Kill Switch 等の主要項目を扱うテンプレートと書き込み機能を実装。
  - 設定検証 CLI: src/kabusys/validate_config.py
    - .env と config/*.yaml の存在・フォーマット・基本的な整合性を検証。
    - `--strict` オプションで警告を FAIL 扱いにできる。
    - 必須環境変数チェック、KABUSYS_ENV の整合性チェック、db path の親ディレクトリチェック、PyYAML の有無による YAML パース検証、ライブ環境向けの注意喚起等を実装。

- 環境管理 / 設定読み込み
  - 設定管理クラス: src/kabusys/config.py
    - Settings クラスを提供し、環境変数をラッパー経由で取得。
    - 自動 .env ロード（プロジェクトルート検出: .git または pyproject.toml を基準）。読み込み順は OS 環境 > .env.local > .env。
    - 自動ロードを無効化する環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - .env パーサは `export KEY=val`、クォート文字列、エスケープ、インラインコメント考慮などに対応。
    - paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）のサポート、paper モード向けの fill mode（PAPER_FILL_MODE）の検証などを実装。
    - 各種閾値や Kill Switch 関連設定（KILL_FLAG_CLEAR_ON_START など）をプロパティとして提供。

- ロギング・プロセス制御ユーティリティ
  - 統一ロギング設定ユーティリティ: src/kabusys/utils/logging_setup.py
    - stdout に出す StreamHandler と日次ローテートする TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ自動作成、作成失敗時はファイル出力をスキップしてコンソールのみで継続。
    - 環境変数 LOG_LEVEL / LOG_DIR のサポート。
  - プロセス優先度／CPU affinity ユーティリティ: src/kabusys/utils/process_priority.py
    - Windows / POSIX (Linux/Mac/FreeBSD) の差を吸収してプロセス優先度を設定（"high" / "normal" / "low"）。
    - CPU affinity を最初の N コアに固定する関数も提供。psutil ベースで権限エラー等は警告でスキップ。

- ポートフォリオ構築関連（純粋関数群）
  - 銘柄選定・重み計算: src/kabusys/portfolio/portfolio_builder.py
    - シグナルのスコア降順フィルタ、等重配分、スコア加重配分（全スコア 0 の場合に等重へフォールバック）を実装。
  - セクター集中制限・レジーム乗数: src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap: セクター別エクスポージャに基づき新規候補を除外するロジックを実装。unknown セクターは除外の対象外。
    - calc_regime_multiplier: レジームに応じた投下資金乗数（bull/neutral/bear）を返す。未知レジームはフォールバックして 1.0。
  - 株数決定・資金配分アルゴリズム: src/kabusys/portfolio/position_sizing.py
    - allocation_method（"risk_based" / "equal" / "score"）に応じた注文株数計算。
    - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash）超過時のスケールダウン、残余配分アルゴリズムを実装。
    - 手数料やスリッページを見積もる cost_buffer を考慮。
  - 上記モジュールをまとめてエクスポート: src/kabusys/portfolio/__init__.py

- リサーチ系ユーティリティ（ファクター計算）
  - ファクター計算モジュール（未完分あり）: src/kabusys/research/factor_research.py
    - Momentum / MA200 / ATR / Volume 等の計算方針および定数を実装。DuckDB 接続を受け取り prices_daily テーブルを参照して計算する設計。
    - P95 等の統計指標、計算範囲バッファ等を定義。

- Paper Trading 検証レポート
  - レポート生成スクリプト: src/kabusys/tools/paper_verification_report.py
    - paper_trading の SQLite DB（デフォルト data/paper_trading.db）からシステム安定性、注文成功率、送信率、レイテンシ（平均/最大/P95）などを集計して標準出力レポートを生成。
    - しきい値（稼働率/成功率/送信率/P95）に基づく PASS/FAIL 判定を実装。
    - DB 不在時のエラーメッセージ、日付フィルタ（--from / --to）のサポート。

### 変更 (Changed)
- 監視の DB 接続方針
  - run_monitoring は実行環境にかかわらず Settings.sqlite_path（本番 sqlite_path）を使って monitoring DB を初期化/接続する仕様とした（監視データは本番 DB に記録される）。

- .env の自動読み込み挙動
  - プロジェクトルート検出ロジックを __file__ ベースに実装し、CWD に依存しない自動読み込み方式を採用。
  - 読み込み優先順位は OS 環境 > .env.local > .env（.env.local が .env を上書き）。

- ロギングの出力先
  - StreamHandler は stdout を使うように統一（stderr ではなく stdout）。cron 等からのリダイレクトを想定。

### 修正 (Fixed)
- 環境/入力パースの堅牢化
  - .env パーサ（_parse_env_line）を改善し、シングル/ダブルクォート、バックスラッシュエスケープ、export プレフィックス、インラインコメント処理に対応。
  - MONITOR_POLL_INTERVAL のマイナス・ゼロ値や非整数入力に対して警告を出しデフォルトにフォールバックする（run_monitoring._get_poll_interval）。

- 例外耐性の強化
  - run_monitoring のポーリング内で monitor.check_once() が例外を投げてもループを継続するように logger.exception で捕捉。
  - ログディレクトリ作成やファイルハンドラ作成失敗が起きてもサービス全体はコンソールログで継続するようにフォールバック。

- Position sizing の端数処理
  - aggregate cap スケールダウン後の残余キャッシュに対して lot_size 単位で再配分するロジックを実装し、安定かつ再現性のある分配を行う。

### セキュリティ (Security)
- API 秘密情報の扱い
  - config_setup にて .env ファイルに API トークン等を記録する際に、ファイルを絶対に Git にコミットしない旨の注意書きを明示。

### 既知の注意点 / Breaking changes
- 監視データの DB 選択
  - run_monitoring は Settings.env に関わらず Settings.sqlite_path（デフォルト data/monitoring.db）を使用します。もし監視データを paper_trading 用 DB と分離したい場合は実装を見直す必要があります。
- factor_research は一部実装が未完（ファイル末尾で途中）であり、完全なファクター出力を期待する場合は追加実装が必要です。

---

将来的には以下のような改善を想定しています（未実装／拡張案）:
- 銘柄ごとの lot_size を銘柄マスタで持たせる（position_sizing の拡張）。
- price の欠損フォールバック（前日終値や取得原価）を適用してエクスポージャの過少見積りを防ぐ。
- factor_research の全関数実装とユニットテスト追加。
- monitoring / execution のより詳細なメトリクス計測と外部アラート統合（LINE への通知等）。

（以上）