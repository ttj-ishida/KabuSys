CHANGELOG
=========

すべての変更は「Keep a Changelog」準拠の形式で記載しています。

[0.1.0] - 2026-04-18
-------------------

Added
- 基本バージョン 0.1.0 を追加（初回公開相当）。
- 実行用スクリプトを追加
  - run_execution.py
    - ExecutionEngine を起動するエントリポイント。
    - KABUSYS_ENV=paper_trading の場合は MockBrokerClient を使用し、data/paper_trading.db（デフォルト）を使用して本番 DB と完全に分離。
    - 起動時にプロセス優先度を "high" に設定。
    - 停止フラグ (data/stop_requested.flag) を監視し、検知時に安全に停止。
    - PID ファイル (data/execution.pid) の取り扱いあり。
  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプト。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトへフォールバックして警告出力。
    - 停止フラグ (data/stop_requested.flag) を検知してループを終了。
    - 監視は環境にかかわらず本番用 sqlite_path を使用して監視データを記録。
    - 起動時にプロセス優先度を "high" に設定。
- 設定管理
  - config.py
    - .env 自動読み込み機能を実装（プロジェクトルートを .git または pyproject.toml から検出）。
    - .env / .env.local の読み込み順序と上書きルールを明示化（OS 環境変数は保護）。
    - クォート付き値や export KEY=val 形式、インラインコメントの取り扱いに対応する柔軟なパーサを実装。
    - Settings クラスを提供し、環境変数の取得とバリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）を集中管理。
    - paper_trading 用 DB パス (PAPER_TRADING_SQLITE_PATH) や各種監視閾値、PID / Kill flag パスを Settings から取得可能に。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
- 設定関連 CLI
  - config_setup.py
    - 対話式ウィザードで .env を生成／更新するツールを追加。
    - J-Quants / kabu API トークン、DB パス、ログレベル、Kill Switch 動作等の主要項目を対話で設定可能。
    - 既存 .env の読み込み・表示、秘密情報のマスク表示、保存確認機能を備える。
  - validate_config.py
    - 起動前の設定検証 CLI を追加（必須環境変数、KABUSYS_ENV/LOG_LEVEL 値、DB パス、config/*.yaml の存在・パース等をチェック）。
    - --strict オプションで警告も失敗扱いにできる。
    - PyYAML 未インストール時は YAML 検証をスキップして警告を出す。
    - 本番 (KABUSYS_ENV=live) 向けの追加ガード（LINE 通知設定未設定や KILL_FLAG_CLEAR_ON_START の危険設定に対する警告）を実装。
- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア加重配分（calc_score_weights）を追加。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックして警告を出す。
  - portfolio/risk_adjustment.py
    - セクター集中上限を適用する apply_sector_cap を追加（売却予定銘柄を除外可能、"unknown" セクターは上限適用除外）。
    - 市場レジームに応じた投下資金乗数 calc_regime_multiplier を追加（bull/neutral/bear のマッピング、未知レジームは警告の上で 1.0 にフォールバック）。
  - portfolio/position_sizing.py
    - position sizing ロジックを追加（allocation_method: "risk_based"|"equal"|"score"）。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap（available_cash によるスケーリング）、cost_buffer（手数料/スリッページ見積り）の考慮。
    - aggregate cap 適用時に端数処理と残余配分ロジックを実装し、lot_size 単位での再配分を行う。
- 研究用ファクター計算
  - research/factor_research.py
    - DuckDB を用いたファクター計算モジュールを追加（prices_daily / raw_financials を参照）。
    - Momentum, Volatility, Liquidity, Value 系の指標を計算する関数を実装（例: calc_momentum, calc_volatility）。
    - 大域定数（窓幅やスキャン期間）を設定して計算精度を担保。
- ユーティリティ
  - utils/process_priority.py
    - クロスプラットフォームなプロセス優先度設定 set_process_priority を実装（Windows と POSIX を抽象化）。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を実装。
    - 権限不足や未対応 OS の際は警告を出し安全にスキップ。
- 監視／検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポートを生成する CLI を追加。
    - system_status / trade_logs / risk_logs などから稼働率、注文成功率、送信率、API レイテンシ（平均／最大／P95）を算出して Pass/Fail 判定を行う。
    - P95 の計算、日付フィルタ、DB パス指定（--db / 環境変数 PAPER_TRADING_SQLITE_PATH）に対応。
    - デフォルトの閾値を定義（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200 ms）。

Changed
- パッケージ情報
  - __init__.py にてバージョンを "0.1.0" に設定。
- DB 初期化
  - run_execution.py / run_monitoring.py で起動時に init_monitoring_db(sqlite_conn) を呼び、監視用テーブルが存在することを保証（冪等操作）。
- .env 自動ロードの動作
  - .env をプロジェクトルート基準で自動読み込みする実装に変更（.env.local は .env を上書きする挙動）。
  - OS 環境変数は既定で保護され、.env の値で上書きされない。

Fixed
- 環境変数パースの堅牢化
  - export キーワード、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いを正しく処理するよう修正。これにより .env 中の複雑な値（URL やトークンに含まれる特殊文字等）が安全に読み込まれるようになった。

Documentation / Notes
- run_monitoring と run_execution は起動直後にプロセス優先度を "high" に設定するため、実行環境の権限により設定が失敗する場合は警告が出力される。権限不足でも処理は継続するよう安全に設計。
- Settings.paper_fill_mode は "instant" | "partial" | "never" | "reject" のいずれかのみ許容し、不正値は ValueError を送出する。
- config/*.yaml の存在チェックおよびパース検証は PyYAML に依存。インストールされていない場合は警告が出るが処理は続行される。
- run_execution は停止フラグ検知時に ExecutionEngine.stop() を呼んで安全終了を試み、スレッド終了待機を行う。
- Paper Trading 用 DB と監視用 DB を分離することで、ペーパートレード実行が本番データに影響を与えない設計。

Security
- .env は生成時に Git にコミットしない旨の注意を .env テンプレートに含めた。

その他
- ロギングやデバッグメッセージを適所に追加して運用時のトラブルシューティング性を向上。

今後の予定（候補）
- stocks マスタに lot_size を持たせ、銘柄別単元対応へ拡張。
- position_sizing の価格フォールバックロジック（欠損価格時の扱い）改善。
- DuckDB を用いたファクター計算の追加カバレッジ（Value / Liquidity の実装拡張）。
- SystemMonitor / ExecutionEngine のユニットテスト追加と CI 統合。

---

この CHANGELOG はコードベースから差分と挙動を推測して作成しています。詳細な変更履歴（コミットログ等）が存在する場合はそちらを優先して更新してください。