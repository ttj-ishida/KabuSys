# Changelog

すべての変更は Keep a Changelog の慣例に従って記載しています。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

## [0.1.0] - 2026-04-18

### Added
- 基本アプリケーション骨格を追加
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`
- 起動スクリプト
  - `run_execution.py`: 発注エンジン (ExecutionEngine) 起動スクリプトを追加。  
    - KABUSYS_ENV に応じて paper_trading 用に専用 SQLite を使う（data/paper_trading.db、環境変数で上書き可）。  
    - ブローカークライアントの抽象化 (BrokerClientFactory) を経由して実行。  
    - エンジンはデーモンスレッドで実行し、data/stop_requested.flag により安全に停止可能。PID ファイル書き出しに対応。
  - `run_monitoring.py`: SystemMonitor ポーリングループ起動スクリプトを追加。  
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。  
    - 監視は常に本番用 sqlite_path（環境に依らず）を使用する仕様。
- 設定管理 / ユーティリティ
  - `config.py`: 環境変数・.env 自動読み込み機能を実装（プロジェクトルート検出、`.env`/`.env.local` の読み込み、KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。  
    - 多数の設定プロパティを提供（DB パス、API トークン、監視閾値、環境判定 helpers 等）。
    - `.env` パース機能はクォート、エスケープ、コメントの扱いを考慮した堅牢な実装。
  - `config_setup.py`: 対話式の .env 作成ウィザードを追加（既存値の再利用、マスク入力表示、保存）。
  - `validate_config.py`: 起動前設定検証 CLI を追加（必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の検証、DB パスの親ディレクトリ確認、config/*.yaml の存在・パースチェック）。`--strict` オプションで警告を失敗扱いにできる。
- ログ / プロセス制御
  - `utils/logging_setup.py`: 統一的なログ設定ユーティリティを追加。  
    - stdout への StreamHandler と日次ローテーションの FileHandler（TimedRotatingFileHandler）をルートロガーに設定。  
    - 既存ハンドラの重複防止（クリア）やログディレクトリ作成失敗時のフォールバック処理を実装。
  - `utils/process_priority.py`: プロセス優先度と CPU affinity 設定ユーティリティを追加。  
    - Windows / POSIX の差分を吸収して呼び出し側は OS を意識せず使用可能。失敗時は警告を出して安全にスキップ。
- ポートフォリオ構築（純関数群）
  - `portfolio/portfolio_builder.py`
    - 候補選定 (select_candidates)、等配分 (calc_equal_weights)、スコア加重 (calc_score_weights) を実装。スコアが全て 0 の場合は等配分へフォールバック。
  - `portfolio/risk_adjustment.py`
    - セクター集中制限を実装 (apply_sector_cap)。既存保有のセクター別時価を計算して上限超過セクターの新規候補を除外。
    - 市場レジームに基づく投下資金乗数 calc_regime_multiplier を実装（bull/neutral/bear）。
  - `portfolio/position_sizing.py`
    - 発注株数算出ロジックを実装（allocation_method: risk_based / equal / score）。  
    - 単元株丸め（lot_size）、1 銘柄上限、aggregate cap、コストバッファ適用、スケールダウンと端数処理（残余キャッシュでの追加配分）等の実用的な振る舞いをサポート。
  - `portfolio/__init__.py` で各関数をパブリックエクスポート。
- 解析・レポート
  - `tools/paper_verification_report.py`: Paper Trading 検証レポート生成スクリプトを追加。  
    - 稼働率 (uptime)、注文成功率（fill_rate）、送信率（send_rate）、レイテンシ（avg/max/P95）を集計して PASS/FAIL を判定する基準を実装。  
    - 日付フィルタ、P95 計算、閾値による判定メッセージ出力をサポート。
- データベース関連
  - 各起動スクリプトで monitoring 用テーブルの初期化を行う `init_monitoring_db` 呼び出しを追加（冪等性を考慮）。

### Changed
- ロギング設定のデフォルト挙動を統一
  - 起動時に必ず setup_logging(app_name=...) を呼ぶことで全スクリプトのログ出力が一貫するようにした。
- 実行時の安全対策
  - 起動直後にプロセス優先度を高にセットする呼び出しを追加（重要処理の優先実行を意図）。

### Fixed
- 環境変数パーサの改善
  - `config._parse_env_line` の実装でクォート内のバックスラッシュエスケープ、コメントの扱い、不正行の無視等を適切に処理するようにし、.env の広い形式に対応。
- 起動/監視ループの堅牢化
  - `run_monitoring._get_poll_interval` で環境変数の不正な値に対して警告し、デフォルトにフォールバックするようにして time.sleep での例外を防止。
  - 監視ループ内で `monitor.check_once()` の例外をキャッチしてログ出力し、次ポーリングへ継続するようにした（耐障害性の向上）。
- ログディレクトリ作成失敗時のフォールバック
  - `setup_logging` でログディレクトリ作成に失敗した場合、ファイルハンドラをスキップしてコンソール出力のみで継続するように修正。

### Performance
- DuckDB を分析用 DB として積極利用
  - Execution / Monitoring / Research モジュールが DuckDB 接続を受け取り、高速な分析処理を行える設計に。

### Documentation / Developer Experience
- CLI ツールの追加
  - `python -m kabusys.validate_config` と `python -m kabusys.config_setup` により初期設定と検証が容易に。
  - `python -m kabusys.tools.paper_verification_report` でペーパートレードの検証レポートを生成可能。
- コード内ドキュメント（docstring）を充実させ、設計上の注意点や将来の拡張点（TODO）を明記。

### Unreleased / Known limitations
- research/factor_research.py の一部（calc_momentum 等）は実装途中（ファイル末尾が途中で切れている）。実データでの完全動作には追加実装が必要。
- 一部機能（例: 銘柄ごとの lot_size マスタや価格フォールバック）は将来的な拡張を想定しているが現時点では簡易実装（コメントで注記あり）。
- PyYAML がインストールされていない場合、`validate_config` の YAML 内容検証はスキップされ、警告が出る仕様。

---

今後の予定（例）
- factor_research の完成（全ファクター計算・正規化ユーティリティとの統合）
- エンドツーエンドの統合テスト追加（paper_trading モードでの動作確認）
- 起動スクリプトのさらに細かい監視 / 再起動ロジックの追加

もしこのリリースノートの内容で補足したい点や、より細かいカテゴリ分け（例: Security、Breaking Changes）をご希望であれば教えてください。