CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
初期リリース(0.1.0)として、以下の機能群・ユーティリティを実装しました（コードベースから推測してまとめています）。

[Unreleased]
------------

- ドキュメント化されている TODO や未実装箇所の注記を追加。
  - portfolio.position_sizing の lot_size を銘柄毎に拡張する検討（TODO コメント）。
  - research.factor_research の calc_momentum 実装が途中で切れている旨（開発継続が必要）。
- いくつかの関数で将来の拡張ポイント（価格フォールバック等）を注記。

[0.1.0] - 2026-04-19
-------------------

Added
- 実行用スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御用ファイル data/stop_requested.flag を監視して安全にループを終了。
    - Monitoring は環境にかかわらず本番 sqlite_path を使用する設計（環境分離方針の明確化）。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading の場合はペーパートレード用 DB（デフォルト data/paper_trading.db）を使用。
    - 起動前に停止フラグを確認し、エンジンを起動しないオプションを実装。
    - 実行中は停止フラグでエンジン停止を安全に行うループとデーモンスレッドを利用。
- 環境設定関連 CLI/ユーティリティ
  - config_setup.py: .env の初期作成・更新を対話式で行うウィザードを実装。
    - デフォルト値、マスク表示（シークレット項目）や説明表示を備えた入力ループ。
    - .env 出力フォーマットを規定し、生成手順を明示。
  - validate_config.py: 起動前設定検証 CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス存在チェック、config/*.yaml の存在と（可能なら）YAML パース検証、live 環境向けの追加ガードを実装。
    - --strict オプションで警告を失敗扱いにできる。
- 環境変数読み込み & 設定管理
  - config.py:
    - プロジェクトルート検出（.git または pyproject.toml）に基づく自動 .env ロード機能を実装（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - .env ファイルの行パーサ（クォートやエスケープ、inline コメントの扱い）を堅牢に実装。
    - Settings クラスを導入し、J-Quants / kabu API / DB パス / 各種監視しきい値 / 環境フラグ等のプロパティを提供。
    - paper_trading 用の PAPER_TRADING_SQLITE_PATH、PAPER_FILL_MODE 等の設定をサポート。
- ポートフォリオ構築ロジック（純粋関数群）
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア順選定（タイブレークルールあり）。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重の重み計算（全スコア 0 の場合は等配分へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中上限チェック（既存保有を考慮）と候補フィルタ。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知値はフォールバックと警告）。
  - portfolio/position_sizing.py:
    - calc_position_sizes: 複数の allocation_method（risk_based / equal / score）に基づく発注株数算出。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（利用可能現金に合わせたスケーリング）、cost_buffer を考慮した保守的見積りを実装。
    - スケーリング時に残差を lot 単位で再配分するロジックを実装（再現性確保のため安定ソート）。
- ロギング / プロセス制御ユーティリティ
  - utils/logging_setup.py:
    - setup_logging を実装。root ロガーへ StreamHandler (stdout) と TimedRotatingFileHandler（日次・30日保持）を設定。
    - ログレベル解決順・ログディレクトリ解決順を定義。ディレクトリ作成失敗時はファイル出力を無効化して継続。
  - utils/process_priority.py:
    - set_process_priority: Windows / POSIX の差分を吸収して優先度設定（psutil 使用）。
    - set_cpu_affinity: 指定コア数へ CPU affinity を固定するユーティリティ（未指定は無変更）。
    - アクセス権限不足時は安全にスキップして警告ログを出す。
- ペーパートレード検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading DB（デフォルト data/paper_trading.db）からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数を集計してレポート出力。
    - Pass/Fail 判定基準を定義（稼働率 99%、fill_rate 90%、send_rate 95%、P95 レイテンシ 200 ms）。
    - P95 計算、期間フィルタリング、欠損テーブルへのフォールバック処理を提供。
- データベース / 分析統合
  - DuckDB を analytics/集計用途に接続するインフラを各スクリプトで確保（duckdb 接続を受け渡す設計）。
  - monitoring 用 SQLite、paper_trading 用 SQLite の分離を明確化。

Changed
- ログ出力の標準化: すべての起動スクリプトは setup_logging を最初に呼び出すことで一貫したログ設定を使用するように変更。
- 環境変数ロードの優先順位: OS 環境 > .env.local > .env（既存 OS 環境変数は保護され上書きされない）。
- run_monitoring/run_execution でプロセス優先度を起動時に "high" へ設定する振る舞いを採用（set_process_priority を利用）。

Fixed
- 環境変数パースの強化: シングル/ダブルクォート内のバックスラッシュエスケープや inline コメント処理を正しく扱うよう修正（.env の読み込みが堅牢に）。
- .env 読み込みエラー時の警告を明確化（読み込み失敗で警告を出し継続）。

Security
- .env を生成する際に README コメントで「.env を絶対に Git にコミットしないこと」を明記（config_setup.py に反映）。

Notes / その他（実装上の注意）
- monitoring は「環境にかかわらず本番 sqlite_path を使用する」方針がコード内に明記されています。テストやペーパートレード環境と本番 DB を物理的に分離したい場合は別途設定・運用上の注意が必要です。
- PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）を Settings クラスで行い、不正値は ValueError を発生させます。
- process_priority/set_cpu_affinity はプラットフォーム差や権限不足により失敗する可能性があるため、失敗時は警告でスキップする安全設計になっています。
- research.factor_research モジュールはファクター計算設計に着手しており、calc_momentum の実装が途中で終端しています。継続実装が必要です。

Contributing
- 設定の検証は validate_config.py を使って行えます。CI や起動前チェックに組み込むことを推奨します。
- .env 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。テスト実行時に有用です。

以上。必要であればバージョンごとの差分をより細かく（ファイルごと・関数ごと）記載します。どの粒度で CHANGELOG を出力するか指定してください。