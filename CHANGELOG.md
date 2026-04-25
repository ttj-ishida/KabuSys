CHANGELOG
=========

すべての注目すべき変更履歴を記録します。フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現時点で未リリースの変更はありません）

[0.1.0] - 2026-04-25
-------------------

Added
- 基本機能を実装した初回リリース。
  - 環境設定 / 起動関連
    - 自動 .env ロード機構を実装（src/kabusys/config.py）。
      - プロジェクトルートの探索を .git / pyproject.toml を基準に行い、.env / .env.local を読み込む（OS 環境変数が優先）。
      - 行パーサは export プレフィックス、シングル/ダブルクォート、エスケープシーケンス、インラインコメント等に対応。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化をサポート。
    - Settings クラスに各種設定プロパティを実装（DB パス、PID / kill flag パス、環境判定、paper_trading 用設定等）。
      - KABUSYS_ENV / LOG_LEVEL 等の値検証を行い、不正値で例外を投げる。
      - PAPER_FILL_MODE の有効値チェックを実装。
  - 起動スクリプト
    - 実行エンジン起動スクリプト（src/kabusys/run_execution.py）を実装。
      - 起動時にプロセス優先度を "high" に設定。
      - paper_trading 環境では専用 SQLite（デフォルト data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory により環境に応じたブローカークライアント（Mock を含む）を生成。
      - 停止フラグ（data/stop_requested.flag）検知による安全なシャットダウンをサポート。
    - 監視ループ起動スクリプト（src/kabusys/run_monitoring.py）を実装。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を指定可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視は環境にかかわらず本番用 sqlite_path を使用する（監視データの一元化）。
      - stop flag によるループ終了および KeyboardInterrupt ハンドリング。
  - 設定支援 / 検証
    - 対話式 .env 作成ウィザード（src/kabusys/config_setup.py）。
      - 複数の設定項目定義（KABUSYS_ENV、API トークン、DB パス、LOG_LEVEL、Kill Switch 等）。
      - 既存 .env の読み込み、シークレットマスク表示、保存（.env に書き込み）を実装。
    - 設定検証 CLI（src/kabusys/validate_config.py）。
      - 必須 / 任意環境変数チェック、KABUSYS_ENV 値チェック、LOG_LEVEL チェック、DB パス親ディレクトリ存在チェック、config/*.yaml 存在／パース検証（PyYAML 有無に応じて挙動を変える）、本番環境向けのガードチェックを実装。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ロギング・プロセス管理ユーティリティ
    - 統一ロギング設定ユーティリティ（src/kabusys/utils/logging_setup.py）。
      - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）を設定。
      - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラの安全なクローズ／再設定処理を実装。
      - ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみ継続。
    - プロセス優先度 / CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）。
      - Windows / POSIX の差分を吸収して nice/priority を設定（psutil 利用）。失敗時は警告を出してスキップ。
      - set_cpu_affinity によりプロセスを最初の N コアにピン留め可能。
  - ポートフォリオ構築（純関数群）
    - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）。
      - select_candidates（スコア降順、タイブレークロジック）、calc_equal_weights、calc_score_weights（全スコア 0 の場合は等配分にフォールバック）。
    - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）。
      - apply_sector_cap（既存保有を考慮したセクター上限チェック）、calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく資金乗数）。
    - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）。
      - allocation_method に応じた発注株数計算（"risk_based" / "equal" / "score"）。
      - 単元株丸め、1銘柄上限、aggregate cap（利用可能現金を超える場合のスケールダウン）および端数配分ロジックを実装。
  - ツール
    - Paper Trading 検証レポート生成スクリプト（src/kabusys/tools/paper_verification_report.py）。
      - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、P95 レイテンシ等を集計して PASS/FAIL 判定を出力。
      - デフォルト DB パスは data/paper_trading.db、コマンドラインで期間指定可能。
  - リサーチ（着手）
    - ファクター計算モジュール（src/kabusys/research/factor_research.py）の骨組みを実装（モメンタム・MA200・ATR などの計算を意図）。DuckDB 経由で prices_daily / raw_financials を参照する設計。

Changed
- 環境変数ロードの挙動
  - .env と .env.local の読み込み順および override 動作を明確化（OS 環境変数はデフォルトで保護）。
- ロギング
  - StreamHandler を stdout に固定（stderr ではなく stdout を使用）。これは cron/タスクスケジューラでの出力取り扱いを簡潔にするため。
- 実行・監視プロセス
  - 起動時にプロセス優先度を上げる処理を各起動スクリプトの最初に入れ、重要処理の安定動作を優先。

Fixed
- 各種失敗時のフェールフォワード挙動を改善
  - ログディレクトリやファイルハンドラの作成失敗時にアプリケーションが停止しないようにし、コンソール出力のみで続行するようにした。
  - 環境変数の不正値（例えば MONITOR_POLL_INTERVAL が非整数／非正）に対してデフォルトを使うようにし、ValueError を回避して安全に稼働するようにした。
  - calc_score_weights で全スコアが 0 の場合に等金額配分へフォールバックすることで 0 除算を回避。

Security
- .env の取り扱いに関する注意喚起を config_setup のヘッダに明記（".env は絶対に Git にコミットしないこと"）。
- config_setup でパスワードなどを対話的にマスクして表示（保存前の確認時にシークレットを伏せる）。

Notes / Known issues / TODO
- research/factor_research.py は計算部分の実装が継続中（ファイル末尾で切れている）。本格利用前に追加実装が必要。
- position_sizing の price フォールバック（価格欠損時の扱い）や lot_size の銘柄別拡張は将来の改善項目としてコメントに残している。
- デフォルトの PID / flag パスや DB パスは data/ 以下に配置される想定だが、運用環境では適切なパスに変更して利用することを推奨。

References
- パッケージバージョン: src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

---

この CHANGELOG はコードベースの内容から推測して作成しています。実際のリリースノートと差分がある場合は適宜修正してください。