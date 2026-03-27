# Changelog

すべての注目すべき変更をこのファイルに記録します。  
このプロジェクトは Keep a Changelog の慣習に準拠しています。  

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

初回リリース。主な機能・設計方針・注意点を以下にまとめます。

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring を __all__ で公開。

- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能をプロジェクトルート（.git または pyproject.toml）を起点に実装。CWD に依存しない探索を行う。
  - 読み込み優先度: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パーサ（クォート、エスケープ、コメント対応）、保護された OS 環境変数の上書き防止ロジックを実装。
  - Settings クラスを提供し、必須環境変数取得用の _require とプロパティ（JQUANTS_REFRESH_TOKEN、KABU_API_PASSWORD、SLACK_*、DUCKDB_PATH、SQLITE_PATH、KABUSYS_ENV、LOG_LEVEL 等）を公開。環境値検証（env / log_level の許容値チェック）を実装。

- データ (kabusys.data)
  - ETL パイプライン型（ETLResult）の公開インターフェース（data.etl/pipeline）。
  - 市場カレンダー管理（data.calendar_management）:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ユーティリティ。
    - calendar_update_job により J-Quants からのカレンダー差分取得と冪等保存（バックフィル、健全性チェックを含む）。
    - market_calendar がない場合の曜日ベースのフォールバック実装。
  - ETL パイプライン基盤（data.pipeline）:
    - 差分取得・保存・品質チェックの設計に基づくユーティリティ。ETLResult データクラス（品質問題・エラー集約、has_errors / has_quality_errors）を提供。
    - DuckDB の最大日付取得などの補助関数を実装。

- 研究モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を DuckDB 上で計算。データ不足時の None ハンドリング。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。NULL の伝播制御に注意。
    - calc_value: raw_financials から最新財務データを取り出し PER/ROE を計算。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（任意ホライズン）計算。horizons の検証、レンジ拡張ロジックを実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸めによる ties の考慮）。
    - factor_summary: カラム毎の count/mean/std/min/max/median を計算。
  - kabusys.data.stats からの zscore_normalize を re-export（research.__init__）。

- AI モジュール (kabusys.ai)
  - news_nlp:
    - ニュース記事を銘柄別に集約し、OpenAI（gpt-4o-mini）を用いて銘柄ごとのセンチメント（-1.0〜1.0）を JSON モードで取得。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST に対応した UTC 変換）を実装（calc_news_window）。
    - 1チャンク最大20銘柄（_BATCH_SIZE）、1銘柄あたり記事最大10件、最大文字数トリム(_MAX_CHARS_PER_STOCK)によるトークン肥大対策。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライ（共通の _MAX_RETRIES, _RETRY_BASE_SECONDS）。
    - レスポンスバリデーション（JSONパース、results リスト、code の照合、スコアの数値性と有限性）、スコアを ±1 にクリップ。
    - スコア書き込みは部分書き換え方式（DELETE（対象コード）→ INSERT）で既存のスコアを保護。
    - API 呼び出し部は差し替え可能（テスト用に _call_openai_api を patch）でテスト容易性を考慮。
  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次市場レジーム（bull / neutral / bear）を判定。
    - マクロニュース抽出は keywords ベース（複数キーワード）で最大 20 件を取得、LLM（gpt-4o-mini）で JSON を期待して評価。
    - レジーム合成スコアのクリップ・閾値判定（_BULL_THRESHOLD / _BEAR_THRESHOLD）、market_regime テーブルへの冪等書き込みを行う。
    - API 失敗時はマクロセンチメントを 0.0 にフォールバック（フェイルセーフ）。
    - OpenAI 呼び出しはテスト差替え可能。

### Changed
- （初回リリースのため過去からの変更はなし）

### Fixed
- （初回リリースのためなし）

### Security
- 環境変数の必須チェックとエラー通知（Settings._require）。OpenAI API キーや Slack トークン等が未設定の場合に ValueError を発生させる設計。
- .env 読み込みで OS 環境変数をプロテクトする仕組みを導入し、意図しない上書きを防止。

### Notes / 注意事項
- OpenAI の API キーは API を呼ぶ関数（score_news, score_regime）で必須。api_key を引数で渡すか、環境変数 OPENAI_API_KEY を設定してください。空文字も未設定として扱われます。
- DuckDB を主要な永続化・計算基盤として使用。関数群は DuckDB 接続（DuckDBPyConnection）を受け取る仕様です。
- 日付/時刻の取り扱い:
  - 各種処理は内部で datetime.today()/date.today() を直接参照しない設計（ルックアヘッドバイアス対策）。score_* や calc_* では target_date を明示的に受け取ります。
  - ニュース時間ウィンドウや calendar_update_job 等は UTC naive datetime / date を前提とし、JST ↔ UTC の変換に注意してください。
- 部分書き込み（ai_scores / market_regime 等）は冪等性を意識して設計されています。DuckDB の executemany に空リストを渡せない点への対処も実装済み。
- テスト容易性:
  - OpenAI 呼び出し箇所はローカル関数（_kabusys.ai.*._call_openai_api）に抽象化してあり、unittest.mock.patch により差し替え可能です。
- 未実装・今後の拡張候補:
  - research.calc_value の PBR・配当利回りは未実装（注記あり）。
  - pipeline._adjust_to_trading_day 以降の処理ファイル末端が一部未表示・拡張余地あり（初期実装は ETLResult など中心）。

---

もし特定コンポーネント（例: news_nlp の出力形式や calendar_update_job の挙動）についてリリースノートをさらに詳しく分割したい場合は指示してください。