CHANGELOG
=========

すべての重要な変更は Keep a Changelog の形式に準拠して記載しています。
https://keepachangelog.com/ja/1.0.0/

[Unreleased]
-------------

（現在のスナップショットは 0.1.0 リリースに相当します。次回以降の変更はここに追記してください。）

0.1.0 - 2026-04-13
------------------

追加 (Added)
- 実行・監視の起動スクリプトを追加
  - run_execution.py: ExecutionEngine を起動するエントリポイントを追加。KABUSYS_ENV=paper_trading 時は paper_trading 用の SQLite DB を使用し、MockBrokerClient が選択される設計になっている。
  - run_monitoring.py: SystemMonitor のポーリングループを起動するスクリプトを追加。MONITOR_POLL_INTERVAL 環境変数でポーリング間隔を上書き可能（デフォルト: 60秒）。監視は環境にかかわらず本番 sqlite_path を使用する旨の設計。

- 設定管理モジュールを追加（kabusys.config）
  - .env 自動ロード機能を導入（プロジェクトルートの .git または pyproject.toml を探索）。
  - .env/.env.local の読み込み順・上書きルールを実装（OS 環境変数保護機能あり）。
  - 複雑な .env 行のパース対応（export プレフィックス、クォート文字列、バックスラッシュエスケープ、インラインコメントの取り扱いなど）。
  - 設定値取得用の Settings クラスを提供。各種環境変数のデフォルト・バリデーション（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE など）を実装。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードの無効化が可能。

- ポートフォリオ構築関連（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルのソート（score 降順、同点は signal_rank）と上限選択。
    - calc_equal_weights / calc_score_weights: 等分配・スコア加重配分。スコア合計が 0 の場合に等分配へフォールバックして警告を出す。
  - risk_adjustment:
    - apply_sector_cap: セクター集中上限による候補フィルタ。売却予定銘柄を除外して評価可能。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear をサポート、未知レジームは 1.0 へフォールバック）。
  - position_sizing:
    - calc_position_sizes: allocation_method（"risk_based"/"equal"/"score"）に基づく発注株数計算。lot_size 単位丸め、per‑stock 上限、aggregate cap によるスケールダウン、cost_buffer を考慮した保守的なコスト見積り、残差処理による追加配分ロジックを実装。

- 研究・リサーチモジュール（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン・MA200 乖離率を DuckDB の prices_daily から計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER/ROE を算出（target_date 以前の最新財務データを取得）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで取得（horizons の検証あり）。
    - calc_ic / rank: スピアマンランク相関（IC）計算、ランク変換（同順位の平均ランク処理）を実装。
    - factor_summary: 各ファクター列の基本統計量（count/mean/std/min/max/median）を返す。

- AI ニュース NLP モジュール（kabusys.ai.news_nlp）
  - raw_news から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメントスコアを ai_scores テーブルへ書き込む処理を追加。
  - バッチサイズ、1 銘柄あたりの最大記事数／文字数上限、JST->UTC のニュース取得ウィンドウ計算（前日15:00〜当日08:30 JST に対応）を実装。
  - API 呼び出しはチャンク単位で行い、429/ネットワーク/5xx 等に対して指数バックオフのリトライを想定。レスポンスのバリデーション、スコアの ±1.0 クリッピング、部分成功時のテーブル置換（該当コードのみ削除→挿入）により安全性を確保。
  - OpenAI API キーは api_key 引数または OPENAI_API_KEY 環境変数から解決。未設定時は ValueError を送出。

- ユーティリティ（kabusys.utils）
  - process_priority モジュールを追加:
    - set_process_priority(level): Windows/POSIX 間の差分を吸収してプロセス優先度を設定。未対応 OS や権限不足時は警告を出してスキップ。
    - set_cpu_affinity(cpu_count): 指定コア数に対して CPU affinity を設定（例外時は警告でスキップ）。
  - start-up スクリプト（run_*）でプロセス優先度を "high" に設定する呼び出しを行うことで、デフォルトの運用優先度を確保。

- モニタリング & DB 初期化
  - init_monitoring_db を用いた監視テーブルの冪等な初期化処理を各起動スクリプトで実行。
  - DuckDB をリサーチ・AI 周りで利用する設計（duckdb_path 設定）。

- ツール（kabusys.tools.paper_verification_report）
  - Paper Trading 検証レポート生成スクリプトを追加。コマンドライン引数（--from/--to/--db）で期間・DB を指定可能。
  - 指標: 稼働率 (uptime)、注文成功率（fill_rate）、送信率（send_rate）、P95 レイテンシ等を集計して PASS/FAIL を判定する。閾値はソースコード内で定義（稼働率 >= 99%、fill_rate >= 90% 等）。
  - データ不足やテーブル未存在時のフォールトトレランスを備える（OperationalError をキャッチして N/A を返す）。

変更 (Changed)
- Settings クラスに多数のプロパティを追加し、環境変数のデフォルト値とバリデーションを明確化（例: DUCKDB_PATH, SQLITE_PATH, PAPER_TRADING_SQLITE_PATH, PID_FILE_PATH, 各種閾値）。
- .env ローダーの上書き仕様: .env は既存 OS 環境変数を上書きせず、.env.local は上書き可能（ただし OS 環境変数は保護）。自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で抑制可能。
- run_execution における paper_trading モードの DB 分離（paper_trading は data/paper_trading.db を使用）を明確化。

修正 (Fixed)
- 各モジュールにおいて、データ不足やゼロ除算等の安全弁を実装（例: score 合計が 0 の場合等）。
- process_priority / set_cpu_affinity はアクセス権限不足や非対応プラットフォームで失敗しても例外を上げず警告ログにとどめるよう堅牢化。

ドキュメント（Doc）
- 各モジュールに詳細な docstring を追加。設計方針・注意点（例: ルックアヘッドバイアス回避、DuckDB の executemany 制約等）を記載。

既知の制約 / 注意事項
- news_nlp の OpenAI 呼び出し周りは外部 API に依存するため、API リミットや料金に注意が必要。API キーの管理はユーザ側で行う。
- position_sizing の price 未取得（price <= 0）の場合はスキップされるため、価格取得の前処理（フォールバック価格など）の強化が将来的に必要。
- apply_sector_cap は "unknown" セクターを上限チェックから除外する設計（意図的な挙動）。
- run_monitoring は監視 DB に常に本番 sqlite_path を使用する（運用上の意図的仕様）。

開発メモ（実装上の設計）
- DuckDB を用いたローカル SQL 分析を中心に設計（prices_daily / raw_financials / raw_news 等のテーブル想定）。
- ほとんどの関数は副作用を伴わない純粋関数として実装（ポートフォリオ構築・計算ロジック等）。
- 再現性を重視したソート・ランク付けや丸め処理（例: rank() の round(v, 12) による ties の安定化）。

今後の予定（案）
- position_sizing の lot_size を銘柄別にサポートする拡張（stocks マスタに lot_size を持たせる）。
- price のフォールバックロジック追加（前日終値や取得原価など）によるエッジケース対処。
- news_nlp の部分失敗耐性をさらに強化するためのトランザクション的実装やリトライの詳細パラメータ調整。

--- 

注: 本 CHANGELOG はコードベースから推測して作成したものであり、実際のコミット履歴やリリースノートと完全には一致しない可能性があります。必要に応じて修正・補完してください。