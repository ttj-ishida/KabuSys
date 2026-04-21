CHANGELOG
=========
すべての重要な変更点を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注: 以下は提示されたコードベースの内容から推測して作成した変更履歴です。

Unreleased
----------
（なし）

[0.1.0] - 2026-04-21
--------------------

Added
- 初期リリース: KabuSys 自動売買フレームワークの基本コンポーネントを追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。
  - 起動スクリプト
    - run_execution.py: 実行エンジン（ExecutionEngine）起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（data/paper_trading.db）を使用し、MockBrokerClient による分離されたペーパートレード実行が可能。
    - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルにより安全にループを終了可能。
  - 設定管理
    - config.py: 環境変数/.env ロード・ラッパーを追加。プロジェクトルート自動検出（.git または pyproject.toml）に基づいて .env/.env.local を自動読み込み。KABUSYS_DISABLE_AUTO_ENV_LOAD で自動ロード無効化可能。Settings クラスに各種設定プロパティ（DB パス、API トークン、ログレベル、監視閾値など）を実装。
    - config_setup.py: 対話式 .env ウィザードを追加。機密値はマスク表示、保存前確認を実施。
    - validate_config.py: 起動前設定検証 CLI を追加。必須環境変数、KABUSYS_ENV、ログレベル、DB パス、config/*.yaml の存在とパース（PyYAML が利用可能な場合）をチェック。--strict オプションで警告をエラー扱いにできる。
  - ロギング / プロセス優先度ユーティリティ
    - utils/logging_setup.py: 統一的なロギング設定関数 setup_logging を追加。StreamHandler（stdout）と TimedRotatingFileHandler（日次ローテーション、30日保持）を設定。LOG_DIR/LOG_LEVEL による制御、ログディレクトリ作成失敗時のフォールバック処理等を実装。
    - utils/process_priority.py: psutil を使ったプロセス優先度設定（Windows/Linux の差分吸収）と CPU affinity 設定ユーティリティを追加。許容レベル "high"/"normal"/"low" をサポートし、権限不足時は警告を出してスキップ。
  - ポートフォリオ構築モジュール
    - portfolio/portfolio_builder.py: 銘柄候補選定と重み算出（等金額・スコア加重）を追加。select_candidates は score 降順、同点は signal_rank 昇順でタイブレーク。
    - portfolio/risk_adjustment.py: セクター集中制限 apply_sector_cap と市場レジームに基づく投下資金乗数 calc_regime_multiplier を追加。unknown セクターに対する挙動やレジームフォールバックを明記。
    - portfolio/position_sizing.py: 発注株数決定ロジックを追加。リスクベース／等配分／スコア配分をサポートし、単元（lot_size）丸め、1銘柄上限・全体上限（aggregate cap）とスケーリング、cost_buffer を使った保守的コスト見積りを実装。
    - portfolio/__init__.py に主要関数をエクスポート。
  - リサーチ / ファクター計算
    - research/factor_research.py: DuckDB を用いたファクター計算モジュールの骨組みを追加（モメンタム、移動平均、ATR、出来高系などを想定）。（実装の一部がスケルトン／継続作業を示唆）
  - ツール
    - tools/paper_verification_report.py: ペーパートレードの検証レポート生成ツールを追加。PAPER_TRADING_SQLITE_PATH（または --db）からデータを読み、稼働率、注文成功率、送信率、API レイテンシ（平均・最大・P95）などを算出して PASS/FAIL 判定を出力。各種しきい値（稼働率 99%、fill 90% など）を定義。
  - 監視 DB 初期化
    - monitoring/monitoring_db.py（モジュール参照あり）経由で監視用テーブルを起動時に作成する仕組みを起動スクリプトから呼び出すように統一。

Changed
- .env パースの堅牢化（config.py）
  - export プレフィックス対応、クォート内のバックスラッシュエスケープ対応、インラインコメントやクォートなしのコメント解釈ルールの明確化を導入。
  - .env 読み込みは override と protected（OS 環境変数保護）オプションをサポート。これにより .env.local が .env を上書きでき、OS 環境変数は保護される。
- ロギング動作
  - setup_logging により既存ルートハンドラを一旦 flush/close してから再設定することで、多重ハンドラ設定を防止。
  - 標準出力は stderr ではなく stdout を使用（cron/Task Scheduler からのリダイレクトを想定）。
- 実行フローの共通化
  - run_execution/run_monitoring 起動時にプロセス優先度を最初に "high" に設定する処理を共通化して配置（utils/process_priority.set_process_priority の利用）。
  - DB 接続では duckdb と sqlite3 を併用する方針を明確化（DuckDB: 分析、SQLite: 監視／履歴）。
- ペーパートレード分離
  - Execution 起動時は settings.is_paper に応じて専用の paper_trading DB を利用し、本番 DB と完全に分離する設計を採用。

Fixed
- run_monitoring のポーリング間隔設定
  - MONITOR_POLL_INTERVAL の不正値（非整数・0 以下）に対して警告ログを出し、デフォルト（60 秒）にフォールバックするように修正。time.sleep に渡す不正値による例外を予防。
- run_monitoring の例外ハンドリング
  - monitor.check_once() 内での予期せぬ例外をキャッチしてログに残し、次ポーリングへ継続するように安全化。
- run_execution のシャットダウン制御
  - 停止フラグ（data/stop_requested.flag）を監視し、検知時に engine.stop() を呼び出して安全にスレッドを停止する処理を導入。PID ファイル path を Engine に渡す設計。

Security
- 機密値取り扱い
  - config_setup のウィザードで機密項目（トークン、パスワード）をマスク表示する実装を導入。これにより対話時に画面上で値が露出しにくい（ただし完全な秘密管理ソリューションではない）。

Notes / Known limitations
- research/factor_research.py はファクター計算の設計方針と多くの定数を含むが、実装が途中で切れている（スケルトンが含まれる）。今後、DuckDB クエリ実装やテストデータでの検証が必要。
- apply_sector_cap 内で価格が欠損（0.0）の場合、エクスポージャーの過少見積りによりブロックが回避される可能性がある旨を TODO コメントで残している。将来的にフォールバック価格（前日終値など）の導入を検討すべき。
- process_priority / set_cpu_affinity は権限やプラットフォーム依存で失敗する可能性があり、失敗時は警告を出してスキップする設計。

今後の予定（提案）
- factor_research の完成（DuckDB SQL 実装・ユニットテスト追加）
- 発注関連（ExecutionEngine / BrokerClient）およびモニタリング各コンポーネントの詳細実装と統合テスト
- ログ/メトリクスの更なる標準化（構造化ログ、Prometheus/Push gateway 連携等）
- .env の秘密管理を Vault 等に統合する検討

----- 
この CHANGELOG はコード内容から推測して作成したため、実際のコミット履歴とは差異がある可能性があります。必要であれば実際の Git 履歴に合わせて調整します。