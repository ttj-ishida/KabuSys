# Changelog

すべての注目すべき変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

## [Unreleased]

（なし）

---

## [0.1.0] - 2026-04-17

初回リリース。本リポジトリは日本株自動売買システム「KabuSys」のコア機能を含みます。下記はソースコードから推測した主要な追加・変更点のまとめです。

### 追加 (Added)
- 全体
  - パッケージ初期化とバージョン管理（kabusys.__version__ = 0.1.0）。
  - keepalive / 停止フラグを用いたプロセス制御（data/stop_requested.flag 等を利用）。

- 設定・環境読み込み（kabusys.config）
  - .env / .env.local の自動ロード機能（プロジェクトルート自動検出: .git または pyproject.toml）。
  - 高度な .env パーサを実装（export プレフィックス対応、シングル/ダブルクォート内のエスケープ処理、インラインコメント処理）。
  - OS 環境変数保護（読み込み時の protected パラメータにより上書きを制御）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能に：
    - J-Quants・kabu API、LINE 設定、DuckDB/SQLite パス、PID/KILL フラグ関連パス
    - Paper Trading 用設定（PAPER_FILL_MODE / PAPER_TRADING_SQLITE_PATH / paper_fill_mode / paper_sqlite_path）
    - 監視しきい値（CPU / memory / disk）
    - 環境検証（KABUSYS_ENV の valid 値検査、LOG_LEVEL 検査）
    - is_live / is_paper / is_dev 判定ヘルパー

- 実行コンポーネント
  - run_execution: ExecutionEngine 起動スクリプト
    - BrokerClientFactory によるブローカークライアント生成（KABUSYS_ENV=paper_trading 時は Mock と専用 DB を使用）。
    - OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine の組み立てと実行制御（スレッド実行、停止フラグ検知）。
    - RiskManager のデフォルト設定（max_position_pct, max_utilization, rate_limit_per_sec, circuit_breaker など）。
    - duckdb 接続の利用（分析用 DB）。
    - 監視テーブルの初期化呼び出し（init_monitoring_db）。

  - run_monitoring: SystemMonitor ポーリングループ起動スクリプト
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔をオーバーライド可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する設計。
    - stop フラグ検出によるループ終了、チェック例外のログ出力、リソースクローズ処理。

- 監視 DB 初期化ユーティリティ（init_monitoring_db の呼び出し場所を整備）

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を実装（Windows と POSIX を吸収）。
  - set_cpu_affinity(cpu_count) を実装（指定コア数での CPU affinity 設定）。
  - psutil の例外をハンドルして失敗時は警告を出すフェイルセーフ設計。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates（スコア降順、signal_rank でタイブレーク）
    - calc_equal_weights（等金額配分）
    - calc_score_weights（スコア正規化・スコア全0 の場合は等配分にフォールバック）
  - risk_adjustment:
    - apply_sector_cap（セクター集中上限チェック。unknown セクターは適用除外）
    - calc_regime_multiplier（市場レジームに応じた投下資金乗数: bull/neutral/bear）
  - position_sizing:
    - calc_position_sizes（allocation_method: risk_based / equal / score をサポート）
    - 単元株丸め、max_position・aggregate cap、cost_buffer を考慮したスケーリング、残差処理（lot 単位での追加配分）

- 研究・ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum（1M/3M/6M リターン、MA200 乖離）
    - calc_volatility（ATR20、相対 ATR、20日平均売買代金、出来高比）
    - calc_value（PER / ROE を raw_financials と prices_daily から計算）
    - 全て DuckDB を用いた SQL ウィンドウ関数で実装（パフォーマンス考慮）
  - feature_exploration:
    - calc_forward_returns（任意ホライズンの将来リターン一括取得。引数 validation を実装）
    - calc_ic（スピアマンランク相関（IC）計算、必要件数チェック）
    - rank / factor_summary（ランク付け、統計サマリ）

- ツール（kabusys.tools）
  - paper_verification_report:
    - Paper Trading の検証レポート生成スクリプト（期間指定オプション、DB パスオーバーライド可能）
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の算出と閾値判定（PASS/FAIL）
    - P95 計算ユーティリティ、DB テーブル存在チェック時の安全ハンドリング

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news から銘柄ごとに記事を集約し OpenAI（gpt-4o-mini）へバッチ送信してセンチメントスコアを ai_scores に書き込む機能を追加
  - 実装の要点:
    - ニュース集約ウィンドウを JST 基準で計算（前日 15:00 ～ 当日 08:30 JST を UTC に変換）
    - 1 銘柄あたりの上限記事数／文字数でトークン肥大化を抑制
    - バッチサイズ、リトライ（429/接続断/5xx 等）を実装（エクスポネンシャルバックオフ）
    - レスポンスバリデーション、スコアの ±1.0 クリッピング
    - OpenAI API キー未設定時は明示的にエラーを返す
    - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない設計（target_date ベース）

### 変更 (Changed)
- 環境変数ロード優先度
  - OS 環境変数 > .env.local > .env の順でロードする挙動を明確化（既存 OS 環境を保護する設計）。
- run_monitoring の監視対象 DB
  - Monitoring は KABUSYS_ENV にかかわらず本番 sqlite_path を参照する（設計上の明示）。
- 実行時のプロセス優先度設定を起動直後に行うよう統一（run_monitoring / run_execution ともに set_process_priority("high") を呼び出し）。

### 修正 (Fixed)
- .env パーサの堅牢化
  - 引用符内のバックスラッシュエスケープ、インラインコメントの扱い、export プレフィックスを適切に処理するよう改善。
- paper_verification_report
  - DB 内のテーブルが存在しない場合に OperationalError を捕捉して N/A を返すようにし、レポート生成が途中で壊れないように修正。
  - P95 計算の境界条件（空リスト → None）の扱いを明確化。
- research.feature_exploration.calc_forward_returns
  - horizons 引数のバリデーション（正の整数かつ <= 252）を追加し、不正入力で早期に ValueError を投げるようにした。
- process_priority
  - 未対応 OS での動作を警告してスキップするフェイルセーフを追加。権限不足時の例外を捕捉して警告出力。

### セキュリティ（Security）
- AI モジュールにおいて OpenAI API キーを明示的に要求し、未設定時に ValueError を発生させることで誤った匿名アクセスや未設定状態での実行を防止。
- ニュース処理でルックアヘッドバイアスを避ける設計（外部的な現在時刻参照を行わず、target_date を明示的に使う）。

### パフォーマンス（Performance）
- ファクター計算（momentum/volatility/value）を DuckDB のウィンドウ関数で実装し、集計処理を DB 側で高速に行うよう最適化。
- AI スコアリングは銘柄単位で集約してバッチ送信（_BATCH_SIZE = 20）し API 呼び出し回数を削減。

### ドキュメント・使い方
- run_execution/run_monitoring/run_tools などは CLI スクリプトとして直接実行可能（if __name__ == "__main__" に対応）。
- paper_verification_report は --from/--to/--db オプションで期間および DB パスを指定可能。
- Settings クラスの各プロパティに docstring を付与し利用方法を明確化。

---

今後の予定（推測）
- AI ニュース処理の続き実装（_fetch_articles 等が途中までのため、記事取得・整形部分の完成）。
- テスト・エラーハンドリングの拡充（特に外部 API 呼び出し周り）。
- 単体テスト・CI 設定の追加。