CHANGELOG
=========

この CHANGELOG は Keep a Changelog の形式に準拠しています。  
コードベース（初期実装）から推測できる変更点・機能を日本語でまとめています。

注記:
- 日付は本ファイル生成日（2026-04-04）を使用しています。
- 記載内容はソースコードの実装から推測したもので、実際のリリースノートや仕様と差異があり得ます。

[Unreleased]
-------------

（将来の変更・予定を記載するセクション。現時点では空です）

[0.1.0] - 2026-04-04
-------------------

Added
- パッケージ初期リリース: kabusys バージョン 0.1.0
  - パッケージの公開 API:
    - kabusys.__version__ = "0.1.0"
    - __all__ = ["data", "strategy", "execution", "monitoring"]
- 環境設定管理モジュール（kabusys.config）
  - プロジェクトルート自動検出機能: .git または pyproject.toml を起点に .env ファイルを探索して自動読み込み
  - .env/.env.local の読み込み順を実装（OS 環境変数保護、.env.local は override）
  - 行パーサ実装: コメント行、export プレフィックス、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント等に対応
  - 必須環境変数チェック機能（_require）を提供
  - 設定クラス Settings を公開（settings インスタンス）
    - J-Quants / kabuステーション / LINE / DB パス / 監視設定 / システム設定等のプロパティを提供
    - デフォルト値やバリデーション（KABUSYS_ENV, LOG_LEVEL の許容値）を実装
    - ファイルパスは Path として返却し expanduser を適用
    - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1
- AI モジュール（kabusys.ai）
  - news_nlp: ニュースセンチメント解析（score_news）
    - ニュース収集ウィンドウ計算（JST → UTC 換算）
    - raw_news / news_symbols を結合して銘柄ごとに記事を集約
    - OpenAI (gpt-4o-mini) を JSON Mode で呼び出し、結果を ai_scores テーブルへ書き込み
    - バッチ処理（最大 20 銘柄/チャンク）、記事・文字数トリム、スコアクリップ（±1.0）
    - 429・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装
    - レスポンスバリデーションと部分書き換え（DELETE → INSERT）で冪等性と部分失敗耐性を確保
    - API キー未設定時は ValueError を送出
  - regime_detector: 市場レジーム判定（score_regime）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とニュース由来の LLM マクロセンチメント（重み 30%）を合成
    - calc_news_window を利用したルックアヘッド防止設計
    - OpenAI 呼び出しのリトライとフェイルセーフ（API 失敗時 macro_sentiment=0.0）
    - market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）および ROLLBACK 処理
    - API キー未設定時は ValueError を送出
  - 公開関数: score_news, score_regime, news のユーティリティ群
  - OpenAI 呼び出しをラップする内部関数（テスト時の差し替えを意識）
- データ処理モジュール（kabusys.data）
  - calendar_management: JPX カレンダー管理
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定 API
    - market_calendar が未取得時の曜日ベースフォールバック（週末を非営業日とする）
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等保存、バックフィル、健全性チェックを実装
    - 最大探索日数や先読み日数、バックフィル日数等の定数を設定
  - ETL パイプライン（pipeline.py / etl.py）
    - ETLResult データクラスを公開（ETL の集計・監査ログ用）
    - 差分更新、J-Quants クライアント呼び出し、品質チェック（quality モジュール）を統合する設計
    - テーブル存在チェック、最大日付取得等のユーティリティ実装
    - ETL のバックフィルと品質問題の収集方針（Fail-Fast ではなく収集して呼び出し元が判断）
  - jquants_client との連携を想定（fetch/save 系関数呼び出し）
  - データベースは DuckDB を前提としている旨の実装（DuckDBPyConnection を受け取る）
- 研究用モジュール（kabusys.research）
  - factor_research: モメンタム / ボラティリティ / バリュー ファクター計算
    - calc_momentum, calc_volatility, calc_value を提供
    - DuckDB SQL を活用して徹底的に DB 内で計算（外部 API 呼び出しなし）
    - 欠損やデータ不足時は None を返すなど安全設計
  - feature_exploration: 将来リターン計算・IC 計算・統計サマリー
    - calc_forward_returns（任意ホライズン、バリデーションあり）
    - calc_ic（Spearman ランク相関）、rank、factor_summary を提供
  - 研究向けユーティリティ（zscore_normalize は kabusys.data.stats から再エクスポート）
- テスト性・堅牢性に配慮した設計
  - datetime.today()/date.today() を直接参照しない（ルックアヘッドバイアス対策）
  - OpenAI 呼び出し箇所は差し替え（モック）可能な内部関数を用意
  - DB 書き込みはトランザクション（BEGIN/COMMIT/ROLLBACK）で保護、部分失敗時の既存データ保護ロジックあり
  - DuckDB の executemany の制約（空リスト不可）に配慮した実装

Changed
- 初版のため特記事項なし

Fixed
- 初版のため特記事項なし

Removed
- 初版のため特記事項なし

Notes / Known limitations（コードから推測）
- 必須環境変数が未設定の場合、Settings のプロパティや score_news/score_regime は ValueError を送出するため、実行前に環境変数を整備する必要あり。
  - 例: OPENAI_API_KEY, JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD 等
- DB スキーマ依存:
  - 本実装は prices_daily, raw_news, news_symbols, ai_scores, market_regime, market_calendar, raw_financials などのテーブル存在を前提としている。実行前にスキーマ整備が必要。
- OpenAI 依存:
  - gpt-4o-mini を JSON Mode（response_format={"type":"json_object"}）で使用する前提。SDK の将来的な API 変更やレスポンス形式の揺らぎに対するパーサ側の耐性はあるが、本番では注意して運用すること。
- ログ・監視:
  - エラー時は警告・情報ログを出す設計だが、オペレーションルール（リトライ回数・アラート連携等）は別途整備が必要。
- 外部ライブラリ軽量化:
  - pandas 等を使わず標準ライブラリ+DuckDBで実装されているため、既存のデータワークフローと統合する際はパフォーマンスやインタフェース確認が必要。

Environment variables（主なもの）
- OPENAI_API_KEY: OpenAI API キー（news_nlp / regime_detector に必要）
- JQUANTS_REFRESH_TOKEN: J-Quants API リフレッシュトークン
- KABU_API_PASSWORD, KABU_API_BASE_URL: kabuステーション API 関連
- LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID: LINE 通知用（空文字で無効）
- DUCKDB_PATH, SQLITE_PATH: デフォルト DB パス（data/ 以下に保存）
- PID_FILE_PATH, KILL_FLAG_PATH, KILL_FLAG_CLEAR_ON_START: 監視用ファイル設定
- CPU_THRESHOLD_PCT 等: リソース閾値設定
- KABUSYS_ENV: development|paper_trading|live（不正値は ValueError）
- LOG_LEVEL: DEBUG|INFO|WARNING|ERROR|CRITICAL（不正値は ValueError）
- KABUSYS_DISABLE_AUTO_ENV_LOAD: 自動 .env 読み込みを無効化する (1)

開発者向けメモ（コードから推測）
- OpenAI 呼び出しをユニットテストする際は内部の _call_openai_api を patch して差し替える設計になっています。
- DuckDB のバージョン差異（配列バインド/ executemany の挙動等）に注意してテストを行ってください。
- news_nlp と regime_detector は OpenAI 呼び出しの実装を意図的に分離している（モジュール間のプライベート関数共有を避ける）。

参考（実装上の重要な設計決定）
- ルックアヘッドバイアス対策として、関数はすべて target_date を引数に取り、内部で date.today() を直接参照しない。
- API 呼び出し失敗時はフェイルセーフ（0 やスキップ）で処理継続し、運用上の可観測性のためログで通知する方針。
- DB 書き込みは「置換（特定コードのみ DELETE → INSERT）」の形で部分失敗耐性を高める実装。

-- End of CHANGELOG --