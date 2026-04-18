CHANGELOG
=========

このファイルは "Keep a Changelog" の形式に準拠しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（なし）

[0.1.0] - 2026-04-18
--------------------

Added
- 基本的なパッケージ構成を追加。パッケージのバージョンは `kabusys.__version__ = "0.1.0"`。
- 環境設定まわり
  - .env 自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml で検出）。OS 環境変数を保護する挙動を持つ。
  - .env のパースロジックを実装。シングル/ダブルクォート、バックスラッシュエスケープ、行末コメント、`export KEY=val` 形式をサポート。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - Settings クラスを実装し、各種環境変数（J-Quants / kabu API / LINE / DB パス / 監視閾値 / 実行環境等）をプロパティ経由で安全に取得できるようにした。`PAPER_FILL_MODE` のバリデーション（"instant"|"partial"|"never"|"reject"）を含む。
- 設定関連 CLI
  - 対話式ウィザード `kabusys.config_setup` を実装。`.env` の初期作成・更新を支援（シークレット表示のマスク、選択肢、デフォルトの適用、ファイル書き込み）。
  - 設定検証 CLI `kabusys.validate_config` を実装。必須環境変数のチェック、KABUSYS_ENV / LOG_LEVEL の検証、DB パスの親ディレクトリ確認、`config/*.yaml` の存在チェック・（PyYAML インストール時は）パース検証を行う。`--strict` オプションで警告をエラー扱いにできる。
- 実行コンポーネント
  - 実行エンジン起動スクリプト `run_execution.py` を追加。
    - 起動時にプロセス優先度を "high" に設定。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用の SQLite DB（デフォルト: `data/paper_trading.db`）を使用して本番 DB と分離。
    - BrokerClientFactory によるブローカークライアントの生成、OrderRepository / OrderManager / RiskManager / Reconciler を組み立て ExecutionEngine を起動する流れを実装。Engine は別スレッドで実行され、 stop flag 検知で安全に停止する。
    - RiskManager のデフォルト設定を導入（max_position_pct, max_utilization, rate_limit_per_sec, circuit breaker 閾値, max_drawdown など）。初期 portfolio value を broker.get_available_cash() から取得して設定。
  - 監視ループ起動スクリプト `run_monitoring.py` を追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔上書き可能（デフォルト 60 秒）。不正値はデフォルトにフォールバックして警告。
    - 停止フラグファイル検知でループ終了。監視は KABUSYS_ENV にかかわらず本番の sqlite_path を使用する（監視用テーブルの初期化処理を呼ぶ）。
- ロギング／プロセス管理ユーティリティ
  - `kabusys.utils.logging_setup.setup_logging` を実装。ルートロガーに stdout ストリームハンドラと日次ローテートファイルハンドラ（`<log_dir>/<app_name>.log`、デフォルト `logs/`、30 日保持）を追加。既存ハンドラは一旦クリアしてから再設定する。ログ出力は stdout に統一（cron 等でのリダイレクトに配慮）。
  - `kabusys.utils.process_priority` を実装。Windows / POSIX の差を吸収してプロセス優先度（high/normal/low）を設定する。`set_cpu_affinity` でプロセスを最初の N コアに固定する機能も提供。権限不足等で失敗した場合は警告を出してスキップ。
- Portfolio 構築ユーティリティ（純粋関数群）
  - `kabusys.portfolio.portfolio_builder`:
    - select_candidates: シグナルのスコアで上位 N を選択。タイブレークは signal_rank で解決。
    - calc_equal_weights, calc_score_weights: 等分配／スコア正規化配分。全スコアが 0 の場合は等分配にフォールバック（警告）。
  - `kabusys.portfolio.risk_adjustment`:
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合、同セクターの新規候補を除外（"unknown" セクターは無視）。
    - calc_regime_multiplier: market regime に応じた投下資金乗数（bull/neutral/bear）を返す。未知のレジームは 1.0 でフォールバック（警告）。
  - `kabusys.portfolio.position_sizing`:
    - calc_position_sizes: risk_based / equal / score の allocation_method に対応した発注株数計算を実装。lot_size（単元）丸め、per-position cap、aggregate cap（available_cash に基づくスケーリング）、cost_buffer（手数料・スリッページの保守的見積り）を含む。スケーリング時は端数処理（lot 単位の余り）に基づいて追加配分する安定なアルゴリズムを実装。
- ツール
  - `kabusys.tools.paper_verification_report` を追加。Paper Trading の検証レポート生成:
    - CLI オプション `--from` / `--to` / `--db` をサポート。
    - 稼働率、注文成功率(Fill)、送信率(Sent)、リスク却下数、API レイテンシ（平均・最大・P95）を算出して判定（PASS/FAIL）を出力。閾値はソース内定義（稼働率 99%、Fill 90%、Send 95%、P95 レイテンシ 200ms）。
    - DB が存在しない／テーブル欠損時に適切に N/A を扱う。
- 研究／ファクター計算（骨組み）
  - `kabusys.research.factor_research` を追加（モメンタム等ファクター算出のための関数骨子）。DuckDB の `prices_daily` / `raw_financials` を想定した実装方針と定数群を定義（1M/3M/6M リターン、MA200、ATR 等）。（ファイル途中まで実装）

Changed
- 監視プロセスの挙動設計:
  - run_monitoring は常に Settings.sqlite_path（本番用）を監視 DB として使用する決定。開発・paper_trading 環境でも同じ監視 DB を利用する設計。

Fixed
- （初回リリース）多数のユーティリティ関数で境界ケースに対する保護ロジックを追加:
  - .env の読み込みでファイル読取失敗時に警告を出す（例外をそのまま上げない）。
  - ログディレクトリ作成失敗時にファイルハンドラの追加をスキップして stdout 出力のみで継続。
  - process_priority / cpu_affinity が権限不足やプラットフォーム非対応で失敗した場合はログに警告し処理を継続。
  - 各種計算関数で入力データ不足や 0 除算の可能性を適切に扱う（None / N/A を返す等）。

Notes / 行動指針
- .env は絶対にリポジトリにコミットしないこと（config_setup がコメントで注意を出力）。
- 本番環境（KABUSYS_ENV=live）では LINE トークン等アラート設定を必ず確認すること。validate_config の live ガードが一部チェック・警告を行う。
- Paper Trading と本番 DB は分離する設計（Execution は paper_trading 時に専用 DB を使用）。ただし監視は本番 monitoring.db を参照する点に注意。

Acknowledgements
- 初期版の設計は将来的な拡張（銘柄ごとの lot_size、価格フォールバック、より高度なレジーム処理、DuckDB ベースのファクター計算の拡張等）を見据えたモジュール分割・API 仕様になっています。

---- 

（補足）この CHANGELOG は提供されたコードベースの内容から推測して作成しています。追加の変更履歴や既知の issue があれば追記してください。