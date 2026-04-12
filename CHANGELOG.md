# Changelog

すべての重要な変更はこのファイルに記録します。フォーマットは Keep a Changelog に準拠します。  
新しいバージョンはセマンティックバージョニングを使用します。

## [Unreleased]

（開発中の変更はここに記載します）

---

## [0.1.0] - 2026-04-12

初回公開リリース。

### Added
- 基本パッケージ情報
  - kabusys パッケージ初期バージョンを追加（__version__ = 0.1.0）。
- 実行エントリ
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` によるポーリング間隔上書き（デフォルト 60 秒）。
    - 監視は実行環境にかかわらず本番用の sqlite_path を使用する設計。
    - プロセス優先度を起動時に設定（utils.process_priority を利用）。
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - `KABUSYS_ENV=paper_trading` の場合は paper_trading 用 DB を使用し MockBrokerClient を利用する分離設計。
    - ExecutionEngine の組み立て（BrokerFactory、OrderRepository、OrderManager、RiskManager、Reconciler 等）。
- 設定管理
  - config.py:
    - .env 自動ロード機能（プロジェクトルートを .git / pyproject.toml で検出）。
    - .env / .env.local の読み込み順序（OS 環境変数 > .env.local > .env）。
    - `.env` 行パーサで export 形式、クォート文字列、インラインコメント等に対応する堅牢な実装を追加。
    - 各種設定プロパティ（DB パス、PID ファイル、kill フラグ、閾値、環境種別チェック、paper trading 関連等）。
    - `PAPER_FILL_MODE` のバリデーション（許容値: instant|partial|never|reject）。
- ユーティリティ
  - utils/process_priority.py:
    - プラットフォーム差を吸収するプロセス優先度（high/normal/low）設定ユーティリティを追加。
    - CPU affinity を最初の N コアに固定する set_cpu_affinity を追加（権限不足時はスキップして警告）。
- 監視 DB 初期化ユーティリティを監視モジュールから利用（init_monitoring_db 呼び出し）。
- ポートフォリオ構築（純粋関数群）
  - portfolio/portfolio_builder.py:
    - シグナルソート（score 降順、同点時 signal_rank）および候補選定関数 select_candidates。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights（全スコアが 0 の場合は等配分にフォールバックし警告）。
  - portfolio/risk_adjustment.py:
    - セクター集中制限適用関数 apply_sector_cap（既存ポジションのセクター露出計算と候補除外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier（"bull"/"neutral"/"bear" をサポートし未知値はログ警告でフォールバック）。
  - portfolio/position_sizing.py:
    - position sizing ロジック（risk_based / equal / score）、単元株丸め（lot_size）、max_position / aggregate cap、cost_buffer を考慮したスケールダウンロジックを実装。
    - スケールダウン時に残余キャッシュを使って端数（lot 単位）を再配分するアルゴリズムを実装。
- リサーチ機能（DuckDB ベース）
  - research/factor_research.py:
    - Momentum / Volatility / Value ファクター計算関数（calc_momentum / calc_volatility / calc_value）。
    - DuckDB の prices_daily / raw_financials を利用するクエリ実装。
    - 長期 MA や ATR のウィンドウサイズなど定数化。
  - research/feature_exploration.py:
    - 将来リターン計算 calc_forward_returns（任意ホライズン対応）。
    - IC（Spearman ρ）計算 calc_ic、ランク付けユーティリティ rank、ファクター統計 summary（factor_summary）。
    - ties を平均ランクで処理する安定したランク実装。
  - research/__init__.py で主要関数と zscore_normalize をエクスポート。
- AI ニュース NLP スコアリング
  - ai/news_nlp.py:
    - raw_news / news_symbols を集約して OpenAI API（gpt-4o-mini）にバッチ問い合わせし、銘柄ごとの ai_score を ai_scores テーブルに書き込む処理を追加。
    - バッチサイズ制御（最大 20 銘柄）、トークン肥大化対策（記事数・文字数トリム）、JSON Mode 出力厳格検証、スコア ±1.0 クリップ、リトライ（指数バックオフ）を実装。
    - ニュース収集ウィンドウ（JST 基準→UTC 変換）ユーティリティ calc_news_window を追加。
- 管理ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用検証レポート生成ツールを追加（コマンドライン実行可能）。
    - 稼働率・注文成功率・送信率・P95 レイテンシ等の指標集計と PASS/FAIL 判定（閾値はファイル内定義）。
    - 日付フィルタ用の --from / --to / --db オプション対応、DB 存在チェック、SQLite の OperationalError に対するフォールトトレラントな扱い。
- DuckDB / SQLite の二重 DB 接続設計
  - 実行系・監視系で sqlite3（主にトランザクションログ・監視）と DuckDB（時系列・ファクタ計算）を併用する設計を導入。

### Changed
- なし（初回リリース）

### Fixed
- なし（初回リリース）

### Notes / Implementation details / Safety
- .env 自動ロードはプロジェクトルートが検出できない場合はスキップされるため、パッケージ配布後の環境でも安全に動作する。
- process priority / cpu affinity 設定は権限不足または未対応 OS では警告を記録してスキップするフェイルセーフ実装。
- Paper Trading モードでは producción DB と明確に分離された paper_trading.db を使用することで実運用への影響を防止。
- AI スコアリングは API キーの未設定で ValueError を返す（明示的なエラー）。API 呼び出しの失敗はリトライ後に失敗しても他処理の継続を保証するフェイルセーフ設計。
- Position sizing / sector cap 等は価格欠損（0 や None）に対する注意喚起コメントや TODO を含む（将来的なフォールバック価格の導入を想定）。

### Security
- 外部 API（OpenAI）利用部分は API キーが必要。秘匿情報は .env / 環境変数で管理することを推奨。

---

今後のリリース予定例:
- ユニットテスト整備・CI 導入、カバレッジ向上
- broker クライアントの実装拡張（kabu API 実装、Mock の拡張）
- 価格欠損時のフォールバック価格導入（前日終値など）
- パフォーマンス最適化（DuckDB クエリ、バッチ処理）
- ドキュメント（API リファレンス、設計ドキュメント）の整備

（必要であれば、各ファイル単位の変更点や補足説明を追加します。）