CHANGELOG
=========

すべての顕著な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
----------

（未リリースの変更はここに記載します）

[0.1.0] - 2026-04-19
-------------------

初回公開リリース。

### 追加 (Added)

- 全体
  - パッケージ初期版を追加。パッケージ名: KabuSys、バージョン 0.1.0（src/kabusys/__init__.py）。
  - モジュール構成を整備し、monitoring / execution / portfolio / utils / research / tools 等の主要機能を提供。

- 実行・監視
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV に応じて paper_trading 用 DB を分離（data/paper_trading.db デフォルト）。
    - BrokerClientFactory によりブローカークライアントを抽象化して生成。
    - ExecutionEngine、OrderManager、OrderRepository、RiskManager、Reconciler を組み立てて実行。デーモンスレッドで run_session を回す。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル（data/execution.pid）により外部停止をサポート。
    - RiskConfig によるリスク制限（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を導入。
  - 監視ループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor を用いた定期チェックのポーリングループを実装。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番用 sqlite_path を使用して監視テーブルを初期化。
    - 停止フラグ（data/stop_requested.flag）を検知して gracefully shutdown。

- 設定管理 / CLI
  - Settings クラスを追加して環境変数から設定を取得（src/kabusys/config.py）。
    - 自動でプロジェクトルート（.git または pyproject.toml）を探索し .env / .env.local を読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
    - DB パス（DUCKDB_PATH, SQLITE_PATH）、PID/kill フラグパス、閾値、LOG_LEVEL、KABUSYS_ENV の検証などを提供。
    - PAPER_FILL_MODE や PAPER_TRADING_SQLITE_PATH 等の paper_trading 関連設定を提供。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数の存在チェック、KABUSYS_ENV/LOG_LEVEL チェック、DB パス親ディレクトリチェック、config/*.yaml の存在とパース（PyYAML があれば）を実施。
    - --strict オプションで警告を失敗扱いにできる。
  - インタラクティブな .env 作成ウィザードを追加（src/kabusys/config_setup.py）。
    - ユーザフレンドリな対話式入力、既存 .env 読み込み、書き出し機能を提供。

- ロギング・プロセス制御ユーティリティ
  - 統一ログセットアップユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - stdout への StreamHandler と日次ローテートの TimedRotatingFileHandler（logs/<app_name>.log）をルートロガーに設定。
    - ログディレクトリ自動作成、既存ハンドラのクリア、ログレベル環境変数/引数からの解決などを実装。
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows と POSIX（Linux/Mac/FreeBSD）を吸収して nice / HIGH_PRIORITY_CLASS を適切に設定。
    - set_cpu_affinity により先頭 N コアにプロセスをピン留め可能（optional）。
    - アクセス権限や未対応 OS の場合は安全に警告を出してスキップ。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates: スコア降順 + signal_rank タイブレークで上位 N を選定。
    - calc_equal_weights, calc_score_weights: 等金額・スコア加重（スコアが全て 0 の場合は等金額にフォールバック）。
  - セクター制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 同一セクターの既存エクスポージャが上限を超える場合に新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: market レジーム (bull/neutral/bear) に応じた投下資金乗数（デフォルト値とフォールバック挙動を実装）。
  - 株数決定・サイズ調整（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。
    - 単元株（lot_size）で丸め、1銘柄上限（max_position_pct）、aggregate cap（available_cash）を適用。
    - cost_buffer を用いた保守的コスト見積り、総額超過時のスケーリングと端数補正ロジックを実装。

- ツール
  - Paper Trading 検証レポート生成スクリプトを追加（src/kabusys/tools/paper_verification_report.py）。
    - データベース（デフォルト: data/paper_trading.db）から system_status / trade_logs / risk_logs を参照して指標を集計。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等を算出し PASS/FAIL 判定を出力。
    - CLI オプション --from/--to/--db をサポート。閾値はソース内定義（稼働率 >= 99% 等）。

- リサーチ
  - ファクター計算モジュールの骨格を追加（src/kabusys/research/factor_research.py）。
    - momentum / ma200 / atr / volume 等の指標計算方針と定数を定義。DuckDB 経由で prices_daily / raw_financials を参照して計算する設計。

- パッケージエクスポート
  - kabusys.portfolio パッケージで主要関数をまとめて再エクスポート（__all__ を定義）。

### 変更 (Changed)

- 環境変数読み込み挙動
  - プロジェクトルート探索により .env / .env.local を自動読み込み（OS 環境変数を保護、.env.local は上書き）。必要に応じて自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD を利用可能。

### 修正 (Fixed)

- ログ周り
  - ログディレクトリ作成失敗時はファイルハンドラをスキップし、コンソール出力のみで継続するように堅牢化。

### 破壊的変更 (Breaking Changes)

- Settings のプロパティが不正値を検出した場合に ValueError を投げる（例: KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE）。環境変数の値が仕様外の場合は起動時に例外となるため、既存のデプロイ環境では .env の見直しが必要です。
- .env 自動読み込みの影響で、プロジェクトルートに存在する .env/.env.local の値がプロセス開始時に反映されます。以前に別の手段で環境変数を管理していた場合は挙動の差異に注意してください。自動読み込みを無効にするには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。

開発・運用上の注意
-----------------

- paper_trading モードでは実際の発注を行わない MockBrokerClient を使用する想定。paper_trading 用 DB は本番 DB と分離されています（PAPER_TRADING_SQLITE_PATH）。
- run_execution/run_monitoring は外部の「停止フラグファイル」や「PID ファイル」を使ってプロセス管理を行います。運用スクリプト/コンテナ運用時は data/ ディレクトリ周りのボリュームや権限に注意してください。
- process priority / CPU affinity の設定はプラットフォーム依存で権限が必要になる場合があります。アクセスが拒否されると警告を出してスキップします。
- Paper Trading 検証ツールは統計的な判定基準を内蔵していますが、必要に応じて閾値や判定ロジックをカスタマイズしてください。

参考
----

- 主要ファイル一覧（抜粋）
  - src/kabusys/__init__.py
  - src/kabusys/config.py
  - src/kabusys/config_setup.py
  - src/kabusys/validate_config.py
  - src/kabusys/run_execution.py
  - src/kabusys/run_monitoring.py
  - src/kabusys/utils/logging_setup.py
  - src/kabusys/utils/process_priority.py
  - src/kabusys/portfolio/*.py
  - src/kabusys/tools/paper_verification_report.py
  - src/kabusys/research/factor_research.py

（この CHANGELOG はコードベースから推測して作成しています。実際の変更履歴やリリースノートは開発履歴・コミットログに基づいて適宜補完してください。）