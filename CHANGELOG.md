CHANGELOG
=========

すべての注目すべき変更を一元管理します。
このファイルは Keep a Changelog の形式に準拠しています。
※ 日付はリリース日を示します。

フォーマット
-----------
- Unreleased: 今後の変更を記載するためのプレースホルダ
- 各バージョン: そのバージョンでの追加・変更点等を分類して記載

[Unreleased]
------------

- 今のところ未定義

[0.1.0] - 2026-04-03
--------------------

初期公開リリース。日本株自動売買およびリサーチ用の基本機能群を実装。

Added
-----

- パッケージ全体
  - 初期パッケージ kabusys を追加。パッケージバージョン: 0.1.0。
  - モジュール公開: data, strategy, execution, monitoring を __all__ で宣言。

- 設定/環境管理 (kabusys.config)
  - .env ファイルおよび環境変数からの設定読み込み機能を実装。
    - プロジェクトルート検出: .git または pyproject.toml を基準に自動検出（カレントワーキングディレクトリに依存しない）。
    - .env と .env.local の読み込み順と上書きルールを実装（OS 環境変数は保護）。
    - export KEY=val 形式、クォート／エスケープ、行末コメント等を考慮したパーサを搭載。
    - 自動読み込みは環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
  - Settings クラスを実装し、アプリケーション設定へプロパティ経由でアクセス可能に。
    - J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / システム環境（env, log_level 等）等のプロパティを提供。
    - env と log_level の値検証を実装（無効値は ValueError）。
    - ファイルパスは Path.expanduser() で解決。

- AI（自然言語処理・レジーム判定）
  - kabusys.ai.news_nlp
    - raw_news と news_symbols を用いて銘柄別にニュースを集約し、OpenAI（gpt-4o-mini、JSON Mode）でセンチメントを評価して ai_scores に書き込む処理を実装。
    - タイムウィンドウ（前日15:00 JST ～ 当日08:30 JST）を厳密に計算して対象記事を決定。
    - 1銘柄あたりの記事数・文字数上限（トークン肥大対策）を導入。
    - バッチ（最大20銘柄）で API コール。429/ネットワーク断/タイムアウト/5xx に対して指数バックオフでリトライ。
    - レスポンスの堅牢なバリデーションと JSON 復元処理（余計な前後テキストの切り出し）。
    - API キー注入対応（引数または環境変数 OPENAI_API_KEY）。未設定時は ValueError。
    - API 失敗時は例外を投げず該当チャンクをスキップ（フェイルセーフ設計）。
    - DuckDB への書き込みは部分失敗時に既存スコアを守るため、対象コードを絞って DELETE → INSERT を行う（エグゼキューション互換性考慮）。

  - kabusys.ai.regime_detector
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime に保存する処理を実装。
    - マクロニュース抽出はキーワードベース（日本・米国などの主要キーワード群）。
    - OpenAI 呼び出しを独立関数で実装し、リトライ・バックオフ・エラー処理（APIError の status_code に基づく挙動）を組み込み。
    - LLM 呼び出し失敗時は macro_sentiment=0.0 のフォールバックを行い継続する。
    - DB 書き込みは冪等化（BEGIN / DELETE / INSERT / COMMIT）を行い、失敗時は ROLLBACK を試みる（失敗ログあり）。

- データプラットフォーム（kabusys.data）
  - calendar_management
    - JPX カレンダー取得・管理のユーティリティを実装。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定 API を提供。
    - market_calendar が未登録の場合は曜日ベース（土日非営業日）でフォールバックし、一貫性のある挙動を確保。
    - 夜間バッチ用 calendar_update_job を実装し、J-Quants から差分取得して保存（バックフィルや健全性チェックあり）。
  - pipeline / etl
    - ETLResult データクラスを公開し、ETL の取得件数・保存件数・品質問題・エラーの集計を提供。
    - 差分更新・バックフィル・品質チェックを行う ETL パイプラインの設計に対応するユーティリティを整備。
    - DuckDB テーブル存在チェック等の内部ユーティリティを実装。

- リサーチ（kabusys.research）
  - ファクター計算と特徴量探索を実装。
    - factor_research: calc_momentum（1M/3M/6M リターン、MA200乖離）、calc_volatility（ATR, turnover, volume_ratio）、calc_value（PER, ROE）を実装。DuckDB SQL を活用。
    - feature_exploration: calc_forward_returns（将来リターン）、calc_ic（Spearmanランク相関によるIC計算）、factor_summary（基本統計量）、rank（同順位は平均ランク）を実装。
    - Pandas 等外部ライブラリに依存せず、標準ライブラリ＋DuckDB のみで計算可能な設計。

- 汎用/ユーティリティ
  - data.etl から ETLResult を再エクスポート。
  - AI モジュールでの OpenAI 呼び出しはテスト容易性のため差し替え可能（ユニットテスト用の patch ポイントを用意）。

Security
--------

- OpenAI API キー、J-Quants トークン、Kabu API パスワードなどは環境変数で管理する設計。Settings は必須キー未設定時に ValueError を送出。
- .env 自動ロードはデフォルトで有効だが、テストや CI 向けに KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- 外部 API 呼び出しはリトライ/フォールバックを備え、直接例外を伝播させない箇所が多い（可用性重視）。

Notes / 運用上のポイント
-----------------------

- DuckDB を主要なローカルデータストアとして利用します。期待するテーブル:
  - prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials など。
- OpenAI のモデルは現状 gpt-4o-mini を利用する想定。
- News/NLP 系の処理は LLM レスポンスの形式に強く依存するため、API バージョンやレスポンス仕様の変更に注意してください。
- ETL・カレンダー更新ジョブは外部の J-Quants クライアント（kabusys.data.jquants_client）へ依存します。API 呼び出しに失敗した場合はログ出力して 0 件返却するフェイルセーフ実装です。
- 日付参照においてはルックアヘッドバイアスを避けるため、datetime.today()/date.today() を直接使わない設計（target_date を明示的に渡す形）。

Changed / Fixed / Deprecated / Removed
--------------------------------------

- 初版のため該当なし。

ライセンス／著作権
------------------

- 本リリースは初期実装の記録です。実際の配布・商用利用時は別途 LICENSE を参照してください。

----------