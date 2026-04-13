# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
このリポジトリの最初のリリース（v0.1.0）に含まれる主要な機能・改善点・修正をコードベースから推測してまとめています。

## [Unreleased]

- （現在未リリースの変更はありません）

## [0.1.0] - 2026-04-13

### Added
- 基本アプリケーションパッケージを追加
  - パッケージメタ情報: kabusys.__version__ = "0.1.0" を導入。

- 実行用スクリプト
  - run_execution.py
    - ExecutionEngine の起動スクリプトを追加。
    - 起動時にプロセス優先度を High に設定。
    - KABUSYS_ENV が `paper_trading` の場合は専用の Paper Trading SQLite DB を使用（data/paper_trading.db をデフォルト）し、Mock ブローカークライアントを利用する仕組みを BrokerClientFactory 経由でサポート。
    - 実行に必要なコンポーネント（OrderRepository / OrderManager / RiskManager / Reconciler / ExecutionEngine）を組み立ててセッションを実行。
    - duckdb 接続（analytics 用）をサポート。

  - run_monitoring.py
    - SystemMonitor のポーリングループ起動スクリプトを追加。
    - 環境変数 MONITOR_POLL_INTERVAL によるポーリング間隔上書き（デフォルト 60 秒）。不正な値はデフォルトにフォールバックし、警告を出力。
    - 監視機能は環境（development/paper_trading/live）に関わらず本番 sqlite_path を使用する点を明記。
    - 監視ループ内で check_once() 実行時の例外を捕捉してログ出力し、次ポーリング継続するフェイルセーフを実装。

- 設定・環境変数管理
  - config.Settings クラスを追加・公開（settings インスタンスを提供）。
  - プロジェクトルート検出機能を導入（.git または pyproject.toml を基準に探索）。
  - .env / .env.local の自動ロードを実装（OS 環境変数は保護し、.env.local は上書き許可）。
  - export KEY=val 形式やクォート、インラインコメントのパースに対応した .env パーサを実装。
  - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - 各種設定プロパティを提供（J-Quants / kabu / LINE / DB パス / PID/KILL フラグ設定 / モニタ閾値 / 環境・ログレベル検証など）。
  - PAPER_FILL_MODE の検証（instant/partial/never/reject）を実装。
  - KABUSYS_ENV / LOG_LEVEL の許容値検証を実装（不正値は ValueError）。

- モニタリング DB 初期化
  - monitoring.monitoring_db.init_monitoring_db を呼んで監視用テーブルの存在を保証（冪等処理）。

- ポートフォリオ構築モジュール
  - portfolio.portfolio_builder
    - select_candidates: BUY シグナルをスコア降順＋タイブレークで選定。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア比率に基づく配分。全スコア 0 の場合は等配分へフォールバックし警告。

  - portfolio.risk_adjustment
    - apply_sector_cap: セクター集中制限を適用し、既存保有比率が閾値を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を返す（未知レジームは警告の上 1.0 にフォールバック）。

  - portfolio.position_sizing
    - calc_position_sizes: risk_based / equal / score の各配分方式を実装。
    - 単元株（lot_size）で丸め、1銘柄上限・aggregate cap（available_cash）を考慮してスケールダウンするロジックを導入。
    - cost_buffer による保守的コスト見積り、スケーリング時の残余配分アルゴリズム（端数評価と再配分）を実装。

- ユーティリティ
  - utils.process_priority
    - set_process_priority(level) を実装（Windows と POSIX を吸収）。
    - set_cpu_affinity(cpu_count) を実装 — カレントプロセスを最初の N コアに固定する機能。
    - 権限不足や未実装環境での安全なフォールバック（警告ログ）を実装。

- 研究・ファクター計算
  - research.factor_research
    - calc_momentum: mom_1m/3m/6m、ma200 乖離を DuckDB SQL で算出。
    - calc_volatility: ATR20、相対 ATR、20日平均売買代金、出来高比率を算出（欠損データ考慮）。
    - calc_value: 最新財務データと当日株価を組み合わせて PER / ROE を算出（raw_financials と prices_daily を参照）。

  - research.feature_exploration
    - calc_forward_returns: 将来リターン（複数ホライズン）を一括クエリで算出。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装（有効レコード数 3 未満で None）。
    - rank: 同順位は平均ランクとなる安定したランク関数（丸めによる ties 回避）。
    - factor_summary: count/mean/std/min/max/median を計算する統計ユーティリティを追加。

  - research パッケージは zscore_normalize を kabusys.data.stats から再エクスポート。

- AI ニュース NLP
  - ai.news_nlp
    - raw_news を OpenAI API（デフォルトモデル gpt-4o-mini）で銘柄単位にセンチメント採点し、ai_scores テーブルへ書き込むワークフローを実装。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）を calc_news_window で提供。
    - 記事の数・文字数上限（1銘柄あたり最大記事数・最大文字数）を設けてトークン肥大化を抑制。
    - 1 API 呼び出しで最大 20 銘柄のバッチ処理、JSON Mode 出力の厳密検証、スコアの ±1.0 でクリップ。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライを実装（上限回数あり）。
    - API キー指定（引数 または 環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
    - 部分失敗時に他コードの既存スコアを保護するため、書き込みは対象コードで絞って置換（DELETE → INSERT）する方針を採用。

- ツール
  - tools.paper_verification_report
    - Paper Trading の検証レポート生成 CLI を追加（python -m kabusys.tools.paper_verification_report）。
    - --from / --to / --db オプションをサポート。
    - システム稼働率、注文成功率（fill_rate）、送信率、P95 レイテンシ、リスク却下数などを集計して閾値（例: uptime 99% 等）に基づく PASS/FAIL 判定を行う。
    - DB が存在しない・テーブルが存在しない場合を考慮したエラーハンドリング。

### Changed
- モジュールの責務を明確化
  - 実行系（ExecutionEngine）と監視系（SystemMonitor / monitoring DB）は DB 接続・duckdb を受け取る形で分離し、分析用に DuckDB を利用する設計に統一。
  - Paper Trading モード時の DB を本番 DB と完全分離する実装で安全性を確保。

- .env 自動読み込みの挙動
  - プロジェクトルートが特定できない場合は自動ロードをスキップするように変更（配布後の動作を考慮）。
  - OS 環境変数を保護する protected set を用意し、.env.local で既存 OS 環境変数を誤って上書きしないようにした。

### Fixed
- 設定値の堅牢性向上
  - MONITOR_POLL_INTERVAL のパースで 0 以下や非整数入力に対してデフォルトへフォールバックし、警告ログを出すようにして time.sleep の ValueError を回避。
  - PAPER_FILL_MODE の不正値チェックを追加し、不正時は ValueError を投げるようにして誤設定を早期検出。
  - calc_score_weights: 全スコアが 0 の場合にゼロ除算を避け、等配分にフォールバックして警告するように実装。
  - research.feature_exploration.calc_ic など、データ不足（有効レコード数不足）時の None ハンドリングを適切に行うよう修正。
  - paper_verification_report のクエリでテーブルがない場合に OperationalError を捕捉してデフォルト値を返すなど、堅牢化を実施。

- プロセス設定の安全化
  - set_process_priority / set_cpu_affinity は権限不足や未サポート環境で失敗しても警告を出してスキップするようにし、起動失敗による致命的エラーを防止。

### Security
- OpenAI API キーの取り扱い
  - score_news は API キーが未設定の状態では明示的にエラー（ValueError）を送出する仕様にして、誤って未設定で API を叩くリスクを低減。

### Notes
- 監視（monitoring）は「環境にかかわらず本番 sqlite_path を使用する」点は重要な挙動です。運用上の意図的な設計かどうかをデプロイ方針に応じて再確認してください。
- 一部の処理（price の欠損時の取り扱いや lot_size 将来的拡張など）には TODO コメントが残されており、将来的な改善ポイントが明示されています。

---

（本 CHANGELOG は現在のソースコードの内容から推測して作成しています。実際のコミット履歴やリリースノートと差異がある場合は、適宜編集してください。）