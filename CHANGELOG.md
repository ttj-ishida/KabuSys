# Changelog

すべての注記は Keep a Changelog の形式に準拠します。  
日付はコードベースから推測できるタイムスタンプに合わせて付与しています。

全般的な注意
- 本ドキュメントはリポジトリ内のソースコードから実装内容を推測して作成しています。実際のリリースノートやコミット履歴と異なる場合があります。

## [Unreleased]
- （現時点のコードはバージョン `0.1.0` を含み、以降の変更は未リリース扱いです）

## [0.1.0] - 2026-04-17

### Added
- 基本パッケージ情報
  - パッケージメタ情報として `kabusys.__version__ = "0.1.0"` を追加。

- 環境設定・ロード機能（kabusys.config）
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git / pyproject.toml）。
  - .env / .env.local の読み込み順をサポートし、OS 環境変数を保護する仕組みを導入。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - .env パーサーの強化:
    - `export KEY=val` 形式対応
    - シングル/ダブルクォート、バックスラッシュエスケープのハンドリング
    - インラインコメントの取り扱い（クォート有無による挙動差）
  - Settings クラスを実装し、各種設定値（API トークン、DB パス、監視閾値、環境種別など）をプロパティ経由で取得。入力値のバリデーションを実施。
  - Paper Trading 用 DB パス・fill モード等の設定（PAPER_TRADING_SQLITE_PATH / PAPER_FILL_MODE 等）を追加。

- 実行/監視ランナー
  - run_execution.py:
    - ExecutionEngine の起動エントリポイントを実装。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 DB を使用して本番 DB と完全分離。
    - BrokerClientFactory によるブローカークライアント生成、OrderRepository / OrderManager / RiskManager / Reconciler の組み立て、Engine のスレッド起動・停止監視を実装。
    - 起動前に data/stop_requested.flag の存在をチェックして起動を抑止する仕組みを実装。
    - 実行用 PID ファイル（data/execution.pid）を取り扱う仕組みを用意。
  - run_monitoring.py:
    - SystemMonitor のポーリングループ起動エントリポイントを実装。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒、0 以下は無効扱いしてデフォルトにフォールバック）。
    - 監視は環境にかかわらず本番の sqlite_path を使用して監視テーブルを初期化・更新。
    - 停止フラグ（data/stop_requested.flag）を検知して安全にループを終了する挙動を実装。

- 監視 DB 初期化フック（monitoring.monitoring_db を通す初期化呼び出し）
  - run_execution/run_monitoring から DB に監視テーブルが存在するよう冪等に初期化する処理を呼び出す。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - シグナルから候補銘柄を選択する select_candidates を実装（スコア降順、タイブレークは signal_rank）。
    - 等金額配分 calc_equal_weights、スコア加重配分 calc_score_weights を実装（全スコアが 0 の場合は等分にフォールバック）。
  - risk_adjustment:
    - セクター集中上限を考慮する apply_sector_cap を実装（既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外。unknown セクターは除外対象外）。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear に対する乗数を定義、未知レジームはフォールバックと警告）。
  - position_sizing:
    - 各銘柄の発注株数を計算する calc_position_sizes を実装。
    - allocation_method = "risk_based" / "equal" / "score" をサポート。
    - 単元株（lot_size）丸め、1 銘柄上限（max_position_pct）、投下資金上限（max_utilization）を考慮。
    - aggregate cap を超えた場合のスケールダウンロジック（端数の再配分を含む）を実装。
    - price が欠損する場合のスキップや cost_buffer による保守的見積り対応を実装。

- リサーチ（kabusys.research）
  - factor_research:
    - モメンタム calc_momentum（1M/3M/6M リターン、MA200 乖離）を実装。必要サンプルが不足する場合は None を返す。
    - ボラティリティ calc_volatility（ATR20、ATR%, 20日平均売買代金、出来高比）を実装。
    - バリュー calc_value（PER/ROE）を実装。raw_financials から target_date 以前の最新財務データを取得。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意ホライズン）を実装。入力の妥当性チェックあり。
    - スピアマンランク相関による IC 計算 calc_ic、ランク変換ユーティリティ rank、ファクター統計量 factor_summary を実装。
  - research パッケージの __all__ に主要 API をエクスポート。

- ニュース NLP スコアリング（kabusys.ai.news_nlp）
  - raw_news / news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込むロジックを実装。
  - 処理フロー:
    - JST 時間窓（前日 15:00 ～ 当日 08:30）を UTC に変換して対象記事を選択。
    - 銘柄あたりの記事数・文字数上限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。
    - 最大バッチサイズ（_BATCH_SIZE=20）で API へ送信し、JSON 出力を期待してパース。
    - 429/ネットワーク/タイムアウト/5xx に対して指数バックオフ付きリトライを実装（上限 _MAX_RETRIES）。
    - レスポンス検証、スコアを ±1.0 にクリップ。
    - 部分失敗時に既存スコアを保護するため、対象コードだけを削除→挿入する手法で更新。
  - OpenAI API キーが未設定の場合は ValueError を送出。

- CLI ユーティリティ
  - tools.paper_verification_report:
    - Paper Trading の検証レポート生成スクリプトを追加（コマンドライン実行可能）。
    - 集計指標: 稼働率、注文成功率（Filled/Created）、送信率（Sent/Created）、リスク却下数、API レイテンシ（avg/max/P95）。
    - デフォルト DB パスは data/paper_trading.db。引数で期間（--from / --to）および DB パス（--db）を指定可能。
    - Pass/Fail 基準を定義（稼働率 >=99%、注文成功率 >=90%、送信率 >=95%、P95 レイテンシ <=200ms）。

- プロセス制御ユーティリティ（kabusys.utils.process_priority）
  - set_process_priority(level) を実装（Windows / POSIX の差分を吸収して nice / priority を設定、失敗時は警告でスキップ）。
  - set_cpu_affinity(cpu_count) を実装（最初の N コアにピン固定、失敗時は警告でスキップ）。
  - run_monitoring/run_execution 起動時にデフォルトでプロセス優先度を "high" に設定する呼び出しを追加。

### Changed
- DB の取り扱いに関する方針を明確化
  - 監視（monitoring）は環境にかかわらず production sqlite_path を利用（monitoring DB は本番 DB を参照/更新する方針）。
  - 実行エンジンは paper_trading 環境時に paper_trading 専用 DB を使い、本番と分離する。

- 設定値のバリデーション強化
  - PAPER_FILL_MODE、KABUSYS_ENV、LOG_LEVEL 等に対して有効値チェックを追加し、無効値時は ValueError を送出。

- ログ出力レベルと起動時メッセージ
  - run_* スクリプトは起動時に logging.basicConfig(level=logging.INFO) をセットし、KABUSYS_ENV の情報やポーリング間隔などを INFO レベルで出力するようにした。

### Fixed
- 環境値の不正入力や欠損に対する堅牢性を改善
  - MONITOR_POLL_INTERVAL が不正（非数や 0 以下）な場合にデフォルトへフォールバックし、警告ログを出力。
  - .env 読み込みでファイルアクセス失敗時に警告（warnings.warn）で処理を継続。
  - process_priority/set_cpu_affinity はアクセス不可や未実装 API で例外が出ても警告でスキップするよう安全化。

### Security
- API キーの取り扱い
  - OpenAI API キー、J-Quants / kabu ステーションの認証情報は Settings 経由で取得し、未設定時は明示的にエラーを出す（故意の無設定を厳格に扱うことで誤った運用を防止）。
  - .env 自動ロードで OS 環境変数を上書きしないデフォルト挙動、さらに protected set を用意することで既存のプロセス環境を保護。

### Internal / Notes
- 多くの関数は DB（DuckDB / SQLite）や外部 API を受け取る設計になっており、テスト時にモック可能な設計を意図している（Dependency Injection 的設計）。
- 一部関数に TODO や拡張予定メモ（例: price 欠損時のフォールバック、lot_size の銘柄別拡張など）が含まれており、将来の拡張ポイントが明示されている。
- ニュース NLP の出力は厳密な JSON を期待する設計（出力検証・バリデーションを実施）。

---

もし特定のファイルや機能（例: news_nlp の未完成箇所、ExecutionEngine の内部挙動、monitoring のテーブル定義など）について詳しい変更点・補足を出力してほしければ、対象ファイルや関数名を指定してください。