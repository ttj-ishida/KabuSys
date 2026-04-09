# CHANGELOG

すべての変更は Keep a Changelog の形式に準拠して記載します。  
各項目はコードベースから推測される追加・改善・修正点をまとめたものです。

全体バージョン: 0.1.0 — 2026-04-09

## [0.1.0] - 2026-04-09

### 追加 (Added)
- 基本パッケージ初期構成
  - パッケージメタ情報 (src/kabusys/__init__.py) に __version__ = "0.1.0" を設定。

- 環境変数 / 設定管理モジュール (src/kabusys/config.py)
  - .env ファイルおよび環境変数からの設定読み込みを実装。プロジェクトルートを .git または pyproject.toml から自動検出して自動ロードを行う。
  - 自動ロードの無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - .env 読み込みの優先順位: OS 環境変数 > .env.local > .env。
  - .env パーサを実装（export プレフィックス対応、クォート／エスケープ処理、インラインコメントの扱い）。
  - 環境変数取得ラッパ（Settings クラス）を提供。主要設定（J-Quants, kabuAPI, LINE, DB パス, 監視閾値, 実行環境・ログレベル等）をプロパティで取得。
  - 設定値の妥当性チェックを追加（KABUSYS_ENV、LOG_LEVEL、PAPER_FILL_MODE 等の許容値検証）。

- ポートフォリオ構築関連 (src/kabusys/portfolio/)
  - 銘柄選定・配分:
    - select_candidates: BUY シグナルをスコア降順 / signal_rank タイブレークで上位 N 件を選択。
    - calc_equal_weights: 等金額配分（各銘柄 1/N を返す）。
    - calc_score_weights: スコア加重配分（スコア合計が 0 の場合は等金額にフォールバックし WARNING を出力）。
  - リスク調整:
    - apply_sector_cap: セクター別上限（max_sector_pct）を既存ポジションのエクスポージャから判定し、新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（bull/neutral/bear）に応じた投下資金乗数を返す（未定義レジームはフォールバックで 1.0）。
  - 建玉サイズ計算:
    - calc_position_sizes: allocation_method（"risk_based" / "equal" / "score"）に応じて発注株数を計算。単元(lot_size)丸め、1銘柄上限、aggregate cap（available_cash に対するスケーリング）、cost_buffer による保守的コスト見積り、残差配分ロジックを実装。

- リサーチ / ファクター計算 (src/kabusys/research/)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離を DuckDB 上で計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（最新レポートの取得ロジックあり）。
  - feature_exploration:
    - calc_forward_returns: 指定ホライズンの将来リターンを一括クエリで計算（ホライズンの検証あり）。
    - calc_ic: スピアマンランク相関（IC）を計算（非数 / None を除外、サンプル数不足は None を返す）。
    - rank: 同順位は平均ランクにするランク関数（丸めで ties の誤検出を防止）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - DuckDB 接続を受け取り、prices_daily / raw_financials テーブルのみを参照する設計。

- AI（LLM）関連機能 (src/kabusys/ai/)
  - ニュース NLP スコアリング (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols を集約して LLM（gpt-4o-mini）へバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込む。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）、記事数／文字数トリム、429/タイムアウト/5xx に対する指数バックオフリトライ、レスポンスバリデーション（JSON 抽出、results 構造検査、未知コードの無視、スコアの数値化・有限確認）、スコア ±1.0 クリップを実装。
    - DB 書き込みは冪等（DELETE → INSERT）で行い、部分失敗時に既存スコアを保護する実装。
    - OpenAI API キーの解決（引数優先/環境変数 OPENAI_API_KEY）と未設定時のエラーメッセージを実装。
  - 市場レジーム判定 (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（ma200_ratio）と、マクロニュースの LLM センチメントを合成して日次レジームを判定（'bull' / 'neutral' / 'bear'）。
    - マクロニュースはキーワード（_MACRO_KEYWORDS）でフィルタし、LLM 呼び出しは記事がある場合のみ行う。API 失敗時は macro_sentiment=0.0 でフォールバック。
    - 判定スコア合成と閾値判定、market_regime テーブルへの冪等書き込みを実装。
  - AI モジュールは OpenAI Python SDK を用いており、テスト時に内部呼び出しを差し替え可能な設計（_call_openai_api をモック可能）。

- 監視ログ永続化 (src/kabusys/monitoring/monitoring_db.py)
  - SQLite を用いた MonitoringDB 初期化関数を実装（init_monitoring_db）。以下テーブル・インデックスの作成（冪等）を行う:
    - system_status（CPU/メモリ/ディスク/プロセス状態）
    - trade_logs（発注・約定ログ）
    - positions（保有ポジション）
    - risk_logs（リスク関連ログ） など（スクリプトの一部がファイル中に含まれる）。

### 変更 (Changed)
- 初期リリースのため過去バージョンからの変更はなし（新規実装）。

### 修正 (Fixed)
- .env パーシングと読み込みにおいて、ファイル読み込み失敗時に warnings.warn してスキップする安全策を追加。
- OpenAI API 呼び出しに対してリトライ・バックオフ・5xx判定等の堅牢化を実装（news_nlp と regime_detector の双方で類似ロジックを採用し、LLM 呼び出し失敗時でもフェイルセーフで継続）。

### セキュリティ (Security)
- OpenAI API キーの未設定時は明示的にエラーを発生させる（score_news / score_regime）。設定方法（引数または環境変数 OPENAI_API_KEY）をドキュメント内で明示。
- .env 自動ロードは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト用途のため）。

### 既知の制約・注意点 (Known issues / Notes)
- .env 読み込み時、プロジェクトルートが特定できない場合は自動ロードをスキップする（配布後の挙動を考慮）。
- apply_sector_cap: price_map に価格が欠損（0.0）がある場合、エクスポージャーが過少見積になり結果的にブロックされない恐れがある（TODO コメントあり — 前日終値や取得原価でのフォールバックを検討）。
- calc_position_sizes:
  - 単元サイズは現在すべての銘柄で共通の lot_size（デフォルト 100）を想定。将来的に銘柄別単位対応を検討する旨コメントあり。
  - aggregate cap スケーリングでは lot_size 単位での残差再配分ロジックにより再現性を確保しているが、極端な相場や欠損値の取り扱いに注意が必要。
- DuckDB / SQLite のバージョン依存性や executemany の空リスト制約（DuckDB 0.10）に合わせた実装上の配慮が行われている。

---

今後のリリース候補（例）
- テストカバレッジの明記・ユニットテスト追加（特に .env パーザ、LLM レスポンスのパース、DB 書き込みトランザクション）。
- ポートフォリオ構築の拡張（銘柄別 lot_size、価格フォールバック、手数料モデルの分離）。
- research モジュールの追加ファクター（PBR/配当利回り等）およびパフォーマンス最適化。