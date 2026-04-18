Keep a Changelog
=================

すべての重要な変更点を記録します。フォーマットは "Keep a Changelog" に従います。

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-18
-------------------

Added
- 初回リリースを追加（パッケージバージョン: 0.1.0）。
  - src/kabusys/__init__.py にて __version__ を 0.1.0 に設定。

- 環境設定 / 読み込み
  - .env / .env.local の自動読み込み機構を追加。プロジェクトルート（.git または pyproject.toml）を基準に探索し、自動で環境変数を取り込む（無効化用フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD）。
    - 実装: src/kabusys/config.py
  - .env パースの強化:
    - export 形式のサポート、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
    - 無効行や空行・コメント行の扱いを明確化。
    - 実装: src/kabusys/config.py

- Settings クラス
  - 環境変数をラップした Settings クラスを提供。J-Quants / kabu API / LINE / DB / 監視 / システム設定など多数のプロパティを提供。
  - PAPER_FILL_MODE の検証、paper_trading 用 DB パス（PAPER_TRADING_SQLITE_PATH）などのユーティリティを含む。
    - 実装: src/kabusys/config.py

- 対話式設定ウィザード
  - .env の初期作成・更新を補助する CLI を追加。シークレット項目のマスク表示、選択肢サポート、既存値の再利用など。
  - 実装: src/kabusys/config_setup.py

- 設定検証ツール
  - .env と config/*.yaml の整合性チェックを行う CLI を追加。必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL 検証、DB パスの親ディレクトリ有無チェック、PyYAML がある場合は YAML のパース検査を実行。
  - --strict オプションで警告を FAIL 扱いにできる。
  - 実装: src/kabusys/validate_config.py

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加:
    - 実装: src/kabusys/run_execution.py
    - 特徴:
      - プロセス優先度を最初に "high" に設定。
      - KABUSYS_ENV=paper_trading の場合は paper_trading 専用 SQLite DB（data/paper_trading.db）を使用し、本番 DB と分離。
      - BrokerClientFactory によりブローカークライアントを生成。
      - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine をデーモンスレッドで起動。
      - 停止は data/stop_requested.flag を検知して安全に実行エンジンを停止。
      - PID ファイル出力（data/execution.pid）をサポート。
      - RiskManager の既定設定（max_position_pct 等）を付与し、初期資産として broker.get_available_cash() を使用。

  - 監視ポーリングループ起動スクリプトを追加:
    - 実装: src/kabusys/run_monitoring.py
    - 特徴:
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告後デフォルトにフォールバック。
      - 監視（monitoring）は KABUSYS_ENV に関わらず本番 sqlite_path を使用する設計。
      - 停止はプロジェクト data/stop_requested.flag の存在で検知。
      - SystemMonitor.check_once() の例外はロギングして次回ポーリングへ復帰。

- ログ設定ユーティリティ
  - 統一的なログセットアップ関数を追加:
    - 実装: src/kabusys/utils/logging_setup.py
    - 特徴:
      - stdout への StreamHandler + 日次ローテーション（TimedRotatingFileHandler）を組み合わせてルートロガーを設定。
      - ログレベル解決順: 関数引数 > 環境変数 LOG_LEVEL > デフォルト INFO。
      - ログディレクトリ解決順: 引数 > LOG_DIR 環境変数 > logs/ デフォルト。
      - ログディレクトリ作成失敗時はファイルハンドラをスキップしコンソール出力のみ継続。

- プロセス優先度 / CPU affinity ユーティリティ
  - psutil を用いて Windows / POSIX の差分を吸収するユーティリティを追加:
    - 実装: src/kabusys/utils/process_priority.py
    - 機能:
      - set_process_priority(level: "high"|"normal"|"low") — Windows の優先度クラスまたは POSIX の nice 値を適用。アクセス権限等で失敗した場合は警告を出してスキップ。
      - set_cpu_affinity(cpu_count) — 最初の N コアにピン留め。未指定時は変更しない。

- ポートフォリオ構築モジュール
  - 候補選択・重み計算:
    - 実装: src/kabusys/portfolio/portfolio_builder.py
    - select_candidates, calc_equal_weights, calc_score_weights（スコアが全て 0 のとき等金額配分にフォールバック。警告出力あり）
  - セクター集中制限・レジーム乗数:
    - 実装: src/kabusys/portfolio/risk_adjustment.py
    - apply_sector_cap（既存保有比率が閾値を超えるセクターの新規候補排除）、calc_regime_multiplier（bull/neutral/bear に基づく乗数、未知のレジームは警告の上でフォールバック）
  - 株数決定・単元丸め・投下金額スケーリング:
    - 実装: src/kabusys/portfolio/position_sizing.py
    - allocation_method に "risk_based" / "equal" / "score" をサポート。lot_size による単元丸め、aggregate cap を超える場合のスケーリングと端数分配ロジック、cost_buffer を考慮した保守的見積り等を実装。
  - これらをパッケージングしてエクスポート:
    - 実装: src/kabusys/portfolio/__init__.py

- リサーチ / ファクター計算基盤
  - DuckDB 接続を受け取るファクター計算モジュールを追加（Momentum / Value / Volatility / Liquidity を想定）。
    - 実装開始: src/kabusys/research/factor_research.py
    - Momentum 計算の仕様と定数（1M/3M/6M、MA200、ATR など）を定義。関数 calc_momentum の骨格を追加（なおファイル末尾で実装断片が存在）。

- ペーパートレード検証ツール
  - Paper Trading の実績を集計・判定するレポート生成スクリプトを追加:
    - 実装: src/kabusys/tools/paper_verification_report.py
    - 機能:
      - system_status / trade_logs / risk_logs を集計して稼働率・注文成功率・送信率・レイテンシ（P95）等を算出。
      - 閾値を用いた PASS/FAIL 判定（稼働率 >= 99%、注文成功率 >= 90% 等）。
      - CLI 引数で期間（--from/--to）と DB パス（--db）を指定可能。
      - P95 計算、欠損データに対するフォールバックを実装。

Changed
- 初期設計で一貫したログ出力・プロセス優先度制御を全起動スクリプトで利用するよう統一。
  - run_execution.py / run_monitoring.py の起動フローで setup_logging() と set_process_priority("high") を先頭で呼ぶように設計。

Fixed
- N/A（初回リリースのため既知の不具合修正履歴はなし）。

Deprecated
- N/A

Removed
- N/A

Security
- 環境設定ファイル (.env) を生成する際に注意喚起を .env ヘッダに記載（.env を Git にコミットしないよう明示）。

Notes / Known limitations
- research/factor_research.py はモメンタム計算の定義を含みますが、一部実装が未完（ファイル末尾にて実装未完の印跡あり）。実運用前に追加実装・テストが必要です。
- apply_sector_cap は price_map に価格がない（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的にフォールバック価格ロジックを導入予定。
- process_priority / set_cpu_affinity は環境（権限・OS）により動作が制限される場合があるため、失敗時は警告を出して処理をスキップする設計。

References
- 主要ファイル:
  - src/kabusys/config.py
  - src/kabusys/config_setup.py
  - src/kabusys/validate_config.py
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/utils/logging_setup.py
  - src/kabusys/utils/process_priority.py
  - src/kabusys/portfolio/*.py
  - src/kabusys/research/factor_research.py
  - src/kabusys/tools/paper_verification_report.py

--- 

この CHANGELOG はソースコードから推測して生成したもので、実際のコミット履歴や変更履歴と完全に一致しない場合があります。必要ならば特定のファイルの差分や追加情報に基づいて修正します。