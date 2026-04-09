CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは "Keep a Changelog" に準拠しています。  

[Unreleased]
------------

- なし

[0.1.0] - 2026-04-09
-------------------

Added
- パッケージ初回リリース（kabusys 0.1.0）。
- パッケージメタ情報
  - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定。

- 設定・環境変数管理（src/kabusys/config.py）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - 自動ロードはプロジェクトルート（.git または pyproject.toml を探索）を基準に行うため、CWD に依存しない設計。
  - 読み込み順序: OS 環境変数 > .env.local > .env。 .env.local は .env を上書き可能。
  - OS 環境変数は保護され、.env/.env.local による上書きを防止（protected オプション）。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント（条件付き）に対応。
  - Settings クラスを提供し、アプリケーションの設定値をプロパティ経由で取得可能（settings = Settings()）。
  - 必須変数未設定時は _require() により ValueError を送出（例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD）。
  - 各種既定値・バリデーション:
    - KABUSYS_ENV 有効値: development / paper_trading / live（それ以外は ValueError）。
    - LOG_LEVEL 有効値: DEBUG/INFO/WARNING/ERROR/CRITICAL。
    - PAPER_FILL_MODE 有効値: instant/partial/never/reject（不正値で ValueError）。
    - 各種パス設定に対してデフォルト値と expanduser() を適用（例: DUCKDB_PATH, PID_FILE_PATH 等）。
    - リソース閾値（CPU/MEM/DISK）や監視フラグの取得をサポート。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順）でソートして上位 N を選択。
  - calc_equal_weights: 等金額配分（各銘柄 weight = 1/N）。
  - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等金額にフォールバックし WARNING ログを出力）。
  - apply_sector_cap: 既存保有のセクター別エクスポージャーを計算し、1 セクター上限を超過するセクターの新規候補を除外（"unknown" セクターは除外対象外）。
  - calc_regime_multiplier: 市場レジームに応じた投下資金乗数を返す（bull=1.0, neutral=0.7, bear=0.3）。未知レジームは警告ログを出して 1.0 にフォールバック。
  - calc_position_sizes:
    - allocation_method に "risk_based" / "equal" / "score" をサポート。
    - リスクベース算出（risk_pct, stop_loss_pct）や、per-position / aggregate cap の考慮。
    - 単元株（lot_size）で丸め、lot 単位での再配分ロジックを実装（端数分は残差順に追加配分）。
    - cost_buffer による手数料・スリッページの保守的見積りを採用。
    - 価格欠損時はログを出力してその銘柄をスキップ。

  - 上記機能はすべて純粋関数であり DB 参照を持たない（メモリ内計算）。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を DuckDB の prices_daily から算出。過不足データは None を返す実装。
  - calc_volatility: 20 日 ATR（true range の平均）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を算出。true_range の NULL 伝播を考慮した実装。
  - calc_value: raw_financials テーブルから target_date 以前の最新財務データを取得し PER（EPS が 0/NULL の場合 None）と ROE を計算。
  - calc_forward_returns: 指定 horizon（営業日）に対する将来リターン（複数ホライズンを一度のクエリで取得）。horizons のバリデーションあり（1..252）。
  - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
  - rank: 同順位を平均ランクで扱うランク計算。丸め誤差対策として round(..., 12) を使用。
  - factor_summary: count/mean/std/min/max/median を計算する統計サマリユーティリティ。
  - これらは DuckDB 接続を引数に取り、prices_daily / raw_financials のみ参照する設計（外部 API へはアクセスしない）。

  - research パッケージは zscore_normalize（kabusys.data.stats から）を含む公開 API をエクスポート。

- AI / ニュース NLP（src/kabusys/ai/news_nlp.py）
  - raw_news を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し、ai_scores テーブルへ書き込む機能を実装（score_news）。
  - ニュース収集ウィンドウ: target_date の前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB クエリに使用）。
  - 1 銘柄あたり最大記事数・最大文字数のトリム（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）。
  - 最大 20 銘柄ごとのバッチ送信（_BATCH_SIZE）。
  - API 呼び出しは JSON Mode を利用し、レスポンスの厳密な JSON パースとバリデーションを実施（results リスト、code と score を検証）。
  - レート制限 (429)、ネットワーク・タイムアウト、5xx は指数バックオフでリトライ（最大回数 _MAX_RETRIES）。その他エラーはフェイルセーフにより該当チャンクをスキップ。
  - スコアは ±1.0 にクリップ。LLM の整数コード応答等を吸収するため code を文字列化して照合。
  - DB 書き込みは部分更新（DELETE（個別）→ INSERT の組合せ、DuckDB executemany の互換性を考慮）で、部分失敗時にも既存スコアを保護。
  - OPENAI API キー未設定時は ValueError を送出（api_key 引数または環境変数 OPENAI_API_KEY）。
  - テスト容易性を考慮し、_call_openai_api を patch で差し替え可能。

- AI / レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動型）200 日 MA 乖離（ma200_ratio）とマクロニュース LLM センチメントを合成して日次の market_regime を算出（score_regime）。
  - 合成式: clip(0.7 * (ma200_ratio - 1) * 10 + 0.3 * macro_sentiment, -1, 1)。閾値で bull/neutral/bear を決定（BULL_THRESHOLD / BEAR_THRESHOLD）。
  - マクロニュースはキーワードベースで raw_news のタイトルを抽出（最大 20 件）。記事がない場合は LLM を呼ばず macro_sentiment=0.0。
  - LLM 呼び出しのリトライ・エラーハンドリングは news_nlp と同様。API エラー時は macro_sentiment=0.0 にフォールバック（例外は投げない）。
  - 1321 のデータ不足や行数不足時は ma200_ratio を 1.0（中立）にフォールバックして警告ログを出力。
  - DB 書き込みは冪等に行う（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）。失敗時は ROLLBACK を試みる。

- パッケージ公開 API の整理
  - src/kabusys/portfolio/__init__.py で主要関数をトップレベルにエクスポート。
  - src/kabusys/research/__init__.py で主要リサーチ関数と zscore_normalize をエクスポート。
  - src/kabusys/ai/__init__.py で score_news をエクスポート。

- 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
  - SQLite を用いた監視ログ層を実装。
  - init_monitoring_db(conn) により冪等にテーブル/インデックスを作成:
    - system_status（CPU/メモリ/ディスク/プロセス状態）
    - trade_logs（発注／約定ログ）
    - positions（ポジション保有）
    - risk_logs（リスクイベントログ） 等（複数テーブルとインデックスを作成）

Notes / Known limitations
- DuckDB / SQLite に依存するクエリ実行時の互換性やバインド挙動（特に executemany に空リストを渡せない等）に注意して設計している。
- news_nlp と regime_detector は OpenAI API の挙動やレスポンス形式に依存するため、モデル側の挙動変化によりパースや検証ロジックの追加調整が必要になる可能性がある。
- position_sizing の価格欠損時（price=0.0）はエクスポージャー過小見積りやスキップを招くため、将来的に価格フォールバック（前日終値や取得原価など）を追加する余地がある旨コメントとして残している。
- 一部関数はログ出力に依存しており、ユニットテストでは適切にログレベルを設定する必要がある。

Security
- OpenAI API キー等の機密値は環境変数で管理する前提（.env ファイル読み込みは任意だが、OS 環境変数が優先され保護される挙動を採用）。

References
- 各モジュール内に設計方針や参照ドキュメント（例: PortfolioConstruction.md, StrategyModel.md）への言及があり、実装はそれらに則っている旨のコメントを含む。

------------------------------------------------------------
今後のリリースでは以下を検討中:
- 単元株サイズを銘柄ごとに管理するための拡張（lot_map）。
- position_sizing の価格フォールバック戦略（前日終値等）。
- news_nlp / regime_detector のレスポンス検証強化とテストカバレッジ拡充。