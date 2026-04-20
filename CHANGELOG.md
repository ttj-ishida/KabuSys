Keep a Changelog準拠の形式で、このリポジトリの初回リリース相当の変更履歴をコード内容から推測して作成しました。日付は現在日付（2026-04-20）を使用しています。必要に応じて日付やリリース名は調整してください。

Keep a Changelog
================

すべての変更はセマンティックバージョニングに従って文書化します。  
このファイルでは主要な追加・変更点・修正点を高レベルで記載しています。

Unreleased
----------

（今後の変更をここに記載）

[0.1.0] - 2026-04-20
-------------------

Added
- 基本アプリケーション骨組みを追加（初期公開）。
  - パッケージバージョンを 0.1.0 に設定。 (src/kabusys/__init__.py)
- 起動スクリプト
  - 監視ループ起動スクリプトを追加: run_monitoring.py
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - プロセス優先度を起動時に設定し、停止フラグ（data/stop_requested.flag）でループを終了。
    - 監視データベース（SQLite）と DuckDB 接続を初期化して SystemMonitor を実行。  
    - 監視は環境に関係なく本番用 sqlite_path を使用する仕様。  
- 実行エンジン起動スクリプトを追加: run_execution.py
  - KABUSYS_ENV=paper_trading の場合は MockBrokerClient（ペーパートレード専用）を使用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
  - プロセス優先度を設定し、停止フラグ検知で安全にセッションを停止する仕組みを実装。
- 設定管理
  - Settings クラスを実装（src/kabusys/config.py）
    - .env の自動読み込み機構（.env.local 優先 etc.）、環境変数の取得ラッパー、各種デフォルト値と妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）。
    - DB パス、PID/kill フラグのパス、監視閾値などのプロパティを提供。
- 設定操作ツール
  - 対話式 .env 作成/更新ウィザード: config_setup.py
    - 必須項目・任意項目を対話的に入力して .env を生成/更新、シークレットマスク表示、確認フロー。
  - 設定検証 CLI: validate_config.py
    - 必須環境変数・KABUSYS_ENV 値チェック・LOG_LEVEL 検証・DB パスの親ディレクトリ存在確認・config/*.yaml の存在と（PyYAML があれば）パース検証。
    - --strict モードで警告を失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ: utils/logging_setup.py
    - stdout ストリームハンドラと日次ローテートファイルハンドラをルートロガーに設定。ログディレクトリ作成に失敗した場合はファイル出力をスキップして標準出力のみで継続。
  - プロセス優先度・CPU affinity ユーティリティ: utils/process_priority.py
    - psutil を用いて Windows と POSIX(Linux/macOS/FreeBSD) を吸収した優先度設定と CPU ピニングを提供。失敗時は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数）
  - 銘柄選定・重み計算: portfolio/portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights: スコア合計が 0 の場合は等分にフォールバック)。
  - セクター集中制限・レジーム調整: portfolio/risk_adjustment.py
    - セクター上限適用 (apply_sector_cap): 指定比率を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - レジーム乗数計算 (calc_regime_multiplier): "bull"/"neutral"/"bear" に対応（未定義は 1.0 にフォールバック）。
  - ポジションサイジング: portfolio/position_sizing.py
    - allocation_method に応じた株数計算（"risk_based"、"equal"、"score"）。単元株（lot_size）丸め、1 銘柄上限・全体の aggregate cap によるスケーリング、cost_buffer を考慮した保守的推定。
- Paper Trading の検証ツール
  - ペーパートレード検証レポート生成スクリプト: tools/paper_verification_report.py
    - 指標: 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、レイテンシ（avg/max/P95）。
    - デフォルト閾値を設定して PASS/FAIL を判定（稼働率 >= 99%、fill_rate >= 90% など）。
    - 日付フィルタと DB 指定オプションをサポート。
- データリサーチ基盤（部分実装）
  - ファクター計算モジュール開始: research/factor_research.py
    - Momentum、MA200、ATR、出来高系などの計算方針と定数が実装（関数 calc_momentum 等の実装が途中まで存在）。

Changed
- N/A（初回リリースのため変更履歴は無し）。

Fixed
- 環境変数パースと安全性を強化（config._parse_env_line）
  - export プレフィックスの対応、クォート付き値のバックスラッシュエスケープ処理、インラインコメント処理などを実装して .env の互換性を向上。
- MONITOR_POLL_INTERVAL の不正値（0 や負数、非整数）に対してデフォルトにフォールバックして警告を出す保護を追加（run_monitoring._get_poll_interval）。

Security
- 秘匿情報取り扱いに関する注意書きと .env の取り扱いを config_setup の生成ファイルヘッダに明記（.env を Git にコミットしないことを推奨）。

Notes / Implementation details（主な設計判断）
- DB 分離: paper_trading モードでは paper_trading 用 SQLite を使用して本番の monitoring DB と完全に分離することでテスト容易性と安全性を確保。
- ログ出力: stdout を StreamHandler に使うことで cron / タスクスケジューラとの相性を重視。
- プロセス優先度設定は万能ではなく、権限不足や未対応 OS の場合は安全にスキップして動作継続する実装。
- Portfolio モジュールは純粋関数群で副作用が無く、テストしやすい設計（DB 参照なし）。

Breaking Changes
- なし（初回公開）。

Acknowledgements / TODO
- research/factor_research.py は実装途中のため、続きを実装してファクター出力を完成させる必要あり。
- position_sizing の lot_size を将来的に銘柄別に対応する（stocks マスタから取得）予定（TODO コメントあり）。
- apply_sector_cap の price 欠損時の取り扱い改善（フォールバック価格の導入検討）。

以上。必要であれば、各ファイルごとの差分レベルの詳細な項目（関数単位の変更点や引数仕様の追記）も生成します。どの粒度で記載するか指示してください。