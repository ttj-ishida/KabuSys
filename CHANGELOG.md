# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
この CHANGELOG は与えられたコードベースの実装内容から推測して作成しています。

## [Unreleased]
- 開発中の変更や今後の改善予定を記載するセクションです。

---

## [0.1.0] - 2026-04-09

### 追加（Added）
- 基本情報
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - パッケージ公開用 __all__ を設定（data, strategy, execution, monitoring）。

- 環境設定管理（src/kabusys/config.py）
  - .env ファイルおよび環境変数から設定を自動読み込みする機能を追加。
    - プロジェクトルートを .git または pyproject.toml を基準に探索して自動ロード（CWD 非依存）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パースの強化:
    - export KEY=val 形式に対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理をサポート。
    - インラインコメントの扱い（クォートの有無に応じたコメント除去）。
  - .env 読み込み時の保護機能:
    - OS 環境変数を protected として .env で上書きされないよう保護。
    - .env.local は override=True で既存値を上書き（ただし protected を尊重）。
  - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得可能。
    - J-Quants / kabuステーション / LINE / DB /監視 /システム設定等のキーをラップ。
    - 各種バリデーションを実装（PAPER_FILL_MODE, KABUSYS_ENV, LOG_LEVEL 等）。
    - ファイルパスは Path オブジェクトとして返却し expanduser を適用。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - portfolio_builder:
    - select_candidates: score 降順で並び替え、同点は signal_rank の昇順でタイブレーク。
    - calc_equal_weights: 等金額配分（各重み = 1/N）。
    - calc_score_weights: スコア比率で重みを計算。全スコアが 0 の場合は等金額にフォールバックして WARNING ログ出力。
  - risk_adjustment:
    - apply_sector_cap: 既存ポジションのセクター別エクスポージャーを計算し、1セクター上限を超える場合に同セクターの新規候補を除外（"unknown" セクターは制限対象外）。
    - calc_regime_multiplier: レジームラベル（bull/neutral/bear）に応じた投下資金乗数を返却。未知レジームは警告ログと共に 1.0 にフォールバック。
  - position_sizing:
    - calc_position_sizes: risk_based / equal / score の各配分方式に対応して発注株数を計算。
    - lot_size（単元）に基づく丸め処理、銘柄別上限（max_position_pct）適用。
    - aggregate cap（利用可能現金 available_cash）超過時のスケールダウン実装。
    - cost_buffer により手数料・スリッページを保守的に見積もり集計判定に反映。
    - スケールダウン後の残余キャッシュで lot_size 単位の追加配分を fractional remainder に基づき決定（再現性確保のためコードで安定ソート）。

- リサーチ / ファクター計算（src/kabusys/research/*）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（MA200）を DuckDB の prices_daily から算出。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均出来高、出来高比率を計算。true_range は high/low/prev_close が NULL の場合に NULL を正しく伝播。
    - calc_value: raw_financials と prices_daily を結合して PER / ROE を計算。最新財務レコードを report_date <= target_date で取得。
  - feature_exploration:
    - calc_forward_returns: target_date から複数ホライズン先のリターンを一括取得。horizons 検証を実施（1〜252 営業日）。
    - calc_ic: スピアマンランク相関（IC）を計算。サンプル数が 3 未満なら None を返す。
    - rank: 同順位は平均ランク（round(v,12) により丸めて ties 検出）。
    - factor_summary: count/mean/std/min/max/median を算出（None 値は除外）。

- AI / ニュース NLP（src/kabusys/ai/*）
  - news_nlp.score_news:
    - raw_news + news_symbols を銘柄ごとに集約して OpenAI（gpt-4o-mini）でセンチメントを取得し、ai_scores テーブルへ書き込む機能を追加。
    - 処理のポイント:
      - ニュースウィンドウを JST ベース（前日 15:00 〜 当日 08:30）で計算し、UTC に変換して DB 比較。
      - 1銘柄あたりの記事数・文字数制限（_MAX_ARTICLES_PER_STOCK / _MAX_CHARS_PER_STOCK）。
      - 最大 _BATCH_SIZE（20 銘柄）ずつバッチで API 呼び出し。
      - 429 / ネットワーク断 / タイムアウト / 5xx に対して指数バックオフでリトライ。
      - レスポンス検証（JSON 抽出、results リスト、code/score チェック、既知コードのみ採用）。
      - スコアを ±1.0 にクリップして保存。
      - DuckDB への書込みは部分失敗を考慮して DELETE（対象コード）→ INSERT を executemany で冪等に実行（トランザクション管理）。
    - テスト容易化のため _call_openai_api を差し替え可能（unittest.mock.patch 対応）。

  - regime_detector.score_regime:
    - ETF 1321 の MA200 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ書き込む機能を追加。
    - マクロキーワードによる raw_news タイトル抽出、最大 _MAX_MACRO_ARTICLES 件。
    - LLM 呼び出しは retry とエラー時のフォールバック（macro_sentiment=0.0）を実装。
    - レジームスコア合成と閾値判定（BULL/BEAR 閾値）を実装し、冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。

- 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
  - init_monitoring_db: SQLite 接続に対して system_status / trade_logs / positions / risk_logs 等のテーブルとインデックスを冪等に作成するスクリプトを実装。

### 変更（Changed）
- なし（初回リリースのため該当なし）。

### 修正（Fixed）
- なし（初回リリースのため該当なし）。

### 既知の制約・注意点（Notes / Known issues）
- apply_sector_cap:
  - price_map に price が欠損（0.0）の場合、エクスポージャーが過少評価されセクター制限が外れる可能性あり。将来的に前日終値や取得原価でフォールバックする案がコメントに残されている。
- DuckDB の executemany 制約:
  - DuckDB 0.10 系では executemany に空リストを渡せないため、書き込み前に params の空チェックを行っている。
- レジーム判定 / ニュース NLP:
  - OpenAI API が必須（api_key 引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError を送出。
  - API 呼び出しは外部サービスに依存するため、失敗時はフォールバック（macro_sentiment=0.0 / スコア取得スキップ）する設計でフェイルセーフを重視。
- テスト支援:
  - OpenAI 呼び出し箇所（news_nlp._call_openai_api, regime_detector._call_openai_api）はユニットテストで差し替え可能に実装。
- 設定関連:
  - Settings の必須キーが存在しない場合は ValueError を投げる（ユーザに .env.example を参照するよう促すメッセージ）。
- 単元株（lot_size）:
  - 現状は全銘柄共通の lot_size（デフォルト 100）で処理。将来的には銘柄別 lot_size をサポートする TODO が残されている。

---

もし特定のリリースノート形式（例えば英語版、より詳細な差分、コミットや PR 番号の付加など）を希望される場合はお知らせください。コード中の TODO や警告ログに基づき、今後の改修候補も別途まとめることができます。