CHANGELOG
=========

すべての変更は Keep a Changelog (https://keepachangelog.com/ja/1.0.0/) のガイドラインに従って記載しています。  
フォーマット: Unreleased / 各バージョン（日付） → Added / Changed / Fixed / Deprecated / Removed / Security

Unreleased
----------
（なし）

[0.1.0] - 2026-04-04
--------------------

初期リリース。日本株自動売買システム "KabuSys" のコアライブラリを整備しました。主な追加機能・設計方針は下記の通りです。

Added
- パッケージ基盤
  - パッケージ初期化: kabusys.__version__ = "0.1.0" として公開 API を定義（data, strategy, execution, monitoring）。
- 設定管理
  - kabusys.config: .env ファイルおよび環境変数から設定を読み込む自動ローダーを実装。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - プロジェクトルート検出は __file__ を基点に .git または pyproject.toml を探索（CWD に依存しない実装）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD を設定することで自動ロードを無効化可能（テスト用）。
    - .env パーサーは export プレフィックス対応、クォート内のエスケープ、インラインコメント処理を実装。
  - Settings クラスで主要設定をプロパティとして提供（J-Quants トークン、kabu API、LINE トークン、DB パス、監視設定、閾値、環境／ログレベル検証等）。
    - 必須環境変数未設定時は ValueError を送出する _require を提供。
    - 環境値検証（KABUSYS_ENV, LOG_LEVEL）のバリデーション実装。
- データ系（DuckDB ベース）
  - kabusys.data.pipeline: ETLResult dataclass を公開（ETL の取得数/保存数、品質問題、エラー集約）。
    - ETL パイプライン方針（差分取得、バックフィル、品質チェックの収集方式）を実装。
  - kabusys.data.calendar_management: JPX カレンダー管理機能を提供。
    - 営業日判定（is_trading_day）、翌営業日/前営業日取得（next_trading_day/prev_trading_day）、期間内営業日取得（get_trading_days）、SQ 判定（is_sq_day）。
    - market_calendar に対する DB 優先ロジックと曜日ベースのフォールバック、最大探索日数の上限設定、夜間更新ジョブ（calendar_update_job）。
  - ETL ユーティリティ公開（kabusys.data.etl は pipeline.ETLResult を再エクスポート）。
  - DuckDB 互換性に配慮した実装（executemany の空リスト制約回避など）。
- 研究（Research）
  - kabusys.research: factor/feature の公開 API（calc_momentum, calc_value, calc_volatility, zscore_normalize, calc_forward_returns, calc_ic, factor_summary, rank）。
  - ファクター計算モジュール（factor_research）:
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR, 相対 ATR, 平均売買代金、出来高比）、Value（PER, ROE）を DuckDB 上で計算する実装。
    - データ不足時の None 処理やスキャン範囲のバッファを考慮した SQL 実装。
  - 特徴探索（feature_exploration）:
    - 将来リターン calc_forward_returns（複数ホライズン対応、入力検証）、IC（Spearman ランク相関）calc_ic、統計サマリー factor_summary、ランク関数 rank（同順位は平均ランク）を実装。
- AI / ニュース NLP
  - kabusys.ai.news_nlp:
    - raw_news と news_symbols を集約し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメント（-1.0〜1.0）を算出して ai_scores に書き込む処理を実装。
    - チャンク（最大 20 銘柄）毎のバッチ送信、記事数・文字数のトリム（1 銘柄あたり最大 10 記事、3000 文字）、レスポンスの厳密なバリデーション、スコアの ±1.0 クリップ、部分成功時に既存データを保護するための差替えロジック（DELETE → INSERT）を提供。
    - API エラー（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライ、失敗時はそのチャンクをスキップして継続（フェイルセーフ）。
    - JSON パース回復処理（前後余計なテキストが混ざる場合に最外の {} を抽出する等）。
    - unittest.mock.patch により _call_openai_api を差し替え可能（テスト容易性）。
  - kabusys.ai.regime_detector:
    - ETF 1321（225 連動）の 200 日 MA 乖離（重み70%）とマクロニュース LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込みする処理を実装。
    - LLM 呼び出しには OpenAI SDK（gpt-4o-mini）を使用。API のリトライ・例外種別ごとのフォールバックを実装。API 失敗時は macro_sentiment=0.0 として継続。
    - DB 書き込みは BEGIN / DELETE / INSERT / COMMIT の冪等パターンを採用。失敗時は ROLLBACK を行い例外を伝播。
- ロギング・監視・運用
  - モジュール全体で適切な logger を使用し、重要な状態（データ不足、API 失敗、ROLLBACK 失敗など）に対して警告・情報ログを出力するように設計。
  - 監視用設定（PID ファイル、kill フラグ、CPU/メモリ/ディスク閾値）を Settings で管理。
- 設計上の注意点（ドキュメントに明記）
  - ルックアヘッドバイアス回避: datetime.today() / date.today() を内部処理で直接参照せず、すべての関数で target_date を明示的に受け取る方針を採用。
  - DuckDB 上での互換性確保（個別 DELETE via executemany、空リスト回避など）。
  - 外部発注や本番アカウントへのアクセスはこのリポジトリ内の研究／データ処理コードでは行わないという分離方針。
  - テスト容易性のため、OpenAI 呼び出し箇所をモック差し替え可能に実装。

Changed
- （初期リリースにつきなし）

Fixed
- （初期リリースにつきなし）

Deprecated
- （初期リリースにつきなし）

Removed
- （初期リリースにつきなし）

Security
- OpenAI API キー関連
  - news_nlp.score_news / regime_detector.score_regime は api_key 引数または環境変数 OPENAI_API_KEY を必須とし、未設定時は ValueError を送出して誤動作を防止。
  - .env 自動読み込みは KABUSYS_DISABLE_AUTO_ENV_LOAD によって明示的に無効化可能（CI/テスト環境での秘匿情報保護に利用）。

補足（実装上の既知点）
- OpenAI SDK と DuckDB に依存するため、ランタイムで両方のライブラリが必要です。
- ai モジュールの JSON mode は LLM 応答の不確実性を伴うため、レスポンスパース失敗時は安全にスキップする実装になっています（部分失敗からの復旧を優先）。
- calendar_update_job および ETL は J-Quants クライアント（kabusys.data.jquants_client）に依存し、API 側呼び出しで例外が発生した場合は 0 を返してログに例外を残します。

今後の予定（例）
- スコアの継続的評価・キャリブレーションを行うためのサンプルパイプライン導入
- strategy / execution / monitoring パッケージの実装（現バージョンでは公開 API のみ定義）
- PBR や配当利回りなど追加バリューファクターの実装

----

脚注:
- 日付はリポジトリ内バージョン情報に基づき 2026-04-04 を当該リリース日として設定しています。必要に応じて差し替えてください。