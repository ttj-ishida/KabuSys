Keep a Changelog
=================

すべての重要な変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  

なお本履歴は、ソースコードから推測して作成したものです。実際のリリースノート作成時にはコミット履歴やリリース方針に合わせて調整してください。

[Unreleased]
-------------

（なし）

[0.1.0] - 2026-04-20
-------------------

Added
- 初期リリース: KabuSys 自動売買システムのコアユーティリティ・CLI・モジュール群を追加。
  - 起動スクリプト
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプトを追加。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
      - 停止フラグファイル (data/stop_requested.flag) を検知してループを終了。
      - Monitoring 用 DB は環境に関わらず本番 sqlite_path を使用する設計。
    - src/kabusys/run_execution.py
      - ExecutionEngine 起動スクリプトを追加。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の SQLite を使用し、MockBrokerClient を利用して本番 DB と完全分離。
      - 停止フラグ・PID ファイルの扱いを実装。
  - 設定・環境関連
    - src/kabusys/config.py
      - .env/.env.local の自動ロード処理を実装（OS 環境変数の保護、KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化）。
      - export KEY=val 形式、クォート文字列、インラインコメント等に対応した .env パーサを実装。
      - Settings クラスを導入し、アプリ設定（DB パス、API トークン、監視閾値、環境種別等）をプロパティ経由で取得可能に。
  - 設定支援 / 検証 CLI
    - src/kabusys/config_setup.py
      - 対話式ウィザードで .env の初期作成・更新を支援する CLI を追加。
      - 秘匿項目はマスク表示、デフォルト/既存値の取り扱いを実装。
    - src/kabusys/validate_config.py
      - .env と config/*.yaml の基本的な整合性チェック CLI を追加。
      - --strict オプションで警告をエラー扱いにするモードを実装。
  - ロギング・プロセス制御ユーティリティ
    - src/kabusys/utils/logging_setup.py
      - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日分保持）を設定するユーティリティを追加。
      - LOG_DIR / LOG_LEVEL の解決順、既存ハンドラのクリアを実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。
    - src/kabusys/utils/process_priority.py
      - クロスプラットフォーム（Windows / POSIX）のプロセス優先度設定と CPU affinity 設定を追加。権限不足や未対応 OS の場合は警告を出して安全にスキップ。
  - ポートフォリオ構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 銘柄選定（select_candidates）および重み計算（等金額 / スコア加重）を追加。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中制限（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を追加。
    - src/kabusys/portfolio/position_sizing.py
      - 発注株数決定ロジック（risk_based / equal / score）を実装。単元株丸め、per-stock 上限、aggregate cap スケールダウン、cost_buffer を考慮。
    - src/kabusys/portfolio/__init__.py
      - 上記関数をパッケージ外へ公開。
  - ツール / レポーティング
    - src/kabusys/tools/paper_verification_report.py
      - ペーパートレード検証レポート生成スクリプトを追加（稼働率 / 注文成功率 / 送信率 / レイテンシ等を算出、PASS/FAIL 判定）。
      - CLI 引数で期間指定、DB パスの上書き可能。デフォルト DB パス: data/paper_trading.db。
  - リサーチ（ファクター計算）
    - src/kabusys/research/factor_research.py
      - DuckDB を用いたファクター（モメンタム、MA200乖離、ATR、売買代金等）計算フレームワークの骨組みを追加（関数、定数、設計方針のドキュメント化）。※ファイル末尾は一部実装途中（ソースから推測）。

Changed
- 環境変数自動ロードの振る舞いを明確化（src/kabusys/config.py）
  - 読み込み優先度: OS 環境変数 > .env.local > .env
  - OS の環境変数キーは保護（.env が上書きしない）される。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
- ロギング設定（src/kabusys/utils/logging_setup.py）
  - 既存ハンドラの二重登録を防ぐため、設定時に既存ハンドラを flush/close してから削除するように変更。
  - stdout を StreamHandler に使用することで cron 等で stdout/stderr を一本化して扱いやすくした。
- run_execution.py / run_monitoring.py の DB 初期化
  - init_monitoring_db() を呼び出して監視テーブルの存在を保証（冪等な初期化）。
  - run_execution は paper_trading 時に paper 用 SQLite を使用することで本番 DB と分離。
- ポジションサイズ計算（src/kabusys/portfolio/position_sizing.py）
  - aggregate cap 超過時はスケーリングして残余キャッシュの分配を小数部の大きい順に行う実装に変更（単元株単位での調整）。

Fixed
- ポーリング間隔の不正値への耐性（src/kabusys/run_monitoring.py）
  - MONITOR_POLL_INTERVAL が非整数または 0/負数のときに警告を出し、デフォルト値（60 秒）にフォールバックするように修正。time.sleep に渡すことでの ValueError を回避。
- ログディレクトリ作成失敗時のフォールバック（src/kabusys/utils/logging_setup.py）
  - ディレクトリ作成に失敗してもプロセスは継続し、コンソール出力のみで動作するように変更。
- プロセス優先度 / affinity 設定の堅牢化（src/kabusys/utils/process_priority.py）
  - 権限不足やプラットフォーム非対応時に例外を投げず警告でスキップするように修正。

Documentation
- 各モジュールに詳細な docstring を追加（使用方法・設計方針・引数説明等を含む）。
- config_setup.py と validate_config.py にユーザ向けの使用例を CLI ヘルプ・README 相当で追記。

Notes / Known issues
- research/factor_research.py はファクター計算の設計と一部の実装が含まれますが、ファイル末尾が切れているため完全実装は未完（ソースから推測）。リファクタや追加実装が想定されます。
- 実際の BrokerClientFactory / ExecutionEngine / SystemMonitor の内部実装は本 CHANGELOG の範囲外（本差分では起動・結合部分の追加が確認できるのみ）。
- 本リリースは初期バージョン（0.1.0）としてのまとめであり、運用環境（特に KABUSYS_ENV=live）での利用前には validate_config による確認・各種設定の見直しを推奨します。

-- End of changelog --