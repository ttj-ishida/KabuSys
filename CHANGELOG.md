# Changelog

すべての重要な変更をここに記録します。本ファイルは「Keep a Changelog」準拠の形式を採用しています。

全般ルール: 破壊的変更（breaking changes）は明示します。可能な限りコードの実装から推測して記載しています。

## [Unreleased]

なし

## [0.1.0] - 2026-04-09

### Added
- 初期リリース: KabuSys のコア機能群を追加。
  - パッケージメタ情報
    - src/kabusys/__init__.py: パッケージバージョンを `0.1.0` に設定。主要サブパッケージ（data, strategy, execution, monitoring）を __all__ で公開。

  - 環境変数 / 設定管理
    - src/kabusys/config.py:
      - .env ファイルまたは環境変数から設定値を読み込む Settings クラスを提供。
      - 自動 .env ロード:
        - プロジェクトルートを .git または pyproject.toml で検出し、`.env` → `.env.local` の順で読み込み（OS 環境変数を保護するため既存キーは保護、`.env.local` は override=True）。
        - 自動ロードは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
      - .env パーサーは `export KEY=val` 形式、クォートとバックスラッシュエスケープ、インラインコメント（条件付き）等に対応。
      - 必須値取得ヘルパ `_require`：未設定時は ValueError を送出。
      - 利用可能な設定プロパティ（例）:
        - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルト localhost）、LINE チャネル設定、データベースパス（DUCKDB_PATH, SQLITE_PATH）、Paper Trading 関連（PAPER_FILL_MODE、PAPER_TRADING_SQLITE_PATH）、
        - 監視用設定（PID/KILL フラグパス、閾値: CPU/MEM/DISK）、環境モード（KABUSYS_ENV: development/paper_trading/live のバリデーション）、LOG_LEVEL のバリデーション。
      - 設定値に対する入力検証と適切なエラーメッセージを実装。

  - ポートフォリオ構築（純粋関数群）
    - src/kabusys/portfolio/portfolio_builder.py:
      - select_candidates: BUY シグナルを score 降順、同点は signal_rank 昇順でソートし上位 N を選択。
      - calc_equal_weights: 等金額配分（{code: 1/N}）。
      - calc_score_weights: スコア比率で重み付け。全スコアが 0 の場合は等金額にフォールバックして WARNING を出力。
    - src/kabusys/portfolio/risk_adjustment.py:
      - apply_sector_cap: 既存保有のセクター別エクスポージャを計算し、1 セクターの比率が閾値（デフォルト 30%）を超える場合、そのセクターの新規候補を除外。`unknown` セクターは除外対象外。
      - calc_regime_multiplier: レジーム（'bull'/'neutral'/'bear'）に応じた投下資金乗数（1.0 / 0.7 / 0.3）を返す。未知レジームは警告を出して 1.0 にフォールバック。
    - src/kabusys/portfolio/position_sizing.py:
      - calc_position_sizes: 発注株数決定ロジックを実装（allocation_method: "risk_based" / "equal" / "score"）。
        - risk_based: base_shares = floor(portfolio_value * risk_pct / (price * stop_loss_pct))、単元(lot_size)で丸め、既存ポジションを考慮して買い増し量を算出。
        - equal/score: weight と価格から per-position の割当を計算、max_position_pct と lot_size に従い丸め。
        - aggregate cap: 全銘柄合計コストが available_cash を超える場合はスケーリングを実施。cost_buffer を考慮して保守的にコストを見積もり、スケール後の端数（lot 単位）の配分は残差の大きい順で行う（再現性のため二次キーに code を使用）。
        - 価格欠損時の挙動（価格 <= 0 の場合はスキップ）や将来の拡張（銘柄別 lot_size 等）はコメントで明示。

    - src/kabusys/portfolio/__init__.py: 上記関数群をパッケージ API として公開。

  - リサーチ／ファクター計算
    - src/kabusys/research/factor_research.py:
      - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離（ma200_dev）を DuckDB の prices_daily から算出。ウィンドウ不足時は None を返す。
      - calc_volatility: 20 日 ATR、相対 ATR（atr_pct）、20 日平均売買代金、出来高比（volume_ratio）を算出。true_range の NULL 伝播を明示的に制御。
      - calc_value: raw_financials の target_date 以前の最新レコードを銘柄ごとに取得して PER（EPS による算出）と ROE を算出。
    - src/kabusys/research/feature_exploration.py:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。horizons 検証（1..252）。
      - calc_ic: Spearman（ランク相関）による IC 計算を実装。None や非有限値を除外し、有効レコードが 3 未満なら None を返す。ties は平均ランクで処理。
      - rank / factor_summary: ランク化ユーティリティ、各ファクター列の count/mean/std/min/max/median を標準ライブラリのみで計算。
    - src/kabusys/research/__init__.py: 主要関数とデータ正規化ユーティリティ（kabusys.data.stats.zscore_normalize）を公開。

  - AI（LLM）統合: ニュースセンチメント & レジーム判定
    - src/kabusys/ai/news_nlp.py:
      - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄別にセンチメントを取得して ai_scores テーブルへ書き込み。
        - ニュース時間ウィンドウ: target_date に対し JST の前日 15:00 〜 当日 08:30 を UTC に変換して使用。
        - 1 銘柄あたり最大記事数・文字数（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）でトリム。
        - 最大バッチサイズ 20 銘柄で API コール。429/ネットワーク断/タイムアウト/5xx は指数的バックオフでリトライ。その他の例外はスキップ。
        - レスポンス検証: JSON パース、"results" リストの存在、各 item の code/score の検証、未知コードの無視、数値性と有限性のチェック。スコアは ±1.0 にクリップ。
        - 書き込みは冪等に実施（BEGIN / DELETE(for codes) / INSERT / COMMIT）。部分失敗時に既存スコアを不必要に消さないために code を絞って削除 → 挿入。
        - テスト用フック: _call_openai_api を patch して差し替え可能。
    - src/kabusys/ai/regime_detector.py:
      - score_regime: ETF 1321（日経225 連動型）の 200 日移動平均乖離（ma200_ratio）と、raw_news から抽出したマクロニュースの LLM センチメントを組み合わせて日次レジーム（'bull'/'neutral'/'bear'）を判定し market_regime テーブルへ書き込み。
        - MA の計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。データ不足時は中立（1.0）を採用。
        - マクロニュースはキーワードリストでタイトルをフィルタし最大件数を取得。記事が無ければ LLM を呼ばず macro_sentiment=0.0 を使用。
        - 合成スコア: clip(0.7*(ma200_ratio-1)*10 + 0.3*macro_sentiment, -1, 1) などの重み付けと閾値でラベル付与。API 失敗時はフェイルセーフでマクロスコアを 0.0 として継続。
        - DB 書き込みは冪等的（BEGIN / DELETE / INSERT / COMMIT）。
      - src/kabusys/ai/__init__.py: score_news を公開。

  - 監視用 DB ラッパー（SQLite）
    - src/kabusys/monitoring/monitoring_db.py:
      - init_monitoring_db(conn): system_status, trade_logs, positions, risk_logs 等のテーブルとインデックスを冪等に作成する初期化関数を提供（監視ログ永続化層）。
      - 実装はビジネスロジックを持たず、単にスキーマ作成を行う。

### Changed
- 該当なし（初期リリース）

### Fixed
- 該当なし（初期リリース）

### Notes / Known limitations（実装から推測）
- OpenAI クライアントの呼び出しは現状 gpt-4o-mini を指定しているため、API 変更やモデル廃止に影響を受ける可能性あり。API 呼び出しはテスト時に差し替えられる設計。
- DuckDB / SQLite 周りの SQL は現行バージョン（DuckDB 0.10 等）向けに互換性への配慮があるが、将来の DB バージョン差異で挙動が変わる可能性あり（executemany の空リスト制約等に注意）。
- price 欠損時のフォールバック価格は TODO として残されており、現在は price が 0/None の銘柄をスキップする挙動。
- ポジションサイズ算出での lot_size は現時点で全銘柄共通。将来的に銘柄別単元対応の拡張が想定されている（コメントあり）。

---

（注）この CHANGELOG は提示されたソースコードから推測して作成しています。実際のリリースノートとして利用する場合は、リリース担当者が変更点・日付・破壊的変更の有無を確認の上で最終調整してください。