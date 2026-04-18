CHANGELOG
=========

すべての変更は Keep a Changelog 準拠で記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- （なし）

0.1.0 - 2026-04-18
------------------

追加 (Added)
- 初回公開リリース。モジュール構成と主な機能を実装。
- 実行スクリプト
  - run_execution.py: 実行エンジン起動スクリプトを追加。  
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を利用し、paper_trading 用 SQLite（デフォルト: data/paper_trading.db）に完全分離して記録。
    - 停止フラグ検知 (data/stop_requested.flag) による安全停止、PID ファイル出力 (data/execution.pid) をサポート。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。  
    - ポーリング間隔は環境変数 MONITOR_POLL_INTERVAL で上書き可能（デフォルト: 60 秒）。
    - 監視は KABUSYS_ENV に関わらず本番用 sqlite_path を使用する設計。停止フラグでループ終了。
- 設定管理・ヘルパー
  - config.py: .env 自動読み込み機能と Settings クラスを追加。  
    - .env/.env.local の読み込み順を実装（OS 環境変数保護、.env.local は上書き可）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env 行パーサーは export 形式、引用符付き値、インラインコメント処理をサポート。
    - 多数の設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視しきい値 / ログ設定 等）。
    - PAPER_FILL_MODE の有効値チェック、KABUSYS_ENV / LOG_LEVEL のバリデーションを実装。
  - validate_config.py: 起動前の設定検証 CLI を追加。  
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パースチェック（PyYAML 未導入時はスキップ）。
    - --strict オプションで警告も FAIL 扱いにできる。
  - config_setup.py: 対話式で .env を作成・更新するウィザードを追加。  
    - シークレットのマスク表示、選択肢・デフォルト値サポート、保存時のテンプレート書き出しを実装。
- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。  
    - stdout へ StreamHandler、日次ローテートの TimedRotatingFileHandler（logs/<app>.log）を設定。LOG_DIR / LOG_LEVEL 対応。
    - 既存ハンドラのクリーンアップ処理およびファイル出力失敗時のフォールバック対応。
  - utils/process_priority.py: クロスプラットフォームのプロセス優先度・CPU affinity 設定ユーティリティを追加。  
    - Windows / POSIX（Linux, macOS 等）対応。psutil を利用しアクセス権限例外は警告でスキップ。
    - set_process_priority(level), set_cpu_affinity(cpu_count) を提供。
- ポートフォリオ構築関連（純粋関数群）
  - portfolio/portfolio_builder.py: シグナル選定と重み計算（スコア順選定、等金額/スコア加重）を追加。
  - portfolio/risk_adjustment.py: セクター上限適用、レジームに応じた乗数（bull/neutral/bear）を追加。未知レジームはフォールバック処理あり。
  - portfolio/position_sizing.py: 銘柄ごとの株数計算ロジックを追加。  
    - allocation_method に "risk_based", "equal", "score" をサポート。単元株（lot_size）丸め、max_position_pct、max_utilization、コストバッファ考慮、aggregate cap によるスケーリングと端数配分ロジックを実装。
  - portfolio/__init__.py で主要 API をエクスポート。
- 監視・ペーパートレード検証ツール
  - monitoring.monitoring_db (参照箇所あり): 監視用 DB 初期化を起動時に冪等で保証。
  - tools/paper_verification_report.py: Paper Trading 用検証レポート生成スクリプトを追加。  
    - 稼働率・注文成功率・送信率・P95 レイテンシなどの指標を集計し PASS/FAIL 判定（デフォルト閾値を定義）。
    - コマンドライン引数で期間指定 (--from / --to) と DB パス (--db) を受け取り、デフォルトは環境変数または data/paper_trading.db。
- リサーチ基盤（部分実装）
  - research/factor_research.py: ファクター計算モジュールの骨格を追加（Momentum / Value / Volatility / Liquidity 設計と計算ユーティリティ）。DuckDB 経由で prices_daily / raw_financials を参照する設計。  
    - 注意: ファイル末尾に未完の実装（続きあり）を示す痕跡あり。今後の実装継続予定。
- パッケージ情報
  - __init__.py にバージョン 0.1.0 を設定。

変更 (Changed)
- なし（初回リリース）

修正 (Fixed)
- なし（初回リリース）

非推奨 (Deprecated)
- なし

削除 (Removed)
- なし

セキュリティ (Security)
- なし

既知の問題 / 注意点
- research/factor_research.py は設計方針と一部機能を実装しているものの、ファイル末尾に未完の箇所があり完全実装されていない可能性があります（今後の実装予定）。  
- run_monitoring は監視用 DB に settings.sqlite_path（本番パス）を常に使用する設計です。開発環境で分離が必要な場合は注意してください。  
- process_priority や CPU affinity の設定は権限不足やプラットフォーム非対応時は警告でスキップされます。運用環境で期待どおり動作するか事前確認を推奨します。  
- .env フォーマットパーサーは多くのケースに対応していますが、極端に複雑なシェル式展開などはサポートしていません。

使い方メモ（主な CLI / エントリポイント）
- 実行エンジン起動:
  - python -m kabusys.run_execution
- 監視起動:
  - python -m kabusys.run_monitoring
- 設定ウィザード:
  - python -m kabusys.config_setup
- 設定検証:
  - python -m kabusys.validate_config [--strict]
- Paper Trading 検証レポート:
  - python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

今後の予定
- research/factor_research の完成とテスト追加。
- 監視・実行の統合テスト、障害注入テストの強化。
- ブローカークライアント実装（Mock と実ブローカの整合性検証）とドキュメント拡充。