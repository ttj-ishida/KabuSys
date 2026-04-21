# Changelog

すべての注目すべき変更はここに記録します。  
フォーマットは「Keep a Changelog」準拠です。

現在のバージョン: 0.1.0

## [Unreleased]
（なし）

## [0.1.0] - 2026-04-21
初期リリース。KabuSys のコアユーティリティ、実行/監視スクリプト、ポートフォリオ構築ロジック、設定関連ツール、およびいくつかの補助ツールを実装しました。

### 追加 (Added)
- パッケージ初期構成
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"` を導入。
- 実行・監視起動スクリプト
  - `run_execution.py`
    - ExecutionEngine を起動するエントリポイント。
    - `BrokerClientFactory` を通じてブローカクライアントを生成（`KABUSYS_ENV=paper_trading` 時はペーパートレード用の MockBroker を利用する想定）。
    - Paper Trading 環境では本番 DB と分離した `data/paper_trading.db` を使用可能。
    - 停止フラグ（data/stop_requested.flag）と PID ファイル（data/execution.pid）を用いた起動/停止制御をサポート。
  - `run_monitoring.py`
    - SystemMonitor のポーリングループを起動するエントリポイント。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。
    - Monitoring は実行環境に関わらず本番用 `sqlite_path` を使用する設計。
- 設定管理・補助ツール
  - `config.py`
    - .env の自動読み込み（プロジェクトルート自動検出: `.git` または `pyproject.toml` を起点）。
    - 環境変数のパース（クォート・エスケープ・コメント処理を考慮した堅牢な実装）。
    - 各種設定プロパティ（DBパス, PID/kill フラグパス, paper trading 関連, CPU/メモリ/ディスク閾値 等）を提供。
    - `paper_fill_mode` のバリデーション（有効値: instant/partial/never/reject）。
  - `config_setup.py`
    - 対話式ウィザードで `.env` を初期作成・更新する CLI ツール。
    - デフォルト値・シークレットマスク・選択肢サポートを実装。
  - `validate_config.py`
    - 起動前に .env と config/*.yaml の検証を行う CLI。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性確認、DB パスの親ディレクトリ確認、YAML パース（PyYAML がない場合は警告）等を実装。
    - `--strict` オプションで警告も失敗扱いにできる。
- ロギング・プロセス制御ユーティリティ
  - `utils/logging_setup.py`
    - ルートロガーに対して stdout 出力の StreamHandler と日次ローテーションのファイルハンドラ (TimedRotatingFileHandler) を設定。
    - ログレベル・ログディレクトリの解決順序を定義し、ディレクトリ作成失敗時はファイル出力をスキップして安全にフォールバック。
  - `utils/process_priority.py`
    - Windows / POSIX を吸収したプロセス優先度（nice / HIGH_PRIORITY_CLASS 等）設定を実装。
    - CPU affinity を設定する `set_cpu_affinity` を提供。
    - 権限不足や未対応 OS に対する安全なフォールバックを実装。
- ポートフォリオ構築ライブラリ（純粋関数群）
  - `portfolio/portfolio_builder.py`
    - 候補選定 (`select_candidates`)、等分配 (`calc_equal_weights`)、スコア加重 (`calc_score_weights`) を実装。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限適用 (`apply_sector_cap`)。
    - 市場レジームに基づく乗数 (`calc_regime_multiplier`)（"bull"/"neutral"/"bear" を定義し未知レジームはフォールバック）。
  - `portfolio/position_sizing.py`
    - 株数決定ロジック (`calc_position_sizes`) を実装。リスクベース/等分/スコア方式をサポートし、単元株（lot_size）丸め、aggregate cap スケーリング、cost_buffer を考慮した安全な配分を実装。
  - `portfolio/__init__.py` で公開 API をまとめてエクスポート。
- Paper Trading 検証ツール
  - `tools/paper_verification_report.py`
    - ペーパートレード SQLite ログから稼働率、注文成功率、送信率、API レイテンシなどを集計してレポート出力。
    - P95 計算、閾値 (uptime 99%、fill_rate 90% 等) による PASS/FAIL 判定を実装。
    - CLI オプションで期間指定（--from / --to）と DB パス指定（--db）をサポート。
- 研究用モジュール（開始実装）
  - `research/factor_research.py`
    - Momentum / Value / Volatility / Liquidity 等のファクター計算を目的とした基盤を追加。DuckDB 接続を受け取って prices_daily / raw_financials を参照する設計。
    - モメンタム計算 API (`calc_momentum`) を実装中（ファイル末尾に実装途中の箇所あり）。

### 変更 (Changed)
- DB 分離ポリシー
  - 実行エンジン（Execution）は paper_trading 環境の場合、専用の paper sqlite DB (`PAPER_TRADING_SQLITE_PATH` / default: data/paper_trading.db) を使用するようにした（本番 DB とデータ分離）。
  - 監視（Monitoring）は環境に関わらず本番の `SQLITE_PATH` を使用する設計（運用上の意図に基づく固定）。
- 環境変数の自動ロード
  - プロジェクトルート自動検出により .env / .env.local を安全にロード。OS 環境変数を上書きしない（protected 機構を導入）。

### 修正 (Fixed)
- ロバストネス強化
  - `.env` パーサーでクォート付き値、バックスラッシュエスケープ、インラインコメントの扱いを改善。無効行や export プレフィックス対応。
  - ログディレクトリ作成やファイルハンドラ生成に失敗した場合にコンソール出力へフォールバックしてプロセスが継続するように修正。
  - process_priority / set_cpu_affinity で権限不足や未対応 OS の例外をキャッチして警告ログに落とし、例外伝播を防止。
  - `validate_config` において PyYAML がない場合は YAML 内容検証をスキップして警告を出すようにした（インストール環境に依存しない挙動）。

### 既知の問題 (Known issues)
- research/factor_research.py の一部実装が途中で終了している（ファイル末尾が不完全）。今後のリリースで完了予定。
- 一部 TODO コメントあり（例: position_sizing の銘柄別 lot_size 拡張、risk_adjustment の価格フォールバック等）。将来の改善項目として残す。
- テストコードは含まれていないため、実運用前に十分な統合テストを推奨。

### セキュリティ (Security)
- セキュリティに関する既知の問題は現時点では報告されていません。ただし、`.env` は絶対にリポジトリにコミットしないよう README / ウィザード注釈で明記しています。

---

（補足）リリースノートはソースコードから推測して作成しています。実際のリリース履歴や公開日付、変更範囲が異なる場合は適宜修正してください。