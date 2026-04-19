# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記述しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- 現在未リリースの変更はありません。

## [0.1.0] - 2026-04-19
初回リリース。KabuSys の基盤機能（設定管理、起動スクリプト、ポートフォリオ構築、ユーティリティ、検証ツールなど）を実装しました。

### 追加 (Added)
- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止はプロジェクト内 data/stop_requested.flag によるフラグ検知で行う。
    - Monitoring は KABUSYS_ENV にかかわらず本番用 sqlite_path を使用する旨を明記。
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を利用し、paper_trading 用 DB（data/paper_trading.db）に記録して本番 DB と分離。
    - 停止フラグ・PID ファイル管理・スレッド駆動による実行制御を実装。

- 設定管理
  - config.py
    - Settings クラスを提供（環境変数による設定取得）。
    - .env の自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml ベース）。
    - .env のパースは引用符・エスケープ・インラインコメントなどに対応。
    - 各種設定プロパティ（DB パス、ログレベル、KABUSYS_ENV 判定、Paper Trading 設定等）を実装。
    - 設定未定義時の明示的エラー（_require）を提供。

- 設定検証・セットアップツール
  - validate_config.py
    - .env と config/*.yaml の事前検証 CLI を追加。
    - 必須環境変数チェック、KABUSYS_ENV と LOG_LEVEL の検証、DB パス / YAML ファイル存在チェック、live 環境向けの追加ガードを実装。
    - --strict オプションで警告も FAIL 扱いにできる。
  - config_setup.py
    - 対話式ウィザードで .env を初期作成 / 更新するツールを追加。
    - 項目定義（J-Quants トークン、kabu API パスワード、DB パス、LINE 設定、KABUSYS_ENV 等）と .env 書き込み機能を実装。

- ポートフォリオ構築ライブラリ (kabusys.portfolio)
  - portfolio_builder.py
    - シグナル選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等配分にフォールバックし警告を出力。
  - risk_adjustment.py
    - セクター集中上限の適用 (apply_sector_cap) を実装（既存保有のエクスポージャを計算し、超過セクターの新規候補を除外）。
    - 市場レジームに応じた投下資金乗数 (calc_regime_multiplier) を実装（bull/neutral/bear と未知レジームのフォールバック）。
  - position_sizing.py
    - 発注株数の計算 (calc_position_sizes) を実装。
    - risk_based / equal / score の配分方式をサポート。
    - lot_size（単元株）丸め、単銘柄上限、aggregate cap によるスケーリングと端数処理（残余現金での lot 単位追加配分）を実装。
    - cost_buffer（手数料・スリッページの保守的見積り）対応。
  - kabusys.portfolio.__init__ で上記関数をエクスポート。

- ユーティリティ
  - utils/logging_setup.py
    - 統一ログ初期化ユーティリティを実装。
    - StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30 日保持）をルートロガーに設定。
    - LOG_DIR 指定やディレクトリ作成失敗時のフォールバック（ファイル出力をスキップ）に対応。
    - stdout を使用することで cron 等でのリダイレクト運用に配慮。
  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを実装（Windows / POSIX の差分吸収）。
    - set_process_priority(level) と set_cpu_affinity(cpu_count) を提供。
    - 権限不足や未対応 OS の場合は警告を出して安全にスキップ。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading 用検証レポート生成スクリプトを追加。
    - system_status / trade_logs / risk_logs を参照して稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を計算・出力。
    - Pass/Fail 判定基準を定義（稼働率 >=99%、成立率 >=90%、送信率 >=95%、P95 <=200ms など）。
    - 日付フィルタ（--from / --to）と DB パス（--db / 環境変数）に対応。

- リサーチ（部分実装）
  - research/factor_research.py
    - ファクター計算モジュールの骨格を追加（Momentum、Value、Volatility、Liquidity に関する設計と定数定義）。
    - calc_momentum 関数の実装（モメンタム／MA200 乖離等の計算に向けた基盤。続き実装の余地あり）。

- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。

### 変更 (Changed)
- ログ出力先の設計
  - logging_setup は stderr ではなく stdout を標準ログ出力に使用するように設計（cron 等からのリダイレクト運用を想定）。

### 修正 (Fixed)
- 環境変数パースの堅牢化
  - config._parse_env_line にて引用符内のバックスラッシュエスケープや inline コメント処理、export プレフィックス対応を実装し、.env をより安全にロードできるようにした。
- MONITOR_POLL_INTERVAL の不正値ハンドリング
  - run_monitoring._get_poll_interval は不正な値（負数・非整数等）を検知して警告を出し、デフォルト値にフォールバックするようにした（time.sleep への不正渡しを回避）。

### 既知の制限 / 注意点
- run_monitoring は Monitoring 用 DB として常に Settings.sqlite_path（本番向けパス）を使用します。テスト実行時は注意してください。
- position_sizing の price が欠損（0.0）の場合、現在は簡易にスキップする動作を採っています。将来的にフォールバック価格（前日終値等）を導入することを検討しています（TODO コメントあり）。
- research/factor_research.py は一部未完（ファイル末尾で途中終了）。今後の実装が必要です。

### セキュリティ (Security)
- 本リリースでは機密情報（API トークンやパスワード）を .env に保管する設計を前提としています。.env を決してリポジトリにコミットしないよう README 等で明示してください（config_setup.py にも同旨の注記あり）。

---

（本 CHANGELOG は提供されたコードベースから機能・変更点を推測して作成しています。実際のリリースノートとして使用する場合は、差分管理履歴やコミットメッセージに基づき適宜調整してください。）