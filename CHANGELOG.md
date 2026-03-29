CHANGELOG.md
=============

すべての顕著な変更を追跡します。  
このファイルは "Keep a Changelog" のフォーマットに準拠しています。  

[Unreleased]
------------

（なし）

[0.1.0] - 2026-03-29
-------------------

Added
- 初回公開リリース: KabuSys 日本株自動売買システムの骨格を実装。
  - パッケージ情報
    - kabusys.__version__ = 0.1.0 を設定。
    - パッケージの公開モジュール一覧を __all__ で定義（data, strategy, execution, monitoring）。

  - 設定 / 環境変数管理（kabusys.config）
    - .env / .env.local 自動読み込み機能を実装（プロジェクトルートの検出: .git または pyproject.toml を基準）。
    - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロード無効化可能。
    - .env の柔軟なパース:
      - export KEY=val 形式対応、クォート内のバックスラッシュエスケープ対応、インラインコメント対応等。
    - Settings クラスを提供し、アプリケーション設定をプロパティ経由で取得:
      - J-Quants / kabuステーション / Slack / DB パス等のプロパティを公開。
      - 環境値検証（KABUSYS_ENV / LOG_LEVEL の許容値チェック）と補助プロパティ（is_live / is_paper / is_dev）。
    - 必須環境変数未設定時は ValueError を投げる _require を実装。

  - AI モジュール（kabusys.ai）
    - ニュースNLP スコアリング（kabusys.ai.news_nlp）
      - raw_news と news_symbols を使って銘柄ごとのニュースを集約し、OpenAI（gpt-4o-mini）の JSON Mode でスコアリング。
      - タイムウィンドウ（JST 基準）を calc_news_window で計算（前日 15:00 JST ～ 当日 08:30 JST、UTC に変換して DB と照合）。
      - バッチ処理（最大 20 銘柄/回）、トークン肥大化対策（記事数・文字数制限）、レスポンスバリデーション、スコアの ±1.0 クリップ。
      - リトライ/バックオフ（429, ネットワーク断, タイムアウト, 5xx）を実装。致命的でない失敗はスキップして継続するフェイルセーフ設計。
      - DuckDB への書き込みは冪等性を意識（対象コードのみ DELETE → INSERT、executemany の空リスト回避）。
      - API キーが未指定（引数 or OPENAI_API_KEY）なら ValueError を送出。
    - 市場レジーム判定（kabusys.ai.regime_detector）
      - ETF 1321 の 200 日 MA 乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で market_regime を算出・保存。
      - マクロキーワードフィルタ、最大記事数の制限、OpenAI 呼び出し（gpt-4o-mini）の独立実装、リトライ/バックオフ、JSON パース・フォールバック（API 失敗時は macro_sentiment=0.0）。
      - look‑ahead バイアス防止設計（target_date 未満のみ参照）と DB への冪等書き込みトランザクション（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK）。

  - データ処理（kabusys.data）
    - マーケットカレンダー管理（kabusys.data.calendar_management）
      - market_calendar を利用した営業日判定 API を提供:
        - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
      - DB データ（登録あり）を優先し、未登録日は曜日ベースのフォールバック（週末は非営業日）で一貫した振る舞い。
      - カレンダーの夜間差分更新ジョブ（calendar_update_job）を実装（J-Quants クライアント経由で差分取得、バックフィル、健全性チェック）。
      - 探索は最大 _MAX_SEARCH_DAYS で制限し無限ループを防止。
    - ETL パイプライン（kabusys.data.pipeline, kabusys.data.etl）
      - ETLResult データクラスを公開（取得/保存件数、品質問題、エラー一覧、ヘルパー: has_errors, has_quality_errors, to_dict）。
      - 差分取得、保存、品質チェックの設計方針を反映（バックフィル、品質チェックを集積し呼び出し元で判断可能にする）。
      - DuckDB 関連ヘルパー（テーブル存在チェック、日付最大値取得など）を実装。

  - リサーチ / ファクター計算（kabusys.research）
    - ファクター計算群（kabusys.research.factor_research）
      - モメンタム（1M/3M/6M リターン、200 日 MA 乖離）, ボラティリティ（20 日 ATR 等）, バリュー（PER, ROE）を計算する関数を実装。
      - DuckDB 上の prices_daily / raw_financials のみ参照する安全設計（実取引 API にはアクセスしない）。
      - データ不足時の挙動（十分な履歴がない場合は None を返す）や SQL ベースのウィンドウ集計を採用。
    - 特徴量探索ユーティリティ（kabusys.research.feature_exploration）
      - 将来リターン calc_forward_returns（複数ホライズン対応、入力チェック）、IC（calc_ic）計算、rank、factor_summary を実装。
      - pandas 等に依存せず標準ライブラリのみで実装。ランクは同順位に平均ランクを割り当てるロジックを採用。

  - その他
    - モジュール設計の一貫性: ルックアヘッドバイアス回避（datetime.today()/date.today() を直接参照しない設計）、テスト容易性（内部 API 呼び出し箇所を差し替え可能にする）を各所で考慮。
    - OpenAI 呼び出し関数は各サブモジュールで独自に実装し、モジュール間でプライベート関数を共有しない設計。

Notes / 運用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID は Settings のプロパティで必須とされているため、本番運用時は .env または環境変数で設定してください。
  - OpenAI を使う関数（score_news, score_regime）は api_key 引数か環境変数 OPENAI_API_KEY が必須。未設定だと ValueError が発生します。
- デフォルト DB パス:
  - DUCKDB_PATH のデフォルトは data/kabusys.duckdb、SQLITE_PATH のデフォルトは data/monitoring.db。必要に応じて環境変数で上書きしてください。
- 自動 .env 読み込み:
  - プロジェクトのルートを .git または pyproject.toml で検出します。配布後やテスト時に自動読み込みを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- フェイルセーフ/ロールバック:
  - AI API の失敗は原則スコアを 0.0 にフォールバック（レジーム判定等）、DB 書き込みはトランザクションで行い、失敗時は ROLLBACK を試行して例外を上位へ伝播します。
- 時刻/ウィンドウ:
  - ニュース集計ウィンドウや calendar_update_job 等は JST と UTC の扱いに注意（コード内に変換ロジックを明示）。

変更履歴の管理方針
- 今後のリリースでは Breaking change / Deprecated / Removed / Fixed / Security 等のカテゴリを使用して差分を明確に記録します。初回リリースのため今回のエントリは機能追加中心の記述にとどめています。

-----