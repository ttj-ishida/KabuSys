CHANGELOG
=========

すべての変更は「Keep a Changelog」規約に準拠して記載しています。  
フォーマットの詳細: https://keepachangelog.com/ja/1.0.0/

v0.1.0 - 2026-03-28
-------------------

初回公開リリース。日本株自動売買・データ基盤・リサーチ用ユーティリティを含む基盤実装を追加。

Added
- パッケージ初期化
  - kabusys パッケージと __version__ = "0.1.0" を追加。
  - パブリックモジュールとして data, strategy, execution, monitoring を公開。

- 環境設定管理 (kabusys.config)
  - .env ファイル（.env, .env.local）および OS 環境変数からの設定読み込み機能を実装。
  - プロジェクトルート検出は __file__ を起点に .git または pyproject.toml を探索して行う（CWD 非依存）。
  - .env パーサを実装（export 形式、クォート内のエスケープ、コメント処理などに対応）。
  - 自動ロードを無効化する環境変数: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを提供し、アプリケーション設定値をプロパティ経由で取得可能:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL
    - SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH（デフォルトパスを用意）
    - KABUSYS_ENV（development / paper_trading / live）、LOG_LEVEL（DEBUG/INFO/...）の検証ロジック
  - 必須設定未定義時は明示的な ValueError を発生させる _require 関数を追加。
  - OS 環境変数と .env の上書きルール（OS > .env.local > .env）と protected キーの概念を追加。

- AI モジュール (kabusys.ai)
  - ニュースセンチメント（score_news）と市場レジーム判定（score_regime）機能を追加。
  - OpenAI（gpt-4o-mini）を JSON Mode で呼び出すラッパー実装を提供（テスト時に差し替え可能な内部呼び出しポイントあり）。
  - score_news:
    - ニュース収集ウィンドウ（JST 前日15:00〜当日08:30）を calc_news_window で算出（UTC naive datetime）。
    - raw_news / news_symbols を銘柄別に集計し、銘柄ごとに最大記事数・文字数でトリムしてバッチ送信（チャンクサイズ: 20）。
    - リトライ（429・ネットワーク・タイムアウト・5xx）を指数バックオフで実装。
    - レスポンスのバリデーション（JSON 抽出、results 構造、コード照合、スコア数値チェック）を実装。
    - スコアは ±1.0 にクリップして ai_scores テーブルへ冪等置換（DELETE → INSERT）する。
    - API 未設定時は ValueError を送出。記事がなければスキップして 0 を返す。
  - regime_detector:
    - ETF 1321（日経225レバ連動型）200日移動平均乖離（重み 70%）とニュースマクロセンチメント（重み 30%）を合成して日次でレジーム判定（bull/neutral/bear）。
    - prices_daily と raw_news を参照し、ma200_ratio を計算。マクロ記事がある場合のみ LLM をコール。
    - LLM 呼び出し失敗時は macro_sentiment を 0.0 にフォールバック（フェイルセーフ）。
    - 結果を market_regime テーブルへ冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）。
    - 外部依存（news_nlp）とのモジュール結合を避ける設計（内部で独自に OpenAI 呼出し実装）。

- データ基盤モジュール (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダーの管理、営業日判定、next/prev/get_trading_days、is_sq_day、夜間バッチ更新(calendar_update_job) を実装。
    - market_calendar が未取得の場合は曜日ベース（土日非営業日）でフォールバック。
    - カレンダー更新は J-Quants クライアント経由で差分取得→冪等保存。バックフィル、健全性チェックを実装。
  - pipeline / etl:
    - ETLResult dataclass と ETL の補助ユーティリティを追加（差分取得、backfill、品質チェックの枠組みを想定）。
    - DuckDB の最終日取得・テーブル存在チェックなどのユーティリティを実装。
    - データ保存は idempotent（既存レコード上書き）を前提に実装する方針。
  - etl は ETLResult を公開インターフェースとして再エクスポート。

- リサーチモジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M、ma200偏差）、ボラティリティ（20日ATR等）、バリュー（PER/ROE）等の計算関数を実装。
    - DuckDB を用いた SQL ベース実装で、prices_daily / raw_financials のみを参照。
    - データ不足時の扱い（None）やログ出力を明記。
  - feature_exploration:
    - 将来リターン calc_forward_returns（任意 horizons 対応）、IC（Spearman の ρ）計算 calc_ic、ランク化ユーティリティ rank、ファクター統計 summary（factor_summary）を実装。
    - 外部ライブラリに依存せず標準ライブラリのみで実装。
  - research パッケージは必要な関数を __all__ で公開。

- 汎用実装上の設計方針・品質改善
  - ルックアヘッドバイアス対策: 各種処理で datetime.today() / date.today() を直接参照しない設計（target_date を引数で明示）。
  - DuckDB と並行で動くことを想定した冪等書き込み（DELETE→INSERT など）。
  - API 呼出しでの堅牢性（リトライ、5xx の扱い、最大リトライ、ログ）を徹底。
  - テスト容易性: OpenAI 呼出しの差し替えポイント、KABUSYS_DISABLE_AUTO_ENV_LOAD による環境依存の無効化等。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- 環境変数取り扱いにおいて OS 環境変数を保護する protected キー概念を導入（.env による上書きを回避）。
- API キー未設定時は明示的に例外を出すことで誤動作の心配を減らす。

Notes / 注意事項
- OpenAI API
  - score_news / score_regime は OpenAI API キー（OPENAI_API_KEY）または api_key 引数が必須。未設定だと ValueError が発生します。
  - JSON Mode を期待したパースロジックを実装していますが、LLM 応答の揺らぎ（前後テキスト混入等）に対する復元ロジックも組み込んでいます。

- データベース / テーブル前提
  - 多くの処理が DuckDB 上の以下テーブルを前提とします:
    - prices_daily, raw_news, news_symbols, ai_scores, market_regime, raw_financials, market_calendar
  - DuckDB の executemany 空リストに対する制約（バージョン依存）に配慮した実装を行っています。

- 時刻とタイムゾーン
  - ニュースウィンドウや calendar の計算は JST/UTC の差分を明示して扱う（内部は UTC naive datetime を使用）。

- テスト容易性
  - 内部の OpenAI 呼び出し関数（_call_openai_api）を unittest.mock.patch などで差し替え可能にしているため、外部 API に依存しない単体テストが行いやすくなっています。

既知の制約 / 今後の改善候補
- score_news の出力は現フェーズで sentiment_score と ai_score を同値で扱っています。将来的に微調整や複数軸スコアの導入を検討。
- 一部の DuckDB SQL バインドの挙動は DuckDB のバージョンに依存する可能性があるため、動作確認済みバージョンに関するドキュメント整備が必要。
- API レートやコストを考慮した運用方針（バッチ間隔、モデル選択など）の追記が必要。

---

今後のリリースでは、strategy / execution / monitoring に関する実運用ロジック（発注戦略、発注実行ラッパー、モニタリング・アラート機能）、より詳細な品質チェック機能、CI テストカバレッジの拡充を予定しています。