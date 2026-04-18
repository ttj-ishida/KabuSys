# Changelog

すべての重要な変更は Keep a Changelog に従って記載しています。  
このファイルはコードベースから推測して作成したリリースノートです。

リンク: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
- （なし）

## [0.1.0] - 2026-04-18
初回リリース。日本株自動売買システム KabuSys の基本コンポーネントを追加。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを設定: __version__ = "0.1.0"（src/kabusys/__init__.py）。

- 起動スクリプト
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV に応じて Paper Trading 時は MockBrokerClient を利用し、paper_trading 用の SQLite（デフォルト: data/paper_trading.db）で本番 DB と分離して動作する。
    - execution.pid ファイルの管理（PID ファイルパス: data/execution.pid）。
    - デーモンスレッドで ExecutionEngine.run_session を起動し、data/stop_requested.flag を検知して安全に停止する制御を実装。
    - RiskManager のデフォルト設定を埋め込み（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）。
    - DuckDB（分析用）への接続を行う。

  - 監視（SystemMonitor）起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 監視は環境にかかわらず本番 sqlite_path を使用して監視テーブルを初期化。
    - プロセス優先度を最初に "high" に設定、異常発生時は例外をログ出力して次回ポーリングへ継続。
    - 停止フラグ（data/stop_requested.flag）検知でループ終了、リソース（sqlite/duckdb 接続）を確実にクローズ。

- 設定管理
  - .env 自動読み込みと設定 API（src/kabusys/config.py）
    - プロジェクトルート探索は .git または pyproject.toml を基準に行い、CWD に依存しない。
    - .env / .env.local を読み込み（優先順位: OS 環境変数 > .env.local > .env）。自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env パーサーは export 文、クォート（'"/）とバックスラッシュエスケープ、行内コメント扱いをサポートする堅牢な実装。
    - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB / 監視閾値 / システム設定等のプロパティを型付きで取得可能。
    - PAPER_FILL_MODE のバリデーション、KABUSYS_ENV / LOG_LEVEL の許容値チェック、便利な bool フラグ（is_live/is_paper/is_dev）を実装。

  - 設定ウィザード CLI を追加（src/kabusys/config_setup.py）
    - 対話式で .env を初期作成・更新するウィザード。
    - 秘匿項目のマスク表示、選択肢/デフォルト値、既存 .env の読み込みによる Enter 押下での再利用をサポート。
    - 書き込みテンプレート（.env の雛形）を生成し、.env を誤ってコミットしない旨の注意コメントを含めて保存。

  - 設定検証 CLI を追加（src/kabusys/validate_config.py）
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、DB パスの親ディレクトリ存在チェック、config/*.yaml の存在・パース検証（PyYAML がインストールされている場合）。
    - KABUSYS_ENV=live の場合の追加ガード（LINE 通知設定や KILL_FLAG_CLEAR_ON_START の警告）。
    - --strict モードで警告を FAIL 扱いにできる。

- ロギング / プロセス管理ユーティリティ
  - 統一ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）
    - コンソール出力（stdout）と日次ローテーション（TimedRotatingFileHandler）をルートロガーへ設定。
    - ログディレクトリ自動作成、ファイルハンドラの失敗時はコンソールのみで継続。既存ハンドラの二重登録を防止。
    - デフォルト保管日数: 30 日。
  - プロセス優先度・CPU アフィニティ設定ユーティリティを追加（src/kabusys/utils/process_priority.py）
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収し、psutil を用いて nice 値や優先度を設定。失敗時は警告ログでスキップ。
    - set_cpu_affinity により最初の N コアへプロセスをピン留め可能。

- ポートフォリオ構築関連（純粋関数群、DB 参照なし）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates、calc_equal_weights、calc_score_weights を実装。スコアが全て 0 の場合は等金額配分へフォールバック。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap: 既存ポジションのセクター暴露に基づき新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: regime ('bull'/'neutral'/'bear') に応じた乗数（1.0/0.7/0.3）を返却。未知レジームは警告して 1.0 をフォールバック。
  - 株数決定・リスク制限（src/kabusys/portfolio/position_sizing.py）
    - calc_position_sizes を実装。allocation_method に "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、per-stock 上限・aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリングと残余配分ロジックを実装。

- 解析 / レポート
  - Paper Trading 検証レポートツールを追加（src/kabusys/tools/paper_verification_report.py）
    - SQLite（paper_trading DB）からシステム稼働率、注文成功率、送信率、リスク却下数、API レイテンシ（平均/最大/P95）を算出してテキストレポートを出力。
    - デフォルトの閾値: 稼働率 >= 99%、注文成立率 >= 90%、送信率 >= 95%、P95 レイテンシ <= 200 ms。
    - コマンドライン引数 --from/--to/--db をサポート。P95 は単純パーセンタイル実装。

- 解析モジュール（研究用）
  - factor_research（src/kabusys/research/factor_research.py）を追加（Momentum / Value / Volatility / Liquidity の設計を含む）。
    - DuckDB 接続を受け取り prices_daily / raw_financials を参照してファクターを計算する設計。モメンタム計算の枠組みを含む（実装途中でファイル末尾が切れているため一部未完）。

- DB 初期化ユーティリティとの連携
  - init_monitoring_db を各起動スクリプトで呼び出し、監視テーブルの存在を保証する（冪等）。

### 変更 (Changed)
- （初回リリースにつき該当なし）

### 修正 (Fixed)
- （初回リリースにつき該当なし）

### 注意事項 / 既知の問題 (Notes / Known issues)
- research/factor_research.py はファイル末尾が途中で切れているように見え、モメンタム計算の実装が未完または一部欠落しています。利用時は実装の完了が必要です。
- position_sizing の注釈にある通り将来的に lot_size を銘柄別に扱う拡張が想定されており、現状は全銘柄共通の単元サイズ（デフォルト 100）を想定しています。
- apply_sector_cap の exposure 計算は price_map が欠損（0.0）の場合に過少評価される旨の TODO が残っています。

### セキュリティ (Security)
- （初回リリースにつき該当なし）

---

今後のリリースでは、Research モジュールの完成、ExecutionEngine 周りの詳細実装（再試行/部分約定の扱い等）、単体テスト／CI の追加を予定してください。