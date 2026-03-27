# Changelog

すべての重要な変更はこのファイルに記載します。  
フォーマットは「Keep a Changelog」に準拠し、セマンティックバージョニングを使用します。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-27

Added
- パッケージ初期リリースを追加。
  - src/kabusys/__init__.py にてバージョンを "0.1.0" に設定し、主要サブパッケージをエクスポート（data, strategy, execution, monitoring）。
- 環境変数／設定管理（src/kabusys/config.py）
  - .env ファイルまたは OS 環境変数から設定値を読み込む自動ローダを実装。プロジェクトルートの検出は .git または pyproject.toml を基準に行うため CWD に依存しない。
  - .env のパース処理を強化（export プレフィックス対応、シングル/ダブルクォート内のエスケープ対応、インラインコメントの取り扱いなど）。
  - 自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - 既存 OS 環境変数を保護する protected 機構、override ロジックを提供。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）とデフォルト値（KABU_API_BASE_URL、DB パス等）をプロパティとして公開。
  - KABUSYS_ENV と LOG_LEVEL のバリデーション（許容値チェック）、と is_live / is_paper / is_dev の便宜プロパティを追加。
- ニュースNLP（src/kabusys/ai/news_nlp.py）
  - raw_news と news_symbols を元に銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）を用いたセンチメントスコアを ai_scores テーブルへ書き込む処理を実装。
  - タイムウィンドウ定義（前日 15:00 JST ～ 当日 08:30 JST に対応する UTC 範囲）と calc_news_window ヘルパーを追加。
  - バッチ処理（最大 _BATCH_SIZE=20 銘柄/コール）、1銘柄あたりの最大記事数／文字数制限（トークン肥大化対策）を実装。
  - OpenAI 呼び出しでのリトライ（429/ネットワーク断/タイムアウト/5xx に対する指数バックオフ）、JSON レスポンスの厳格な検証とパース後のスコア ±1.0 クリップを実装。
  - テスト容易性のため _call_openai_api を patch 可能に設計。
  - API キー未設定時は ValueError を送出。
- 市場レジーム判定（src/kabusys/ai/regime_detector.py）
  - ETF 1321（日経225 連動 ETF）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で market_regime テーブルへ冪等書き込みする score_regime を実装。
  - マクロニュースの抽出（マクロキーワードリスト）と LLM（gpt-4o-mini）呼び出しを実装。API 失敗時はフェイルセーフで macro_sentiment=0.0 にフォールバック。
  - MA 計算は target_date 未満データのみを使用し、ルックアヘッドバイアスを防止。
  - LLM 呼び出しのリトライ／バックオフ、レスポンスパース時のロバスト処理を実装。
- 研究（research）モジュール（src/kabusys/research/）
  - factor_research: モメンタム、ボラティリティ、バリュー等の定量ファクター計算を実装。
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離（ma200_dev）を計算。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算。必要行数未満は None を返す。
    - calc_value: raw_financials から直近財務を取得し PER（EPS が 0/欠損時は None）・ROE を計算。
  - feature_exploration: 将来リターン計算、IC（Spearman ランク相関）計算、rank ユーティリティ、統計サマリー関数を実装。
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）の将来リターンを一度のクエリで取得。
    - calc_ic: factor と forward を code で結合し Spearman ρ を計算（有効レコード <3 の場合は None）。
    - rank: 同順位は平均ランクで処理（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を計算。
  - research パッケージは zscore_normalize（kabusys.data.stats）を再利用可能にエクスポート。
- データ管理（src/kabusys/data/）
  - calendar_management: JPX カレンダー管理／営業日判定ロジックを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を実装。
    - market_calendar が未取得の場合は曜日ベース（週末除外）でフォールバック。DB 登録値があれば優先して使用。
    - calendar_update_job: J-Quants から差分取得して market_calendar テーブルを更新。バックフィルと健全性チェックを実装。
  - pipeline / etl: ETL パイプライン向けユーティリティを実装。
    - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラー一覧等を保持）。to_dict(), has_errors, has_quality_errors を提供。
    - データ取得の差分更新・backfill・品質チェック連携を想定した設計。
  - jquants_client を経由したデータ取得 / 保存を想定（fetch/save 関数を利用する形）。
- テスト・実装上の設計方針（全体）
  - ルックアヘッドバイアス防止のため、いかなるモジュールも datetime.today() / date.today() を内部ロジックの基準に用いない設計（一部ジョブで明示的に date.today() を参照する箇所を除く）。
  - DuckDB を主要なオンライブラリとして利用し、SQL と Python を組み合わせて計算を行う。
  - 外部 API 呼び出しの失敗はフェイルセーフでスキップまたはデフォルト値を採用し、部分失敗時に既存データを不必要に消さない（冪等保存、コード絞り込みによる守り込み）。
  - OpenAI 呼び出し部分はモジュール単位で _call_openai_api を独立実装しており、ユニットテストで差し替え可能。

Changed
- （初回リリースのためなし）

Fixed
- （初回リリースのためなし）

Deprecated
- （初回リリースのためなし）

Security
- （該当なし）

Notes / 要点
- 必須環境変数（例）:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（AI 機能利用時）
- OpenAI は gpt-4o-mini を JSON Mode（response_format={"type":"json_object"}）で使用する想定。API レスポンスやステータスコードの変化に対して堅牢に処理する実装が入っています。
- AI 系処理（ニュース NLP / レジーム判定）は外部 API の不安定さを考慮したリトライ・フォールバック設計になっており、テスト用に _call_openai_api をモック差替え可能です。