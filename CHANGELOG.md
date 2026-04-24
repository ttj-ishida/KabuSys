CHANGELOG.md

すべての重要な変更は「Keep a Changelog」形式で記録しています。
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-04-24
--------------------

Added
- 初期公開リリース: KabuSys 自動売買基盤のコアスクリプト・ユーティリティ・ライブラリを追加。
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と完全分離。
      - BrokerClientFactory を介してブローカークライアントを生成（ペーパートレード時は MockBrokerClient 想定）。
      - エンジンはバックグラウンドスレッドで実行され、data/stop_requested.flag を検知すると安全に停止。実行中の PID は data/execution.pid に記録。
      - プロセス優先度を "high" に設定（set_process_priority を使用）。
    - run_monitoring.py
      - SystemMonitor をポーリングする監視ループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバック。
      - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path（monitoring DB）を使用する仕様。
      - 停止はプロジェクトルート/data/stop_requested.flag によって検知。
  - 設定管理
    - config.py
      - .env 自動読み込み機能を実装（プロジェクトルートに .env/.env.local がある場合）。OS 環境変数は保護され、.env.local は上書き可。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 によって自動ロードを無効化可能。
      - 複数の設定プロパティを提供（J-Quants / kabu API / DB パス / Paper Trading 設定 / 監視閾値など）。
      - PAPER_FILL_MODE（ペーパートレードでの約定挙動）検証と制約（instant/partial/never/reject）。
    - config_setup.py
      - 対話式ウィザードで .env を初期作成・更新する CLI を追加。
      - .env の既存値読み込み、シークレットマスキング、デフォルト提示、書き込みテンプレートを提供。
      - 生成された .env に対する注意（Git にコミットしない等）を含む。
    - validate_config.py
      - .env と config/*.yaml の簡易検証 CLI を追加。
      - 必須環境変数チェック、KABUSYS_ENV や LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ確認、PyYAML があれば YAML のパースチェックを実施。
      - --strict オプションで警告も失敗扱いにできる。
  - ツール
    - tools/paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI。
      - 稼働率（uptime）、注文成功率（fill rate）、送信率（send rate）、API レイテンシ（平均/最大/P95）などを集計して PASS/FAIL 判定を出力。
      - デフォルト DB パスは data/paper_trading.db。--db/環境変数で指定可能。
      - 代表的な閾値: uptime >= 99%、fill_rate >= 90%、send_rate >= 95%、P95 latency <= 200ms。
  - ポートフォリオ構築ライブラリ（kabusys.portfolio）
    - portfolio_builder.py
      - select_candidates: BUY シグナルをスコア降順＋タイブレークで選択。
      - calc_equal_weights / calc_score_weights: 等金額配分およびスコア比例配分（スコア合計が 0 の場合は等配分にフォールバック）。
    - risk_adjustment.py
      - apply_sector_cap: セクター集中制限ロジック（既存保有のセクター比率が閾値を超える場合に新規候補を除外）。"unknown" セクターは除外対象外。
      - calc_regime_multiplier: 市場レジームに応じた資金乗数（bull:1.0 / neutral:0.7 / bear:0.3、未知は警告とともに 1.0 フォールバック）。
    - position_sizing.py
      - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に対応した株数計算を実装。
      - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap として available_cash 超過時のスケーリング、cost_buffer を利用した保守見積り、端数処理（残差に基づく追加割当）を実装。
      - 価格欠損や price <= 0 のケースはスキップしてログ出力。
  - ユーティリティ
    - utils/logging_setup.py
      - 一貫したログ初期化ユーティリティを提供（StreamHandler を stdout に、TimedRotatingFileHandler を日次ローテーションでログディレクトリへ出力）。
      - デフォルトログディレクトリは logs/、ログは 30 日分保持。
      - ログレベルとログディレクトリの解決順を明示（引数 > 環境変数 > デフォルト）。
    - utils/process_priority.py
      - プラットフォーム依存差分（Windows / POSIX）を吸収してプロセス優先度（high/normal/low）を設定するユーティリティを提供。
      - CPU affinity を最初の N コアに固定する set_cpu_affinity を提供。権限不足などは警告してスキップ。
  - リサーチ
    - research/factor_research.py（モジュール追加、主要ファクター計算の骨子を実装）
      - Momentum / Value / Volatility / Liquidity 等のファクターを DuckDB の prices_daily / raw_financials テーブルから計算する方針と基本定数を実装。モメンタム計算（calc_momentum）の実装開始。
  - パッケージ情報
    - __init__.py にてバージョンを 0.1.0 に設定。

Changed
- .env 読み込みの優先順位を明確化: OS 環境変数 > .env.local > .env。OS 環境変数は保護され .env ファイルから上書きされない。
- ログ出力の標準化: すべての起動スクリプトで共通の setup_logging を使うことで stdout とファイル出力が一貫化。

Fixed
- （初版のため該当なし／実装時に既知の不整合を排した旨の改善を実施）

Notes / Implementation details（補足）
- セーフガードやフォールバックが多めに組み込まれており、権限不足・ファイル作成失敗・不正な環境変数値などの場面では警告ログを出して処理を継続する設計です。
- Paper Trading の分離: paper_trading 環境は本番 DB と独立する設計で、誤って本番データを書き込まないよう配慮されています。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用するため、環境設定による誤差を生じさせない意図があります（監視は本番実データに基づいて行うため）。
- research/factor_research.py はファイル末尾で実装途中（calc_momentum の続きが未完成）に見えるため、今後の追加実装が想定されます。

Acknowledgements
- 初期実装はモジュール分割とテスト容易性を考慮した純粋関数・副作用制御を目標に設計されています。今後、新機能追加やパラメータ調整、ユニットテストの充実を推奨します。