# CHANGELOG

すべての注目すべき変更点を記録します。  
フォーマットは「Keep a Changelog」準拠です。

## [0.1.0] - 2026-04-19

初回公開リリース。主要な機能群・ユーティリティ・CLI をまとめて追加しました。

### 追加 (Added)
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として設定。
- 起動スクリプト
  - run_monitoring: SystemMonitor のポーリングループを起動するスクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する挙動。
    - 停止フラグ(`data/stop_requested.flag`)を検出して安全にループを終了する。
  - run_execution: ExecutionEngine を起動するスクリプトを追加。  
    - `KABUSYS_ENV=paper_trading` のときは MockBroker を使用し、paper_trading 用 DB（`data/paper_trading.db`）を使用して本番 DB と分離。
    - デーモンスレッドでエンジンを起動し、停止フラグ検知で安全に停止する。
- 環境設定・検証ツール
  - config_setup: 対話式ウィザードで `.env` を作成・更新する CLI を追加。
  - validate_config: `.env` と `config/*.yaml` の事前検証 CLI を追加（`--strict` オプションあり）。
  - 設定読み込み機構 (`kabusys.config`) を実装。
    - プロジェクトルート自動検出（.git / pyproject.toml 基準）と `.env` / `.env.local` の自動読み込み。自動ロードを無効化する `KABUSYS_DISABLE_AUTO_ENV_LOAD` をサポート。
    - 複雑な .env パースをサポート（export プレフィックス、シングル/ダブルクォート、エスケープ、インラインコメント処理など）。
    - 各種設定プロパティ（DB パス、PAPER_FILL_MODE、各種しきい値やフラグ）を提供する Settings クラスを実装。
- ロギング・プロセスユーティリティ
  - logging_setup: StreamHandler（stdout） と TimedRotatingFileHandler（日次ローテーション）を統一的に設定するユーティリティを追加。ログディレクトリの自動作成、既存ハンドラのクリア、環境変数によるログレベル/ログディレクトリ制御をサポート。
  - process_priority: Windows / POSIX を吸収するプロセス優先度設定ユーティリティを追加（`set_process_priority`, `set_cpu_affinity`）。
- ポートフォリオ構築ライブラリ（純粋関数）
  - portfolio_builder: シグナル選定・等重/スコア重み計算（select_candidates, calc_equal_weights, calc_score_weights）。
    - calc_score_weights は全スコアが 0 の場合に等金額配分へフォールバックし警告を出力。
  - risk_adjustment: セクター集中制限（apply_sector_cap）と市場レジームに応じた乗数（calc_regime_multiplier）を実装。
  - position_sizing: 各銘柄の発注株数計算（risk_based / equal / score の各方式）を実装。単元株丸め、per-position 上限・aggregate cap のスケーリング、コストバッファの考慮、残余キャッシュによる端数配分ロジックを含む。
  - portfolio パッケージのエクスポートを整備。
- Paper Trading 検証ツール
  - tools/paper_verification_report: Paper Trading の SQLite DB を解析して検証レポートを生成する CLI を追加。  
    - 稼働率、注文成功率（fill rate）、送信率（send rate）、レイテンシ（平均 / 最大 / P95）などを出力。
    - PASS/FAIL 判定基準を定義（例: 稼働率 >= 99%、P95 <= 200 ms など）。
    - 日付範囲フィルタ（--from / --to）と DB パス上書き（--db）をサポート。
- リサーチ（ファクター計算）基盤
  - research/factor_research: ファクター計算（Momentum / Value / Volatility / Liquidity）の骨格を追加。DuckDB 接続を受け取り DB 上の prices_daily / raw_financials を参照する設計方針で実装。
    - Momentum 計算関数の実装開始（営業日ベースの窓幅定義など）。※コードベースの一部が継続実装前提の状態。

### 変更 (Changed)
- DB の扱い
  - 監視用スクリプトは環境にかかわらず監視用の sqlite_path を使用する明示的な設計に。
  - run_execution は paper_trading 環境のとき専用の paper_sqlite_path を使用して本番 DB と分離。
- ロギング
  - ファイルハンドラ作成に失敗した場合はコンソールのみで継続するフェイルセーフを実装。
  - StreamHandler は stdout を利用（stderr ではなく）して cron 等からのリダイレクト運用を想定。
- 環境変数取り扱い
  - .env パースロジックを強化（引用符・エスケープ・コメント処理）し、より現実の .env フォーマットに対応。
  - .env 読み込みの優先順位は OS 環境 > .env.local > .env（`.env.local` は OS 環境を上書きできるが、既存 OS 環境は保護される）。
- process_priority
  - プラットフォーム差を吸収する実装により、Windows / POSIX (Linux/Mac/FreeBSD) で適切な優先度や nice 値を設定可能。失敗時はログ警告でスキップ。
- validate_config
  - YAML パーサが存在しない場合は YAML 検証をスキップして警告を出す（PyYAML optional）。
  - `--strict` オプションで警告もエラー扱いにできる機能を追加。

### 修正 (Fixed)
- 環境変数の数値変換で無効値がセットされた場合にフォールバックする処理を追加（例: MONITOR_POLL_INTERVAL が不正な値のときデフォルト 60 秒にフォールバック）。
- calc_score_weights: 全スコアが 0.0 の場合は等金額配分にフォールバックして警告を出力するようにして、0 除算や不正な重み生成を回避。
- position_sizing: aggregate cap のスケーリングと lot_size による丸め処理で、残余キャッシュを用いた端数配分を導入。これにより資金超過時の再配分が安定化。
- logging_setup: ログディレクトリ作成失敗時にファイルハンドラ作成処理が壊れる問題を回避し、コンソール出力のみで継続するように改善。
- process_priority / set_cpu_affinity: 権限不足や未サポート環境での例外をキャッチして、実行停止にならないように修正（警告ログで継続）。

### ドキュメント (Documentation)
- 各モジュール・関数に日本語ドキュメンテーション文字列を追加。使用例や設計方針、注記（TODO、重要点）を明記。
- config_setup のウィザードでの表示文言と .env 書式テンプレートを整備。

### 既知の問題 (Known issues)
- research/factor_research の一部関数は継続実装が想定される（ソースの終端が未完の状態を含む場合があるため、完全なファクター計算の使用前には追加実装が必要）。
- 一部の機能は外部ライブラリ（psutil, duckdb, PyYAML など）に依存。これらが存在しない環境では機能限定または警告でスキップされる設計。

---

その他の小さな改善点や内部調整はソース内の docstring / コメントに記載しています。リリース後はユニットテスト・統合テストを通じて実運用環境での動作確認を推奨します。