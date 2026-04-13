# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog のフォーマットに従っています。  

現在のバージョン方針: セマンティックバージョニング（MAJOR.MINOR.PATCH）

## [Unreleased]

（保留中の変更はここに記載）

---

## [0.1.0] - 2026-04-13

初回リリース。自動売買システム「KabuSys」のコア機能群を追加しました。以下はコードベースから推測した主要な追加・修正点の要約です。

### 追加
- 基本パッケージとバージョン情報
  - パッケージ初期化とバージョン定義を追加。 (src/kabusys/__init__.py)

- 環境・設定管理
  - .env/.env.local 自動読み込み機能を実装。プロジェクトルートを .git / pyproject.toml で探索し、OS 環境変数を保護する仕組みを導入。export 形式やクォート、インラインコメント等を考慮した .env パーサを実装。 (src/kabusys/config.py)
  - Settings クラスに各種設定プロパティを実装（DB パス、API トークン、監視閾値、環境判定、paper_trading 用設定など）。値検証とデフォルト値を含む。

- 実行・監視ランナー
  - ExecutionEngine 起動スクリプトを追加。paper_trading 環境では専用の MockBroker と paper_trading DB を使用する。プロセス優先度を開始時に設定。 (src/kabusys/run_execution.py)
  - SystemMonitor のポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数で間隔を変更可能（不正値時はデフォルト 60 秒にフォールバック）。監視は環境に依らず本番 sqlite_path を使用する旨を明記。 (src/kabusys/run_monitoring.py)

- プロセス制御ユーティリティ
  - プロセス優先度（Windows の HIGH_PRIORITY_CLASS / POSIX の nice）設定ユーティリティを追加。CPU affinity を最初 N コアに固定する機能も提供。AccessDenied 等の例外を捕捉して安全にスキップ。 (src/kabusys/utils/process_priority.py)

- ポートフォリオ構築モジュール（純粋関数群）
  - 候補選定と重み計算: スコア順ソート、等金額配分、スコア加重配分（スコアが全て 0 の場合は等金額にフォールバック）。 (src/kabusys/portfolio/portfolio_builder.py)
  - セクター集中制限適用: 既存保有を考慮してセクター上限に抵触する銘柄を除外するロジック。売却予定銘柄の除外や "unknown" セクターの扱いも実装。 (src/kabusys/portfolio/risk_adjustment.py)
  - レジーム乗数: market regime に応じた投下資金乗数（bull/neutral/bear）を提供。未知のレジームは警告を出してフォールバック。 (src/kabusys/portfolio/risk_adjustment.py)
  - 株数決定ロジック: risk_based / equal / score の割当方式に対応。単元株丸め、最大ポジション比率、aggregate cap によるスケールダウン、残差再配分（lot 単位）などを実装。コストバッファも考慮。 (src/kabusys/portfolio/position_sizing.py)
  - portfolio パッケージのエクスポートを整備。 (src/kabusys/portfolio/__init__.py)

- リサーチ / ファクター計算
  - Momentum / Volatility / Value ファクター計算を実装。DuckDB 接続を受け prices_daily / raw_financials を参照してリターン・MA200乖離・ATR・出来高指標・PER/ROE などを算出。欠損データの扱い・ウィンドウ制約を考慮。 (src/kabusys/research/factor_research.py)
  - 特徴量探索機能: 将来リターン計算（任意ホライズン）、IC（Spearman ランク相関）計算、ファクター統計サマリ、ランク付けユーティリティを実装。外部ライブラリに依存せず純粋 Python 実装。 (src/kabusys/research/feature_exploration.py)
  - research パッケージのエクスポートを整備。 (src/kabusys/research/__init__.py)

- AI ニューススコアリング
  - raw_news を OpenAI API（gpt-4o-mini）でスコアリングし、ai_scores テーブルへ書き込むワークフローを追加。ターゲットウィンドウ定義（前日15:00 JST 〜 当日08:30 JST）、記事集約、チャンク（最大20銘柄）送信、429/5xx/ネットワークのリトライ（指数バックオフ）、レスポンス検証、±1.0 のクリップ、部分更新（DELETE→INSERT）による原子性配慮などを実装。APIキーの解決と未設定時のエラーも扱う。 (src/kabusys/ai/news_nlp.py)

- Paper Trading 検証ツール
  - paper_verification_report スクリプトを追加。SQLite の paper_trading DB を参照して稼働率、注文成功率、送信率、リスク却下数、レイテンシ（avg/max/P95）等を集計し、PASS/FAIL 判定（閾値付き）で標準出力レポートを生成。日付フィルタや DB パスの CLI オプションをサポート。 (src/kabusys/tools/paper_verification_report.py)

- DB ユーティリティ
  - monitoring 用 DB 初期化関数を利用する呼び出しを run_execution/run_monitoring に追加して、存在しないテーブルがあっても冪等に対応。 (src/kabusys/run_execution.py, src/kabusys/run_monitoring.py)

### 変更（実装上の注意）
- モニタリングは環境変数 KABUSYS_ENV にかかわらず本番 sqlite_path を使う設計（意図的な動作として明記）。 (src/kabusys/run_monitoring.py)
- Paper trading 環境は本番 DB と完全分離するため、実行時に paper_sqlite_path を優先。 (src/kabusys/run_execution.py)
- .env 解析は複雑なクォート・エスケープ・インラインコメント挙動に対応するよう拡張。OS 環境変数を保護するため、.env.local の上書きでも既存 OS 環境は上書きされない。 (src/kabusys/config.py)

### 修正 / 安全対策
- 環境変数 MONITOR_POLL_INTERVAL の不正値（0 や負値、非数）を検出してログ警告のうえデフォルト 60 秒にフォールバック。time.sleep に渡せない値を回避。 (src/kabusys/run_monitoring.py)
- process priority / cpu affinity 設定時に権限不足や未対応プラットフォームの場合は警告を出して安全にスキップ。 (src/kabusys/utils/process_priority.py)
- DuckDB/SQLite のクエリでテーブルが存在しない場合に備え、レポート系ツールは sqlite3.OperationalError を捕捉してデフォルト値にフォールバック。 (src/kabusys/tools/paper_verification_report.py)
- ニュースNLP の API 呼び出しは失敗時にスキップして処理を継続するフェイルセーフ設計。部分失敗時に既存スコアを保護する更新戦略を採用。 (src/kabusys/ai/news_nlp.py)

### ドキュメント / その他
- 各モジュールに詳細な docstring と使用例を追加。設計上の注記（将来の拡張や TODO、フォールバック戦略）をコード内コメントとして明記。

### 既知の制約 / TODO（コード中に記載）
- position_sizing: lot_size を銘柄別に対応する拡張が将来必要（現在は全銘柄共通単元を想定）。 (src/kabusys/portfolio/position_sizing.py)
- apply_sector_cap: price の欠損時にエクスポージャーが過少評価される可能性あり。前日終値や取得原価でのフォールバックを検討。 (src/kabusys/portfolio/risk_adjustment.py)
- news_nlp: 実行時の OpenAI レスポンスフォーマットの検証に依存するため、API 仕様変更時の互換性検証が必要。 (src/kabusys/ai/news_nlp.py)

---

この CHANGELOG はコードベースから推測した変更履歴です。実際のコミット履歴や設計意図に基づく詳細はリポジトリの履歴（git log 等）を参照してください。