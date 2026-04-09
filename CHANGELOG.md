# CHANGELOG

すべての重要な変更はこのファイルに記載します。フォーマットは Keep a Changelog に準拠します。  
このプロジェクトはセマンティックバージョニングを採用します。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回リリース。

### Added
- 全体
  - プロジェクト初期実装を追加。主要サブモジュール（設定、ポートフォリオ構築、リサーチ、AI、監視DB）が含まれます。
  - package バージョン定義: `__version__ = "0.1.0"`。

- 設定 / 環境読み込み (src/kabusys/config.py)
  - .env ファイルおよび環境変数から設定をロードする自動読み込み機能を実装。プロジェクトルートは `.git` または `pyproject.toml` を上位ディレクトリから探索して特定。プロジェクトルートが特定できない場合は自動ロードをスキップ。
  - .env パーサーで以下をサポート:
    - 空行・コメント行（#）の無視、`export KEY=val` 形式、シングル/ダブルクォートのエスケープ処理、インラインコメントの扱い（非クォート時は直前が空白/タブならコメント扱い）。
  - 自動ロードの制御: 環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` により自動ロードを無効化可能。
  - OS 環境変数を保護する機能（.env の上書きを防ぐ protected set）。`.env` は既存変数を上書きせず、`.env.local` は上書き可能だが OS 環境変数は保護。
  - Settings クラスを実装し、アプリケーション設定をプロパティ経由で取得可能（J-Quants、kabuステーション、LINE、DB パス、Paper Trading 設定、監視閾値、環境/ログレベル検証など）。
  - 環境変数検証ロジック:
    - `PAPER_FILL_MODE` の有効値検証（instant/partial/never/reject）。
    - `KABUSYS_ENV` の有効値検証（development/paper_trading/live）。
    - `LOG_LEVEL` の有効値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
  - Path の expanduser() 対応（例: DuckDB / SQLite パス、PID / kill flag など）。

- ポートフォリオ構築 (src/kabusys/portfolio/*.py)
  - portfolio_builder
    - select_candidates: BUY シグナルリストをスコア降順にソート、同点は signal_rank でタイブレーク。
    - calc_equal_weights: 等金額配分を計算。
    - calc_score_weights: スコア加重配分を計算。全銘柄スコアが 0 の場合は等金額配分にフォールバックし WARNING をログ出力。
  - risk_adjustment
    - apply_sector_cap: セクター集中上限に基づき候補を除外（既存ポジションのセクター別エクスポージャ計算、売却予定銘柄を除外できるオプション）。"unknown" セクターは上限適用対象外。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に対する投下資金乗数を返す。未知レジームはログ警告の上フォールバック値 1.0。
  - position_sizing
    - calc_position_sizes: 発注株数計算を実装。以下をサポート:
      - allocation_method: "risk_based" / "equal" / "score"
      - lot_size 単位で丸め、per-position 上限（max_position_pct）・aggregate cap（available_cash）・cost_buffer（手数料・スリッページ見積り）を考慮したスケーリング
      - risk_based 時の risk_pct / stop_loss_pct に基づく株数算出
      - aggregate スケールダウン時に fractional remainder を考慮して残余資金で lot 単位を追加配分（再現性確保のため安定ソート）

- リサーチ / ファクター計算 (src/kabusys/research/*)
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を DuckDB SQL で計算。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算。true_range の NULL 伝播に注意した設計。
    - calc_value: raw_financials の最新財務データと prices_daily を組み合わせて PER / ROE を計算。
  - feature_exploration
    - calc_forward_returns: 指定 horizon の将来リターンを一括で取得（SQL による LEAD にて）。
    - calc_ic: スピアマン順位相関（IC）を計算。データ不足（有効レコード < 3）時は None。
    - rank: 同順位は平均ランク扱い、丸めによる ties 検出漏れ対策あり（round(v, 12)）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出。
  - research パッケージは zscore_normalize を含めた主要関数をエクスポート。

- AI / NLP 機能 (src/kabusys/ai/*)
  - news_nlp
    - score_news: raw_news と news_symbols を日次ウィンドウで集約し、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄ごとのセンチメントスコアを算出・ai_scores テーブルへ書き込み。
    - ニュースウィンドウの計算（JST ベースを UTC に変換）を実装（calc_news_window）。
    - バッチ送信（最大 20 銘柄/リクエスト）、1銘柄あたり最大記事数・最大文字数でトリムする制御を実装。
    - API の 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライし、その他の例外はリトライせずフェイルセーフでスキップ。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、各要素の型検査、未知コードの無視、スコアを ±1.0 にクリップ）。
    - DuckDB への書き込みは部分失敗を考慮し、対象コードのみ DELETE → INSERT（トランザクション）する実装。DuckDB executemany の空パラメータ制約を回避。
    - テスト用に _call_openai_api を差し替え可能な設計。
  - regime_detector
    - score_regime: ETF 1321 の ma200 乖離とマクロニュースの LLM センチメントを合成して市場レジーム（bull / neutral / bear）を判定・market_regime テーブルへ冪等書き込み。
    - ma200 計算は target_date 未満のデータのみ使用し、データ不足時は中立（1.0）にフォールバックして警告ログ出力。
    - マクロニュース取得はキーワードベース（設定されたキーワード群）でタイトルを抽出。記事がない場合は LLM 呼び出しをスキップし macro_sentiment=0.0 を使用。
    - OpenAI 呼び出しはリトライとエラー処理を実装。API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - news_nlp の API 呼び出し実装とは意図的に別実装（モジュール間で private 関数を共有しない）。

- 監視 / 永続化 (src/kabusys/monitoring/monitoring_db.py)
  - init_monitoring_db: SQLite 用の監視テーブル群とインデックスを作成する冪等スクリプトを実装（system_status, trade_logs, positions, risk_logs 等の作成）。

### Changed
- （初版のため該当なし）

### Fixed
- （初版のため該当なし）
- 実装面で以下の堅牢化が含まれる:
  - .env 読み込み失敗時に warnings.warn を出して処理を継続。
  - DuckDB / DB 書き込み時にトランザクションと ROLLBACK の保護を追加。
  - API レスポンスの不正時は例外を上位に伝播させずロギングして安全にスキップするフェイルセーフ設計（AI モジュール）。

### Security
- OpenAI API キーは引数または環境変数（OPENAI_API_KEY）で渡す設計。キーのハードコードは行っていません。
- .env 自動ロードは環境変数で無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

### Notes / Known limitations
- DuckDB / SQLite のスキーマや API バージョン差異に依存する実装箇所あり（例: executemany に空リスト渡せない制約への対応）。
- 一部の計算（価格未取得時のエクスポージャ計算や position sizing）では price が欠損すると保守的にスキップ・過少評価される可能性があることをログ注記している（将来的なフォールバック価格導入を検討）。
- AI 呼び出しに関する JSON パースで余計なテキストが混在するケースに対し、最外の `{...}` を抽出する復元ロジックを実装しているが完全ではありません。
- レジーム判定・ニューススコアリングは LLM を使用するため API の可用性・料金に依存します。API 失敗時は安全側のデフォルト（macro_sentiment=0.0、スコア未取得扱い）で継続する設計。

---

（以降のリリースでは、Added / Changed / Fixed を使って差分を記載してください）