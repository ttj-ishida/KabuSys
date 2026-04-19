# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは Keep a Changelog に準拠しています。

現在のバージョン: 0.1.0

## [Unreleased]

（現時点で未リリースの変更はありません）

---

## [0.1.0] - 2026-04-19

初回公開リリース。以下の機能を提供します。

### 追加 (Added)
- 実行スクリプト
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は常に本番用の SQLite パスを使用するよう設計。
    - 停止はプロジェクト配下の `data/stop_requested.flag` によるフラグ検知で行う。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` 時は MockBrokerClient を使用し、ペーパートレード専用 DB (`data/paper_trading.db`) に記録（本番 DB と分離）。
    - 実行中の PID 管理（`data/execution.pid`）および停止フラグ検知による安全停止をサポート。
    - 実行はデーモンスレッドで行い、メインスレッドで停止フラグを監視。

- 設定管理
  - config.py: Settings クラスを導入し、環境変数から設定を取得。
    - `.env` / `.env.local` 自動読み込み（プロジェクトルート検出: `.git` または `pyproject.toml` を基準）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` のパース強化（`export` プレフィックス、クォート内のエスケープ、インラインコメント処理等に対応）。
    - 各種パス設定（DUCKDB/SQLITE/PAPER_TRADING_SQLITE）、ログレベル、環境判定プロパティ（is_live/is_paper/is_dev）等を提供。
    - `paper_fill_mode` の検証（許容値: instant/partial/never/reject）。

- 設定補助ツール
  - config_setup.py: 対話式の .env ウィザードを追加。
    - 主要な環境変数の入力支援、既存 .env の読み込み・既存値再利用、保存確認、.env 書き込み。
    - `.env` に関する注意文（コミット禁止など）を出力。

- 設定検証 CLI
  - validate_config.py: 起動前に環境設定と config/*.yaml を検証するツールを追加。
    - 必須環境変数チェック、KABUSYS_ENV/LOG_LEVEL の妥当性検証、DB パスの親ディレクトリ存在確認、YAML ファイルのパースチェック（PyYAML がインストールされている場合）。
    - `--strict` オプションで警告を失敗扱い（exit 1）にできる。

- ロギング・ユーティリティ
  - utils/logging_setup.py: 統一的なロギング設定を提供。
    - コンソール出力は stdout（StreamHandler）、ファイル出力は日次ローテーション（TimedRotatingFileHandler、30 日保持）。
    - 既存ハンドラの二重登録防止、ログディレクトリ自動作成（失敗時はファイル出力をスキップ）等の堅牢化。

- プロセス制御ユーティリティ
  - utils/process_priority.py:
    - Windows と POSIX 系（Linux/Mac 等）でのプロセス優先度設定を抽象化（high/normal/low）。
    - CPU affinity を指定コア数に固定する関数を提供。
    - 権限不足や未対応 OS では安全に警告を出してスキップ。

- ポートフォリオ構築モジュール
  - portfolio/portfolio_builder.py:
    - 候補選定（select_candidates）、等金額配分（calc_equal_weights）、スコア重み配分（calc_score_weights）を純粋関数として実装。
    - スコアが全て 0 の場合のフォールバック処理（等金額配分）をログ出力とともに実装。
  - portfolio/risk_adjustment.py:
    - セクター集中制限を適用する apply_sector_cap を実装（既存ポジションのセクター別時価計算、上限超過セクターの新規候補除外）。
    - 市場レジームに応じた資金乗数 calc_regime_multiplier を実装（bull/neutral/bear に対応、未知値は警告とともにフォールバック）。
  - portfolio/position_sizing.py:
    - position sizing ロジックを実装（risk_based / equal / score の allocation メソッド対応）。
    - 単元株（lot_size）での丸め、ポジション単位上限と aggregate cap（利用可能現金）に基づくスケーリング、cost_buffer を考慮した保守的見積り、端数処理のための再配分ロジックを実装。

- Execution / Monitoring の DB 初期化
  - run_monitoring/run_execution 内で monitoring 用テーブルを冪等に初期化する init_monitoring_db の呼び出しを追加。

- Paper Trading 検証ツール
  - tools/paper_verification_report.py:
    - Paper Trading の SQLite DB（デフォルト: data/paper_trading.db）を読み取り、稼働率、注文成功率・送信率、レイテンシ（平均・最大・P95）等の検証レポートを生成する CLI を追加。
    - デフォルト基準値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を定義し、PASS/FAIL 判定を出力。

- 研究モジュール（ファクター計算）
  - research/factor_research.py: DuckDB を用いたファクター計算の基盤を追加（モメンタム・MA・ATR 等の定数と calc_momentum の骨組み）。  
    - （注）ファイルは途中まで含まれており、今後の拡張で完全な実装が予定される。

### 変更 (Changed)
- ログ出力の標準出力先として stderr ではなく stdout を採用（cron / Task Scheduler での取り扱いを考慮）。
- ログハンドラの再設定時に既存ハンドラを flush/close してから削除するように改善（ハンドラ二重登録の回避とリソース解放）。
- .env パーサの堅牢化により、引用符やエスケープ、コメントの扱いを改善。

### 修正 (Fixed)
- run_execution の DB 接続は環境に応じて paper_trading 用 DB を使用するように修正（paper_trading と本番 DB の分離を保証）。
- run_monitoring のポーリング間隔設定で 0 以下の値が誤設定された場合にデフォルトへフォールバックするように修正（time.sleep の ValueError 回避）。

### ドキュメント (Documentation)
- 各 CLI スクリプトに簡易的な使用方法と環境変数の説明を追加（ファイル docstring およびコマンドラインヘルプに記載）。
- config_setup に .env に関する注意（Git コミット禁止など）を明示。

### セキュリティ (Security)
- .env を絶対に Git にコミットしない旨の注意書きを config_setup の書き出しテンプレートに含めた。

---

開発上の注記
- 現在のリポジトリは初期段階の設計・実装を中心に含み、research/factor_research.py のように未完の部分が存在します。将来的なリリースではファクター計算や ExecutionEngine の詳細な挙動、外部ブローカー連携の実装強化・テストカバレッジ追加などを予定しています。
- 本 CHANGELOG はソースコードから推測して記載しています。実際のコミット履歴や追加予定の機能により差異が生じる可能性があります。