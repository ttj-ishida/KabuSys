# Changelog

すべての重要な変更をここに記録します。本ファイルは Keep a Changelog の形式に従います。

なお、本CHANGELOGはリポジトリ内のコード内容から推測して作成した初回リリース向けの要約です。

## [Unreleased]

（なし）

## [0.1.0] - 2026-03-28

Added
- 初期リリースを公開。
- パッケージ基盤
  - kabusys パッケージを導入。パッケージバージョンは 0.1.0。
  - __all__ に data, strategy, execution, monitoring を公開。
- 設定・環境変数管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能（プロジェクトルートを .git または pyproject.toml で検出）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサーの実装（コメント、export プレフィックス、クォート・エスケープ対応、インラインコメント処理）。
  - 環境変数保護（既存 OS 環境変数を protected として扱う上書き制御）。
  - Settings クラスを実装し、アプリ設定をプロパティ経由で提供（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, DUCKDB_PATH, SQLITE_PATH, KABUSYS_ENV, LOG_LEVEL 等）。
  - env / log_level に対する入力検証（許容値チェック）と is_live / is_paper / is_dev のユーティリティ。
- データプラットフォーム (kabusys.data)
  - ETL パイプライン基盤（kabusys.data.pipeline）
    - 差分取得、バックフィル、品質チェック設計を反映した ETLResult データクラスを導入。
    - DuckDB を想定した最大日付取得やテーブル存在判定ユーティリティを実装。
    - J-Quants クライアント（外部モジュールとして参照）との結合を想定。
  - ETL 公開インターフェース (kabusys.data.etl) として ETLResult を再エクスポート。
  - マーケットカレンダー管理 (kabusys.data.calendar_management)
    - market_calendar を用いた営業日判定ロジック（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録ありの場合は DB 値優先、未登録日は曜日ベースでフォールバックする一貫した実装。
    - calendar_update_job により J-Quants から差分取得して冪等保存（バックフィル・健全性チェックを含む）。
- リサーチ（kabusys.research）
  - factor_research モジュール
    - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）、ボラティリティ（20 日 ATR 等）、バリュー（PER, ROE）等の計算関数を実装（calc_momentum, calc_volatility, calc_value）。
    - DuckDB SQL を活用した高効率な集計実装。データ不足時は None を返す設計。
  - feature_exploration モジュール
    - 将来リターン計算（calc_forward_returns）、IC（Spearman のランク相関）計算（calc_ic）、ランク変換（rank）、ファクター統計サマリ（factor_summary）、その他ユーティリティを実装。
    - pandas 等外部ライブラリに依存しない標準ライブラリのみの実装。
  - 研究向け機能を __init__ で再エクスポート（zscore_normalize を含む）。
- AI/NLP（kabusys.ai）
  - ニュース NLP スコアリング（kabusys.ai.news_nlp）
    - raw_news / news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON モードでセンチメントを取得、ai_scores テーブルへ書き込む機能（score_news）。
    - チャンクバッチ処理（最大 20 コード／リクエスト）、1 銘柄あたり記事数・文字数上限（トリム）によるトークン肥大化対策。
    - レスポンスの厳密なバリデーションとスコアの ±1.0 クリップ。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライとフォールバック（失敗時は該当チャンクをスキップして継続）。
    - DuckDB executemany の注意点（空リストを渡さない）に配慮した DB 書き込み（DELETE → INSERT の冪等操作）。
    - テスト容易性のため _call_openai_api を patch 可能な設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み（score_regime）。
    - マクロ記事のフィルタリングキー、最大記事数、LLM 呼び出し（gpt-4o-mini）、リトライ / フェイルセーフ（失敗時 macro_sentiment=0.0）、スコアクリップを実装。
    - ルックアヘッドバイアスに対する注意（target_date 未満のみ参照）を徹底。
    - news_nlp と実装を共有しないことでモジュール結合を低減（_call_openai_api は独立実装）。
- 汎用・品質面の配慮
  - ルックアヘッドバイアス防止の方針をコード全体で採用（datetime.today() / date.today() をスコープ外で参照しない実装）。
  - DuckDB を主要ストアとして想定し、SQL と Python の組合せで処理を実装。
  - ロギングを広範に追加し、失敗時のフォールバックや警告を明示。
  - テスト支援のため外部依存を差し替え可能にする（OpenAI 呼び出しの patch 等）。

Changed
- （新規リリースのため該当なし）

Fixed
- （新規リリースのため該当なし）

Deprecated
- （なし）

Removed
- （なし）

Security
- OpenAI API キーは引数または環境変数 OPENAI_API_KEY で注入する設計。キー管理は利用者側で適切に行うこと。

Notes / 既知の制約
- OpenAI（gpt-4o-mini）への依存
  - score_news / score_regime は実行に OpenAI API キーを必要とする。API 呼び出し失敗時は部分的にスコアを取得できない可能性があるが、フェイルセーフ（スキップや 0.0 フォールバック）で全体処理を継続する。
- DuckDB のバージョン依存
  - executemany に空リストを渡すと失敗する（DuckDB 0.10 等）ため、空チェックを行っている。DuckDB の将来バージョンで挙動が変わる可能性あり。
- テーブル依存
  - 多くの関数は prices_daily, raw_news, news_symbols, raw_financials, ai_scores, market_calendar, market_regime 等の存在を前提としている。運用前にスキーマ準備が必要。
- 外部クライアント（jquants_client 等）は本リリースでは参照するが実装は含まれていない可能性がある（連携先の実装に依存）。

署名
- 本リリースはコードベースの内容に基づき推測して作成した CHANGELOG です。実際のリリースプロセスでは日付や項目の最終確認を行ってください。