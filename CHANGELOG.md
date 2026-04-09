# Changelog

すべての notable な変更はこのファイルに記録します。
フォーマットは「Keep a Changelog」に準拠しています。  
このプロジェクトはセマンティックバージョニング（http://semver.org/）を採用しています。

なお、本CHANGELOGは提示されたソースコードから実装内容を推測して作成しています。

## [Unreleased]

## [0.1.0] - 2026-04-09
初回公開リリース。

### Added
- 基本パッケージ定義
  - kabusys パッケージの初期バージョン（__version__ = 0.1.0）。
  - パッケージ公開時にエクスポートする主要モジュール群を定義（data, strategy, execution, monitoring）。

- 環境設定・.env 管理（src/kabusys/config.py）
  - .env / .env.local からの自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を探索）。
  - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き許可）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD 環境変数で自動ロードを無効化可能（テスト用）。
  - .env 行パーサを実装（コメント行・export 形式・クォート・エスケープ対応、インラインコメント判定等）。
  - 環境変数必須チェック用 _require() と、各種設定プロパティ（J-Quants/LINE/kabu API、DB パス、監視パラメータ、運用環境/ログレベル等）を提供。
  - validation を実装（PAPER_FILL_MODE / KABUSYS_ENV / LOG_LEVEL などの有効値チェック）。

- ポートフォリオ構築（src/kabusys/portfolio/）
  - portfolio_builder:
    - select_candidates: BUY シグナルをスコア降順 + タイブレークで選定。
    - calc_equal_weights: 等金額配分。
    - calc_score_weights: スコア比率に基づく配分（全スコアが 0 の場合は等配分にフォールバックし警告）。
  - risk_adjustment:
    - apply_sector_cap: 既存保有のセクター比率が上限を超える場合に当該セクターの新規候補を除外（unknown セクターは除外対象外）。
    - calc_regime_multiplier: 市場レジームに応じた投下資金乗数（bull/neutral/bear、未知レジームはフォールバックで 1.0）。
  - position_sizing:
    - calc_position_sizes: allocation_method（risk_based / equal / score）に応じて発注株数を計算。
    - 単元（lot_size）丸め、1 銘柄上限、aggregate cap（available_cash によるスケーリング）を実装。
    - cost_buffer を考慮した保守的見積もり、スケールダウン時の端数処理（lot 単位で残差を大きい順に追加配分）を実装。
    - risk_based では stop_loss_pct / risk_pct に基づく計算を行う。

- リサーチ・ファクター計算（src/kabusys/research/）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日移動平均乖離 (MA200) を DuckDB 上で計算。
    - calc_volatility: 20 日 ATR、ATR 比率、20 日平均売買代金、出来高比率を計算（true_range の NULL 伝播を注意深く扱う）。
    - calc_value: latest raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS が 0/NULL の場合は None）。
    - DuckDB を利用した SQL + Python のハイブリッド実装により外部 API へ依存しない設計。
  - feature_exploration:
    - calc_forward_returns: target_date 基準の将来リターンを複数ホライズンで計算（単一クエリで取得）。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算（有効レコード < 3 の場合は None）。
    - rank / factor_summary: ランク計算（同順位は平均ランク）および基本統計量（count/mean/std/min/max/median）を算出。内部で丸め処理により ties の扱いを安定化。

- AI（LLM）連携機能（src/kabusys/ai/）
  - news_nlp:
    - calc_news_window: ニュース収集ウィンドウ（JST → UTC 変換）を計算。
    - score_news: raw_news と news_symbols を集約して OpenAI（gpt-4o-mini）にバッチ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ書き込み。処理はチャンク（最大 20 銘柄）単位。
    - レスポンスの堅牢なバリデーション（JSON 抽出、results 配列、code/score 検査、スコアの有限性検査）・スコアの ±1.0 クリッピングを実装。
    - 冪等的な DB 書き込み（DELETE → INSERT、トランザクション制御）を実装。DuckDB の executemany の制約に配慮。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライと、その他エラー時はフェイルセーフでスキップ（例外を上げない挙動）。
    - テスト容易性のため _call_openai_api をモック差替え可能。
  - regime_detector:
    - ETF（1321）MA200 乖離とマクロニュースの LLM センチメントを合成して日次の market_regime（bull/neutral/bear）を判定・永続化。
    - マクロキーワード検索、LLM 呼出し（JSON 応答期待）、スコア合成ロジック（重み付け・閾値）を実装。
    - LLM エラー時はマクロセンチメントを 0.0 にフォールバックするフェイルセーフ。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - news_nlp.calc_news_window を再利用してウィンドウ計算を統一。

- 監視ログ永続化（src/kabusys/monitoring/monitoring_db.py）
  - init_monitoring_db: SQLite で利用する監視用スキーマを冪等的に作成するスクリプトを実装。
    - system_status / trade_logs / positions / risk_logs 等のテーブルとインデックス作成をサポート（初期スキーマの用意）。

### Changed
- （初回リリースのため該当なし）

### Fixed
- （初回リリースのため該当なし）

### Security
- OpenAI API キーや各種シークレットは環境変数参照により管理。config モジュールで必須項目は _require() により未設定時に明示的なエラーを発生させる（誤設定検出を容易にする）。

### Notes / Implementation details / Known limitations
- research モジュールは DuckDB のテーブル（prices_daily / raw_financials / raw_news 等）に依存。外部 API によるデータ取得は行わない想定。
- news_nlp と regime_detector は OpenAI SDK（OpenAI クライアント）に依存するため、実行環境で OPENAI_API_KEY の設定が必要。
- .env パーサは基本的なケース（export, quoted values, inline comments）に対応しているが、極端な edge case は未検証。
- apply_sector_cap:
  - price_map に price が欠損（0.0）だとエクスポージャーが過少評価される可能性がある旨を TODO コメントで注記。将来的に前日終値等でフォールバックする余地あり。
- position_sizing:
  - 将来的な拡張として銘柄毎の lot_size を導入することが想定されている（現状はグローバル lot_size）。
- テスト支援:
  - OpenAI API 呼び出し箇所は内部関数を patch することで外部 API を呼ばずにテスト可能な設計になっている（_call_openai_api を差し替え）。

(以降のリリースでは各機能の微細な改善、エッジケースへの対応、不具合修正、パフォーマンス改善等を記録予定)
