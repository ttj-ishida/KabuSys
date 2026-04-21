# CHANGELOG

すべての重要な変更はこのファイルに記載します。フォーマットは「Keep a Changelog」に準拠しています。

なお本 CHANGELOG はコードベース（src/ 以下）から実装内容を推測して作成したものであり、実際のコミット履歴とは差異がある場合があります。

## [Unreleased]

- ドキュメント化・補足
  - 内部で検出された未実装箇所や注意点（例: price フォールバック、将来的な lot_size マスタ対応等）を CHANGELOG に追記。

## [0.1.0] - 2026-04-21

Added
- 基本機能
  - KabuSys の初期バージョンを追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 起動スクリプト
  - run_execution.py
    - ExecutionEngine 起動スクリプトを追加。起動時にプロセス優先度を上げる処理を行い、BrokerClientFactory を使ってブローカークライアントを生成する。
    - 環境変数 `KABUSYS_ENV=paper_trading` の場合、Paper Trading 用の専用 SQLite（デフォルト `data/paper_trading.db`）を使用して本番 DB と完全に分離する動作をサポート。
    - エンジンはデーモンスレッドで実行され、プロジェクトルートの `data/stop_requested.flag` を監視して安全に停止可能。
    - 起動時に pid ファイル（デフォルト `data/execution.pid`）を書き込む仕組みを用意。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - ポーリング間隔は環境変数 `MONITOR_POLL_INTERVAL` で上書き可能（デフォルト 60 秒）。不正な値は警告を出しデフォルトにフォールバック。
    - 監視では環境にかかわらず本番の sqlite_path（`Settings().sqlite_path`）を使用し、DuckDB も接続する。
    - 停止フラグ（`data/stop_requested.flag`）を検知してループを終了する。

- 設定管理
  - config.py
    - .env ファイル自動ロード機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を探索）。OS 環境変数を保護して `.env.local` を上書きする挙動をサポート。
    - `.env` パース時にシングル/ダブルクォートやバックスラッシュエスケープ、`export KEY=val` 形式、インラインコメントの扱いなど堅牢に対応。
    - 必須環境変数取得用の `_require()`、`Settings` クラスによるプロパティベースの設定読み出し（J-Quants、kabu、LINE、DB パス、監視閾値、環境判定等）を実装。
    - `KABUSYS_DISABLE_AUTO_ENV_LOAD` による自動ロード無効化を提供。

  - config_setup.py
    - 対話式設定ウィザードを実装。`.env` の初期作成・更新を支援。シークレット項目のマスク表示、選択肢、既存値の利用、保存確認をサポート。

  - validate_config.py
    - 設定検証 CLI を追加。必須環境変数や `KABUSYS_ENV`、ログレベル、DB パス、`config/*.yaml` の存在や YAML パース（PyYAML インストール時）を検査。
    - `--strict` オプションで警告を FAIL 扱いにできる。

- ロギング・プロセス管理ユーティリティ
  - utils/logging_setup.py
    - ルートロガーに StreamHandler（stdout）と TimedRotatingFileHandler（日次、30日保管）を設定する共通ユーティリティを実装。
    - ログレベル／ログディレクトリの解決順序（関数引数 > 環境変数 > デフォルト）を実装。ログディレクトリ作成失敗時はファイル出力をスキップしてコンソール出力のみで継続。

  - utils/process_priority.py
    - psutil を用いたクロスプラットフォームのプロセス優先度設定機能を追加（"high" / "normal" / "low"）。Windows と POSIX 系で適切に nice/priority を設定する。
    - CPU affinity を特定コア数に固定する `set_cpu_affinity` を追加。
    - 権限不足や未サポート環境では警告を出して安全にスキップする。

- ポートフォリオ構築ライブラリ（純粋関数群）
  - portfolio/portfolio_builder.py
    - シグナルをソートして候補選定する `select_candidates` を追加。
    - 等金額配分 `calc_equal_weights`、スコア加重配分 `calc_score_weights` を追加。全スコアが 0 の場合は等金額へフォールバック（警告あり）。

  - portfolio/risk_adjustment.py
    - セクター集中制限を適用する `apply_sector_cap` を追加（売却予定銘柄の除外対応、"unknown" セクターは制限対象外）。
    - 市場レジームに基づく投下資金乗数 `calc_regime_multiplier` を追加（'bull'/'neutral'/'bear' のマップ、未知の値は 1.0 でフォールバックして警告）。

  - portfolio/position_sizing.py
    - 発注株数算出アルゴリズム `calc_position_sizes` を追加。
    - `risk_based`, `equal`, `score` の配分方式をサポート。単元株（lot_size）で丸め、ポジション上限・最大利用率・コストバッファを考慮した aggregate cap スケーリングを実装。
    - スケーリング時に残差を lot 単位で配分するロジックを採用。

  - portfolio/__init__.py にて上記関数を公開。

- 研究・リサーチ
  - research/factor_research.py（実装開始）
    - モメンタム等のファクター計算モジュールの骨組みを追加。DuckDB 接続を受け取り `prices_daily` 等のテーブルを参照して計算する設計。
    - モメンタム（1M/3M/6M、200日移動平均乖離）や ATR/出来高等の定義と定数を導入。
    - （注）ファイル末尾で実装が途中で終わっている箇所あり（今後の実装予定）。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。SQLite（デフォルト `data/paper_trading.db`）からデータを集計してシステム稼働率、注文成功率、送信率、レイテンシ（平均・最大・P95）等を算出し Pass/Fail 判定を出力。
    - 日付フィルタ（--from / --to）、DB パス指定（--db または環境変数 `PAPER_TRADING_SQLITE_PATH`）をサポート。
    - P95 計算、SQL クエリの堅牢化（テーブルが存在しない場合は安全に N/A 扱い）を実装。
    - 検証基準（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）をコード内に定義。

Changed
- なし（初回リリース相当の追加実装が中心）。

Fixed
- なし（現状のコードからは明示的なバグ修正履歴は推測できません）。

Security
- 環境変数の取り扱いに際してシークレット項目はウィザード表示時にマスクするよう配慮。

Notes / Known limitations / TODO
- apply_sector_cap 内で価格が欠損（0.0）の場合にエクスポージャーが過少評価される可能性があり、将来的に前日終値や取得原価をフォールバックとして使うことが検討されている（コード内に TODO コメントあり）。
- position_sizing は現状単元株数が全銘柄共通である前提（lot_size）。将来的に銘柄別 lot_map を導入する予定（TODO コメントあり）。
- research/factor_research.py は途中まで実装されており、完全なファクター計算は今後の実装が必要。
- validate_config は PyYAML が未インストールの場合に YAML 検証をスキップする（警告）仕様。
- process_priority / set_cpu_affinity は権限やプラットフォーム制約により実行できない場合があるため、失敗時は警告を出してスキップする。

Compatibility
- 本バージョンでは主に内部ライブラリと CLI を提供。外部依存として psutil, duckdb, sqlite3, PyYAML（任意）が想定される。Paper Trading と本番 DB は分離される設計のため、環境設定で切り替え可能。

----

（補足）この CHANGELOG はコードの静的解析とコメント・ドキュメント、関数実装から推測して作成しています。実際のリリースノートとして利用する場合はコミット履歴やリリース差分に基づいた検証を行ってください。