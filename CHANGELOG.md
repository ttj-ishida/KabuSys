CHANGELOG
=========

すべての注目すべき変更をこのファイルに記録します。  
フォーマットは "Keep a Changelog" に準拠します。  
リリース日付はコードベースから推測して記載しています。

フォーマット詳細: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在未リリースの変更はここに記載します）

[0.1.0] - 2026-04-12
-------------------

追加 (Added)
- 全体
  - 初期公開リリース。本リポジトリは日本株自動売買システム「KabuSys」の基礎機能群を提供。
  - パッケージメタ情報: バージョン __version__ = 0.1.0 を設定。

- 設定 / 環境読み込み (kabusys.config)
  - .env / .env.local の自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索。
  - .env のパースを堅牢化:
    - export KEY=val 形式対応
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理対応
    - クォート無し行のインラインコメント取り扱いルールを導入
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを導入し、環境依存設定をプロパティ経由で取得可能に（各種 API トークン、DB パス、監視閾値、実行環境判定など）。
  - PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL 等の値検証を追加。

- 実行入口スクリプト
  - run_execution.py: ExecutionEngine 起動スクリプトを追加。
    - KABUSYS_ENV=paper_trading 時は paper_trading 専用 SQLite DB（data/paper_trading.db をデフォルト）を使用し、本番 DB と完全分離する挙動を実装。
    - BrokerClientFactory を用いてブローカークライアントを生成。
    - OrderRepository, OrderManager, RiskManager (RiskConfig)、Reconciler を組み立て ExecutionEngine を起動。
    - プロセス起動時にプロセス優先度を "high" に設定。
  - run_monitoring.py: SystemMonitor のポーリングループ起動スクリプトを追加。
    - MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト 60 秒）。
    - 監視は KABUSYS_ENV にかかわらず本番 sqlite_path を使用して記録（監視データは本番 DB を参照する設計）。
    - プロセス優先度を "high" に設定してから開始。

- 監視 DB 初期化
  - monitoring_db.init_monitoring_db を用いて、起動時に監視用テーブルの存在を保証（冪等）。

- ポートフォリオ構築 (kabusys.portfolio)
  - portfolio_builder:
    - シグナル選定 (select_candidates)、等金額・スコア加重 (calc_equal_weights, calc_score_weights) を実装。スコアが全て 0 の場合は等金額へフォールバック。
  - risk_adjustment:
    - セクター上限適用ロジック (apply_sector_cap) を実装。既存保有のセクター別時価を計算し、上限超過セクターの新規候補を除外。
    - 市場レジームに応じた乗数 calc_regime_multiplier を実装（bull/neutral/bear のマッピング、未知のレジームは警告を出して 1.0 にフォールバック）。
  - position_sizing:
    - allocation_method (risk_based / equal / score) に基づく株数算出（単元株丸め、1銘柄上限、aggregate cap、cost_buffer を考慮したスケーリング）を実装。
    - 投下資金超過時のスケールダウンと余剰の lot 単位での再配分アルゴリズムを実装。

- 研究（Research）モジュール (kabusys.research)
  - factor_research:
    - モメンタム (calc_momentum)、ボラティリティ (calc_volatility)、バリュー (calc_value) の各ファクター計算を実装。DuckDB の prices_daily / raw_financials を参照して計算。
    - 各種ウィンドウ長・欠損ハンドリングを設計（MA200 要件、ATR 欠損処理など）。
  - feature_exploration:
    - 将来リターン calc_forward_returns、IC（Spearman）計算 calc_ic、ファクター統計サマリ factor_summary、およびランク付けユーティリティ rank を実装。
    - pandas 等外部依存を用いず、標準ライブラリと DuckDB のみで実装。

- AI ニュース NLP (kabusys.ai.news_nlp)
  - raw_news を OpenAI（gpt-4o-mini）でスコアリングして ai_scores に書き込む処理を実装。
  - 処理フロー:
    - タイムウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）で記事を抽出。
    - 銘柄ごとの記事を集約し、1 銘柄あたり最大記事数 / 最大文字数でトリム。
    - 最大 20 銘柄ずつバッチ送信（JSON Mode）。429 / ネットワークエラー / 5xx 等は指数バックオフでリトライ。
    - レスポンス検証とスコアの ±1.0 クリップ。
    - 成功した銘柄のみ対象日に対して ai_scores テーブルを差し替え（部分失敗時に他銘柄を保護）。
  - API キー未指定時は環境変数 OPENAI_API_KEY を参照し、未設定時は ValueError を送出。

- ツール (kabusys.tools)
  - paper_verification_report:
    - Paper Trading 用の検証レポート生成スクリプトを追加。コマンドライン引数 --from / --to / --db をサポート。
    - 判定基準（稼働率、注文成功率、送信率、P95 レイテンシ）を定義し、DB（paper_trading.db）から集計して人間向けのレポート出力を行う。
    - P95 計算、各種 NULL/テーブル無存在時のフォールバック処理を実装。

- ユーティリティ (kabusys.utils)
  - process_priority:
    - set_process_priority(level) を実装。Windows (psutil の HIGH_PRIORITY_CLASS 等) と POSIX (nice 値) を吸収し、未対応 OS や権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count) を実装し、指定数のコアにピン留めする機能を追加（権限不足/未対応 OS では警告でスキップ）。

変更 (Changed)
- DB 周り
  - Execution エンジンは paper_trading 環境時に専用 SQLite を使用するよう分離（本番 DB と分離して安全にペーパートレードを行える設計）。
  - 監視(run_monitoring) は常に本番 sqlite_path を参照して監視データを記録（監視データを冗長に分離しない運用判断）。

- ログ / 起動順序
  - 起動スクリプトは最初にプロセス優先度を高く設定するように変更（set_process_priority("high") を起動直後に呼び出す）。

修正 (Fixed)
- 環境ファイル読み込みでの I/O エラーを warnings.warn で通知して処理を継続するように堅牢化。
- .env のキー/値解析で不正行を無視するようにし、誤った行でのクラッシュを回避。
- calc_score_weights: 全スコアが 0 の場合にゼロ除算する不具合を回避し、等金額配分へフォールバックして警告を出す。

パフォーマンス (Performance)
- Research モジュールのファクター計算は DuckDB のウィンドウ関数を多用しており、単一クエリで複数指標を計算して I/O を削減。

設計上の注記 (Notes)
- DuckDB 接続は研究・AI などの分析処理で利用する設計。prices_daily / raw_financials 等のテーブルを前提としている。
- OpenAI 呼び出しは外部 API 依存であるため、API キー管理やレート制御に注意が必要。失敗耐性は実装されているが、運用時は API 利用量とコスト管理が必要。
- position_sizing の価格欠損（price が 0.0 / None）の扱いについてコメントと TODO を残しており、将来的にフォールバック価格の導入を検討。

セキュリティ (Security)
- 環境変数の必須項目が未設定の場合は明示的に ValueError を発生させることで起動時に早期検出する設計。

今後の予定 (Future)
- 銘柄毎の lot_size を stocks マスタに持たせる拡張（position_sizing の TODO）。
- price 欠損時のフォールバック価格導入（前日終値・取得原価など）。
- AI スコアリングのより詳細なエラーハンドリングと監査ログの強化。
- テストカバレッジの追加（特に外部 API と DB 操作部分）。

--- 

注: 上記 CHANGELOG は与えられたコードから推測して作成しています。実際のリリース履歴や日付・バージョンはプロジェクトの正式な履歴に合わせて調整してください。