# CHANGELOG

すべての重要な変更点をこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。  

## [Unreleased]

（なし）

## [0.1.0] - 2026-04-11

Added
- 基本リリース: KabuSys 初期実装を追加。
- 実行/監視ランナー
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV が `paper_trading` の場合は paper 用の SQLite（デフォルト: `data/paper_trading.db`）を使用し、本番 DB と分離。
    - BrokerClientFactory を利用してブローカークライアントを生成。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine を起動するエントリポイントを提供。
    - 起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 `MONITOR_POLL_INTERVAL` でポーリング間隔を上書き可能（デフォルト: 60 秒）。不正値（0 以下や非整数）はデフォルトへフォールバックして警告出力。
    - 監視は環境にかかわらず本番用の sqlite_path を使用する実装。
    - プロセス優先度を "high" に設定し、DuckDB と SQLite の接続管理、KeyboardInterrupt による整終了処理を実装。

- 設定・環境変数管理
  - config.py:
    - プロジェクトルート自動検出（`.git` または `pyproject.toml` を基準）を行い、ルートが見つかれば `.env` / `.env.local` をロードする自動読み込みを実装（`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能）。
    - `.env` パーサの堅牢化: `export ` プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理をサポート。
    - Settings クラスを導入し、各種環境変数をプロパティとして取得・検証。
      - 必須項目チェック（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`）。
      - `PAPER_FILL_MODE` のバリデーション（`instant|partial|never|reject`）。
      - DB パスのプロパティ（`DUCKDB_PATH`, `SQLITE_PATH`, `PAPER_TRADING_SQLITE_PATH` 等）。
      - 監視・閾値設定（PID/kill flag パス、CPU/メモリ/ディスク閾値）。
      - `KABUSYS_ENV` と `LOG_LEVEL` の許容値検査およびユーティリティプロパティ（`is_live`, `is_paper`, `is_dev`）。

- ポートフォリオ構築ロジック
  - portfolio/portfolio_builder.py:
    - シグナル候補選定 (`select_candidates`) と重み計算 (`calc_equal_weights`, `calc_score_weights`) を提供。
    - スコア合計が 0 の場合は等配分にフォールバックして警告出力。
  - portfolio/risk_adjustment.py:
    - セクター集中制限 (`apply_sector_cap`) を実装。既存保有をセクター別に評価し、上限超過セクターから新規候補を除外。
    - レジーム乗数 (`calc_regime_multiplier`) を実装（`bull=1.0`, `neutral=0.7`, `bear=0.3`、未知は 1.0 にフォールバックして警告）。
    - 一部のケース（price 欠損時）に関する注意点をコメントで明記。
  - portfolio/position_sizing.py:
    - ポジションサイズ計算 (`calc_position_sizes`) を実装。`risk_based` と `equal`/`score` の両方式に対応。
    - 単元（lot_size）丸め、1銘柄上限、aggregate cap（available_cash を超える場合のスケールダウン）、cost_buffer を用いた保守的なコスト見積りを実装。
    - スケールダウン後の残余キャッシュを用いて残差順に lot 単位で追加配分するロジックを実装。
    - 将来的な拡張（銘柄別 lot_size）に関する TODO を残す。

- ユーティリティ
  - utils/process_priority.py:
    - プロセス優先度設定と CPU affinity 設定をクロスプラットフォームで実装（psutil を利用）。
    - Windows / POSIX (Linux/Mac/FreeBSD) における差分を吸収し、アクセス権限不足や未対応 OS の場合は警告を出してスキップ。
    - `set_cpu_affinity` で最初 N コアに固定するユーティリティを追加。

- リサーチ / ファクター計算
  - research/factor_research.py:
    - モメンタム（1M/3M/6M、MA200乖離）、ボラティリティ（ATR20 等）、バリュー（PER/ROE）ファクター算出関数を追加。DuckDB の SQL ウィンドウ関数を活用し高速に集計する設計。
    - データ不足時に None を返すなど堅牢化。
  - research/feature_exploration.py:
    - 将来リターン計算（複数ホライズンをサポート）、Spearman ランク相関による IC 計算、ファクター統計サマリー、ランク化ユーティリティを追加。
    - 外部依存（pandas 等）を使わず標準ライブラリのみで実装。
  - research/__init__.py で主要 API を公開。

- ツール
  - tools/paper_verification_report.py:
    - Paper Trading 用の検証レポート生成スクリプトを追加。
    - 稼働率・注文成功率・送信率・P95 レイテンシなどを算出して PASS/FAIL 判定を行う。
    - CLI オプション `--from` / `--to` / `--db` をサポート。デフォルト DB は `data/paper_trading.db`。
    - P95 の計算・各種 SQL クエリの実装と出力フォーマットを提供。
    - 閾値はファイル先頭の定数で定義（稼働率 99%、成立率 90%、送信率 95%、P95 200ms）。

- AI ニュース NLP
  - ai/news_nlp.py:
    - raw_news を OpenAI（デフォルトモデル: `gpt-4o-mini`）でセンチメントスコア化し、ai_scores テーブルへ書き込む処理を実装（バッチ処理、JSON Mode 期待）。
    - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）を計算するユーティリティ。
    - 1 チャンクあたり最大 20 銘柄、1銘柄当たり最大記事数/文字数制限、429/ネットワーク/5xx に対する指数バックオフリトライ、結果検証、スコアの ±1.0 クリッピング等を設計。
    - API キーの解決（引数または環境変数 `OPENAI_API_KEY`）と未設定時の ValueError を実装。
    - （注）ファイル末尾で書き込み処理の流れが実装されており、部分失敗時に既存スコアを保護する戦略（対象コードに限定した DELETE→INSERT）を採用。

Changed
- パッケージメタ
  - __init__.py にパッケージ名と初期バージョン `0.1.0` を追加。

Fixed
- 環境変数読み込みや数値変換周りでの堅牢性向上
  - MONITOR_POLL_INTERVAL や PAPER_FILL_MODE の検証を追加し、不正値に対してフォールバックまたは例外を発生させることで早期検出を実現。

Notes / Known limitations
- 一部のコメントにあるように、apply_sector_cap は price 欠損時にエクスポージャーが過小評価される可能性があり、将来的に前日終値等のフォールバックを検討する必要がある。
- position_sizing の将来的拡張点として銘柄別の lot_size を持たせる可能性がコメントで示されている。
- news_nlp の API 実行部分は外部サービス依存のため、API キーや呼量制限に起因する運用上の配慮が必要。
- DuckDB / SQLite 接続は起動スクリプト側で明示的にクローズする実装だが、長時間運用時の接続監視・リカバリやトランザクション設計は将来の改善対象。

参考
- 自動環境読み込みはプロジェクトルート検出に成功した場合のみ行われ、OS の既存環境変数はデフォルトで保護される（.env.local は上書き可能だが OS 環境は protected）。
- ログレベルや環境変数の許容値チェックにより、誤設定に対する早期警告が出力される設計。

---

この CHANGELOG は現行コードベースの実装内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合があります。必要であれば日付やカテゴリ分けの調整、個々のコミットメッセージに基づく詳細化を行います。