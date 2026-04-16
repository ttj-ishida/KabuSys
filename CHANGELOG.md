# Changelog

すべての注目すべき変更点を記載します。  
このファイルは Keep a Changelog の形式に準拠しています。

現在のバージョン: 0.1.0 — 2026-04-16

## [0.1.0] - 2026-04-16
初回リリース。KabuSys 自動売買フレームワークのコア機能群を実装・追加しました。

### 追加 (Added)
- 全体
  - パッケージ初期化とバージョン管理を追加（src/kabusys/__init__.py, __version__="0.1.0"）。
- 実行・監視ランナー
  - 実行エンジン起動スクリプトを追加（src/kabusys/run_execution.py）。
    - KABUSYS_ENV=paper_trading 時は paper_trading 用 SQLite を使用して本番 DB から完全分離。
    - BrokerClientFactory 経由でブローカークライアントを生成し、ExecutionEngine をスレッドで実行。
    - 停止フラグ（data/stop_requested.flag）および PID ファイル管理（data/execution.pid）をサポート。
  - 監視ポーリングループ起動スクリプトを追加（src/kabusys/run_monitoring.py）。
    - 環境変数 MONITOR_POLL_INTERVAL でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は環境にかかわらず本番 sqlite_path を使用する仕様。
    - 停止フラグ検知でループを安全に終了。
- 設定管理
  - 環境変数/.env 読み込みロジックを実装（src/kabusys/config.py）。
    - プロジェクトルート検出（.git または pyproject.toml を基準）により .env 自動ロードを行う。
    - .env/.env.local のロード順序を導入（OS 環境変数の保護対応）。
    - export 形式・クォート文字列・行内コメント等のパースに対応する堅牢な .env パーサを実装。
    - 必須環境変数検査 helper (_require) と各種設定プロパティを実装（DB パス、API トークン、閾値 など）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
- ポートフォリオ構築（純粋関数群）
  - 候補選定と重み付けロジックを実装（src/kabusys/portfolio/portfolio_builder.py）。
    - select_candidates: スコア降順・タイブレークによる選定。
    - calc_equal_weights / calc_score_weights: 等金額・スコア正規化重み。
  - セクター制限・レジーム乗数を実装（src/kabusys/portfolio/risk_adjustment.py）。
    - apply_sector_cap: 既存保有状況からセクター集中を除外するフィルタ。
    - calc_regime_multiplier: market regime による投下資金乗数（bull/neutral/bear）。
  - ポジションサイジングを実装（src/kabusys/portfolio/position_sizing.py）。
    - risk_based / equal / score 方式に対応。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（利用可能現金）を考慮したスケーリングを実装。
    - cost_buffer（手数料・スリッページ見積り）を加味した保守的評価。
  - portfolio パッケージエクスポートを追加（src/kabusys/portfolio/__init__.py）。
- リサーチ（DuckDB ベース）
  - ファクター計算モジュールを実装（src/kabusys/research/factor_research.py）。
    - calc_momentum, calc_volatility, calc_value：価格・財務データから各種ファクターを算出（DuckDB を使用）。
  - 特徴量探索モジュールを実装（src/kabusys/research/feature_exploration.py）。
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic）、統計サマリー（factor_summary）、ランク付けユーティリティを提供。
  - research パッケージエクスポートを追加（src/kabusys/research/__init__.py）、zscore_normalize の再エクスポートを含む。
- AI ニュース NLP（OpenAI 統合）
  - raw_news を集約して OpenAI（gpt-4o-mini）でセンチメントを算出し ai_scores に書き込むためのモジュールを追加（src/kabusys/ai/news_nlp.py）。
    - ターゲット日のニュースウィンドウ計算（calc_news_window）。
    - チャンク単位（最大 20 銘柄）でのバッチ送信、最大文字数・記事数のトリミング、スコアの ±1.0 クリップ、429/ネットワーク/5xx に対する指数バックオフ再試行などの仕様を盛り込んだ設計。
    - 出力 JSON 検証と部分更新（対象コードのみ DELETE→INSERT）による耐障害性を考慮。
- ユーティリティ
  - プロセス優先度・CPU affinity 設定ユーティリティを追加（src/kabusys/utils/process_priority.py）。
    - Windows/Linux/macOS 等の差分を吸収し set_process_priority(level) で "high"/"normal"/"low" を設定。
    - set_cpu_affinity(cpu_count) で最初の N コアに固定する機能を追加（権限不足や未対応環境では警告を出してスキップ）。
- ツール
  - Paper Trading 検証レポート生成 CLI を追加（src/kabusys/tools/paper_verification_report.py）。
    - --from/--to/--db オプションで期間フィルタと DB パスを指定可能。
    - 稼働率、注文成功率、送信率、P95 レイテンシ等の指標を算出し PASS/FAIL 判定（閾値はモジュール内定義）。
    - P95 計算、各種 SQL クエリ、欠損時のフォールバックを実装。

### 変更 (Changed)
- 設定・環境変数処理の挙動を明確化
  - .env 自動ロードの探索ロジックは __file__ を基点に行われ、ワークディレクトリに依存しないように設計（src/kabusys/config.py）。
  - PAPER_TRADING_SQLITE_PATH / SQLITE_PATH / DUCKDB_PATH 等のデフォルトパスを明示（data/*.db）。
- run_monitoring / run_execution の起動シーケンス
  - 起動時にプロセス優先度を "high" に設定（set_process_priority を最初に呼び出す）。
  - 監視は常に本番 sqlite_path を参照する設計（環境に依存しない監視データ収集）。
  - ExecutionEngine は paper_trading 環境では専用 DB を使用し、mock ブローカーと完全分離するよう変更。

### 修正 (Fixed)
- 環境変数パーサの頑健性改善
  - export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメントの扱いなど、従来の単純パースで失敗しうるケースへの対応（src/kabusys/config.py）。
- calc_score_weights のゼロスコア取り扱い
  - 全銘柄スコア合計が 0 の場合に等金額配分にフォールバックし警告を出すようにして、安全性を確保（src/kabusys/portfolio/portfolio_builder.py）。
- position sizing のスケーリングロジック
  - aggregate cap を超える場合のスケールダウン処理と lot_size 単位での再配分アルゴリズムを実装（src/kabusys/portfolio/position_sizing.py）。
- DuckDB クエリの NULL / 欠損値取り扱い
  - ATR 等の計算で NULL 伝播を明示的に制御し、窓幅不足時には None を返すようにした（src/kabusys/research/factor_research.py）。
- Paper レポートの堅牢性
  - テーブルがない・DB 操作で sqlite3.OperationalError が発生した場合に個別指標を N/A でフォールバックするようにした（src/kabusys/tools/paper_verification_report.py）。

### 既知の制限 / 注意点 (Known issues / Notes)
- src/kabusys/ai/news_nlp.py は概ね実装済みですが、配布されたコードの末尾が切れており（ファイル終端で一部ロジックが途中）、完全な処理フロー（記事フェッチ関数の継続・API 呼び出しループの最終処理・DB 更新処理など）が未表示の可能性があります。実運用前に該当ファイルの末尾が完全であることを確認してください。
- price_map に 0.0（価格欠損）があるとエクスポージャー算出が過少見積りされる可能性がある点を TODO として注記（src/kabusys/portfolio/risk_adjustment.py）。将来的に前日終値や取得原価でのフォールバックを検討する必要があります。
- set_process_priority / set_cpu_affinity は権限（root や管理者）や環境依存で失敗する場合があり、その場合は警告を出してスキップします。

---

将来のリリースでは次を予定しています（例）:
- news_nlp の完全実装と単体テスト整備
- 戻り値/例外の整合性を保証するための型ヒント強化とユニットテスト充実
- 銘柄別 lot_size マスタ対応（position sizing の拡張）
- DuckDB クエリのパフォーマンス最適化とインデックス/マテリアライズ検討

変更や不明点があれば指摘してください。必要に応じてバージョン管理・リリースノートを更新します。