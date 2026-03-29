# Changelog

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠しています。  
このファイルでは、リポジトリ内の現行コードベースから推測される機能追加・設計方針・振る舞いをまとめています。

## [0.1.0] - 2026-03-29

### Added
- パッケージ初期リリースとして kabusys 名前空間を追加。
  - src/kabusys/__init__.py にてバージョン `0.1.0` を定義。公開モジュールとして data, strategy, execution, monitoring を列挙。

- 環境設定管理モジュールを追加（src/kabusys/config.py）。
  - .env / .env.local 自動読み込み機能（プロジェクトルート検出: .git または pyproject.toml を基準）。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。`KABUSYS_DISABLE_AUTO_ENV_LOAD=1` で自動ロード無効化可能。
  - .env パーサは `export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント処理に対応。
  - 既存 OS 環境変数を保護するための protected キーセットを考慮して上書き制御。
  - Settings クラスで主要設定値をプロパティ経由で提供：
    - JQUANTS_REFRESH_TOKEN（必須）
    - KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト: http://localhost:18080/kabusapi）
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（必須）
    - DUCKDB_PATH（デフォルト: data/kabusys.duckdb）, SQLITE_PATH（デフォルト: data/monitoring.db）
    - KABUSYS_ENV の検証（許容値: development, paper_trading, live）とログレベル検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - ヘルパー: is_live / is_paper / is_dev

- ニュースNLP（AI）モジュールを追加（src/kabusys/ai/news_nlp.py）。
  - 指定日の前日 15:00 JST ～ 当日 08:30 JST の記事を対象に、銘柄ごとに OpenAI (gpt-4o-mini) を用いてセンチメントを算出。
  - タイムウィンドウ計算（calc_news_window）を実装。
  - 記事集約: raw_news と news_symbols を結合して各銘柄ごとに最新最大 N 記事（デフォルト 10）をトリムし結合。
  - バッチ処理: 最大 20 銘柄をまとめて API へ送信。
  - レスポンス取得と検証:
    - OpenAI JSON Mode（厳密JSON）を期待、だが余計なテキスト混入時も中括弧抽出で復元を試みる。
    - results 配列の存在、各要素の code/score 検証、未知コードは無視、スコアは ±1.0 にクリップ。
  - ネットワーク・429・タイムアウト・5xx に対する指数バックオフリトライ実装。非リトライエラーはスキップして継続（フェイルセーフ）。
  - 書き込み: 成功したコードのみ ai_scores テーブルの当該日分を置換（DELETE→INSERT）し、部分失敗時に既存データを保護。
  - テスト容易性として、内部の OpenAI 呼び出し関数を patch で差し替え可能な実装を提供。

- レジーム検知モジュールを追加（src/kabusys/ai/regime_detector.py）。
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロ経済ニュースの LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を判定。
  - prices_daily から ETF データを参照して ma200_ratio を計算（target_date 未満のデータのみ使用してルックアヘッドを防止）。
  - マクロ記事は news_nlp.calc_news_window に基づく時間範囲で抽出し、内部 LLM 呼び出しで macro_sentiment を取得（記事が無い場合は LLM 呼出しなしで 0.0）。
  - OpenAI 呼び出しに対するリトライ、API エラー時は macro_sentiment を 0.0 にフォールバック。
  - 結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT）。DB エラー時は ROLLBACK を試行して例外を伝播。

- データプラットフォーム関連モジュールを追加
  - calendar_management（src/kabusys/data/calendar_management.py）
    - market_calendar を用いた営業日判定および参照ヘルパー:
      - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day
    - DB にカレンダーデータがない場合は曜日ベースのフォールバック（土日除外）。
    - next/prev/get_trading_days は DB の登録値を優先しつつ未登録日は曜日フォールバックで扱う。最大探索日数を設定して無限ループ防止。
    - 夜間バッチ calendar_update_job により J-Quants API から差分取得し market_calendar を更新。バックフィル、健全性チェックを実装。
    - jquants_client 経由での fetch/save 処理に依存。

  - pipeline / etl（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
    - ETLResult データクラスを実装し、ETL の取得数・保存数・品質問題・エラー概要を表現。
    - _get_max_date 等の DB ユーティリティを実装。
    - 差分取得、バックフィル、品質チェック（quality モジュール経由）を想定した設計（実装の呼び出しフローはコードから推測）。
    - etl モジュールは ETLResult を再エクスポート。

- 研究（Research）モジュールを追加（src/kabusys/research/*）。
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、ATR 比率（atr_pct）、平均売買代金、出来高比率を計算。ウィンドウ不足時は None。
    - calc_value: raw_financials から最新財務を取得し PER / ROE を計算（EPS が 0/欠損時は None）。（PBR/配当利回りは未実装）
  - feature_exploration:
    - calc_forward_returns: 指定 horizon の将来リターンを一括して取得（デフォルト [1,5,21]）。horizons の検証あり。
    - calc_ic: factor_records と forward_records を code で結合して Spearman のランク相関（IC）を計算。有効レコード < 3 の場合は None。
    - rank: 値をランクに変換（同順位は平均ランク）。丸めによる ties 検出を工夫。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリ関数。
  - research パッケージは主要関数を再エクスポートしている。

### Changed
- （初期リリースのため該当なし）ただし各モジュールは以下の設計方針を明示:
  - ルックアヘッドバイアス防止のため datetime.today() / date.today() を評価に直接使用しない（target_date を明示引数として扱う）。
  - 外部 API 呼び出しはフェイルセーフで扱い、API エラー時はスコアを 0.0 にフォールバックする等、上位処理の継続を優先。
  - DuckDB のバージョン差異（executemany の空リスト制約やリスト型バインドの不安定性）を考慮した実装を採用。

### Fixed
- .env パーサ強化:
  - export プレフィックス、クォート内エスケープ、インラインコメントの取り扱いを改善。
  - ファイル読み込み失敗時に warning を出す（IOError を抑えて処理継続）。

### Internal / テスト向け
- OpenAI 呼び出し箇所は内部関数化しており、テストで patch して差し替え可能（news_nlp._call_openai_api / regime_detector._call_openai_api）。
- DuckDB 依存の SQL クエリは明示的にコメント・条件分岐を入れて互換性や NULL 伝播を制御している。

### Security & Errors
- 必須環境変数が未設定の場合は Settings のプロパティが ValueError を送出する（早期検出）。
- API 呼び出し中の致命的な DB 書き込み失敗時は例外を伝播させ、可能であれば ROLLBACK を試行する実装。

---

注記:
- 上記はソースコード（2026-03-29 時点）から推測して作成した CHANGELOG です。実際のリリースノートでは動作確認済みの変更点・互換性情報・マイグレーション手順などを追記してください。