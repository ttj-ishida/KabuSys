# CHANGELOG

すべての変更は Keep a Changelog の形式に従います。慣例としてセマンティックバージョニングを使用します。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース

### Added
- パッケージ基盤
  - パッケージメタ情報を src/kabusys/__init__.py に追加（バージョン: 0.1.0、公開 API の __all__ 指定）。
- 環境設定 / 起動時自動読み込み
  - src/kabusys/config.py:
    - .env / .env.local ファイルおよび環境変数から設定を読み込む自動ロード機能を実装。自動ロードの優先順位は OS 環境変数 > .env.local > .env。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定（CWD 非依存）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、シングル／ダブルクォート内のバックスラッシュエスケープ、行内コメント処理等に対応。
    - Settings クラスを提供し、主要な環境変数をプロパティで取得。必須変数未設定時に ValueError を送出するヘルパー _require を実装。
    - 各種設定の妥当性チェックを実装（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。
    - デフォルトパスや閾値（DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEM/DISK 閾値 等）を定義。
- ポートフォリオ構築（Portfolio）
  - src/kabusys/portfolio/portfolio_builder.py:
    - select_candidates: BUY シグナルをスコア降順かつ signal_rank でタイブレークして上位 N を選択。
    - calc_equal_weights: 等金額配分（1/N）。
    - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等金額にフォールバックし WARNING）。
  - src/kabusys/portfolio/position_sizing.py:
    - calc_position_sizes: 発注株数決定ロジックを実装。allocation_method に "risk_based" / "equal" / "score" をサポート。
      - risk_based: risk_pct / stop_loss_pct に基づく株数計算。
      - equal/score: weight に基づく割当。
      - 単元株（lot_size）での丸め、1銘柄上限（max_position_pct）、投下上限（max_utilization）、手数料・スリッページの保守的見積り（cost_buffer）を考慮。
      - aggregate cap（全銘柄合計が available_cash を超える場合）でスケールダウンし、残余キャッシュで端数を lot_size 単位で再配分する公平化ロジックを導入。
      - 価格欠損時は該当銘柄をスキップし DEBUG ログを出力。
  - src/kabusys/portfolio/risk_adjustment.py:
    - apply_sector_cap: 既存保有のセクター比率が max_sector_pct を超えるセクターの新規候補を除外（"unknown" セクターは除外対象外）。sell_codes を指定して当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: レジーム（"bull"/"neutral"/"bear"）に応じた投下資金乗数を提供（デフォルト: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは警告を出して 1.0 にフォールバック。
  - パッケージエクスポート: select_candidates, calc_equal_weights, calc_score_weights, calc_position_sizes, apply_sector_cap, calc_regime_multiplier を公開。
- リサーチ（Research / ファクター計算）
  - src/kabusys/research/factor_research.py:
    - calc_momentum: 1M/3M/6M リターンと MA200 乖離を DuckDB 上の prices_daily テーブルから計算。
    - calc_volatility: 20日 ATR（true range の適切な NULL 伝播制御）、相対 ATR（atr_pct）、20日平均売買代金、出来高比率を計算。窓データ不足時に None を返す仕様。
    - calc_value: raw_financials と prices_daily を結合して PER（EPS が 0 または NULL の場合は None）と ROE を計算。最新財務レコードの取得に ROW_NUMBER を使用。
  - src/kabusys/research/feature_exploration.py:
    - calc_forward_returns: 複数ホライズンの将来リターンをまとめて取得。horizons のバリデーション（正の整数かつ <= 252）を実施。
    - calc_ic: スピアマンのランク相関（IC）を計算。レコード数が不足する場合は None。
    - rank: 同順位は平均ランクとするランク関数（浮動小数誤差対策として round(..., 12) を使用）。
    - factor_summary: count/mean/std/min/max/median を計算する統計要約ユーティリティ。
  - src/kabusys/research/__init__.py に主要関数と zscore_normalize の再エクスポートを追加。
  - 実装方針: DuckDB 接続を受け取り、外部ライブラリ（pandas 等）に依存しない純粋 Python + SQL 実装。
- AI（OpenAI を用いた自然言語処理）
  - src/kabusys/ai/news_nlp.py:
    - calc_news_window: ニュース集計ウィンドウ（JST ベース、内部は UTC naive datetime）計算ロジックを実装（前日 15:00 JST ～ 当日 08:30 JST）。
    - score_news: raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON Mode）へバッチ送信して銘柄別センチメント（ai_score）を ai_scores テーブルへ書き込むフローを実装。
      - バッチサイズ、1銘柄当たりの最大記事数／文字数トリム、最大リトライ回数、指数バックオフなどの制御。
      - レスポンスの厳格なバリデーション（JSON 抽出、results リスト、code/score 検証、スコアの有限性、±1.0 クリップ）を実施。失敗時は該当チャンクのみスキップして継続する設計（フェイルセーフ）。
      - DuckDB への書き込みは冪等化（DELETE → INSERT）で実施。DuckDB の executemany の仕様を考慮して空パラメータを渡さない保護を実装。
      - テスト容易性のため OpenAI 呼び出しを行う内部関数 _call_openai_api を用意し、ユニットテスト時に patch できる設計。
  - src/kabusys/ai/regime_detector.py:
    - score_regime: ETF 1321 の ma200 乖離とマクロニュースの LLM センチメントを重み合成してレジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする機能を実装。
      - ma200_ratio 計算は target_date 未満のデータのみ使用してルックアヘッドを防止。データ不足時は中立（1.0）でフォールバックして警告を出す。
      - マクロニュース取得はキーワードベースで raw_news のタイトルをフィルタし、タイトルが無ければ LLM 呼び出しを行わず macro_sentiment=0.0 を使用。
      - OpenAI 呼び出しは retries/backoff を実装し、失敗時は macro_sentiment=0.0 にフォールバック（例外を投げない）。
      - news_nlp とは API 呼び出し関数を分離しており、テスト時に個別に差し替え可能。
  - src/kabusys/ai/__init__.py で score_news をエクスポート。
- モニタリング永続化層
  - src/kabusys/monitoring/monitoring_db.py:
    - init_monitoring_db: SQLite 用の監視ログ永続化テーブル群（system_status, trade_logs, positions, risk_logs など）とインデックスを作成する冪等スクリプトを実装。

### Design / Implementation notes
- ルックアヘッドバイアス防止: news / regime / research いずれも date.today()/datetime.today() を直接参照せず、target_date を明示的に受け取る設計。
- 外部ライブラリ依存を最低限に抑える方針（DuckDB は使用するが pandas 等には依存しない）。
- OpenAI 連携:
  - レスポンスの堅牢な検証、429/ネットワーク/タイムアウト/5xx のリトライ、非 5xx の APIError はリトライしないなどの安全策を導入。
  - テストのために API 呼び出し箇所をモックしやすい構造にしている（内部 _call_openai_api を patch 可能）。
- DuckDB / SQLite の実運用考慮:
  - DuckDB への executemany は空リストを渡せないバージョンがあるため、それに配慮した記述になっている。
  - prices_daily / raw_financials 等のテーブルへは SQL 内でウィンドウ関数を使用して効率的に集計。

### Known issues / TODO
- risk_adjustment.apply_sector_cap:
  - price_map が 0.0 の場合にエクスポージャーが過少推定され、ブロックが外れる可能性がある旨の TODO（前日終値や取得原価でのフォールバックを将来検討）。
- position_sizing:
  - 現在 lot_size は全銘柄共通（デフォルト 100）。将来的に銘柄別 lot_map を受け取る設計への拡張予定。
- 一部のエラー/例外はフェイルセーフでスキップする設計のため、運用時はログ監視が重要。
- ai/regime_detector の閾値・重み付けは現フェーズのハードコード値（MA_WEIGHT=0.7 等）。将来的に設定化する余地あり。

### Security
- OpenAI API キーは引数経由または環境変数 OPENAI_API_KEY により供給。未設定時は ValueError を送出して明示的に失敗させる（安全側）。
- .env の読み込み時、既存 OS 環境変数は protected として上書きを防止する挙動をサポート。

<!--
注: 今後の変更は Unreleased セクションに記載し、リリース時にバージョンと日付を追加してください。
-->