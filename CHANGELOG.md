CHANGELOG
=========

すべての変更は Keep a Changelog の形式に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

注意: バージョン番号はパッケージ内の __version__ (src/kabusys/__init__.py) に合わせています。

Unreleased
----------

- ドキュメントやテストに基づく細かな修正・リファクタ（将来のリリースに向けた整理）。

0.1.0 - 2026-04-18
-----------------

Added
- 基本アプリケーション骨格を実装
  - パッケージメタ情報: src/kabusys/__init__.py に __version__ = "0.1.0" を追加。
- 起動スクリプト
  - 実行エンジン起動スクリプト: src/kabusys/run_execution.py
    - ExecutionEngine を起動する CLI ラッパー。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用の SQLite DB を使用（分離された data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可能）。
    - BrokerClientFactory を介して本番/モックのブローカークライアントを切り替え（コメント・ドキュメントで MockBrokerClient の利用を明示）。
    - 停止フラグ（data/stop_requested.flag）検知および PID ファイル管理（data/execution.pid）。
    - プロセス優先度を起動時に high に設定。
  - 監視ループ起動スクリプト: src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループを起動。
    - MONITOR_POLL_INTERVAL 環境変数によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用 sqlite_path を使用する旨を仕様として明示。
    - 停止フラグによる安全終了をサポート。
- 設定管理・補助ツール
  - Settings / 環境変数読み込み: src/kabusys/config.py
    - .env 自動読み込み機能（.env, .env.local）をプロジェクトルート（.git または pyproject.toml）から行う（無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD を提供）。
    - .env の読み込みは既存 OS 環境変数の保護（protected）を行い、.env.local は上書き可能。
    - 各種設定プロパティ（DB パス、LINE, KABU, J-Quants トークン、監視閾値、環境判定メソッドなど）を提供。
    - 必須環境変数が未設定の場合は明示的に ValueError を送出。
  - 設定ウィザード CLI: src/kabusys/config_setup.py
    - .env を対話式に作成・更新するウィザード。
    - デフォルト値、選択肢、シークレット入力、既存値の再利用、保存の確認機能を持つ。
  - 設定検証 CLI: src/kabusys/validate_config.py
    - 必須環境変数・KABUSYS_ENV・LOG_LEVEL・DB パス・config/*.yaml の存在や YAML パースをチェック。
    - --strict オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 設定未設定、KILL_FLAG_CLEAR_ON_START の危険設定等）を実施。
- ロギング・プロセス制御ユーティリティ
  - 統一ロギングセットアップ: src/kabusys/utils/logging_setup.py
    - ルートロガーに StreamHandler (stdout) と TimedRotatingFileHandler（日次、30日保持）をセット。
    - LOG_DIR / LOG_LEVEL の解決、既存ハンドラのクリア、ログディレクトリ作成失敗時のフォールバックを考慮。
    - stdout を利用（stderr ではなく）する方針を採用。
  - プロセス優先度 / CPU affinity: src/kabusys/utils/process_priority.py
    - Windows/Linux/Mac 等の差分を吸収して優先度設定（high/normal/low）をサポート。
    - CPU affinity を最初の N コアに固定するユーティリティを提供。
    - 権限不足や未対応 OS へのフォールバック処理あり。
- ポートフォリオ構築ライブラリ: src/kabusys/portfolio/*
  - portfolio_builder.py
    - 候補選定 (select_candidates)、等金額配分 (calc_equal_weights)、スコア配分 (calc_score_weights) を実装。
    - スコアが全て 0 の場合は等配分にフォールバック。
  - risk_adjustment.py
    - セクター集中制限を適用する apply_sector_cap。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier（bull/neutral/bear とフォールバック挙動）。
  - position_sizing.py
    - ポジションサイズ計算（risk_based / equal / score）を実装。
    - 単元株（lot_size）、コストバッファ（cost_buffer）、max_utilization などの制約を考慮したスケーリングロジックを実装。
    - aggregate cap 超過時のスケールダウンと端数配分アルゴリズムを実装。
- リサーチ / ファクター計算（骨組み）
  - src/kabusys/research/factor_research.py にモメンタム等のファクター計算ロジック（DuckDB 接続を前提）を実装（未完の箇所あり）。
- Paper Trading 検証ツール
  - src/kabusys/tools/paper_verification_report.py
    - ペーパートレード用 SQLite を読み取り、稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）等を集計し PASS/FAIL を判定するレポートを CLI 出力。
    - デフォルト閾値を設定（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）。
    - 日付フィルタ（--from / --to）および --db で DB パス指定可能。
- その他
  - 停止フラグ（data/stop_requested.flag）による安全停止の統一的取り扱いを run_execution と run_monitoring がサポート。
  - SQLite / DuckDB の接続初期化処理を各起動スクリプトで行う（監視テーブル初期化関数 init_monitoring_db を呼び出す旨が実装）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数のシークレット（トークン・パスワード）は .env に保存されるが .env を Git にコミットしないようウィザードと出力コメントで注意喚起。

Notes / Breaking Changes
- Settings の必須プロパティ（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）未設定時は ValueError を送出するため、これらを設定せずにコードを利用すると起動時にエラーになります。validate_config を事前に実行して設定を確認することを推奨します。
- run_monitoring は「監視は常に本番 sqlite_path を使う」と明記されており、開発 / ペーパートレード環境でも監視データの保存先が本番の monitoring DB になる点に注意してください（設計上の仕様）。
- ログはデフォルトで stdout に出力され、ログファイルは logs/<app_name>.log に日次ローテーションで保存されます。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみになります。

開発メモ / TODO（今後のリリース候補）
- research/factor_research.py の実装完了（ファクターの全計算とテスト）。
- BrokerClientFactory / ExecutionEngine / SystemMonitor 等の詳細実装のユニットテスト追加。
- price フォールバック（前日終値など）を使った exposure 計算の強化（risk_adjustment.apply_sector_cap の TODO）。
- 銘柄別 lot_size サポート（position_sizing の拡張）。
- config/*.yaml のスキーマ定義と厳密な検証（validate_config の拡張）。

--- 

（記載はコードベースの現状から推測してまとめています。実際の変更履歴・リリースノートはリポジトリのコミット履歴やリリースタグに基づいて追記してください。）