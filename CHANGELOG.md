# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
バージョン/日付は、提供されたコードベースの内容から推測して記載しています。

全般的な注意
- 環境変数やファイルパスに依存するため、デフォルトや動作は .env / 環境変数で上書き可能です。
- 一部のモジュール（例: research/factor_research）は実装途中の箇所が含まれているため、将来のリリースで拡張されることを想定しています。

## [Unreleased]
- （今後の変更点をここに記載）

## [0.1.0] - 2026-04-18
初回リリース（推定）。自動売買システム KabuSys の基盤的機能を実装。

### 追加 (Added)
- アプリケーションのバージョン定義
  - `kabusys.__version__ = "0.1.0"` を導入。

- 起動スクリプト
  - `src/kabusys/run_monitoring.py`
    - SystemMonitor ポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔の上書き（デフォルト 60 秒）。
    - 停止フラグ (data/stop_requested.flag) を検知して安全終了。
    - プロセス優先度を "high" に設定してから起動。
    - 監視は環境にかかわらず設定された（本番想定の）`sqlite_path` を使用する旨をドキュメント化。
  - `src/kabusys/run_execution.py`
    - ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は Paper Trading 用の専用 SQLite (`data/paper_trading.db` など) を使用し、本番 DB と分離する挙動を実装。
    - ブローカークライアントのファクトリ、オーダー管理、リスク管理、Reconciler、ExecutionEngine を組み立てて起動。エンジンはデーモンスレッドで実行され、停止フラグ検知で停止処理。
    - 起動時に `execution.pid` を使う設計（PID ファイルパスの受け渡し）。

- 設定管理
  - `src/kabusys/config.py`
    - 環境変数・.env ファイル自動読み込み機能（プロジェクトルート検出: .git / pyproject.toml を基準）。
    - `.env` と `.env.local` の読み込み順序（OS 環境変数を保護しつつ .env.local が上書き可能）。
    - `.env` のパースは export プレフィックス、クォート文字列、インラインコメント、エスケープを考慮して堅牢に実装。
    - 各種設定プロパティを提供（J-Quants トークン、kabu API、LINE 設定、DuckDB/SQLite パス、PID/kill flag、閾値等）。
    - `PAPER_FILL_MODE` の妥当性チェック（有効値: instant/partial/never/reject）。
    - `KABUSYS_ENV` の妥当性チェック（development/paper_trading/live）。
    - `settings` インスタンスをエクスポート。

- 設定ユーティリティ（CLI）
  - `src/kabusys/config_setup.py`
    - 対話式ウィザードで .env を作成・更新する CLI を実装。
    - シークレット項目のマスク表示、選択肢サポート、既存 .env の読み込み再利用、ファイル書き込みロジックを提供。
    - 書き込みテンプレートには注意書き（.env を Git にコミットしない）を含む。

  - `src/kabusys/validate_config.py`
    - 起動前に環境変数と config/*.yaml の設定不備を検出する CLI を実装。
    - 必須環境変数チェック、KABUSYS_ENV の妥当性、LOG_LEVEL チェック、DB パス（親ディレクトリ存在）チェック、YAML ファイルの存在/パース検証（PyYAML がない場合は警告）、および本番時の追加安全チェック（LINE 通知設定や KILL_FLAG_CLEAR_ON_START）を提供。
    - `--strict` オプションで警告も失敗扱いにできる。

- ログ・プロセスユーティリティ
  - `src/kabusys/utils/logging_setup.py`
    - ルートロガー設定ユーティリティを追加。
    - stdout への StreamHandler と、日次ローテーション (TimedRotatingFileHandler) によるファイル出力（デフォルト logs/<app_name>.log、30日保持）を設定。
    - LOG_DIR 作成失敗時はファイルハンドラをスキップして stdout のみで継続するフェールセーフを実装。
    - 引数 / 環境変数 / デフォルトの優先順位でログレベル・ログディレクトリを決定。

  - `src/kabusys/utils/process_priority.py`
    - Windows と POSIX 系（Linux/Mac 等）を抽象化したプロセス優先度設定ユーティリティを追加。
    - `set_process_priority(level)` により nice 値 / Windows 優先度クラスを設定（権限不足時は警告でスキップ）。
    - `set_cpu_affinity(cpu_count)` によりプロセスを最初の N コアにピン留めする機能を提供（未対応環境や権限不足は警告でスキップ）。

- ポートフォリオ構築ライブラリ
  - `src/kabusys/portfolio/portfolio_builder.py`
    - シグナル選定（score 降順 + tie-break）、等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等金額へフォールバック）を追加。

  - `src/kabusys/portfolio/risk_adjustment.py`
    - セクター集中管理 apply_sector_cap: 既存保有のセクター比率が max_sector_pct を超える場合、同セクターの新規候補を除外。unknown セクターは除外しない。
    - レジームに応じた乗数 calc_regime_multiplier（bull:1.0 / neutral:0.7 / bear:0.3）。未定義レジームでは 1.0 にフォールバックし警告を出す。

  - `src/kabusys/portfolio/position_sizing.py`
    - 発注株数算出 calc_position_sizes:
      - allocation_method に "risk_based" / "equal" / "score" をサポート。
      - risk_based: portfolio_value・risk_pct・stop_loss_pct に基づくポジション算出。
      - equal/score: weight に基づく割付、per-position 上限（max_position_pct）を考慮。
      - lot_size（単元）に基づく丸め処理、cost_buffer を見積りに含めた aggregate cap（available_cash 超過時にスケーリング）と残余配分アルゴリズムを実装。
      - 価格未取得時は当該銘柄をスキップしてログ出力。

  - `src/kabusys/portfolio/__init__.py`
    - 上記関数群をパブリック API としてエクスポート。

- ツール
  - `src/kabusys/tools/paper_verification_report.py`
    - Paper Trading 向け検証レポート生成ツールを追加。
    - system_status / trade_logs / risk_logs テーブルから稼働率、注文成立率、送信率、レイテンシ（平均/最大/P95）を算出してレポート出力。
    - 基準値（稼働率 99% / 成功率 90% / 送信率 95% / P95 レイテンシ 200ms）を定義し PASS/FAIL 判定を行う。
    - 日付フィルタ、DB パス指定（--db または 環境変数 PAPER_TRADING_SQLITE_PATH）をサポート。
    - P95 算出ロジックを実装。

- リサーチ（初期実装）
  - `src/kabusys/research/factor_research.py`
    - ファクター計算モジュールを追加（Momentum、Value、Volatility、Liquidity を想定）。
    - momentum の定数（1M/3M/6M 日数、MA200、ATR 等）を定義し、calc_momentum の骨格を実装（ファイル末尾はコード断片で続きがあることを示唆）。

### 変更 (Changed)
- 環境読み込みの挙動明確化
  - 自動 .env ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能（テスト用途想定）。
  - .env の読み込み優先度: OS 環境 > .env.local > .env（.env.local は override=True）。

### 修正 (Fixed)
- ロギング初期化でのハンドラ重複防止
  - setup_logging は既存ハンドラを flush/close してから削除し、二重出力を防止するようになっている。

### 既知の制限 / 注意点 (Known issues / Notes)
- run_monitoring.py は「監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用する」とドキュメント化しているため、開発環境でのテストには注意。意図的な設計のため、必要に応じて環境変数でパスを上書きするかコード修正が必要。
- `research/factor_research.py` はファイル末尾が断片的で、関数実装が未完の可能性あり。実運用で使用する前に完全実装とテストが必要。
- position_sizing の価格欠損時の挙動はログ出力でスキップするのみ。将来的に価格フォールバック（前日終値など）を実装予定（TODO コメントあり）。
- process_priority / set_cpu_affinity は権限や OS によっては適用できない場合があり、その場合は警告を出してスキップする安全設計。
- validate_config は PyYAML の未インストール時に YAML 内容検証をスキップする（警告）。YAML 構成検証を有効にするには PyYAML の導入が必要。

### セキュリティ (Security)
- .env の取り扱いに関する注意書きを config_setup に含め、.env を Git にコミットしないように推奨。

---

（この CHANGELOG は、提供されたソースコードの内容および内在するコメントやドキュメントから推測して作成しました。実際のリリースノートとして使用する場合は、コミット履歴やリリース方針に合わせて調整してください。）