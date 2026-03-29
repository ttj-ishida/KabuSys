Keep a Changelog
=================

すべての重要な変更はこのファイルに記録します。  
このプロジェクトはセマンティック バージョニングを使用します。  
https://keepachangelog.com/ja/1.0.0/

0.1.0 — 2026-03-29
------------------

Added
- 初期リリース。パッケージ名: kabusys、バージョン: 0.1.0。
- パッケージ構成:
  - kabusys.config: 環境変数・設定管理
    - .env / .env.local の自動読み込み（プロジェクトルートは .git または pyproject.toml を起点に探索）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
    - .env パーサ: export 形式対応、クオート文字列（エスケープ考慮）対応、行末コメントの扱い改善。
    - 環境変数保護（OS 環境変数は .env.local で上書きされないよう保護）と override フラグ。
    - Settings クラスで主要設定をプロパティとして提供（J-Quants、kabu API、Slack、DB パス、実行環境、ログレベル等）。
    - 必須環境変数未設定時は ValueError を送出する _require ユーティリティ。
  - kabusys.ai:
    - news_nlp:
      - raw_news / news_symbols を元にニュースを銘柄別に集約して OpenAI（gpt-4o-mini）でセンチメントを評価。
      - タイムウィンドウ（前日 15:00 JST ～ 当日 08:30 JST）計算ユーティリティ（calc_news_window）。
      - バッチ処理（最大 20 銘柄 / コール）、1 銘柄あたり記事・文字数のトリム制御。
      - JSON Mode を利用した厳密な JSON レスポンス期待。レスポンスのバリデーションとスコアクリップ（±1.0）。
      - リトライ（429・ネットワーク断・タイムアウト・5xx）を指数バックオフで実装。失敗は安全にスキップして継続（フェイルセーフ）。
      - DuckDB 用の書き込みは部分置換（DELETE → INSERT）で部分失敗時の既存データ保護。DuckDB 互換性考慮（executemany 空リスト回避等）。
      - テスト容易性のため _call_openai_api を差し替え可能に実装。
    - regime_detector:
      - ETF 1321（日経225連動）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定。
      - prices_daily, raw_news, market_regime を参照して計算・冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - マクロニュース抽出（マクロキーワードによるフィルタ）、OpenAI 呼び出し（gpt-4o-mini）のリトライロジック、API 失敗時は macro_sentiment=0.0 にフォールバック。
      - ルックアヘッドバイアス回避設計（date 引数基準で DB クエリは target_date 未満等の制約）。
  - kabusys.data:
    - calendar_management:
      - JPX カレンダー管理（market_calendar テーブル）用ユーティリティ。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 等の営業日判定ロジックを提供。
      - カレンダー未取得時は曜日ベースのフォールバック（週末を非営業日扱い）。DB 登録値優先の一貫した補完ロジック。
      - calendar_update_job: J-Quants から差分取得して market_calendar を冪等更新。バックフィル・健全性チェックを実装。
    - pipeline / etl:
      - ETLResult データクラスを公開（ETL 実行結果の集約）。
      - ETL パイプライン設計（差分取得、idempotent 保存、品質チェックの集約と報告）を支援するユーティリティ群。
      - jquants_client 経由でのデータ取得・保存呼び出しを想定。
  - kabusys.research:
    - factor_research:
      - モメンタム（1M/3M/6M）、200 日 MA 乖離、ATR（20 日）、出来高・売買代金の流動性指標、バリューファクター（PER, ROE）等の計算を提供。
      - DuckDB の SQL ウィンドウ関数を活用した実装。データ不足時は None を返す（安全対処）。
    - feature_exploration:
      - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）、IC（Spearman の ρ）計算、ランク変換、ファクター統計サマリーを提供。
      - pandas 等に依存せず標準ライブラリと DuckDB を用いた実装。
  - テストと運用上の工夫:
    - OpenAI 呼び出し部分をモック差し替え可能に実装してユニットテストを容易に。
    - DuckDB の特性（executemany の空リスト不可等）に対応したコードパス。

Changed
- （初期リリースのため変更履歴なし）

Fixed
- （初期リリースのため修正履歴なし）

Security
- 環境変数の読み込みは OS 環境変数を上書きしない既定動作（.env.local は上書き可能だが OS の既存変数は保護）など、意図しない上書きを防ぐ設計。

Notes / 実装上の注意
- OpenAI クライアントは gpt-4o-mini モデル、JSON Mode を利用する想定。API キーは api_key 引数経由または環境変数 OPENAI_API_KEY から解決。
- 多くの処理は「ルックアヘッドバイアス回避」を重視しており、datetime.today()/date.today() に依存しない設計（target_date を明示的に渡す）。
- API 呼び出し失敗時は例外を全て投げずにロギングしフェイルセーフで継続する箇所が複数ある（運用時に部分データ欠落が起きても全体処理を継続する方針）。
- デフォルトの DB パスなどは Settings で指定可能（例: DUCKDB_PATH default "data/kabusys.duckdb"、SQLITE_PATH default "data/monitoring.db"）。
- 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（機能に応じて必要）。

今後の計画（抜粋）
- monitoring モジュールの実装と監視/通知ワークフローの充実化。
- ETL の具体的な pipeline 実装と quality モジュールの追加チェック。
- モデルとプロンプト改善、バッチスループットとコスト最適化。

もしこの CHANGELOG に追加してほしいリリース日付・詳細や、特定の変更点（例: あるファイルの変更履歴をもっと詳しく）を反映したい場合は教えてください。