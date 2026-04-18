# Changelog

すべての変更は [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) に準拠して記載します。  
フォーマット: "変更種別" を見出しにして、影響範囲・説明を日本語で記載しています。

なお、本 CHANGELOG は配布されたソースコードから推測して作成しています（実装コメント・ドキュメンテーションに基づく）。

## [0.1.0] - 2026-04-18

初回公開リリース。

### Added
- 基本アプリケーションメタ
  - パッケージバージョンを `__version__ = "0.1.0"` として設定（src/kabusys/__init__.py）。
  - パッケージ公開用に主要サブパッケージを `__all__` にエクスポート（data, strategy, execution, monitoring）。

- 実行エントリスクリプト
  - run_execution.py
    - ExecutionEngine を起動するためのエントリポイントを追加。
    - KABUSYS_ENV による paper_trading モード対応：paper_trading の場合は専用 SQLite（data/paper_trading.db をデフォルト）を使用して本番 DB と分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、OrderRepository、OrderManager、RiskManager、Reconciler を組み立てて ExecutionEngine を起動。
    - 停止フラグ（data/stop_requested.flag）を監視し、停止時はエンジンに停止要求を送る。
    - PID ファイル (data/execution.pid の既定) をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループを起動するエントリポイントを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によりポーリング間隔を上書き可能（デフォルト 60 秒）。不正な値はデフォルトにフォールバックして警告をログ出力。
    - 監視用の SQLite DB 接続は KABUSYS_ENV に依存せず常に本番 sqlite_path を使用する設計（監視データは本番 DB を対象に確実に記録する意図）。
    - 停止フラグ（data/stop_requested.flag）でループを終了。

- 設定管理
  - config.py
    - 環境変数自動読み込み機能を実装（.env, .env.local）。既存 OS 環境変数を保護しつつ .env.local で上書き可能。
    - プロジェクトルート検出ロジック（.git または pyproject.toml を基準）により CWD に依存しない自動ロード。
    - 複雑な .env 行のパース実装（export プレフィックス、引用符付き値のエスケープ、コメントの扱いなど）。
    - Settings クラスを導入し、環境依存設定値をプロパティ経由で型安全に取得（DuckDB/SQLite パス、paper_trading 用 DB、ログレベル、しきい値等）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化オプションをサポート。
    - 必須環境変数未設定時に ValueError を送出する `_require()` を提供。

  - config_setup.py
    - 対話式ウィザードで .env を生成/更新する CLI を追加。
    - デフォルト値、選択肢、シークレットマスク表示、既存 .env の読み込み、保存確認などのユーザー体験を実装。
    - 出力される .env ファイルは Git にコミットしない旨の警告コメントを含めて生成。

  - validate_config.py
    - 起動前に .env と config/*.yaml の妥当性を検証する CLI を追加。
    - 必須環境変数の存在確認、KABUSYS_ENV と LOG_LEVEL の検証、DB パスの親ディレクトリ存在確認、YAML ファイルの存在と（PyYAML があれば）構文検証を行う。
    - `--strict` オプションで警告も失敗扱いにできる。
    - 本番環境（KABUSYS_ENV=live）向けの追加ガード（LINE 通知設定確認、KILL_FLAG_CLEAR_ON_START の警告）を実装。

- ポートフォリオ構築（純関数群）
  - portfolio/portfolio_builder.py
    - 候補選出 select_candidates（スコア降順、同点は signal_rank でタイブレーク）。
    - 重み計算 calc_equal_weights（等金額）、calc_score_weights（スコア加重、スコア合計が 0 の場合は等金額にフォールバック）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限（max_sector_pct）を超える場合にそのセクターの新規候補を除外するロジックを実装（売却予定銘柄を除外して既存のセクターエクスポージャーを計算）。
    - calc_regime_multiplier: 市場レジーム ("bull"/"neutral"/"bear") に応じた投下資金乗数を提供。未知レジームは 1.0 にフォールバックし警告ログを出力。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に基づき発注株数を計算。
    - 単元株（lot_size）丸め、per-position 上限、aggregate cap によるスケーリング（利用可能現金を超える場合のスケールダウンと残差処理）を含む。
    - cost_buffer を考慮した保守的なコスト見積もりを導入。

- ユーティリティ
  - utils/logging_setup.py
    - ルートロガーを統一的に設定する setup_logging を実装（コンソール stdout 出力 + 日次ローテーションのファイル出力）。
    - ファイル出力はデフォルト logs/ ディレクトリに日次ローテーション（30 日保持）。LOG_DIR 環境変数で上書き可能。
    - 既存ハンドラの重複登録を避けるため、再設定時は一旦ハンドラをクローズして削除。
    - stdout を使用することで cron 等でのリダイレクト運用を考慮。
    - ディレクトリ作成に失敗した場合はファイルハンドラをスキップしてコンソール出力のみにフォールバック。

  - utils/process_priority.py
    - クロスプラットフォームに対応したプロセス優先度設定（set_process_priority）を追加。Windows と POSIX（Linux/Mac/FreeBSD）の差分を吸収。
    - CPU affinity 設定（set_cpu_affinity）を追加（指定したコア数にプロセスを固定）。
    - 権限不足等で操作できない場合は警告ログを出力して安全にスキップ。

- モニタリング DB 初期化 API
  - monitoring/monitoring_db.py（呼び出し箇所あり）
    - run_monitoring/run_execution 起動時に監視テーブルが存在することを保証する init_monitoring_db を想定して利用。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py
    - Paper Trading の SQLite DB（既定: data/paper_trading.db）から統計を抽出してレポートを出力する CLI を追加。
    - 指標: 稼働率（uptime）、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）、リスク却下数など。
    - レポート用閾値（PASS/FAIL 判定）を定義:
      - 稼働率 >= 99.0%
      - 注文成功率 >= 90.0%
      - 送信率 >= 95.0%
      - P95 レイテンシ <= 200 ms
    - 日付フィルタ（--from/--to）および DB パス指定（--db）をサポート。

- 研究用ファクター計算（下位モジュール）
  - research/factor_research.py（ファクター計算の骨格を実装）
    - モメンタム（1M/3M/6M リターン、MA200 乖離）、ATR（20 日）、ボリューム等の計算設計を実装予定の関数を用意。
    - DuckDB 接続を受け取り prices_daily / raw_financials テーブルを参照して計算する設計。

### Changed
- ログ出力の統一化
  - すべての起動スクリプト・主要モジュールは setup_logging を呼び出す想定でログ出力が統一されるように設計。

- DB パスの扱い
  - Execution は paper_trading モード時に専用 SQLite を使用して本番 DB と分離（デフォルト paths を明示的に切り替え）。

### Fixed
- .env パースの改善
  - 引用符付き値のバックスラッシュエスケープ、コメントの扱い（インラインコメントの検出）を改善して .env の多様な記法に対応。

### Deprecated
- なし

### Removed
- なし

### Security
- なし（注意: .env に認証情報を平文で保存することに注意する旨、config_setup の生成スクリプトに警告を記載）。

---

## Notes / Known issues / TODO（コード中コメントに基づく）
- portfolio/risk_adjustment.py の apply_sector_cap:
  - price が欠損（0.0）の場合にエクスポージャーが過少見積りされる可能性がある旨の TODO コメントあり。将来的に前日終値や取得原価でのフォールバックが必要。
- position_sizing の将来的拡張:
  - lot_size を銘柄ごとに管理する設計への拡張が検討されている（現在は全銘柄共通の lot_size を想定）。
- research/factor_research.py はファイル末尾で途中（トランケート）になっているため、実装が未完または抜粋の可能性あり。
- run_monitoring は「監視」が常に本番 sqlite_path を使う設計になっているため、開発環境での監視データ分離が必要な場合は設計上の注意が必要（意図的な挙動である旨 docstring に明記）。

---

開発者向けの補足:
- 自動環境変数読み込みはプロジェクトルート検出に依存するため、パッケージ配布後に期待どおり動作しない場合は KABUSYS_DISABLE_AUTO_ENV_LOAD を設定して手動で環境変数を管理してください。
- Logging はデフォルト logs/ を使用します。権限や環境によってディレクトリ作成に失敗するとコンソールのみ出力となるため、運用環境では LOG_DIR の設定を推奨します。