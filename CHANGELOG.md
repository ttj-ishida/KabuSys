# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠しています。  
フォーマット: 主なリリース / 日付 → セクション (Added, Changed, Fixed, etc.)

## [Unreleased]
- ドキュメント・コードの細かな改善やテストの追加など（作業中）。

---

## [0.1.0] - 2026-04-09
初回リリース。日本株自動売買システムのコアユーティリティ群を実装。

### Added
- パッケージ基盤
  - パッケージ初期化（kabusys.__init__）にバージョン `0.1.0` と主要サブモジュールの exports を追加。

- 環境変数 / 設定管理（src/kabusys/config.py）
  - .env / .env.local の自動ロード機能を実装（プロジェクトルートを .git / pyproject.toml から探索）。
  - ロード順: OS 環境変数 > .env.local > .env（.env.local は上書き許可、OS 環境変数は保護）。
  - 自動ロード抑止用フラグ: `KABUSYS_DISABLE_AUTO_ENV_LOAD=1`。
  - .env パーサは export 形式、クォート（シングル/ダブル）およびバックスラッシュエスケープ、インラインコメントの処理に対応。
  - Settings クラスを提供し、アプリケーション設定（API トークン・パス・閾値・環境・ログレベル等）をプロパティ経由で取得。
  - 設定値のバリデーション:
    - PAPER_FILL_MODE（instant/partial/never/reject）
    - KABUSYS_ENV（development/paper_trading/live）
    - LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL）
  - ファイルパス系設定は Path 型で返却し expanduser を適用。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - select_candidates: BUY シグナルをスコア降順にソートして上位 N 件を選択。
  - calc_equal_weights / calc_score_weights: 等金額配分・スコア加重配分を提供。全スコアが 0 の場合は等金額にフォールバックし WARN ログを出力。
  - calc_position_sizes:
    - 発注株数算出ロジック（risk_based / equal / score）を実装。
    - lot_size（単元）丸め、1銘柄上限、利用可能現金に対する aggregate cap のスケーリング、cost_buffer を用いた保守的見積りを実装。
    - スケールダウン時の再配分は端数（fractional remainder）順で lot 単位で割り当てるアルゴリズムを採用。
  - リスク調整（risk_adjustment）:
    - apply_sector_cap: 既存保有のセクター別エクスポージャを算出し、セクター比率が閾値超過のセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数（1.0 / 0.7 / 0.3）を提供。未知レジームは 1.0 でフォールバックし WARN を出力。

- リサーチ（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（DuckDB の prices_daily を使用）。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を結合し PER / ROE 計算（最新財務レコードの取得）。
    - すべて DuckDB クエリベースで実装し、外部 API には依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン先の将来リターン（LEAD ベース）を計算。horizons の検証あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装。データ不足（有効レコード < 3）の場合は None を返す。
    - rank: 同順位は平均ランクで処理。浮動小数丸め誤差対策に round(..., 12) を導入。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリ関数を実装。
  - research パッケージは zscore_normalize（kabusys.data.stats から）などを __all__ で再エクスポート。

- AI（自然言語）機能（src/kabusys/ai/*）
  - news_nlp.score_news:
    - raw_news + news_symbols からニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）でセンチメントを取得して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 _BATCH_SIZE=20）・1銘柄あたりの文字数/記事数上限（トリム）を導入。
    - API 呼び出しはリトライ（429 / ネットワーク / タイムアウト / 5xx）を実装。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスの堅牢なバリデーション（JSON モードでも前後余分テキストを抽出可能）とスコアクリップ（±1.0）。
    - DuckDB への書き込みはトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等性を担保。部分失敗時に既存スコアを保護するため対象コードのみを DELETE → INSERT。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得（未設定時は ValueError）。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日 MA 乖離とマクロニュースの LLM センチメントを組み合わせて日次レジーム（bull/neutral/bear）を判定。
    - LLM 呼び出しは news_nlp と独立した内部実装（モジュール結合回避）。
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。データ不足時は中立（1.0）でフォールバックし WARN を出力。
    - マクロニュース抽出はキーワードベースの ILIKE 検索を実施（最大件数制限）。
    - 合成スコアは重み付け（MA 70%, マクロ 30%）、閾値によりラベル決定。LLM 失敗時は macro_sentiment=0.0 で継続。
    - 市場レジームの DB 書き込みは冪等（BEGIN / DELETE / INSERT / COMMIT）。

- 監視 DB（src/kabusys/monitoring/monitoring_db.py）
  - SQLite を用いた監視ログ永続化層を追加。
  - system_status / trade_logs / positions / risk_logs ... 等のテーブルとインデックスを作成する初期化関数を実装（冪等性あり）。

- モジュール導出
  - portfolio、research、ai などの主要関数をパッケージトップでエクスポート（__all__ の整備）。

### Changed
- なし（初回リリースのため）。

### Fixed
- なし（初回リリースのため）。

### Notes / Implementation details / Safety
- ルックアヘッドバイアス防止: date.today() / datetime.today() を参照しない設計を徹底（target_date を明示的に渡す設計）。
- OpenAI API 呼び出し部はテスト容易性のため直接呼び出し箇所をプライベート関数にして差し替え可能にしている（unittest.mock.patch によるモック想定）。
- DuckDB / SQLite 周りの executemany 空リスト制約など実運用上の注意点を考慮した実装（空リストは実行しないガードを配置）。
- ロギングを多用し、データ不足・異常系は WARN/INFO/DEBUG ログで可視化することで運用上の原因追跡を容易にしている。

--- 

今後の予定（例）
- 戦略実行エンジン / ブローカークライアントの実装
- テストカバレッジ強化（特に OpenAI 呼び出しと DuckDB クエリ）
- 銘柄単位の lot_size マスタ対応（position_sizing の拡張）
- factor 群・リスク管理の追加パラメータ化

（必要であれば、各ファイル単位の詳細な変更点や設計上の決定理由を追記します。）