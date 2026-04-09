# CHANGELOG

すべての注目すべき変更を記録します。フォーマットは「Keep a Changelog」に準拠しています。

注：以下の変更点は提供されたソースコードから推測して作成した初期リリース向けの変更履歴です。

## [0.1.0] - 2026-04-09
### Added
- パッケージ初期リリース。
- 基本情報
  - パッケージ名: kabusys
  - バージョン: 0.1.0

- 環境設定管理（src/kabusys/config.py）
  - .env / .env.local ファイルおよび OS 環境変数から設定を読み込む自動ローダーを実装。
  - プロジェクトルート検出のために __file__ を起点に親ディレクトリを探索（.git または pyproject.toml を基準）。プロジェクトルートが見つからない場合は自動読み込みをスキップ。
  - .env 行パーサーを実装（コメント、export プレフィックス、シングル/ダブルクォート・エスケープ、インラインコメント処理等に対応）。
  - 自動読み込みは環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で無効化可能。
  - 主要設定プロパティ提供（J-Quants トークン、kabu API パスワード／ベース URL、LINE トークン／ユーザ、DB パス、Paper Trading 用設定、監視パラメータ、環境（development/paper_trading/live）、ロギングレベルなど）。
  - 設定のバリデーション実装：
    - KABUSYS_ENV の有効値チェック（development/paper_trading/live）。
    - LOG_LEVEL の有効値チェック（DEBUG/INFO/WARNING/ERROR/CRITICAL）。
    - PAPER_FILL_MODE の有効値チェック（instant/partial/never/reject）。
  - 必須環境変数未設定時は明確な ValueError を発生させるユーティリティ `_require()` を提供。

- ポートフォリオ構築（src/kabusys/portfolio/*）
  - 銘柄選定
    - select_candidates: BUY シグナルをスコア降順（同点は signal_rank 昇順でタイブレーク）でソートして上位 N を返す。
  - 重み計算
    - calc_equal_weights: 等金額配分を返す。
    - calc_score_weights: スコア比率に基づく加重配分を返す。全スコアが 0 の場合は等金額にフォールバックし WARN 出力。
  - 単元・株数計算（position_sizing）
    - calc_position_sizes: allocation_method に応じて発注株数を計算（"risk_based", "equal", "score" をサポート）。
    - risk_based: 許容リスク率、損切り率に基づく株数算出。
    - equal/score: 重みと price から各銘柄の割当額を算出。
    - lot_size（単元株）考慮、max_per_stock（1銘柄上限）、max_utilization（投下資金上限）を適用。
    - cost_buffer（手数料・スリッページの保守的見積）を考慮した aggregate cap（利用可能現金を超える場合のスケーリング）を実装。スケーリング後の端数は lot_size 単位で残差を大きい順に再配分するアルゴリズムを採用。
    - 価格欠損時は銘柄をスキップし、デバッグログを出力。
  - リスク調整（risk_adjustment）
    - apply_sector_cap: 既存保有のセクター別エクスポージャーが上限を超える場合、そのセクターの新規候補を除外（"unknown" セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジーム（"bull"/"neutral"/"bear"）に応じた資金乗数（1.0/0.7/0.3）を返す。未知のレジームは 1.0 にフォールバックして警告ログを出力。

- リサーチ / ファクター算出（src/kabusys/research/*）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、MA200 乖離（ma200_dev）を計算。ウィンドウ内データ不足時は None を返す仕様。
    - calc_volatility: 20日 ATR（atr_20）・相対 ATR（atr_pct）・20日平均売買代金（avg_turnover）・出来高比（volume_ratio）を計算。true_range 計算で high/low/prev_close の NULL 伝播を厳密に扱う。
    - calc_value: raw_financials の target_date 以前の最新財務情報と prices_daily を組み合わせて PER / ROE を計算（EPS が 0 や NULL の場合は PER を None）。
  - feature_exploration
    - calc_forward_returns: target_date 終値から指定ホライズン先の終値までの将来リターンを計算（複数ホライズンを一括取得、horizons の検証を実施）。
    - calc_ic: factor と将来リターンのスピアマンランク相関（IC）を計算。有効レコードが 3 未満の場合は None。
    - rank: 同順位の平均ランクを返す実装（浮動小数誤差対策として round を使用）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算（None を除外）。

- AI 関連（src/kabusys/ai/*）
  - ニュース NLP（news_nlp.py）
    - score_news: raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄別センチメントを計算して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 _BATCH_SIZE=20 銘柄）・1銘柄あたり最大記事数・文字数制限（トークン肥大化対策）を実装。
    - JSON Mode を使用したレスポンス受け取りと、JSON パースの堅牢化（前後余計テキストの復元）を実装。
    - スコアは ±1.0 にクリップ。レスポンス検証（results 配列、code と score の型、既知コードチェック）を実施。検証失敗のアイテムは無視。
    - エラーハンドリング: 429/ネットワーク/タイムアウト/5xx は指数バックオフでリトライ。その他はスキップして継続（フェイルセーフ）。部分成功時には該当コードのみ DELETE→INSERT（冪等的かつ部分失敗時に既存データを保護）。
    - OpenAI API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を投げる。
  - 市場レジーム判定（regime_detector.py）
    - score_regime: ETF 1321 の MA200 乖離（重み 70%）とマクロセンチメント（LLM、重み 30%）を合成して日次のレジーム（bull/neutral/bear）を判定し、market_regime テーブルへ冪等書き込み。
    - マクロニュースはキーワードマッチでタイトルを抽出し、LLM でセンチメント評価。記事が無い場合または API 失敗時は macro_sentiment=0.0 として処理を継続。
    - LLM 呼び出しに対するリトライとエラーハンドリングを実装。未知のレスポンスやパース失敗時は 0.0 にフォールバックして警告ログを出力。
    - API キーは引数または環境変数 OPENAI_API_KEY から取得。未設定時は ValueError を投げる。

- モニタリング DB（src/kabusys/monitoring/monitoring_db.py）
  - init_monitoring_db: SQLite 接続に対して監視用のテーブル群（system_status, trade_logs, positions, risk_logs など）とインデックスを冪等的に作成するスクリプトを提供（永続化層）。

- パッケージエクスポート
  - src/kabusys/__init__.py にて __version__ を定義（"0.1.0"）し、主要サブパッケージを __all__ に宣言。
  - research と portfolio パッケージで利用しやすい名前で関数をエクスポート（__all__ を整備）。

### Changed
- （初回リリースのため無し）

### Fixed
- （初回リリースのため無し）

### Security
- OpenAI API キー等の機密情報は環境変数から取得する設計とし、.env 自動読み込みはプロジェクトルートの検出が成功した場合のみ行うことで配布後の安全性に配慮。

### Notes / 注意事項
- .env 自動ロードの挙動:
  - 読み込み優先順位は OS 環境変数 > .env.local > .env。
  - OS 環境変数は protected として .env による上書きを防止。
  - プロジェクトルートが見つからない場合、自動ロードはスキップされる（パッケージ配布後の安全策）。
  - テスト等で自動ロードを無効化するには環境変数 `KABUSYS_DISABLE_AUTO_ENV_LOAD=1` を設定する。
- OpenAI 関連処理は外部 API に依存するため、テスト時は各モジュール（news_nlp._call_openai_api, regime_detector._call_openai_api 等）をモックすることを推奨。
- DuckDB / SQLite クエリは特定のバージョン依存や executemany の空リスト制約（例: DuckDB 0.10）を考慮した実装になっているため、運用環境の DB バージョンに応じた動作確認を行ってください。
- 一部関数はデータ欠損時に安全側のフォールバック値（例: ma200_ratio=1.0、macro_sentiment=0.0）を返す設計のため、運用上は警告ログを監視してください。

--- 

今後のリリース候補（例）
- 未実装 / 検討中: PBR・配当利回りの計算、銘柄別 lot_size のサポート（stocks マスタ）、価格欠損時のフォールバック価格採用など。