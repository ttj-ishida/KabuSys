Keep a Changelog に準拠した変更履歴を以下に日本語で作成しました。コード内容から推測して記載しています（初回リリース相当のまとめ、既知の挙動や構成項目も併記）。

CHANGELOG.md
============
すべての注目すべき変更はこのファイルで管理します。  
フォーマットは Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) に準拠します。

Unreleased
----------
（なし）

0.1.0 - 2026-03-31
------------------
初回公開リリース。以下の主要機能と設計方針を実装しています。

Added
- パッケージ基礎
  - kabusys パッケージを追加。__version__ = "0.1.0"。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ に設定。

- 設定 / 環境変数
  - 環境変数/設定管理モジュールを追加（kabusys.config）。
  - プロジェクトルート探索 (.git または pyproject.toml) に基づく自動 .env ロード機能を実装。
  - .env と .env.local の読み込み順序を定義（OS 環境変数を保護しつつ .env.local を上書き）。
  - .env パーサ: export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントを適切に処理。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化をサポート。
  - Settings クラスを追加し、主要設定プロパティを提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH, CPU/MEMORY/DISK の閾値, KABUSYS_ENV, LOG_LEVEL 等）。
  - 環境変数の必須チェック (_require) と値バリデーション（env, log_level）を実装。

- AI（ニュース NLP / レジーム判定）
  - kabusys.ai.news_nlp: raw_news を OpenAI（gpt-4o-mini）に投げて銘柄ごとのセンチメントを計算し ai_scores テーブルへ書き込み。
    - タイムウィンドウ計算（前日 15:00 JST ～ 当日 08:30 JST）の calc_news_window を実装。
    - 銘柄ごとに記事集約、バッチ（最大 20 銘柄）で API 呼び出し、スコア検証・クリップ、DuckDB への冪等書き込み（DELETE→INSERT）を実装。
    - JSON Mode を用いた厳密 JSON 期待、レスポンス復元ロジック（前後余計なテキストの抽出）や詳細なバリデーションを導入。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフリトライ、その他エラーはスキップしてフェイルセーフに継続。
    - テスト用HOOK: _call_openai_api をモック可能。
  - kabusys.ai.regime_detector: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime テーブルへ日次で書き込む score_regime を実装。
    - ma200_ratio 計算、マクロ記事抽出(_fetch_macro_news)、OpenAI 呼び出し、マクロスコアのリトライ/フォールバックを実装。
    - レジームスコア合成ロジックと閾値による regime_label (bull/neutral/bear) 判定。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT による冪等処理と ROLLBACK の保護。
    - news_nlp とは内部で OpenAI 呼び出し実装を分離（モジュール結合の軽減）。

- Data（ETL / カレンダー / パイプライン）
  - kabusys.data.calendar_management: JPX カレンダー管理と営業日判定ユーティリティを実装。
    - is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days を提供。
    - market_calendar が無ければ曜日ベースのフォールバック。DB 登録があれば優先する一貫した判定ロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存。バックフィルと健全性チェック実装。
  - kabusys.data.pipeline: ETLResult データクラスと ETL 用ユーティリティを追加。
    - ETLResult: 取得/保存件数、品質問題、エラー一覧、has_errors / has_quality_errors / to_dict 等を提供。
    - ETL パイプライン設計（差分更新、バックフィル、品質チェックの収集方針）を反映した内部ユーティリティを実装。
  - kabusys.data.etl: pipeline.ETLResult を再エクスポート。

- Research（ファクター計算 / 特徴量解析）
  - kabusys.research.factor_research: Momentum / Volatility / Value の定量ファクターを提供。
    - calc_momentum: 1M/3M/6M リターン、ma200_dev（200日MA乖離率）を prices_daily から算出。データ不足時の None 処理。
    - calc_volatility: 20日 ATR（true range の扱いを明示）、相対 ATR、20日平均売買代金、出来高比率を算出。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を算出（EPS＝0/欠損時は None）。
  - kabusys.research.feature_exploration:
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。ホライズン入力検証あり。
    - calc_ic: factor と forward returns のスピアマン（ランク）相関を計算（3 件未満は None）。
    - rank: 同順位は平均ランクで処理（float の丸めで ties の検出を安定化）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

- ロギング・耐障害性
  - 各所で詳細な logger 設定を想定したログ出力を追加（info/debug/warning/exception）。
  - OpenAI/API 呼び出しに対するリトライ・バックオフ実装、失敗時の適切なフォールバック（0.0 やスキップ）を多数導入。
  - DuckDB のバージョン差異対策（executemany の空リスト回避、ANY(?) バインド回避など）を実装。

Changed
- （初版のため該当なし）

Fixed
- （初版のため該当なし）

Security
- 特になし（ただし機密情報（API キー等）は環境変数で管理する設計）。設定必須環境変数:
  - OPENAI_API_KEY（AI 呼び出しに必須）
  - JQUANTS_REFRESH_TOKEN
  - KABU_API_PASSWORD
  - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
  - これらが未設定の場合は Settings のプロパティ / score_* 関数で ValueError を投げるか、処理を中止する。

Notes / Known issues / Migration
- 自動環境変数ロード
  - .env/.env.local の自動ロードはプロジェクトルートが検出できる場合のみ実行されます。テスト時等に自動ロードを無効化するには KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- OpenAI（gpt-4o-mini）利用
  - news_nlp と regime_detector は JSON Mode（厳密 JSON 出力）を期待します。LLM レスポンスの不整合に対しパース復元やバリデーションを行いますが、出力フォーマット変更があるとスコアが取得できない場合があります。
  - テストでは内部関数 _call_openai_api をモックすることで外部 API に依存しない単体テストが可能です。
- DB 書き込み
  - ai_scores / market_regime 等への書き込みは冪等化（削除→挿入）を行いますが、部分的な失敗を防ぐためコード単位で削除を限定しています。
- Look-ahead バイアス対策
  - date.today() や datetime.today() を直接参照しない設計（target_date を明示して呼ぶ形）にしています。運用側は必ず target_date を指定して呼び出してください。
- 互換性
  - DuckDB のバージョン依存挙動（executemany 空リスト不可、配列バインドの挙動など）を考慮した実装になっています。
- 既知の不完全箇所
  - pipeline モジュールの末尾付近にソースの切れやタイプミス（例: return date.fro のような未完了の行）が見受けられます。リポジトリの完全版を用いるか、該当箇所の修正（正しい日付変換の return）を行ってください。

Breaking Changes
- 初回リリースのため Breaking Changes はありません。

Contributing
- バグや改善提案は issue を立ててください。AI 呼び出し等外部依存を含むコードはモック可能な設計を心掛けています。

ライセンス
- （この CHANGELOG にはライセンス情報を含めていません。プロジェクトの LICENSE を参照してください。）

以上。必要であれば各モジュールごとの詳細な変更点（関数一覧、引数仕様、戻り値の厳密な型など）や英語版CHANGELOGも作成できます。どのレベルの情報を追加しますか？