# Changelog

すべての注目すべき変更点を記録します。フォーマットは "Keep a Changelog" に準拠しています。

## [0.1.0] - 2026-04-09

### Added
- 基本パッケージ情報
  - パッケージバージョンを `__version__ = "0.1.0"` として定義。
  - public API として主要サブパッケージ（data, strategy, execution, monitoring）を `__all__` に公開。

- 環境設定管理 (src/kabusys/config.py)
  - .env ファイルと環境変数を読み込む自動ローダーを実装。プロジェクトルートは `.git` または `pyproject.toml` を基準に探索するため、CWD に依存しない読み込みを実現。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロードを無効化可能。
  - .env の行パーサを実装（`export KEY=val` 形式・クォート・エスケープ・インラインコメント処理に対応）。
  - .env 読み込み時、OS 環境変数を保護する機能（protected set）を実装。
  - `Settings` クラスを提供し、各種設定値をプロパティ経由で取得可能（例: `JQUANTS_REFRESH_TOKEN`, `KABU_API_PASSWORD`, `DUCKDB_PATH` 等）。
  - 設定値のバリデーション実装（`PAPER_FILL_MODE`, `KABUSYS_ENV`, `LOG_LEVEL` 等）。未設定の必須キーは `ValueError` を送出。

- ポートフォリオ構築モジュール (src/kabusys/portfolio)
  - 銘柄選定: `select_candidates` を追加（スコア降順、同点は signal_rank でブレーク）。
  - 重み計算: `calc_equal_weights`, `calc_score_weights` を追加。スコア合計が 0 の場合は等金額配分にフォールバックし WARN ログを出力。
  - リスク調整:
    - `apply_sector_cap` を実装。同一セクターの既存保有比率が閾値を超える場合、新規候補を除外（"unknown" セクターは除外対象外）。
    - `calc_regime_multiplier` を実装。市場レジーム（'bull'/'neutral'/'bear'）に応じた投下資金乗数を返却し、未知レジームは 1.0 にフォールバック（警告ログ）。
  - 株数決定:
    - `calc_position_sizes` を実装。`risk_based`, `equal`, `score` の配分方式に対応。
    - 単元株（lot_size）での丸め、per-position 上限、aggregate cap（利用可能現金とのスケーリング）、手数料・スリッページの保守的見積もり（cost_buffer）を考慮。
    - キャッシュ不足時のスケーリングは、小数端数や lot_size 単位での再配分（残差処理）を行い再現性を保持。

- リサーチ／ファクター計算 (src/kabusys/research)
  - DuckDB を用いた純粋関数群を追加:
    - `calc_momentum`：1M/3M/6M リターン、200 日 MA 乖離の計算。
    - `calc_volatility`：20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率の計算。
    - `calc_value`：最新財務データ（raw_financials）と株価から PER, ROE を計算。
    - `calc_forward_returns`：指定ホライズンの将来リターンを一括で取得（可変ホライズン対応、入力検証あり）。
    - `calc_ic` / `rank`：ファクターと将来リターンのスピアマンランク相関（IC）計算、ランク付け（同順位は平均ランク）。
    - `factor_summary`：各ファクター列の基本統計量（count/mean/std/min/max/median）を算出。
  - 設計方針として external ライブラリ（pandas 等）を利用せず標準ライブラリと DuckDB のみで完結する実装を採用。
  - ログ出力により処理状況を追跡可能。

- AI 関連機能 (src/kabusys/ai)
  - ニュース NLP（src/kabusys/ai/news_nlp.py）
    - raw_news と news_symbols から銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini）を用いてセンチメントスコア（-1.0〜1.0）を計算し `ai_scores` テーブルへ書き込む `score_news` を実装。
    - タイムウィンドウ計算（JST 基準 → UTC 変換）を提供する `calc_news_window`。
    - バッチ処理（最大 20 銘柄/コール）、1 銘柄あたり記事数・文字数制限（_MAX_ARTICLES_PER_STOCK, _MAX_CHARS_PER_STOCK）、JSON Mode を想定したレスポンスバリデーションを実装。
    - リトライ（429, ネットワーク, タイムアウト, 5xx）と指数バックオフを実装。失敗時は当該チャンクをスキップしプロセス継続（フェイルセーフ）。
    - レスポンス検証は厳密に実施（JSON 抽出、results リスト、code/score の型チェック、スコアを ±1.0 でクリップ）。
    - DuckDB への書き込みは部分的な失敗時に他コードの既存スコアを保護するため、該当コードのみ DELETE→INSERT を実施（トランザクション、ROLLBACK 対応）。
    - テスト容易性のため OpenAI 呼び出し箇所は差し替え可能（モック推奨）。
  - レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321（日経連動型）の ma200 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して 'bull'/'neutral'/'bear' を判定する `score_regime` を実装。
    - マクロニュースの抽出はキーワード照合（複数キーワード）で行い、LLM による評価は記事がある場合のみ実行。API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
    - レジームスコアは閾値によりラベル付けされ、結果は `market_regime` テーブルに冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - news_nlp とは依存を切り分け、API 呼び出しはモジュールごとに独立実装。こちらもテスト用の差し替え可能実装あり。

- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - SQLite を用いた監視用 DB 初期化関数 `init_monitoring_db` を実装。`system_status`, `trade_logs`, `positions`, `risk_logs` などのテーブルとインデックスを冪等的に作成。

- モジュール公開 (各 __init__.py)
  - portfolio, research, ai の public 関数を __all__ で整理して公開。

### Changed
- （初期リリースのため該当なし）

### Fixed
- （初期リリースのため該当なし）

### Security
- OpenAI API キーは明示的に引数で渡すか環境変数 `OPENAI_API_KEY` を参照。未設定時は `ValueError` を送出し安全に失敗する設計。

### Performance
- DuckDB を用いて集計・ウィンドウ関数で効率的にファクター・将来リターンを計算。
- API バッチ処理とチャンク化によりリクエスト回数を低減。

### Notes / Known issues / TODO
- position_sizing:
  - lot_size を将来的に銘柄別に持たせる設計（stocks マスタ経由）へ拡張する TODO をコメントで残す。
- apply_sector_cap:
  - price_map に 0.0（欠損）がある場合にエクスポージャーが過少見積りされてセクター上限が回避されてしまう可能性がある点をコメントで指摘。将来的にフォールバック価格（前日終値等）を導入する予定。
- DuckDB の executemany は空リストを受け付けないバージョン差異があるため、INSERT/DELETE 前に空リストチェックを実装している。
- AI モジュール:
  - JSON モードでも余計な前後テキストが混入する可能性があるため、パース時に最外の `{...}` を抽出する復元処理を実装しているが、完全ではないケースがありうる。
- 時刻取り扱い:
  - ルックアヘッドバイアス防止のため、global な datetime.today()/date.today() を参照せず、対象日（target_date）ベースで処理する方針を採用。

---

このリリースは初期の機能群を含み、リサーチ、ポートフォリオ構築、AI を用いたセンチメント/レジーム判定、環境設定管理、監視ログの永続化を一通りカバーしています。今後はテストカバレッジの拡充、エラーケースの追加強化、パフォーマンス最適化、単元株/価格フォールバック等の拡張を予定しています。