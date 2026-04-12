# Keep a Changelog

すべての重要な変更をこのファイルに記載します。  
フォーマットは Keep a Changelog に準拠します。

## [Unreleased]

- 実装済み機能の改善・追加予定事項やマイナー修正をここに記載してください。

---

## [0.1.0] - 2026-04-12

初回リリース。以下の主要機能・モジュールを実装しています。

### 追加 (Added)

- 全体
  - パッケージ初期版を公開（バージョン `0.1.0`）。
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。

- 実行・監視
  - 起動スクリプト
    - run_execution.py
      - ExecutionEngine 起動スクリプトを追加。プロセス優先度を高に設定して起動。
      - 環境 `KABUSYS_ENV=paper_trading` の場合、paper_trading 用の専用 SQLite DB (`PAPER_TRADING_SQLITE_PATH` / default: `data/paper_trading.db`) を使用して本番 DB と分離。
      - BrokerClientFactory を介してブローカークライアントを生成し、OrderRepository / OrderManager / RiskManager / Reconciler を組み合わせて ExecutionEngine を起動。
      - RiskManager に対するデフォルト構成値（max_position_pct, max_utilization, rate_limit_per_sec 等）を設定。
    - run_monitoring.py
      - SystemMonitor ポーリングループ起動スクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を変更可能（デフォルト 60 秒）。
      - 監視（monitoring）処理は KABUSYS_ENV に依存せず本番用 sqlite_path を使用する設計。
      - プロセス優先度を高に設定してから監視ループを開始。
  - 監視 DB 初期化
    - monitoring 用テーブルの冪等初期化を行う `init_monitoring_db` 呼び出しを起動時に実行（監視テーブルが存在しない場合に作成）。

- 設定・環境読み込み
  - config.py
    - .env 自動ロード機能を実装（プロジェクトルート検出: `.git` または `pyproject.toml` を探索）。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - `.env` / `.env.local` の読み込み順序と上書きルール（OS 環境変数は保護）を実装。
    - `.env` パースの細かな振る舞いをサポート:
      - `export KEY=val` 形式を認識。
      - シングル/ダブルクォート内でのバックスラッシュエスケープ対応。
      - インラインコメント処理（クォートなしの場合は `#` の直前に空白があるとコメントとして扱う等）。
    - Settings クラスを実装し、環境変数から各種設定を取得するプロパティを提供（例: `duckdb_path`, `sqlite_path`, `paper_sqlite_path`, `pid_file_path`, 各種しきい値、`env` / `is_live` / `is_paper` など）。
    - `paper_fill_mode` の検証（有効値: "instant" | "partial" | "never" | "reject"）を実装。

- ユーティリティ
  - utils/process_priority.py
    - プロセス優先度と CPU affinity 設定ユーティリティを追加。
    - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収する実装。優先度レベルは `"high"|"normal"|"low"`。
    - 権限不足や未サポート環境では安全にスキップして警告を記録。

- ポートフォリオ構築
  - portfolio/portfolio_builder.py
    - 候補選定 (`select_candidates`) — スコア降順、同点は signal_rank 昇順でタイブレーク。
    - 重み算出: `calc_equal_weights`, `calc_score_weights`（全スコアが 0 の場合は等金額にフォールバックし WARNING を出力）。
  - portfolio/risk_adjustment.py
    - セクター集中制限 (`apply_sector_cap`) — 既存保有をセクター別に集計し、上限超過セクターの新規候補を除外。`unknown` セクターは制限対象外。
    - 市場レジームに応じた投下資金乗数 (`calc_regime_multiplier`) — `"bull":1.0`, `"neutral":0.7`, `"bear":0.3`。未知のレジームは 1.0 にフォールバックして警告。
    - 既存ポジション評価時の価格欠損に対する注意（将来的なフォールバック価格の TODO コメントあり）。
  - portfolio/position_sizing.py
    - 株数決定ロジック (`calc_position_sizes`) を実装:
      - アロケーション方式: `"risk_based"`, `"equal"`, `"score"` をサポート。
      - lot_size（単元株）の考慮、max_position_pct、max_utilization、cost_buffer による保守的見積り、aggregate cap（利用可能現金を超える場合のスケーリング）を実装。
      - スケールダウン時の端数処理（lot_size 単位）と残余キャッシュを使った再配分アルゴリズム。

- 研究 (Research)
  - research/factor_research.py
    - Momentum / Volatility / Value ファクター計算を実装:
      - mom_1m/3m/6m、MA200乖離、ATR20、ATR比率、20日平均出来高、volume_ratio、PER/ROE 等。
      - DuckDB を利用した SQL ベースの計算。データ不足時は None を返す設計。
  - research/feature_exploration.py
    - 将来リターン計算 (`calc_forward_returns`)、IC（Spearman）計算 (`calc_ic`)、ファクター統計サマリー (`factor_summary`)、ランク付け (`rank`) を実装。
    - 外部依存を持たず標準ライブラリのみで実装。
  - research/__init__.py
    - 主要関数をパブリック API としてエクスポート。

- ツール
  - tools/paper_verification_report.py
    - Paper Trading の検証レポート生成スクリプトを追加。
    - 稼働率、注文成功率、送信率、P95 レイテンシなどを計算し PASS/FAIL を判定するレポートを標準出力へ出力。
    - コマンドライン引数 `--from` / `--to` / `--db` をサポート。デフォルト DB は `data/paper_trading.db`。
    - 指標の閾値（稼働率 99%、成立率 90%、送信率 95%、P95 レイテンシ 200ms）を設定。

- AI / NLP
  - ai/news_nlp.py
    - raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄別センチメントスコアを ai_scores テーブルへ書き込む処理を追加。
    - バッチサイズ、チャンク単位処理、トークン肥大化対策（1銘柄あたり最大記事数 / 最大文字数）、リトライ（429 / タイムアウト / 5xx）、レスポンス検証、スコアの ±1.0 クリップ、部分失敗時の置換戦略（DELETE + INSERT で対象コードのみ更新）などを含む設計。
    - ニュース収集ウィンドウの計算ユーティリティ (`calc_news_window`) を実装（JST 時間帯を UTC に変換）。
    - OpenAI API キー解決ロジック（引数 > 環境変数 OPENAI_API_KEY）を実装。
    - フェイルセーフ設計: API 失敗時はスキップして処理継続。

### 変更 (Changed)

- なし（初回リリースのため既存コードの大規模変更はありません）。

### 修正 (Fixed)

- なし（初回リリース）。コード内にエラーハンドリングや冗長チェックが組み込まれています（例: DB 接続の finally でのクローズ、OpenAI キー未設定チェック、psutil の例外キャッチ等）。

### 既知の問題 / 制限 (Known issues / Limitations)

- apply_sector_cap における価格欠損 (price == 0.0) によりエクスポージャーが過少見積りされる可能性があり、将来的なフォールバック価格採用が TODO。
- DuckDB の `executemany` に関するバージョン依存制約に注意（ai/news_nlp.py のコメントに記載）。
- news_nlp.py の実装は外部 API（OpenAI）依存のため、API 利用制限・料金・レート制限に注意が必要。
- process_priority / set_cpu_affinity は権限やプラットフォームに依存するため、設定に失敗した場合はワーニングを出してスキップする動作となる。
- run_monitoring/run_execution はログレベルや詳細な起動オプションを増やす余地がある。

### セキュリティ (Security)

- 環境変数・APIキーは環境変数や .env から読み込まれる。`.env` 自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD` で無効化可能。機密情報取り扱い時はこの点に注意してください。

---

必要に応じて、将来のリリースでは以下を追加予定:
- より詳細な CLI オプション（ログ設定・デバッグ・dry-run 等）
- 銘柄ごとの lot_size をマスタ化して position_sizing を拡張
- price フォールバックロジック（前日終値・取得原価の使用）
- news_nlp の部分再試行 / トランザクション性の強化

もし CHANGELOG の書式やリリース日、カテゴリ分けを変更したい場合は指示してください。