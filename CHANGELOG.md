# Changelog

すべての変更は「Keep a Changelog」仕様に準拠します。バージョン番号はパッケージ内の __version__ に合わせています。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回公開リリース。

### Added
- 基本パッケージ情報
  - パッケージメタ情報を追加（src/kabusys/__init__.py, __version__ = "0.1.0"）。

- 環境変数・設定管理
  - .env ファイルや環境変数を読み込む設定モジュールを追加（src/kabusys/config.py）。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。プロジェクトルートは .git または pyproject.toml を基準に探索するため CWD に依存しない。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - エントリポイント Settings クラスを提供（settings）。下記の設定プロパティを提供：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN / LINE_USER_ID
    - DUCKDB_PATH / SQLITE_PATH / PAPER_TRADING_SQLITE_PATH
    - PAPER_FILL_MODE（入力検証: instant/partial/never/reject）
    - PID_FILE_PATH / KILL_FLAG_PATH / KILL_FLAG_CLEAR_ON_START
    - CPU_THRESHOLD_PCT / MEMORY_THRESHOLD_PCT / DISK_THRESHOLD_PCT
    - KABUSYS_ENV（検証: development/paper_trading/live）
    - LOG_LEVEL（検証: DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev ユーティリティプロパティ
  - .env パーサは export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、行内コメントなどに対応。OS 環境変数（読み込み時点のキー集合）は protected として .env.local による上書きから保護。

- ポートフォリオ構築（純粋関数群）
  - 銘柄選定
    - select_candidates: スコア降順・タイブレークを signal_rank で行い上位 N を選択（src/kabusys/portfolio/portfolio_builder.py）。
  - 配分重み
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア比率による配分。全スコアが 0 の場合は等金額にフォールバックし WARNING を出力。
  - ポジションサイズ計算
    - calc_position_sizes: risk_based / equal / score の allocation_method をサポートし、単元（lot_size）で丸め、ポートフォリオ／ポジション上限、aggregate cap、手数料・スリッページ用の cost_buffer を考慮したスケーリングを実装（src/kabusys/portfolio/position_sizing.py）。
    - raw_shares -> スケールダウン -> 残余キャッシュを fractional (lot) の残差順に割当てるアルゴリズムを実装。
    - lot_size の将来的な銘柄別拡張を想定した TODO コメントあり。
  - リスク調整
    - apply_sector_cap: 同一セクター集中上限(max_sector_pct)をチェックし、既存ポジションのセクター露出が上限を超える場合はそのセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: market regime（bull/neutral/bear）に応じた投下資金乗数を返す（未知レジームは警告を出して 1.0 でフォールバック）。
  - これら関数はすべてメモリ内計算・DB 参照なしで純粋関数として設計（テスト容易性を重視）。

- リサーチ / ファクター計算
  - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算（DuckDB を用いた SQL 実装、src/kabusys/research/factor_research.py）。
  - calc_volatility: 20日 ATR・相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。
  - calc_value: raw_financials から直近財務データを取得し PER / ROE を算出。
  - すべて prices_daily / raw_financials テーブルのみ参照し、外部 API に依存しない設計。

- 研究用ユーティリティ（feature_exploration）
  - calc_forward_returns: target_date の終値から複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得。
  - calc_ic: ファクターと将来リターンのスピアマン順位相関（IC）を計算。データが不十分な場合は None。
  - rank: 同順位は平均ランクを割り当てる実装。丸め誤差対策として round(v, 12) を比較に用いる。
  - factor_summary: count/mean/std/min/max/median を算出するシンプルな統計サマリー。
  - 依存は標準ライブラリと DuckDB のみ（pandas 等に依存しない）。

- AI（ニュース NLP / レジーム判定）
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - score_news: raw_news と news_symbols を集約し、OpenAI (gpt-4o-mini) を用いて各銘柄のセンチメント(ai_score) を ai_scores テーブルへ書き込み。
    - バッチ処理: 最大 _BATCH_SIZE=20 銘柄ごとに送信。1銘柄あたりの入力文字数制限・記事数制限を実装（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）。
    - API エラー処理: 429・ネットワーク断・タイムアウト・5xx を指数バックオフ付きでリトライ。その他の例外はスキップ（フェイルセーフ）。
    - レスポンス検証: JSON 抽出、"results" リスト形式、コード整合性、数値変換、スコアクリップ（±1.0）。
    - DB 書き込みは冪等に行い、部分失敗時でも既存スコアを不必要に消さない（対象コードのみ DELETE → INSERT）。
    - テスト用フック: _call_openai_api をパッチ差替え可能。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - score_regime: ETF 1321 の ma200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ書き込み。
    - マクロニュースは title ベースでキーワードフィルタ（_MACRO_KEYWORDS）し、最大件数で LLM に投げて macro_sentiment を取得。
    - API 失敗時は macro_sentiment=0.0 を使用（フェイルセーフ）。出力は regime_score を -1..1 にクリップしてラベル化（bull/neutral/bear）。
    - _call_openai_api は news_nlp のものと別実装で、モジュール間でプライベート関数を共有しない設計。
    - ルックアヘッドバイアス防止: date 未満のデータのみを使用する等の防止策を実装。

- モニタリング永続化層
  - SQLite を用いた監視ログ用 DB 初期化関数を追加（src/kabusys/monitoring/monitoring_db.py）。
  - system_status, trade_logs, positions, risk_logs 等のテーブルとインデックスを冪等に作成するスクリプトを実装。

- モジュールエクスポート
  - kabusys.portfolio、kabusys.research、kabusys.ai などで主要 API を __all__ により整理して公開。

### Changed
- 設計上の方針を明記（コードコメント）:
  - Research / Portfolio / AI モジュールで「ルックアヘッドバイアス防止」「DB のみ参照」「外部発注 API にアクセスしない」等の方針を明確化。
  - テスト容易性のため API 呼び出し箇所に差し替え（モック）ポイントを用意。

### Fixed / Defensive improvements
- .env パーサの堅牢性向上:
  - export プレフィックス、引用符内のバックスラッシュエスケープ、行内コメントの取り扱いなどを正しく処理するように実装。無効行は無視。
  - .env 読み込みでファイルオープン失敗時に警告を出して継続する（warnings.warn）。
- DuckDB / SQLite 書き込みの互換性を考慮:
  - executemany に空リストを渡さないよう事前チェックを実装（DuckDB 0.10 の制約回避）。
  - トランザクションでの例外発生時に ROLLBACK を試行し、それも失敗した場合は警告ログを出すようにして上位へ例外を伝播。
- 数値処理の安定化:
  - ランキング関数で浮動小数点の丸め誤差対策として round(v, 12) を使用（同順位検出の信頼性向上）。
- AI モジュールの堅牢性:
  - API レスポンスパース失敗時はログを出して対象チャンクをスキップし、全処理継続。部分成功のスコアのみ DB に書き込む戦略を採用。
  - score_news / score_regime 共に API キー未設定時は ValueError を返し、呼び出し側で明示的に対応可能に。

### Known issues / TODO
- position_sizing.calc_position_sizes:
  - price が欠損（0.0）の場合、エクスポージャーやサイズ計算が過小評価される懸念あり。将来的に前日終値や取得原価でのフォールバックを検討中（TODO コメントあり）。
  - lot_size は現状一律の設計。将来は銘柄別 lot_map を受け取る設計へ拡張予定。
- risk_adjustment.apply_sector_cap:
  - "unknown" セクターは上限適用対象外。場合によっては扱いを見直す可能性あり。
- AI の LLM 呼び出しは外部ネットワークや API 仕様の変化に依存するため、将来 SDK やレスポンス形式の変化に応じた対応が必要。

---

署名:
- 初期実装: ポートフォリオ構築、リサーチ、AI（ニュース/レジーム）、設定、監視永続化の主要機能を含む
- 日付: 2026-04-09