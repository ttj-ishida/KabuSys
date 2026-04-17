# Changelog

すべての変更は Keep a Changelog の形式に従い、重大度の高い変更から下に記載しています。日付はこのリリース作成時点のものです。

[Unreleased]
- なし

[0.1.0] - 2026-04-17
----------------------------------------
Added
- 初期リリース。以下の主要機能・モジュールを追加。
  - 実行スクリプト・監視スクリプト
    - src/kabusys/run_execution.py
      - ExecutionEngine を起動するエントリポイント。
      - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite（data/paper_trading.db 既定）を使用し、本番 DB と分離。
      - BrokerClientFactory によるブローカークライアント生成、OrderRepository/OrderManager/RiskManager/Reconciler の組み立て、ExecutionEngine の起動監視（停止フラグによる安全停止）を実装。
      - 実行前にプロセス優先度を "high" に設定する処理を追加（src/kabusys/utils/process_priority.py を利用）。
      - 実行中の PID を data/execution.pid に保存する仕組みの受け皿（pid_file を渡す）。
    - src/kabusys/run_monitoring.py
      - SystemMonitor のポーリングループ起動スクリプト。
      - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値は警告を出してデフォルトにフォールバック。
      - 監視は KABUSYS_ENV にかかわらず監視用（本番） sqlite_path を使用する設計。
      - 起動時にプロセス優先度 "high" を設定、停止フラグ（data/stop_requested.flag）検出でループを終了。
  - 設定管理・ウィザード・検証
    - src/kabusys/config.py
      - .env 自動読み込み（プロジェクトルート検出: .git または pyproject.toml）。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
      - .env および .env.local の読み込み順序（OS 環境変数が優先、.env.local は上書き）を実装。
      - 複雑な .env 行パースを実装（export プレフィックス、クォート内のバックスラッシュエスケープ、インラインコメント判定など）。
      - Settings クラスを導入し、環境変数のプロパティ化（パス、しきい値、ログレベル判定、PAPER_FILL_MODE のバリデーション等）を実装。
    - src/kabusys/config_setup.py
      - 対話式ウィザードで .env を初期作成・更新する CLI を実装。既存値の読み込み、秘密値のマスク表示、選択肢やデフォルトの提示、保存確認をサポート。
    - src/kabusys/validate_config.py
      - 設定検証 CLI を追加。必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パスの親ディレクトリ存在確認、config/*.yaml の存在・パース検証（PyYAML の有無を考慮）などをチェック。
      - --strict オプションで警告を FAIL 扱いにできる。
  - ポートフォリオ構築関連（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py
      - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。score が全て 0 の場合は等配分へフォールバックして警告を出す。
    - src/kabusys/portfolio/risk_adjustment.py
      - セクター集中チェック（apply_sector_cap）と市場レジームに基づく乗数（calc_regime_multiplier）を実装。未知レジームは 1.0 でフォールバックし警告を出す。
      - apply_sector_cap は "unknown" セクターに対してセクター上限を適用しない仕様。
    - src/kabusys/portfolio/position_sizing.py
      - position sizing ロジックを実装（allocation_method: "risk_based" / "equal" / "score" をサポート）。
      - 単元（lot_size）丸め、1 銘柄上限（max_position_pct）、aggregate cap（available_cash を超える場合のスケーリング）を実装。スケール時は残差に基づく lot 単位の再配分を行う。
      - コストバッファ（cost_buffer）で保守的見積もりを行う設計。
      - 将来的拡張の TODO（銘柄別 lot_size のサポート）を注記。
  - リサーチ / ファクター計算
    - src/kabusys/research/factor_research.py（部分実装）
      - DuckDB を用いたファクター計算（Momentum, Volatility, Liquidity 等の計算ロジック）を実装。prices_daily / raw_financials を参照。
      - 計算窓・欠損取り扱い、P95 など統計的指標の算出を考慮。
  - ツール
    - src/kabusys/tools/paper_verification_report.py
      - Paper Trading の検証レポート生成 CLI を追加。稼働率、注文成功率、送信率、レイテンシ（P95）などを評価し PASS/FAIL を判定。期間指定 --from/--to、DB パス指定 --db をサポート。
  - ユーティリティ
    - src/kabusys/utils/process_priority.py
      - Windows/Linux/Mac の差分を吸収するプロセス優先度設定ユーティリティを追加。psutil を利用し、優先度設定失敗時は警告を出して安全にスキップする。
      - CPU affinity を指定コア数に固定するユーティリティも提供（set_cpu_affinity）。
  - パッケージ
    - src/kabusys/__init__.py にバージョン情報 __version__ = "0.1.0" を追加。

Changed
- 該当なし（初期リリースのため既存変更履歴なし）。

Fixed
- 該当なし（初期リリース。ただし多くの箇所で堅牢化・フォールバック処理を導入）。
  - 例: MONITOR_POLL_INTERVAL の不正値を検知してデフォルトにフォールバックする警告追加。
  - .env 読み込みで失敗したファイルは警告（warnings.warn）を出して処理継続するように変更。

Deprecated
- なし

Removed
- なし

Security
- セキュリティ関連注意事項:
  - .env ファイルは絶対に Git にコミットしない旨を config_setup.py のヘッダに明記。
  - 本番環境（KABUSYS_ENV=live）では LINE のトークン未設定や KILL_FLAG_CLEAR_ON_START=1 の危険性を validate_config.py で警告するように実装。

Notes / Known limitations / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）だと exposure が過少見積りとなる可能性がある（risk_adjustment にも同様の注記）。将来的に前日終値や取得原価をフォールバック価格として導入予定。
  - lot_size は現状全銘柄共通（将来、銘柄別 lot_map に拡張予定）。
- research/factor_research.py:
  - ファイルは主要ロジックを含むが、DuckDB テーブル（prices_daily / raw_financials）のスキーマ依存があるため、実運用前にデータ準備が必要。
- 一部モジュール（monitoring_db.py、system_monitor.py、ExecutionEngine 本体、BrokerClient 実装など）はこの差分に含まれていないため、統合時に実際の動作確認が必要。

参考
- コマンド例:
  - 設定ウィザード: python -m kabusys.config_setup
  - 設定検証: python -m kabusys.validate_config [--strict]
  - 監視起動: python -m kabusys.run_monitoring
  - 実行エンジン起動: python -m kabusys.run_execution
  - Paper 検証レポート: python -m kabusys.tools.paper_verification_report [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--db PATH]

----------------------------------------
（この CHANGELOG はコード内容から推測して作成しています。実際のリリースノートとして使用する場合は、差分やコミット履歴と照合してください。）