KEEP A CHANGELOG
すべての重要な変更点を追跡します。  
フォーマットは Keep a Changelog に準拠しています。  

[Unreleased]
- なし

[0.1.0] - 2026-03-31
-------------------
Added
- パッケージ基盤
  - 初期バージョンをリリース (kabusys v0.1.0)。
  - パッケージ公開情報: src/kabusys/__init__.py に __version__ = "0.1.0" を設定。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルおよび環境変数から設定値を読み込む自動ロード機能を実装。
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して判定。
    - 読み込み順序: OS環境変数 > .env.local > .env。KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env パーサは export KEY=val 形式、シングル/ダブルクォート、エスケープ、インラインコメント等に対応。
    - .env 読み込み時の既存 OS 環境変数保護（protected set）をサポート。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）や
    DB パス（DUCKDB_PATH, SQLITE_PATH）、環境種別（KABUSYS_ENV）やログレベル（LOG_LEVEL）をプロパティで取得。
  - 無効な env/log level 値に対する検証を実装（ValueError を送出）。

- AI 関連 (kabusys.ai)
  - ニュース NLP スコアリング (news_nlp)
    - raw_news / news_symbols を集約し、銘柄単位にまとめて OpenAI (gpt-4o-mini, JSON Mode) に送信してセンチメント (ai_score) を算出。
    - チャンク処理 (最大 20 銘柄/コール)、1 銘柄当たり記事数上限・文字数上限、レスポンス検証を実装。
    - レート制限 (429)、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。非リトライエラーはスキップして継続するフェイルセーフ設計。
    - レスポンスのパースとバリデーション: JSON 抽出、results 配列確認、code の正規化、スコア数値チェック、±1.0 クリップ。
    - DuckDB の executemany に対する空パラメータ回避ロジックを実装して互換性を確保。
    - 公開関数: score_news(conn, target_date, api_key=None) → 書き込み銘柄数（int）。API キー未指定時は ValueError。
    - ニュースウィンドウの計算ユーティリティ calc_news_window(target_date) を提供（JST で前日15:00〜当日08:30 を UTC に変換）。
  - 市場レジーム判定 (regime_detector)
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して
      日次の市場レジーム（bull / neutral / bear）を算定し、market_regime テーブルへ冪等的に書き込む。
    - OpenAI 呼び出しは専用実装（news_nlp とは別実装）で、API 失敗時は macro_sentiment=0.0 にフォールバック。
    - レトライ/バックオフ、エラー種別に応じたハンドリングを実装。score_regime(conn, target_date, api_key=None) を提供（成功時 1 を返す）。API キー未指定時は ValueError。
    - lookahead バイアス防止のため、target_date 未満のデータのみ参照するクエリ等の設計方針を採用。

- データ基盤 (kabusys.data)
  - マーケットカレンダー管理 (calendar_management)
    - market_calendar テーブルを基に営業日判定ロジックを提供:
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days
    - DB 登録値優先、未登録日は曜日ベースのフォールバックを行う一貫した動作。
    - カレンダー夜間バッチ calendar_update_job(conn, lookahead_days=90) を実装（J-Quants API 経由で差分取得→保存、バックフィル、健全性チェック）。
    - 最大探索日数・バックフィル日数・先読み日数などの定数による安全機構を導入。
  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを導入: ETL 実行結果の構造化（取得件数、保存件数、品質問題、エラーなど）。
    - ETL パイプラインのユーティリティ（差分取得、backfill、品質チェック、idempotent 保存方針）を実装予定のインターフェースとして整備。
    - jquants_client, quality モジュールとの連携を想定する実装（例: 最終取得日の取得、テーブル存在チェック、日付変換ユーティリティ等）。
    - etl モジュールから ETLResult を再エクスポート。

- リサーチ / ファクター (kabusys.research)
  - factor_research モジュール
    - モメンタム（1M/3M/6M）、200 日移動平均乖離、ATR（20 日）、流動性（20 日平均売買代金／出来高変化率）、バリューファクター（PER、ROE）を計算する関数を実装:
      - calc_momentum(conn, target_date)
      - calc_volatility(conn, target_date)
      - calc_value(conn, target_date)
    - DuckDB 上の SQL ウィンドウ関数を活用し、結果は (date, code) をキーとする dict のリストで返す。
    - データ不足時の None 返却やログ出力など堅牢性を考慮。
  - feature_exploration モジュール
    - 将来リターン計算: calc_forward_returns(conn, target_date, horizons=None)（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算: calc_ic(factor_records, forward_records, factor_col, return_col)（Spearman ρ、有効レコード 3 件未満は None）。
    - ランク化ユーティリティ rank(values)、統計サマリー factor_summary(records, columns) を提供。
    - pandas など外部依存を持たない純標準ライブラリ実装。

Changed
- 全般
  - 多くの計算・バッチ処理で「datetime.today() / date.today() を直接参照しない」設計方針を採用し、target_date を明示的に引数で受け取ることでルックアヘッドバイアスを排除。

Fixed
- トランザクション安全性
  - DB 書込み時に例外発生した場合、ROLLBACK を試行し、ROLLBACK 自体が失敗した場合は警告ログを出す実装を追加（score_regime, score_news 等）。
- DuckDB 互換性
  - executemany に空リストを渡さないガードを追加（DuckDB 0.10 の制約回避）。

Security
- 外部 API キーの取り扱い
  - OpenAI API キーは引数で注入可能（テスト用）かつ環境変数 OPENAI_API_KEY を参照する実装。未設定時は ValueError。

Notes / Implementation details
- OpenAI 呼び出しは gpt-4o-mini を利用し、JSON Mode（response_format={"type":"json_object"}）で整形された JSON を期待する。
- LLM 呼び出しは冗長性対策（リトライ・バックオフ・フォールバック値）を含む安全設計。
- 多くのモジュールが DuckDB 接続を受け取り SQL と Python を組み合わせて処理する設計（外部ネットワーク呼び出しは AI / J-Quants クライアントに限定）。
- ロギングを広範に追加し、情報・警告・例外時のトレースを確保。
- 将来的には pipeline / etl での実行順序・監査ログ・品質チェック結果の収集を通じた運用向け機能拡張を想定。

署名
- 本 CHANGELOG は提示されたソースコードから推測して作成した初期リリースノートです。実際のコミット履歴・リリース手順に合わせて必要に応じて修正してください。