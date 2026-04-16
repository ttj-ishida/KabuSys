# CHANGELOG

すべての変更は「Keep a Changelog」に準拠します。  
以前のリリースとの互換性に関してはセクションごとの説明を参照してください。

## [0.1.0] - 2026-04-16
初期リリース。コードベースから推測される主要な機能追加・設計方針を記載します。

### 追加 (Added)
- 基本アプリケーション情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。

- 設定・環境変数管理（kabusys.config）
  - プロジェクトルート検出機能を実装（.git / pyproject.toml を探索）。
  - .env 自動ロード機能を実装（優先度: OS 環境変数 > .env.local > .env）。自動ロードは `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - .env のパースは export 形式、クォートされた値（バックスラッシュエスケープ対応）、コメント付き行をサポート。
  - 必須環境変数未設定時にエラーを投げる `_require()` を提供。
  - 多数の設定プロパティを提供（J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / 環境判定等）。
  - Paper Trading 用設定（`PAPER_TRADING_SQLITE_PATH`、`PAPER_FILL_MODE` の検証）を追加。

- 実行・監視スクリプト
  - 実行エンジン起動スクリプト（run_execution.py）
    - `KABUSYS_ENV=paper_trading` の場合、Paper Trading 用 SQLite DB を使用して本番 DB から分離（`settings.paper_sqlite_path`）。
    - ブローカークライアント生成を `BrokerClientFactory.create(settings)` で抽象化。
    - OrderRepository / OrderManager / RiskManager / Reconciler を組み立て、ExecutionEngine をスレッドで起動。停止フラグ検知で安全に停止処理を実行。
    - 実行プロセス用 PID ファイルパスを管理。
    - RiskManager に対するデフォルト構成（最大ポジション比率、利用率、レート制限、サーキットブレーカー等）を設定。初期資金はブローカーから取得。
  - 監視ループ起動スクリプト（run_monitoring.py）
    - プロセス優先度を最初に High に設定。
    - 監視は環境設定にかかわらず本番 sqlite_path を使用する旨の設計。
    - `MONITOR_POLL_INTERVAL` 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。不正値はデフォルトへフォールバック。
    - 停止フラグ（data/stop_requested.flag）検知によるループ終了、例外を捕捉して次ポーリングへ継続。
    - duckdb を併用して集計処理等を行えるように接続を確保。

- 監視 DB 初期化ユーティリティ
  - `init_monitoring_db` を通じて監視テーブル群の冪等な初期化を保証（監視/実行ともに呼び出し）。

- ユーティリティ（kabusys.utils.process_priority）
  - Windows / POSIX（Linux, Darwin, FreeBSD）を吸収するプロセス優先度設定ユーティリティ `set_process_priority(level)` を追加。
  - CPU アフィニティ固定 `set_cpu_affinity(cpu_count)` を提供。
  - 権限不足・未サポート環境では警告ログを出して安全にスキップする実装。

- ポートフォリオ構築（kabusys.portfolio）
  - 候補選定・重み計算（portfolio_builder.py）
    - `select_candidates`, `calc_equal_weights`, `calc_score_weights` を提供。
    - スコア降順・同点時の tie-break ロジックなどを実装。スコア全ゼロ時のフォールバック警告。
  - リスク調整（risk_adjustment.py）
    - セクター集中制限 `apply_sector_cap`（当日売却予定銘柄除外、"unknown" セクターの扱いなど）。
    - 市場レジームに応じた投下資金乗数 `calc_regime_multiplier`（bull/neutral/bear のマップとフォールバック挙動）。
  - ポジションサイジング（position_sizing.py）
    - `calc_position_sizes` による株数決定（risk_based / equal / score 方式）、単元株（lot_size）丸め、1銘柄上限、aggregate cap（利用可能現金に応じたスケールダウン）、cost_buffer による保守的見積り、残余キャッシュでの割当改善ロジックを実装。

- 研究機能（kabusys.research）
  - ファクター計算（research/factor_research.py）
    - Momentum（1M/3M/6M リターン、MA200 乖離）、ボラティリティ（ATR20、相対ATR、平均売買代金、出来高比率）、Value（PER、ROE）計算の実装。DuckDB を想定した SQL ベースの実装。
    - データ不足時の None 処理やウィンドウサイズ管理を実装。
  - 特徴量探索（research/feature_exploration.py）
    - 将来リターン計算（複数ホライズン対応）、IC（スピアマンランク相関）計算、ファクター統計サマリの実装。標準ライブラリのみでの統計実装、ランク処理における同順位の平均ランク処理を含む。
  - モジュールエクスポートを通じて z-score 正規化ユーティリティ等を結合。

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news テーブルから記事を集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメントスコアを算出して ai_scores テーブルへ書き込む仕組みを実装（スコアは ±1.0 にクリップ）。
  - バッチ送信（最大 20 銘柄）、トークン肥大対策（記事数・文字数トリム）、JSON モード厳格検証、429/ネットワーク/5xx などに対する指数バックオフリトライを実装。
  - ニュース収集ウィンドウ計算（JST 基準: 前日 15:00 〜 当日 08:30 を UTC に変換）を提供。
  - API キーの解決（引数または OPENAI_API_KEY 環境変数）と未設定時の ValueError。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading の検証レポート生成スクリプトを追加。
  - 検証指標:
    - 稼働率（uptime）閾値: 99.0%
    - 注文成功率（fill rate）閾値: 90.0%
    - 送信率（send rate）閾値: 95.0%
    - P95 レイテンシ閾値: 200 ms
  - CLI オプション: --from / --to（日付フィルタ）、--db（DB パス）。環境変数 `PAPER_TRADING_SQLITE_PATH` を考慮。
  - DB 存在チェック、テーブル存在に伴う例外ハンドリング、指標の Pass/Fail 判定と分かりやすいレポート出力。

- DuckDB を利用した分析インフラ
  - 研究 / AI / 集計処理に対して duckdb 接続を受け取り SQL を利用する方針を採用。

### 変更 (Changed)
- 監視・実行起動時にプロセス優先度を最初に設定する方針を採用（安定動作優先）。
- 監視ルーチンは stop flag（data/stop_requested.flag）で外部から安全に停止可能にした（監視・実行ともに同様の仕組みを採用）。

### 修正 (Fixed)
- .env パーサのクォート処理でバックスラッシュエスケープを考慮することで、引用符内の特殊文字を正しく扱うよう改善。
- .env コメントの解釈を改良（クォートなし値の '#' は直前がスペース/タブの場合のみコメントと扱う）して既存環境値との整合性を向上。

### 注意事項 (Notes)
- 監視（run_monitoring.py）はソース上の注釈にある通り、KABUSYS_ENV にかかわらず本番用 sqlite_path を用いる仕様です。Paper Trading の監視を完全に分離したい場合は設定値や起動スクリプトの調整が必要です。
- `PAPER_FILL_MODE` 等の環境変数は値検証があり、不正な値は ValueError を発生させます。
- process priority / cpu affinity の変更はプラットフォーム依存かつ権限が必要な場合があり、失敗時はログ警告の上スキップされます。
- AI モジュールは OpenAI API を用いるため、API キー管理と利用上のレート制限に注意してください。API 呼び出しの失敗はフェイルセーフ（スキップ継続）設計ですが、部分的な欠損が生じる可能性があります。
- DuckDB に対して executemany を行う前にパラメータが空でないことを確認する実装方針（DuckDB のバージョン依存の制約を回避）を採用しています。

今後の想定作業（未実装・改善予定の例）
- position_sizing の lot_size を銘柄別にサポートするための拡張（stocks マスタの導入）。
- price 欠損時のフォールバック（前日終値や取得原価）を導入してエクスポージャー算出を堅牢化。
- news_nlp の完全な実装とエラーハンドリング改善（ファイルは途中で切れている箇所あり、実装完了が必要）。

------------- 
（注）本 CHANGELOG は提示されたコード内容から推測して作成したものであり、実際のコミット履歴や意図とは異なる可能性があります。