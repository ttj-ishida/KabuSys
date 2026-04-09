# Keep a Changelog — 変更履歴

すべての重要な変更はこのファイルに記録します。  
このプロジェクトでは [Keep a Changelog](https://keepachangelog.com/ja/1.0.0/) の慣例に従います。

## [0.1.0] - 2026-04-09 (初回リリース)

### 追加 (Added)
- パッケージ初期公開
  - パッケージメタ情報: `kabusys.__version__ = "0.1.0"`。トップレベルのエクスポート: `data`, `strategy`, `execution`, `monitoring`。

- 環境・設定管理 (`src/kabusys/config.py`)
  - .env ファイル（および .env.local）や環境変数から設定を自動読み込みする機能を実装。
    - プロジェクトルートは `.git` または `pyproject.toml` を基準に `__file__` から親ディレクトリを探索して特定（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
    - OS 環境変数を保護するため、既存の環境変数キーを protected として扱う。
  - .env パーサーは以下をサポート:
    - コメント行・空行の無視、`export KEY=val` 形式の対応。
    - シングル/ダブルクォート文字列のエスケープ解析（バックスラッシュ処理、対応する閉じクォートまでを値として扱う）。
    - クォートなし値に対するインラインコメント処理（`#` の前に空白がある場合のみコメントとみなす）。
  - `Settings` クラスを提供（アプリケーション設定のプロパティ群）。
    - J-Quants / kabuステーション / LINE API / DB パス等の設定取得。
    - 環境変数が未設定の場合にエラーを投げる `_require()` ヘルパー。
    - 値検証:
      - `PAPER_FILL_MODE` の有効値検査（`instant|partial|never|reject`）。
      - `KABUSYS_ENV` の有効値検査（`development|paper_trading|live`）。
      - `LOG_LEVEL` の有効値検査（`DEBUG|INFO|WARNING|ERROR|CRITICAL`）。
    - デフォルト値・パスの既定値を設定（例: `DUCKDB_PATH = data/kabusys.duckdb` 等）。
    - 便利なブールプロパティ: `is_live`, `is_paper`, `is_dev`。

- ポートフォリオ構築ユーティリティ (`src/kabusys/portfolio/`)
  - 候補選定・重み計算 (`portfolio_builder.py`)
    - select_candidates: BUY シグナルをスコア降順でソートし上位 N を返す。スコア同点時は `signal_rank` の昇順でタイブレーク。
    - calc_equal_weights: 等金額配分 (1/N)。
    - calc_score_weights: スコア加重配分（合計スコアが 0 の場合は等金額配分へフォールバックし WARNING を出力）。
  - リスク調整 (`risk_adjustment.py`)
    - apply_sector_cap: 同一セクターの既存保有比率が閾値を超える場合、新規候補を除外（"unknown" セクターは無視）。当日売却予定銘柄をエクスポージャー計算から除外可能。
    - calc_regime_multiplier: 市場レジーム（`bull|neutral|bear`）に応じた投下資金乗数（デフォルト mapping: bull=1.0, neutral=0.7, bear=0.3）。未知のレジームは 1.0 にフォールバックしログ出力。
  - 株数決定・単元丸め (`position_sizing.py`)
    - calc_position_sizes: 以下の方式で発注株数を算出:
      - risk_based: 許容リスク率と損切り率から基準株数を算出、単元 (lot_size) に丸め、既存保有分を差し引く。
      - equal / score: weight に基づく割当で単元丸め。`max_position_pct` による per-stock 上限、`max_utilization` によるポートフォリオ全体上限を考慮。
    - aggregate cap（全銘柄合計が利用可能現金を超える場合）のスケーリング実装:
      - cost_buffer に基づく保守的な価格見積り。
      - スケールダウン後に単元ごとの端数を残差（fractional_remainder）で再配分する再現性あるアルゴリズムを採用。
    - 設計上の注記: 将来的に銘柄別 lot_size を受け取る拡張を想定する TODO 注釈あり。

- リサーチ / ファクター計算 (`src/kabusys/research/`)
  - ファクター計算 (`factor_research.py`)
    - calc_momentum: 1M/3M/6M リターンと 200 日移動平均乖離 (MA200_dev)。MA200 のウィンドウが不十分なら None を返す。
    - calc_volatility: 20 日 ATR、相対 ATR (atr_pct)、20 日平均売買代金 (avg_turnover)、出来高比 (volume_ratio)。true_range の NULL 伝播を正確に扱う実装。
    - calc_value: raw_financials の target_date 以前の最新レコードと prices_daily を組み合わせて PER と ROE を算出（EPS が 0/欠損のときは PER を None）。
  - 特徴量探索ユーティリティ (`feature_exploration.py`)
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。入力ホライズン検証（正の整数 <=252）。
    - calc_ic: スピアマンのランク相関（IC）を計算。有効レコードが 3 件未満なら None。
    - rank: 同順位は平均ランクを与えるランキングユーティリティ（比較前に round(v, 12) して浮動小数点の ties 問題に対処）。
    - factor_summary: count/mean/std/min/max/median を計算（None 値は除外）。
  - パッケージエクスポートに zscore_normalize（kabusys.data.stats 由来）を含む。

- AI 関連機能 (`src/kabusys/ai/`)
  - ニュース NLP スコアリング (`news_nlp.py`)
    - score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）へ送り、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む一連の処理を提供。
    - ニュース時間ウィンドウ: target_date を基準に「前日 15:00 JST 〜 当日 08:30 JST」を対象（内部では UTC 変換して比較）。calc_news_window ユーティリティあり。
    - 大きなポイント:
      - 1 銘柄あたり最大記事数 / 最大文字数でトリム（トークン肥大化対策）。
      - 最大 20 銘柄ずつバッチ処理、JSON Mode を使って厳密な JSON 出力を期待。
      - 429 / ネットワーク断 / タイムアウト / 5xx を対象に指数バックオフでリトライ（リトライ上限設定あり）。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、各要素の `code` と `score` 検査、未知コードの無視、数値変換、有限値確認）。
      - スコアは ±1.0 にクリップ。
      - DB 書き込みはトランザクションで冪等に行う（DELETE → INSERT、executemany を用いるが空リストは避ける互換性対策）。
      - API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError。
      - API 呼び出し部はテスト容易性のため関数化（モック差し替え可能）。
  - 市場レジーム判定 (`regime_detector.py`)
    - score_regime: ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して `bull|neutral|bear` を決定し `market_regime` テーブルへ書き込む。
    - 処理詳細:
      - 1321 の直近 200 日データを用いて MA200 乖離を計算（データ不足時は中立扱い 1.0）。
      - raw_news からマクロキーワードでフィルタしたタイトルを取得し、LLM により macro_sentiment を算出（記事なし時は LLM 呼び出しを行わず macro_sentiment=0.0）。
      - 合成スコアに基づき閾値でラベルを決定（閾値定義あり）。
      - DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）で実行。
      - API キーは引数または環境変数 OPENAI_API_KEY で解決。未設定時は ValueError。
      - LLM 呼び出し周りはリトライ／フォールバックの処理を備え、フェイルセーフで macro_sentiment=0.0 にフォールバックする。

- 監視ログ永続化（SQLite） (`src/kabusys/monitoring/monitoring_db.py`)
  - init_monitoring_db: 監視用の永続化スキーマを作成するユーティリティを実装（冪等）。
    - 作成されるテーブル（初期実装）:
      - system_status（cpu/memory/disk, process_ok 等、記録時刻インデックス）
      - trade_logs（注文ログ、client_order_id インデックス等）
      - positions（保有ポジション、updated_at インデックス）
      - risk_logs（イベント種別などのログ）
    - 各テーブルに必要なインデックスを作成する SQL スクリプトを含む。
    - SQLite の標準ライブラリ sqlite3 を利用。

### 変更 (Changed)
- （初回リリースのため該当なし）

### 修正 (Fixed)
- （初回リリースのため該当なし）

### 注意事項 / 既知の制限
- news_nlp / regime_detector が外部 OpenAI API を利用するため、運用環境では OPENAI_API_KEY の設定が必須（関数呼び出し時に引数で渡すことも可）。
- DuckDB / SQLite のバージョン互換性に関する注意:
  - news_nlp の executemany に空リストを渡すとエラーとなるため、呼び出し前に空チェックを行っている（DuckDB 0.10 対応）。
- 一部の箇所に TODO コメントあり（例: 銘柄別 lot_size のサポート、価格欠損時のフォールバックなど）。
- ドキュメントやマイグレーション手順は別途整備予定。

-- END --