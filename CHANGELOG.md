CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠しています。

Unreleased
----------

（現在なし）

0.1.0 - 2026-04-19
------------------

Added
- プロジェクト初期リリースを追加。
- 基本パッケージ情報を追加:
  - src/kabusys/__init__.py にバージョン (0.1.0) とエクスポート一覧を追加。
- 起動スクリプト:
  - src/kabusys/run_execution.py
    - ExecutionEngine 起動ロジックを実装。
    - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite（デフォルト: data/paper_trading.db）を使用する分離を実装。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、ExecutionEngine のスレッド実行と停止フラグ検知（data/stop_requested.flag）を実装。
    - プロセス優先度を "high" に設定する処理を起動時に実行。
    - PID ファイル管理用パスを使用。
  - src/kabusys/run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境に関係なく本番用 sqlite_path を使用する扱いを明示。
    - stop フラグ検知でループ終了、例外時にログ出力して次ポーリングへ継続する堅牢化。
- 設定・環境管理:
  - src/kabusys/config.py
    - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml を探索）。
    - .env 読み込みでの詳細なパース処理を実装（exportプレフィックス、クォート内エスケープ、コメント処理等）。
    - Settings クラスを提供し各種環境変数アクセスをラップ（J-Quants, kabuAPI, DB パス, ログレベル, 環境種別フラグ等）。
    - PAPER_FILL_MODE のバリデーション、paper_sqlite_path、各種閾値設定プロパティを実装。
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD に対応。
  - src/kabusys/config_setup.py
    - 対話式 .env 作成/更新ウィザードを実装（各種設定項目、シークレット入力対応、既存 .env の読み込みと保存機能）。
  - src/kabusys/validate_config.py
    - 起動前の設定検証 CLI を実装（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ確認、config/*.yaml の存在確認と YAML パース検査）。
    - --strict オプションで警告をエラー扱いにできる。
- ログ・プロセスユーティリティ:
  - src/kabusys/utils/logging_setup.py
    - 統一的なログ設定ユーティリティを実装（コンソール stdout ハンドラ + 日次ローテーションファイルハンドラ、LOG_DIR/LOG_LEVEL の解決順を実装、既存ハンドラのクリア処理）。
  - src/kabusys/utils/process_priority.py
    - Windows / POSIX を吸収するプロセス優先度設定機能を実装（nice / HIGH_PRIORITY_CLASS 等のフォールバック処理）。
    - CPU affinity を設定する set_cpu_affinity を実装（存在しない場合はスキップして警告ログ）。
- ポートフォリオ構築関連 (純粋関数群、データベース参照なし):
  - src/kabusys/portfolio/portfolio_builder.py
    - 候補選定 select_candidates、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装。
    - スコアが全て 0 の場合に等金額配分へフォールバックする警告を実装。
  - src/kabusys/portfolio/risk_adjustment.py
    - セクター集中制限 apply_sector_cap を実装（既存保有をポートフォリオ比で評価し、上限超過セクターの候補除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知レジームは警告してフォールバック）。
    - 実装内に price 欠損時の注意点（TODO）を明記。
  - src/kabusys/portfolio/position_sizing.py
    - position sizing ロジックを実装（risk_based / equal / score 各方式、lot_size 単位丸め、aggregate cap によるスケーリング、cost_buffer を考慮）。
    - スケーリング時の残差処理（lot 単位で再配分）を実装。
  - src/kabusys/portfolio/__init__.py にエクスポートを整備。
- Paper Trading 検証ツール:
  - src/kabusys/tools/paper_verification_report.py
    - Paper Trading 用 SQLite（デフォルト data/paper_trading.db）から指標を抽出しレポートを生成する CLI を実装。
    - システム稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）やリスク却下件数を計算。
    - PASS/FAIL 判定基準（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）を実装。
    - --from / --to / --db オプション対応。
- 研究用モジュール（骨組み実装）:
  - src/kabusys/research/factor_research.py
    - ファクター計算モジュールの設計と一部定数・関数骨子を追加（モメンタム、MA、ATR、出来高等の定義と意図）。
    - DuckDB 接続を受けて prices_daily / raw_financials を参照する設計方針を記述。
- 監視 DB 初期化フック:
  - init_monitoring_db を各起動スクリプトで呼び出し、監視テーブルの存在保証（冪等）を行う実装を追加。

Changed
- （初期リリースのため該当なし）

Fixed
- （初期リリースのため該当なし）

Deprecated
- （初期リリースのため該当なし）

Removed
- （初期リリースのため該当なし）

Security
- （初期リリースのため該当なし）

Notes / Known limitations
- research/factor_research.py は途中までの実装で、実際の SQL クエリ実装は継続が必要（ファイル終端が未完成）。
- apply_sector_cap 内で price が欠損 (0.0) の場合にエクスポージャーが過少見積りされる旨の TODO コメントあり。将来的にフォールバック価格の導入を検討する必要あり。
- logging_setup はログディレクトリ作成に失敗した場合にファイルハンドラをスキップする設計。運用時は LOG_DIR の書き込み権限を確認すること。
- process_priority / set_cpu_affinity は権限不足やプラットフォーム差分で無効化される可能性がある（警告ログを出力してスキップ）。

今後の予定（例）
- factor_research の実装完了とユニットテスト追加。
- ExecutionEngine / SystemMonitor 周りの統合テストと動作確認用のサンプル設定を追加。
- 各コンポーネントに対するユニットテスト・CI の整備。

--- 

（翻訳・記載はソースコード中の実装とコメントから推測して作成しています。運用・リリース時は実際のコミット履歴に基づいて更新してください。）