# Changelog

すべての注目すべき変更点を記録します。  
このファイルは Keep a Changelog の形式に準拠しています。  

※ バージョン番号は src/kabusys/__init__.py の __version__ に基づきます。

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-18
最初のリリース。シンプルな日本株自動売買フレームワークのコア機能を実装しました。

### 追加
- 基本パッケージ構成
  - kabusys パッケージの初期バージョンを追加（__version__ = 0.1.0）。
- 設定・環境管理
  - Settings クラス（src/kabusys/config.py）を導入し、環境変数経由で全設定を取得する仕組みを提供。
  - 自動 .env ロード機能をサポート（プロジェクトルート検出: .git / pyproject.toml）。
  - .env/.env.local の読み込み順序（OS 環境変数 > .env.local > .env）および KABUSYS_DISABLE_AUTO_ENV_LOAD による無効化を実装。
  - .env の高度なパースを実装（export プレフィックス、シングル/ダブルクォート内のエスケープ、インラインコメント処理など）。
  - Settings にて多数のプロパティを提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 実行環境フラグ 等）。
- 設定ツール・検証ツール
  - 対話式環境設定ウィザード（src/kabusys/config_setup.py）を追加。.env の初回作成や更新を支援。
  - 設定検証 CLI（src/kabusys/validate_config.py）を追加。必須環境変数や config/*.yaml、パスの存在などを検証。--strict オプションで警告を失敗扱いにできる。
- 実行・監視ランナースクリプト
  - ExecutionEngine 起動スクリプト（src/kabusys/run_execution.py）を追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 DB を使い MockBrokerClient を利用する設計（本番 DB と分離）。
    - 実行用 PID ファイル、停止フラグ（data/stop_requested.flag）による安全停止に対応。
  - SystemMonitor ポーリングループ起動スクリプト（src/kabusys/run_monitoring.py）を追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視用 DB は環境にかかわらず本番 sqlite_path を使用（設計上の決定）。
    - 停止フラグ検知でループを終了、例外発生時はログを出して次ポーリングへ継続。
- ロギング・プロセス制御ユーティリティ
  - 統一ログ設定ユーティリティ（src/kabusys/utils/logging_setup.py）を追加。
    - stdout への StreamHandler と日次ローテートする TimedRotatingFileHandler（ログディレクトリ作成、30 日保持）をルートロガーに設定。
    - LOG_LEVEL / LOG_DIR の環境変数や引数からの解決をサポート。ログディレクトリ作成失敗時はファイル出力を安全にスキップ。
  - プロセス優先度・CPU affinity ユーティリティ（src/kabusys/utils/process_priority.py）を追加。
    - Windows / POSIX の差分を吸収して set_process_priority("high"|"normal"|"low") を提供。
    - set_cpu_affinity により最初の N コアにプロセスを固定可能。アクセス権限や非対応 OS の場合は警告を出してスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio モジュールを追加（src/kabusys/portfolio/）。
    - portfolio_builder: シグナル選定・重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - risk_adjustment: セクター集中制限・レジーム乗数（apply_sector_cap, calc_regime_multiplier）。
    - position_sizing: 発注株数計算・集約キャップ処理（calc_position_sizes）。lot_size, cost_buffer, risk_based/equal/score の割当方式をサポート。
- リサーチ
  - factor_research（src/kabusys/research/factor_research.py）を追加（モメンタム / ATR / ボラティリティ等の計算を想定する実装骨子。DuckDB 接続を受け取る設計）。
- ペーパートレード検証ツール
  - paper_verification_report（src/kabusys/tools/paper_verification_report.py）を追加。
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）を読み、稼働率・注文成功率・送信率・レイテンシ等を集計して PASS/FAIL レポートを出力。
    - P95 レイテンシ計算、閾値定義（稼働率 99% 等）を実装。
- モニタリング DB 初期化ユーティリティ
  - init_monitoring_db を利用して監視テーブルが存在することを保証（冪等処理）。
- DuckDB / SQLite のハイブリッド利用
  - 分析用に DuckDB、監視/発注履歴には SQLite を使う構成を採用（パスは Settings 経由）。

### 変更
- なし（0.1.0 は初回リリースのため過去差分なし）。

### 修正
- .env パーサーの堅牢化
  - クォートを含む値のエスケープ処理や、コメントの取り扱いを改善。
- ログ設定の堅牢化
  - ログディレクトリ作成失敗時にファイルハンドラ作成を安全に回避し、コンソール出力のみで継続するように。
- プロセス優先度設定の例外ハンドリング強化
  - 権限不足などで失敗した場合は警告を出して処理を継続するように。

### 既知の制約 / 注意点
- run_monitoring は監視 DB に常に settings.sqlite_path（本番パス）を使用する設計になっているため、開発環境で別 DB を使いたい場合は注意が必要です。
- position_sizing 等は price が欠損（0.0）だと誤った低めのエクスポージャー評価になる旨の TODO コメントあり。将来的に価格フォールバック実装を検討する必要があります。
- factor_research の実装はファイル末尾が途中までであり、実際の計算ロジックの完成が必要です（本リリースではモジュール骨子を含む）。
- config/*.yaml のパース検証は PyYAML がないとスキップされる（validate_config が警告を出す）。

### セキュリティ
- 機密情報（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等）は .env に保存される前提。.env の Git 管理禁止を README /ウィザードの注意文で強調。
- config_setup の出力は .env に平文で書き出すため、適切なファイル権限管理を推奨。

---

（以降のリリースでは、新機能、破壊的変更、バグ修正等をここに追記してください）