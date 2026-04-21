# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
通常の運用では、各リリースごとにセクションを追加してください。

全般的な前提:
- 本ドキュメントはソースコードから推測して作成しています。実際の変更履歴と差異がある場合があります。

## [0.1.0] - 2026-04-21

### 追加 (Added)
- 全体
  - KabuSys の初期リリース相当のコア機能を追加。
  - パッケージバージョンを `__version__ = "0.1.0"` として定義（src/kabusys/__init__.py）。

- 起動スクリプト / 実行
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - ExecutionEngine をバックグラウンドスレッドで起動・監視する仕組みを提供。
    - KABUSYS_ENV=paper_trading 時は MockBrokerClient を使用し、paper_trading 用 SQLite（data/paper_trading.db）へ記録して本番 DB と分離。
    - 停止フラグ（data/stop_requested.flag）や PID ファイル（data/execution.pid）を用いた制御をサポート。
  - 監視プロセス起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - SystemMonitor のポーリングループを起動。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書きをサポート（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番用の sqlite_path を使用して監視テーブルを管理。

- 設定管理 / CLI
  - Settings クラスによる環境変数ラッパーを追加（src/kabusys/config.py）。
    - .env 自動ロード機能（プロジェクトルート検出 .git / pyproject.toml を基準）。
    - .env 読み込みの上書き制御（OS 環境変数保護）を実装。
    - 各種設定（DB パス、API トークン、PID / Kill flag パス、閾値など）をプロパティで提供。
    - PAPER_FILL_MODE の検証、KABUSYS_ENV / LOG_LEVEL の検証ロジック内蔵。
  - 設定検証 CLI を追加（src/kabusys/validate_config.py）。
    - 必須環境変数チェック、KABUSYS_ENV 検証、ログレベル、DB パス、config/*.yaml の存在・パース検証（PyYAML が無ければ警告）等を実施。
    - --strict オプションで警告を FAIL 扱いにできる。
  - 対話式 .env ウィザードを追加（src/kabusys/config_setup.py）。
    - .env の初期作成・更新を支援。シークレット入力、既存値の再利用、保存確認機能あり。

- ポートフォリオ構築（純粋関数群）
  - 候補選定・重み計算（src/kabusys/portfolio/portfolio_builder.py）
    - select_candidates（スコア降順、タイブレークロジック）、等金額/スコア加重の重み計算を実装。
  - セクター集中制限・レジーム乗数（src/kabusys/portfolio/risk_adjustment.py）
    - apply_sector_cap（既存保有を考慮したセクター上限フィルタリング）。
    - calc_regime_multiplier（"bull"/"neutral"/"bear" に基づく投下資金乗数。未知レジームはフォールバック）。
  - 株数決定・リスク制限・単元丸め（src/kabusys/portfolio/position_sizing.py）
    - risk_based / equal / score の allocation_method をサポート。
    - 単元（lot_size）丸め、ポジション上限、aggregate cap（available_cash によるスケーリング）、cost_buffer を考慮した保守的計算を実装。
    - 価格欠損時のスキップ処理や各種安全弁（max_per_stock 等）を備える。
  - ポートフォリオ API エクスポート（src/kabusys/portfolio/__init__.py）。

- ユーティリティ
  - ログ設定ユーティリティを追加（src/kabusys/utils/logging_setup.py）。
    - StreamHandler（stdout）と日次ローテートのファイルハンドラ（TimedRotatingFileHandler）をルートロガーに設定。
    - ログディレクトリ自動作成、既存ハンドラの安全なクリーンアップ、環境変数によるログレベル / 出力先の上書きをサポート。
    - stdout を使用することで cron 等からのリダイレクト運用に適合。
  - プロセス優先度 / CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows / POSIX（Linux, macOS, FreeBSD）を吸収して nice / HIGH_PRIORITY_CLASS 相当を設定。
    - アクセス権限不足や未サポート環境では警告を出してスキップ。
    - CPU affinity 設定関数 set_cpu_affinity を提供。

- モニタリング DB 初期化（src/kabusys/monitoring/* への参照が複数ファイルにあり、起動時に init_monitoring_db を呼び出すことで監視テーブルの冪等的作成を保証）。

- ツール
  - Paper Trading 検証レポート生成ツールを追加（src/kabusys/tools/paper_verification_report.py）。
    - ペーパートレード用 SQLite（env / 引数で指定可）からシステム稼働率、注文成功率、送信率、レイテンシ（平均/最大/P95）、リスク却下数等を集計してレポート出力。
    - デフォルト閾値（稼働率 99%、注文成功率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し PASS/FAIL を判定。
    - P95 の計算ロジック、日付フィルタ（ISO8601 UTC 文字列化）をサポート。

- リサーチ（未完／追加）
  - ファクター計算モジュールの雛形を追加（src/kabusys/research/factor_research.py）。モメンタム / ボラティリティ / Value / Liquidity を想定した設計。DuckDB を使った prices_daily 等の参照方針を記載（実装途中のファイルあり）。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- .env パーサーの堅牢化（src/kabusys/config.py）
  - export プレフィックス、クォート（シングル／ダブル）、バックスラッシュエスケープ、インラインコメント、コメント判定ルールなどを細かく実装し、実運用での .env 記述パターンに対応。
  - .env 自動ロードはプロジェクトルートが見つからない場合はスキップされるように安全化。

- Logging / ファイル出力に関する回復性向上（src/kabusys/utils/logging_setup.py）
  - ログディレクトリ作成失敗時はファイルハンドラをスキップしてストリームのみで継続するようにして、起動不能にならない設計に。

- プロセス優先度設定のフォールバックと例外回避（src/kabusys/utils/process_priority.py）
  - 未サポートプラットフォームや権限不足に対して警告を出しつつ安全にスキップするように修正。

### 破壊的変更 (Breaking Changes)
- なし（初回リリース）。ただし以下の点に注意:
  - run_monitoring はどの環境でも監視用 sqlite_path（Settings.sqlite_path）を使用する設計になっているため、development / paper_trading と monitoring DB を分離したい場合は運用側でパスを変更する必要があります。
  - PAPER_TRADING 用 DB は paper_trading 環境時に Execution が専用 DB を使うように分離されている点に注意。

### セキュリティ (Security)
- 機密情報（API トークンやパスワード）は .env に格納する想定。config_setup の出力では .env を Git にコミットしないよう注記あり。  
- ログ設定等で機密を誤って出力しない運用ポリシーは別途運用ドキュメントで管理推奨。

### 既知の制限 / TODO
- ファクター計算モジュール（research/factor_research.py）は実装途中（モメンタム計算の途中で切れている）。完全実装が必要。
- position_sizing の単元情報（lot_size）は現状全銘柄共通の引数で渡す設計。将来的には銘柄別 lot_map への拡張を予定（TODO コメントあり）。
- apply_sector_cap の価格欠損（price == 0.0）時のエクスポージャー過少推定に関する注意（将来的なフォールバック価格導入を検討する旨の TODO コメントあり）。
- run_execution / run_monitoring は停止フラグや PID ファイルに依存するため、運用手順の整備が必要。

---

以上。必要であれば、各ファイルごとの変更点をさらに詳細に分解したバージョン別履歴（将来の Unreleased セクションやパッチリリース向けのエントリ）を作成します。どの程度の粒度で出力するか指示してください。