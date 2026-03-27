Keep a Changelog
=================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。

Unreleased
----------

（現在の開発中の変更はここに記載してください）

0.1.0 - 2026-03-27
------------------

Added
- パッケージ初期リリース: kabusys v0.1.0
  - パッケージ公開APIのエントリポイントを追加（kabusys.__init__）。
- 環境設定管理
  - 環境変数・.env 読み込みユーティリティを実装（kabusys.config）。
  - プロジェクトルート探索: .git / pyproject.toml を基準に .env 自動読み込み（KABUSYS_DISABLE_AUTO_ENV_LOAD で無効化可能）。
  - .env パーサの実装: export 形式対応、クォート／エスケープ処理、インラインコメントの取り扱い、保護付き上書き（protected）をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / Slack / DB パス / 実行環境フラグ等のプロパティを環境変数から取得。
  - KABUSYS_ENV／LOG_LEVEL の検証（許容値チェック）を実装。
- AI モジュール（自然言語処理 / レジーム判定）
  - ニュースセンチメントスコアリング: score_news を実装（kabusys.ai.news_nlp）。
    - ニュース収集ウィンドウ計算（JST基準で前日15:00〜当日08:30相当のUTC範囲）。
    - raw_news と news_symbols を銘柄単位で集約、記事数・文字数トリム制御。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大バッチサイズ 20）、JSON Mode を想定したレスポンス検証。
    - 429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライ。
    - レスポンス検証・スコア ±1 にクリップ、取得成功銘柄のみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT）。
    - テスト容易性のため _call_openai_api を patch 可能に設計。
  - 市場レジーム判定: score_regime を実装（kabusys.ai.regime_detector）。
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で 'bull'/'neutral'/'bear' 判定。
    - prices_daily からの MA200 比率計算、raw_news からマクロキーワードでのフィルタ、OpenAI 呼び出し（gpt-4o-mini）でのマクロセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込み。
    - API 失敗時は macro_sentiment=0.0 にフォールバック（フェイルセーフ）。
- Research（因子計算・特徴量探索）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: 1M/3M/6M リターン、200 日 MA 乖離率の計算（データ不足時は None を返す）。
    - ボラティリティ/流動性: 20 日 ATR（true range の扱いを含む）、avg turnover、volume ratio の計算。
    - バリュー: raw_financials から直近財務値を取得して PER / ROE を算出。
    - DuckDB を用いた SQL ベースの効率的実装、外部 API にはアクセスしない設計。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン calc_forward_returns（任意ホライズン、入力検証あり）。
    - IC（スピアマンランク相関）calc_ic とランク変換ユーティリティ rank。
    - factor_summary による基本統計量（count/mean/std/min/max/median）計算。
    - 外部ライブラリ非依存（標準ライブラリのみ）。
  - re-export: 研究用ユーティリティ群をパッケージ公開（kabusys.research.__init__）。
- Data（ETL / カレンダー管理）
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得ロジック、バックフィル制御、品質チェック統合。
    - ETLResult データクラスを実装（取得数／保存数／品質問題／エラー集計、has_errors 等のプロパティ）。
    - ETLResult の辞書変換ユーティリティ（品質問題を (check_name, severity, message) 形式に変換）。
  - カレンダー管理（kabusys.data.calendar_management）
    - market_calendar に基づく営業日判定ユーティリティ群: is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days。
    - DB 登録がない場合の曜日ベースフォールバック（週末は非営業日）。
    - calendar_update_job: J-Quants API からの差分取得と market_calendar 更新、バックフィルと健全性チェック（将来日付の異常検出）。
    - 最大探索日数制限で無限ループを防止。
  - ETL 公開インターフェース（kabusys.data.etl）で ETLResult を再エクスポート。
- 依存関係 / 実行設計
  - DuckDB を主要ストレージとして想定した SQL 実装（DuckDB 接続オブジェクトを引数に受ける）。
  - OpenAI SDK（OpenAI クライアント）を利用する実装（API キー注入可能）。
  - ログ出力を多用し、フェイルセーフ設計（API 失敗時に処理継続）を採用。
  - テスト容易性を考慮した差し替えポイント（_call_openai_api 等）を用意。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数の自動ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD により無効化可能（テスト時に環境漏洩リスクを低減）。

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Notes / 補足
- すべての日付処理はルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計を原則としている（target_date を引数で受ける）。
- DuckDB executemany に関する互換性考慮（空リスト渡し回避）など、実運用上の細かいハンドリングを実装している。
- OpenAI 呼び出しは JSON mode を想定しつつ、JSON 以外の余計な前後テキストが混ざるケースにも耐えるパースロジックを含む。

要望があれば、各機能ごとにより詳細な変更点（関数シグネチャ、返り値仕様、エラーハンドリング例など）を追記します。