CHANGELOG
=========

すべての重要な変更を記録します。本ファイルは「Keep a Changelog」形式に準拠しています。

注: 日付・説明はリポジトリ内のコードから推測して作成しています。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-24
-------------------

Added
- 基本アーキテクチャとランタイムスクリプトを追加
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV に応じて paper_trading 用に専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient が利用されることを想定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。監視は本番 sqlite_path を使用する挙動を明示。
- 設定管理および自動.env ロード
  - config.py: Settings クラスを追加。環境変数の読み取り/検証ロジック（KABUSYS_ENV、LOG_LEVEL、各種パス、API トークン等）を提供。
  - 自動 .env 読み込み機能を追加（プロジェクトルート検出に .git / pyproject.toml を利用）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - .env のパース改善: export プレフィックス対応、クォート値のエスケープ処理、インラインコメントの扱いなどを実装。
- 設定ユーティリティ / CLI
  - config_setup.py: 対話式ウィザードで .env を作成・更新する CLI を追加。シークレット値はマスク表示し、ファイル保存前に確認を促す。
  - validate_config.py: 起動前に .env と config/*.yaml を検証する CLI を追加。--strict オプションで警告を FAIL 扱いにできる。YAML パーサがない場合は検証をスキップして警告。
- ロギング & プロセス制御ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次・30 日保持）を設定。既存ハンドラをクリアして二重設定を防止。
  - utils/process_priority.py: プラットフォーム差分（Windows / POSIX）を吸収したプロセス優先度設定と CPU affinity 設定機能を追加。失敗時は警告を出して安全にスキップ。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: シグナルのスコアで上位 N 件を選択。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分。全スコアが 0 の場合は等配分にフォールバック（警告）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限（max_sector_pct）を適用して候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す。未知レジームはフォールバックで 1.0（警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に基づき発注株数を算出。単元株（lot_size）単位で丸め、aggregate cap（available_cash）超過時にはスケールダウンして残差処理を行う。cost_buffer による保守見積りに対応。
- Paper Trading 検証ツール
  - tools/paper_verification_report.py: Paper Trading の SQLite 履歴から稼働率、注文成功率、送信率、レイテンシ（P95 等）を集計し PASS/FAIL 判定するレポート生成スクリプトを追加。閾値はソース内定義（稼働率 99%、成立率 90%、送信率 95%、P95 <=200ms）。
- 研究用ファクター計算基礎
  - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨子を追加（モメンタム・移動平均・ATR 等の方針と定数を実装）。（モジュールの一部は実装途中の断片あり）
- パッケージメタ情報
  - __init__.py に __version__ = "0.1.0" を追加し、主要サブパッケージを __all__ でエクスポート。

Changed
- ログの標準出力先を stderr ではなく stdout に変更（utils/logging_setup.py）。cron 等からのリダイレクト運用を考慮。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラをスキップしてコンソールのみで継続する耐障害性を追加。
- .env 読み込みの優先順位を明確化: OS 環境 > .env.local > .env。既存 OS 環境変数は保護される（protected 機構）。
- run_monitoring と run_execution の挙動
  - run_monitoring: MONITOR_POLL_INTERVAL の不正値に対して警告を出しデフォルトにフォールバックする堅牢化を追加。
  - run_execution: 停止フラグ（data/stop_requested.flag）を検知して安全にエンジン停止または起動中止する仕組みを実装。エンジンはデーモンスレッドで実行し、停止時は最大 30 秒待機して終了。

Fixed
- env パーサの不具合対策: export プレフィックス / クォート文字内のエスケープ / インラインコメント処理を正しく扱うように改善し、.env の柔軟な記述に対応。
- process_priority のクロスプラットフォーム例外ハンドリングを強化。管理者権限がない環境や未対応プラットフォームでは警告を出してスキップするようにした。
- ポートフォリオ算出におけるゼロ・負価格やデータ欠損時の安全弁を追加（価格未取得の銘柄はスキップ、分母ゼロ回避など）。
- Paper Trading レポート: データ不足（テーブル自体が存在しない等）に対して sqlite3.OperationalError を捕捉してレポート生成を継続するよう堅牢化。

Security
- config_setup が出力する .env ヘッダに「.env は絶対に Git にコミットしないこと」を明記。
- validate_config の本番チェック（KABUSYS_ENV=live 時）で LINE 通知設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告を追加。

Notes / Known limitations
- research/factor_research.py は設計方針と一部実装を含むが、関数実装が途中で切れている個所がある（ファイル末尾が不完全）。今後の実装が必要。
- 一部モジュール（execution の BrokerClientFactory、ExecutionEngine、OrderManager など）はインターフェイス呼び出し側を用意しているが、実装の詳細はこの差分のみでは不明。実ランタイムでの動作確認が推奨される。
- 単元株（lot_size）は現時点でグローバル固定（デフォルト 100）。将来的に銘柄別の lot_map 対応が予定されているコメントあり。

---

参考:
- 環境変数・構成関連: src/kabusys/config.py, src/kabusys/config_setup.py, src/kabusys/validate_config.py
- 実行スクリプト: src/kabusys/run_execution.py, src/kabusys/run_monitoring.py
- ユーティリティ: src/kabusys/utils/logging_setup.py, src/kabusys/utils/process_priority.py
- ポートフォリオ関連: src/kabusys/portfolio/*
- ツール: src/kabusys/tools/paper_verification_report.py
- 研究: src/kabusys/research/factor_research.py

（この CHANGELOG はコードの内容から推測して作成しています。実際のコミット履歴と差異がある場合は適宜調整してください。）