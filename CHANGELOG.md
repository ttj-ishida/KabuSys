CHANGELOG
=========

このプロジェクトの変更履歴は「Keep a Changelog」形式に準拠します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

- なし

[0.1.0] - 2026-04-09
--------------------

Added
- 基本情報
  - パッケージ初期バージョンを追加（__version__ = "0.1.0"）。
  - パッケージ公開に向けた主要モジュール群を実装。

- 環境・設定管理 (src/kabusys/config.py)
  - .env / .env.local ファイルおよび OS 環境変数から設定を自動ロードする仕組みを追加。
    - プロジェクトルート判定は __file__ を起点に .git または pyproject.toml を探索して行う（CWD に依存しない）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能（テスト用途）。
    - .env のパースは export 形式、クォート、インラインコメント、エスケープ対応。
    - 読み込みに失敗したファイルは warnings.warn で通知して継続。
  - 必須環境変数取得用ヘルパー _require を実装（未設定時は ValueError）。
  - 各種設定プロパティを実装（J-Quants / kabuAPI / LINE / DB パス / Paper Trading / 監視閾値 / 環境判定 / ログレベル等）。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL, PAPER_FILL_MODE 等）。不正な値は ValueError を送出。

- ポートフォリオ構築 (src/kabusys/portfolio/)
  - 銘柄選定・配分ロジックを実装。
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 小さい方優先）で選抜。
    - calc_equal_weights: 等金額配分の重み計算。
    - calc_score_weights: スコア比例配分（全銘柄スコアが 0 の場合は等分にフォールバックし WARNING を出力）。
  - リスク調整 (risk_adjustment)
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合、新規候補の同セクター銘柄を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に基づく投下資金乗数を実装（未知レジームは警告の上 1.0 にフォールバック）。
  - 株数決定・単元丸め (position_sizing)
    - calc_position_sizes: allocation_method("risk_based" / "equal" / "score") に応じた発注株数計算を実装。
      - risk_based: 許容リスク率、損切り幅から株数算出。
      - equal/score: 重み・最大利用率・lot_size に基づく配分。
      - 単元(lot_size)での丸め、1銘柄上限、price が欠損/0 の場合のスキップ。
      - aggregate cap: 全体投下コストが available_cash を超える場合のスケーリング（スケール後の端数は lot 単位で再配分）。
      - cost_buffer による手数料・スリッページを保守的に見積もる機能。

- リサーチ（因子計算・特徴量解析） (src/kabusys/research/)
  - factor_research: DuckDB 接続を受け取り純粋関数でファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を計算。データ不足時の None ハンドリング。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播を適切に扱う。
    - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS=0/欠損時は None）。
  - feature_exploration:
    - calc_forward_returns: 与えたホライズン（営業日）に対する将来リターンを一括で取得。horizons の検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank: 同順位は平均ランクを扱うランク付け実装（round で浮動小数の ties 回避）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ。

  - research パッケージのエクスポートに zscore_normalize（kabusys.data.stats から）を含む。

- AI / ニュース NLP (src/kabusys/ai/)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して OpenAI (gpt-4o-mini) にバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - ニュースウィンドウ計算（JST基準: 前日15:00〜当日08:30）を calc_news_window で実装（UTC naive datetime を返す）。
    - バッチ処理（_BATCH_SIZE=20）、記事・文字数トリム（最大記事数・最大文字数制限）、JSON Mode レスポンスの検証・スコアクリップ（±1.0）。
    - リトライポリシー: 429/ネットワーク/タイムアウト/5xx を指数バックオフでリトライ（最大 _MAX_RETRIES 回）。
    - API キーの引数または環境変数 OPENAI_API_KEY からの解決。未指定時は ValueError を送出。
    - DuckDB への書き込みは冪等（DELETE -> INSERT）で行い、部分失敗時に他銘柄の既存スコアを保護する実装。
    - テスト用に _call_openai_api をモック可能（unittest.mock.patch 推奨）。

  - regime_detector.score_regime:
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して 'bull'/'neutral'/'bear' を日次判定し market_regime テーブルへ書き込み。
    - マクロニュース抽出はキーワードリストによるタイトル検索（上限件数）。
    - LLM 呼び出しは独自の _call_openai_api 実装（news_nlp と共有せずモジュール結合を避ける）。
    - API 失敗時は macro_sentiment = 0.0 でフォールバックしフェイルセーフに動作。
    - DB 書き込みはトランザクションで冪等に実行（BEGIN / DELETE / INSERT / COMMIT）。

- モニタリング DB (src/kabusys/monitoring/monitoring_db.py)
  - SQLite を利用した監視ログ永続化レイヤを実装（init_monitoring_db でテーブル群とインデックスを冪等作成）。
    - system_status / trade_logs / positions / risk_logs などのテーブル作成スクリプトを追加。

- パッケージ公開インターフェース
  - kabusys.portfolio, kabusys.research, kabusys.ai の __all__ を整備し主要関数をエクスポート。

Changed
- 新規リリースのため初期実装。既存コードの変更履歴はなし。

Fixed
- なし（初版）

Security
- OpenAI API キーは引数または環境変数から取得。ログにキーを出力しないよう注意して実装。

Notes / Known limitations
- .env のパース実装は多くの一般ケースに対応するが、すべての .env 書式のパターンを網羅しているわけではありません。
- price が欠損（0.0）の場合、apply_sector_cap のエクスポージャーが過少評価される可能性がある（ソースに TODO コメントあり）。
- calc_value では現時点で PBR・配当利回りは未実装。
- DuckDB に対する executemany の挙動に関する互換性対応（空リスト不可など）を行っているため、使用する DuckDB のバージョンによっては注意が必要。
- テスト容易性のため一部 API 呼び出し（OpenAI）の内部ラッパー関数は patch して差し替え可能にしている。
- 日付・時間の取り扱いはルックアヘッドバイアス防止のため、target_date を明示的に渡す実装になっている（datetime.today()/date.today() を直接使用しない）。

Authors
- 実装コード内の docstring / コメントに基づき本リリースを記述。

Acknowledgments
- 設計文書（PortfolioConstruction.md, StrategyModel.md 等）に基づく実装が多数含まれます（リポジトリ外文書参照）。