# CHANGELOG

すべての注記は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

なお、本CHANGELOGは与えられたコードベースから機能・設計・開発意図を推測して作成したものであり、実際のコミット履歴や公開リリースノートとは差異がある可能性があります。

## [Unreleased]

- 進行中 / 今後の作業（コード内コメントから推測）
  - research/factor_research.py の実装完了（スニペットが途中で終わっているため未完了を想定）。
  - position_sizing の将来的拡張:
    - 銘柄ごとの単元（lot_size）を stocks マスタから読み込む設計への拡張。
    - 価格欠損時のフォールバック（前日終値・取得原価など）対応。
  - テストおよび例外ハンドリングの充実（DB パス作成失敗やファイルIO失敗時のフォールバック強化）。
  - ドキュメント整備（PortfolioConstruction.md 等の参照箇所の公開/整備）。

---

## [0.1.0] - 2026-04-19

### 追加 (Added)
- 起動スクリプト / デーモン
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。停止フラグファイルで安全に終了。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。KABUSYS_ENV=paper_trading の場合は専用のペーパートレード DB を使用し、MockBrokerClient 経由で動作を分離。停止フラグ / PID 管理に対応。

- 設定管理 / CLI
  - config.py: 環境変数読み込み・ラッパー Settings を実装。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動ロード。
    - .env パースの堅牢化（export 形式、クォート文字内のエスケープ、インラインコメントの扱いなど）。
    - 各種設定プロパティ（DB パス、paper_trading 用パス、しきい値、ログレベル判定、環境判定等）。
  - config_setup.py: .env 初期作成・更新の対話式ウィザードを追加（保存・既存値読み込み対応）。
  - validate_config.py: 起動前検証 CLI を追加（必須環境変数の確認、KABUSYS_ENV/LOG_LEVEL の妥当性チェック、config/*.yaml の存在およびパース確認、--strict オプション）。

- ロギング / プロセス管理ユーティリティ
  - utils/logging_setup.py: 統一的なログ設定ユーティリティを追加。StreamHandler（stdout）と日次ローテーションのファイルハンドラ（TimedRotatingFileHandler）を設定。ログディレクトリ作成失敗時はコンソール出力のみで継続。
  - utils/process_priority.py: プロセス優先度・CPU affinity 設定ユーティリティを追加。Windows/Linux/macOS を吸収する実装。優先度は "high" / "normal" / "low" をサポート。CPU ピンニング機能も提供。

- ポートフォリオ構築ライブラリ
  - portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルのスコア順選定（同点は signal_rank でタイブレーク）。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア加重配分（全スコアが 0 の場合は等金額へフォールバック）。
  - portfolio/risk_adjustment.py:
    - apply_sector_cap: セクター集中制限ロジック（既存ポジションのセクター比率が閾値を超える場合に新規候補を除外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数の計算。未知レジームは 1.0 にフォールバック。
  - portfolio/position_sizing.py:
    - calc_position_sizes: allocation_method ("risk_based", "equal", "score") に基づく発注株数計算。単元株丸め、per-stock 上限、aggregate cap（利用可能現金でのスケール）、cost_buffer（手数料・スリッページ見積り）に対応。
  - portfolio/__init__.py: 上記機能をパッケージとして公開。

- 実行 / 注文関連
  - run_execution が BrokerClientFactory を使用し、OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine を組み立てるワークフローを提供。RiskManager に初期設定（max_position_pct、max_utilization、rate_limit_per_sec、circuit_breaker 等）を投入。
  - monitoring.monitoring_db.init_monitoring_db を呼び出して監視テーブルの存在を保証（冪等）。

- 分析用 DB 統合
  - DuckDB 接続を各コンポーネントで受け入れる設計（duckdb_path 設定）。分析用クエリやファクター計算向けに準備。

- ツール
  - tools/paper_verification_report.py: ペーパートレード検証レポート生成ツールを追加。期間指定可（--from / --to）で稼働率、注文成功率・送信率、リスク却下数、API レイテンシ（avg / max / P95）などを集計し PASS/FAIL 判定を行う。P95 計算・欠損値扱いに配慮。

- リサーチ
  - research/factor_research.py: DuckDB を使ったファクター計算モジュールを追加（モメンタム、MA200 乖離、ATR、流動性等）。設計方針と定数が定義済み（実装途中あり）。

- パッケージ情報
  - __init__.py にバージョン __version__ = "0.1.0" を追加。

### 改良 (Changed)
- .env 読み込みの優先順位を明確化: OS 環境 > .env.local > .env（既存 OS 環境変数を protected として上書きを防ぐ）。
- logging_setup:
  - デフォルトで stdout を使用することで cron/Task Scheduler などでの出力取り扱いを改善。
  - ログディレクトリ作成失敗時にファイルハンドラをスキップする安全設計。
- process_priority:
  - OS 毎の差分を隠蔽し、呼び出し側を簡潔化。

### 修正 (Fixed)
- .env パースにおけるクォート内エスケープやインラインコメントの扱いを考慮して堅牢化（export 形式対応、コメント扱いのルール明確化）。
- run_execution/run_monitoring における DB 閉じ忘れを finally ブロックで対処。

### 注意点 / 既知の制限
- research/factor_research.py はファイル末尾が途中で終わっているため、実装が未完了の関数や未公開のユーティリティに依存している可能性あり。
- position_sizing.calc_position_sizes の TODO:
  - price が欠損（0.0）の場合のフォールバックロジック未実装。現状だと過小見積もりになる可能性あり。
  - lot_size は現状グローバル共通で、銘柄別単元対応は将来の拡張予定。
- Paper Trading と本番 DB の完全分離は考慮されているが、運用ルールの遵守（環境変数設定など）はユーザ側の注意が必要（validate_config にガードあり）。

### セキュリティ (Security)
- 秘密値（J-Quants トークン、kabu API パスワード、LINE トークン等）は .env に保存する設計のため、.env を絶対にリポジトリにコミットしない旨を config_setup.py に明記。

---

（参考）今後のリリース案
- 0.2.0 (予定)
  - research/factor_research の完成・最適化
  - 単元株・銘柄ごとの lot_size 対応
  - .env パース/検証のさらなる強化とユニットテスト整備
  - ExecutionEngine の監視/リトライ・性能メトリクス強化

--- 

以上。必要であれば各項目をより詳細なコミット単位に分解して追記できます。どの粒度で履歴を残したいか（例: 機能ごと / ファイルごと / コミットごと）を指定してください。