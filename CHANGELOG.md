CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
バージョン、追加事項、変更点、修正点を日本語で記載しています。

Unreleased
----------

- なし

[0.1.0] - 2026-04-24
--------------------

Added
- パッケージ初期リリース (バージョン 0.1.0)
  - パッケージ識別子: kabusys.__version__ = "0.1.0"

- 起動スクリプト
  - run_monitoring.py
    - SystemMonitor を用いた監視ポーリングループを起動するエントリポイントを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 停止制御: プロジェクト data/stop_requested.flag の存在を検知してループを終了。
    - 監視 DB（SQLite）と分析用 DuckDB に接続し、監視テーブルの初期化を行う。
    - 起動時にプロセス優先度を "high" に設定。

  - run_execution.py
    - ExecutionEngine を起動するエントリポイントを追加。
    - KABUSYS_ENV=paper_trading の場合、paper_trading 用の専用 SQLite（デフォルト: data/paper_trading.db）を使用して本番 DB と分離。
    - BrokerClientFactory を用いてブローカークライアントを切り替え（モック / 実ブローカー）。
    - 停止制御: data/stop_requested.flag を検知してセッションを停止。
    - PID ファイル管理 (data/execution.pid をデフォルト位置として使用)。
    - 起動時にプロセス優先度を "high" に設定。

- 設定管理・ユーティリティ
  - config.py
    - .env 自動読み込み機能を搭載（プロジェクトルートを .git または pyproject.toml で検出）。
    - 読み込み順序: OS 環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
    - .env ファイルパーサを実装（export 形式、クォート値とバックスラッシュエスケープ、インラインコメントの扱いをサポート）。
    - Settings クラスを実装し、環境変数の型変換・妥当性チェック（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE など）を提供。
    - 各種パス定義（DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH / PID_FILE_PATH / KILL_FLAG_PATH）および閾値設定をプロパティで提供。

  - config_setup.py
    - インタラクティブな .env 作成/更新ウィザードを追加。
    - J-Quants / kabu API / データベース / ログ設定 / Kill Switch 等の主要設定を対話的に設定可能。
    - 既存の .env を読み込み、既存値の再利用をサポート。
    - .env の書式化（コメント付きテンプレート）で保存。

  - validate_config.py
    - 起動前チェック CLI を実装。
    - 必須環境変数の有無、KABUSYS_ENV/LOG_LEVEL の妥当性、DB パス周り、config/*.yaml の存在とパース（PyYAML が存在する場合）を検査。
    - KABUSYS_ENV=live のときの追加ガード（LINE 通知設定・KILL_FLAG_CLEAR_ON_START の確認）を実装。
    - --strict オプションで警告を失敗扱いにできる。

- ロギング・プロセス制御ユーティリティ
  - utils/logging_setup.py
    - ルートロガー向けの共通設定関数 setup_logging を追加。
    - stdout 出力用 StreamHandler と日次ローテート（TimedRotatingFileHandler、30日保持）のファイルハンドラを設定。
    - ログレベル解決順: 引数 > 環境変数 LOG_LEVEL > デフォルト "INFO"。
    - ログディレクトリ自動作成。作成失敗時はファイル出力をスキップしてコンソールのみで継続する安全設計。

  - utils/process_priority.py
    - プロセス優先度設定ユーティリティを追加（set_process_priority）。
    - Windows と POSIX (Linux/Mac/FreeBSD) を抽象化して優先度を設定。
    - CPU affinity 設定関数 set_cpu_affinity も提供。
    - psutil の権限エラー等は警告を出して安全にスキップ。

- Portfolio（銘柄選定・配分・ポジションサイズ）
  - portfolio/portfolio_builder.py
    - select_candidates: BUY シグナルのスコア降順選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等配分にフォールバックし警告）。

  - portfolio/risk_adjustment.py
    - apply_sector_cap: セクター集中上限の適用。既存保有（および当日売却予定銘柄の除外）に基づいて新規候補を除外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知レジームは 1.0 にフォールバック（警告）。

  - portfolio/position_sizing.py
    - calc_position_sizes: allocation_method に応じた株数算出を実装。
      - risk_based: 許容リスク率・ストップロスから株数計算。
      - equal/score: 重みから配分計算。
    - 単元株（lot_size）で切り上げ/切り下げ、1 銘柄上限（max_position_pct）、利用可能現金による aggregate cap、cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング処理を提供。
    - スケーリング時の残差補正ロジック（fractional remainders に基づく lot 単位での追加配分）を採用。

- 解析・検証ツール
  - tools/paper_verification_report.py
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 指標: 稼働率 (uptime)、注文成功率 (fill rate)、送信率 (send rate)、P95 レイテンシなど。
    - デフォルト閾値を定義（稼働率 >= 99%、成立率 >= 90%、送信率 >= 95%、P95 <= 200 ms）。
    - 日付フィルタ（--from, --to）と DB パス上書き（--db / PAPER_TRADING_SQLITE_PATH）をサポート。
    - データ欠損やテーブル未存在時に耐性を持たせた実装。

Changed
- なし（初回リリース）

Fixed
- なし（初回リリース）

Notes
- 設計方針
  - 各コンポーネントは可能な限り副作用を抑えた純粋関数（ポートフォリオ算出等）と、起動スクリプト／ユーティリティ（DB 接続、ログ、プロセス制御）に分離。
  - 本番/ペーパートレードのデータ分離を明確にし、安全な運用を支援する設計（paper_trading 用 DB と本番 DB を分離）。
  - .env の自動読み込みは OS 環境変数を保護（上書き禁止）する仕組みを導入。
  - psutil を利用した優先度設定は権限不足や未対応 OS の場合にフォールバックして警告に留め、起動失敗を回避。

開発者向け補足
- このリリースはパッケージ内の主要ユーティリティ群・起動スクリプト・ポートフォリオ構築ロジック・検証ツールを含む初期実装です。
- 実際のブローカー接続（BrokerClientFactory, ExecutionEngine, SystemMonitor 等の詳細実装）は別モジュール/ファイルで定義され、起動スクリプトはそれらを組み合わせて利用します（本ログでは参照のみ）。
- 今後の改善案:
  - テストカバレッジの追加（特に position sizing のスケーリングロジック、.env パーサのエッジケース）。
  - 銘柄ごとの lot_size をマスタ化して細粒度対応。
  - ファイルハンドラ周りのローテーション設定やログ圧縮の拡張。
  - DuckDB / SQLite のコネクションプールやより堅牢なエラーハンドリング。

---