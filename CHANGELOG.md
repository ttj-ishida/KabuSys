CHANGELOG
=========

すべての注目すべき変更点を時系列で記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-22
-------------------

Added
- 基本パッケージ初回リリース。
- 起動スクリプト
  - run_execution.py: ExecutionEngine を起動するスクリプトを追加。  
    - KABUSYS_ENV=paper_trading の場合は専用のペーパートレード用 SQLite（data/paper_trading.db、環境変数 PAPER_TRADING_SQLITE_PATH で上書き可）を使用して本番 DB と完全分離。  
    - BrokerClientFactory を利用して実行環境に応じたブローカークライアントを作成。エンジンは別スレッドで実行され、 data/stop_requested.flag による停止を検知して安全に停止する。PID ファイル管理をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、無効値はデフォルトにフォールバック）。  
    - 監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する旨の挙動を明記。停止フラグファイルによりループ終了。
- 設定管理
  - config.py: Settings クラスを導入。環境変数から各種設定値（J-Quants、kabuAPI、DB パス、監視閾値、環境種別 等）を取得・検証するユーティリティを提供。  
    - .env / .env.local の自動ロード機能（プロジェクトルート検出ベース）。自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。  
    - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等の妥当性チェックを実装。
  - config_setup.py: .env を対話式に作成・更新するウィザード CLI を追加。シークレット項目はマスク表示。生成テンプレートは .env に上書き保存。
  - validate_config.py: 起動前に .env と config/*.yaml を検査する CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、YAML パース（PyYAML があれば）や本番環境時のガードチェックを行う。--strict オプションで警告も失敗扱いにできる。
- ロギング・プロセス管理
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - stdout への StreamHandler（標準出力）、および日次ローテート（TimedRotatingFileHandler）をルートロガーに設定。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソールのみで継続。ログローテーションは 30 日分保持。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度設定ユーティリティを追加。Windows/Linux(Mac 等 POSIX) の差分を吸収して set_process_priority(level)、set_cpu_affinity(n) を提供。権限不足などで失敗した場合は警告ログを出してスキップする設計。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: ペーパートレード用 SQLite を解析して検証レポートを生成する CLI を追加。  
    - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（P95 等）などを集計。  
    - デフォルトの合否基準（例: uptime >= 99%、fill_rate >= 90%、P95 <= 200ms）を定義し、PASS/FAIL 判定を出力。日付フィルタ（--from, --to）と DB パス指定をサポート。
- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py: 候補選定と重み計算（等配分、スコア加重）を提供。スコア全てが 0 の場合は等分配にフォールバックして警告。
  - portfolio/risk_adjustment.py: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。unknown セクターはセクター上限の対象外とする挙動、未定義レジームはフォールバックで 1.0 を返す。
  - portfolio/position_sizing.py: 単元株丸め、リスクベース / 等分配 / スコア配分に基づく株数計算ロジックを実装。  
    - aggregate cap（投下資金が利用可能現金を超える場合）のスケーリングと、lot_size（デフォルト 100）単位での丸め・残余配分アルゴリズムを備える。cost_buffer（スリッページ/手数料見積）も考慮。
  - portfolio/__init__.py: これら関数を公開 API としてまとめてエクスポート。
- 研究・指標
  - research/factor_research.py: DuckDB の prices_daily / raw_financials を元にファクター（Momentum, Value, Volatility, Liquidity）を計算するためのモジュールを追加（設計方針と定数群を含む）。（実装はファイル内で継続実装中）
- パッケージメタ
  - __init__.py にバージョン __version__ = "0.1.0" を設定。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （該当なし）

Removed
- （該当なし）

Security
- （現時点で特記事項なし）

Notes / Implementation details
- .env パーサは export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、行末コメントの扱い等に対応する堅牢な実装になっています。
- run_monitoring は監視 DB 初期化（init_monitoring_db）と DuckDB 接続を行い、例外時にも次ポーリングまで継続するよう例外ハンドリングが組み込まれています。
- run_execution は停止フラグを起動前に確認し、既に停止フラグが立っている場合は起動せず終了する安全措置を持ちます。
- process_priority や CPU affinity の設定は OS/権限によって失敗する可能性があるため、失敗時は警告を出して処理を続行する設計です。
- 一部モジュール内に将来対応を示す TODO コメントが存在します（例: position_sizing の銘柄別 lot_size 対応、risk_adjustment の price フォールバックなど）。

今後の予定（例）
- research/factor_research.py の完全実装（ファクター計算ロジックの SQL/Python 実装完了）
- 監視・実行のより詳細なテストカバレッジ追加
- 設定/起動周りの UX 改善（ログ出力、PID/状態管理の強化）
- ドキュメント（運用手順、デプロイ手順）の整備

---
この CHANGELOG はコードベースから推測して作成しています。実際のコミット履歴や設計仕様書に基づく更新があれば、適宜内容を反映してください。