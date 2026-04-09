# CHANGELOG

すべての重要な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]
- ドキュメント・内部実装の改善、ログメッセージの強化、型注釈の追加などのマイナー改善（テスト・運用時の可観測性向上）。

---

## [0.1.0] - 2026-04-09
初回リリース。以下の主要機能を実装。

### Added
- 全体
  - パッケージ基盤を追加。__version__ = "0.1.0" を定義。
  - モジュール構成: config, portfolio, research, ai, monitoring などの主要モジュールを提供。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定値を読み込む自動ロード機能を実装。
  - プロジェクトルート検出: __file__ を起点に親ディレクトリから .git または pyproject.toml を探索してプロジェクトルートを特定。
  - .env / .env.local の読み込み順序をサポート（OS 環境変数を保護する機構を実装）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能。
  - .env パーサーの実装:
    - export プレフィックスをサポート。
    - シングル/ダブルクォートされた値内のバックスラッシュエスケープ処理に対応。
    - クォートなし値のインラインコメント処理（'#' の前が空白またはタブの場合）に対応。
  - Settings クラスを提供し、アプリケーションで必要な設定（API トークン、DB パス、監視閾値、環境モード、ログレベルなど）をプロパティとして取得可能。
  - 設定値の検証を実装（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL などの許容値チェック、未設定必須キーは ValueError を送出）。

- ポートフォリオ構築（kabusys.portfolio）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 小さい方優先）でソートして上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分。全銘柄スコアが 0.0 の場合は等金額配分にフォールバックして WARNING を出力。
  - risk_adjustment:
    - apply_sector_cap: セクター集中を抑制するため、既存保有比率が閾値を超えるセクターの新規候補を除外（"unknown" セクターは適用外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返却。未知レジームはロギングしてフォールバック。
  - position_sizing:
    - calc_position_sizes: 複数の配分方式（risk_based / equal / score）に対応した発注株数計算を実装。
    - 単元株（lot_size）での丸め、1銘柄上限、aggregate cap（利用可能現金）に対するスケーリング、手数料・スリッページ見積り用 cost_buffer を考慮した保守的見積りを実装。
    - aggregate スケールダウン時に残差処理を行い、lot_size 単位で再配分するアルゴリズムを実装。
    - 価格欠損時のスキップとデバッグログを実装。

- リサーチ / ファクター計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離率（ma200_dev）を DuckDB の prices_daily テーブルから取得して計算。
    - calc_volatility: 20 日 ATR、ATR 比率（atr_pct）、20 日平均売買代金、出来高比（volume_ratio）を計算。true_range の NULL 伝播を適切に処理。
    - calc_value: raw_financials から直近財務データを取得し PER / ROE を計算（EPS が 0 または NULL の場合は None）。
    - 全関数はいずれも DuckDB SQL を活用して効率的に集約処理を実行。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンに対する将来リターン（複数ホライズン対応）を一回のクエリで取得。ホライズンの検証（正数かつ <= 252）を実施。
    - calc_ic: ファクター値と将来リターンのスピアマンランク相関（IC）を計算。データ不足（有効レコード < 3）時は None を返す。
    - rank: 同順位は平均ランクを採る実装。丸め（round(v, 12)）により浮動小数の ties 検出漏れに対応。
    - factor_summary: count/mean/std/min/max/median を算出するユーティリティ。

- AI / NLP（kabusys.ai）
  - news_nlp:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントスコアを算出して ai_scores テーブルに書き込むワークフローを実装。
    - ニュース時間ウィンドウ（前日 15:00 JST 〜 当日 08:30 JST）を計算するユーティリティ calc_news_window。
    - バッチ処理（最大 _BATCH_SIZE 銘柄）・1銘柄あたりのトリム制限（_MAX_ARTICLES_PER_STOCK、_MAX_CHARS_PER_STOCK）を実装。
    - OpenAI 呼び出しで JSON mode を使用し、レスポンスのバリデーションを厳格に実施（results 配列・型チェック・未知コード除外・数値変換・クリップ）。
    - 429・接続断・タイムアウト・5xx を対象とした指数バックオフ付きリトライを実装。その他の例外はスキップして継続（フェイルセーフ）。
    - DuckDB への書き込みはトランザクション内で実行（DELETE → INSERT）、部分失敗時に既存スコアを保護する手順を採用。
    - API キー解決時は引数優先、その後 OPENAI_API_KEY 環境変数を参照。未設定時は ValueError を送出。
  - regime_detector:
    - ETF 1321 の ma200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースはキーワードベースで抽出（複数キーワード）し、最大記事数を制限して LLM に送信。
    - LLM 呼び出しは JSON mode、再試行ロジック、失敗時は macro_sentiment=0.0 とするフォールバックを実装。
    - レジーム合成後、market_regime テーブルに冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - API キー未設定時は ValueError を送出。

- 監視ログ永続化（kabusys.monitoring.monitoring_db）
  - SQLite を用いた MonitoringDB の初期化関数を実装（init_monitoring_db）。
  - system_status, trade_logs, positions, risk_logs 等のテーブルと関連インデックスを作成する SQL スクリプトを提供（冪等）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Notes / Design decisions
- ルックアヘッドバイアス防止のため、日付比較で target_date の取り扱いに注意してクエリを設計（prices_daily の date < target_date 等）。
- 外部 API 呼び出しはフェイルセーフ設計（API 失敗時にスコア 0.0 を使う、例外を投げずに処理継続）で運用リスクを低減。
- DuckDB / SQLite のバージョン差異に対する互換性考慮（executemany に空リスト不可への対応など）。
- 単体テスト容易化のため、OpenAI 呼び出し箇所はラッパー関数（_call_openai_api）を用意し、テスト用にモック差替え可能。

---

過去の変更履歴やリリース計画が必要な場合、または特定機能（例: position_sizing の lot_size を銘柄別に拡張する等）の詳細な変更案内が必要であればお知らせください。