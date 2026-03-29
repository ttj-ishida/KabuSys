KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは「Keep a Changelog」に準拠し、安定版リリースごとに主要な追加・変更点を日本語で記載します。

0.1.0 - 2026-03-29
------------------
初回リリース。KabuSys のコア機能を提供する多数のモジュールを追加しました。主な追加点と設計上の留意点は以下の通りです。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = "0.1.0"）。
  - パッケージ外部公開サブパッケージ: data, strategy, execution, monitoring（__all__ に宣言）。
- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ロード実装。
  - プロジェクトルート自動検出機能: .git または pyproject.toml を基準に探索（CWD 非依存）。
  - .env の堅牢なパーサ実装:
    - export KEY=val 形式対応、シングル/ダブルクォート内のバックスラッシュエスケープ対応。
    - インラインコメント扱いの判定（クォート無し時は '#' の直前がスペース/タブならコメントと判定）。
  - 自動ロード順序: OS 環境変数 > .env.local（上書き）> .env（既存値保護）。
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD。
  - Settings クラスを公開（settings）。以下の主要設定プロパティを提供:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL（デフォルトローカル）、SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH / SQLITE_PATH（Path 型で展開）
    - KABUSYS_ENV（development / paper_trading / live の検証）、LOG_LEVEL（DEBUG/INFO/WARNING/ERROR/CRITICAL の検証）
    - is_live / is_paper / is_dev のヘルパープロパティ
  - 未設定の必須環境変数アクセス時は ValueError を投げるように統一。
- データ処理（kabusys.data）
  - ETL パイプライン公開インターフェース（kabusys.data.etl が pipeline.ETLResult を再エクスポート）。
  - pipeline.ETLResult: ETL 実行結果を表す dataclass（品質問題／エラーの集約、辞書化メソッド等を提供）。
  - pipeline モジュール: 差分取得、バックフィル、品質チェック連携（設計の骨子を実装）。DuckDB を用いた最大日付取得等のユーティリティを実装。
  - calendar_management モジュール:
    - market_calendar を基にした営業日判定ユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録が無い場合は曜日ベース（土日を休日）でフォールバックする一貫したロジック。
    - calendar_update_job: J-Quants からの差分フェッチと冪等保存（バックフィルと健全性チェック付き）。
    - 最大探索範囲制限や不整合時の安全停止を実装（例: _MAX_SEARCH_DAYS, _SANITY_MAX_FUTURE_DAYS）。
- 研究・因子計算（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離 (ma200_dev) を DuckDB の SQL で計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率を計算（true_range の NULL 伝播を考慮）。
    - calc_value: raw_financials からの最新財務データと株価を組み合わせて PER / ROE を計算（EPS=0/欠損時は None）。
    - 全関数は prices_daily / raw_financials のみ参照し外部APIを呼ばない設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンをまとめて取得する最適化されたクエリ実装。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を実装。データ不足時は None。
    - rank: 同順位は平均ランク処理。丸め誤差対策のため round(..., 12) を使用。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算するユーティリティ。
- AI（kabusys.ai）
  - news_nlp.score_news:
    - raw_news と news_symbols を元に銘柄ごとに記事を集約し、OpenAI（gpt-4o-mini, JSON mode）でバッチ評価して ai_scores テーブルへ書き込む。
    - タイムウィンドウ: 前日 15:00 JST ～ 当日 08:30 JST（UTC に変換して DB クエリで比較）。
    - バッチサイズ、記事数・文字数トリム、429/ネットワーク/5xx の指数バックオフリトライ、レスポンス検証（results 配列・型チェック）を実装。
    - 部分失敗を許容する書き込み戦略（対象コードのみ DELETE → INSERT）で既存スコアの保護。
    - テスト容易性: _call_openai_api をモックパッチ可能に設計。
  - regime_detector.score_regime:
    - ETF 1321 の 200 日 MA 乖離（70%）とマクロニュース LLM センチメント（30%）を合成して market_regime に日次で保存。
    - マクロニュースは news_nlp.calc_news_window と raw_news からフィルタして取得。LLM 呼び出しは専用実装でモジュール分離。
    - API 障害時は macro_sentiment=0.0 としてフォールバック。計算結果はクリッピングしてラベル付け（bull/neutral/bear）。
    - DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT）と ROLLBACK の取り扱いを実装。
  - 両モジュール共通:
    - OpenAI クライアントを使う関数は api_key を引数で上書き可能（環境変数 OPENAI_API_KEY をデフォルト参照）。
    - レスポンスの JSON パース失敗や想定外フォーマットに対して安全にスキップ・フォールバックする設計。
- テスト・運用を意識した設計
  - いくつかの関数は datetime.today()/date.today() を直接参照しないことでルックアヘッドバイアスを防止（target_date を明示受け取り）。
  - API 呼び出しや外部依存は差し替え可能（モック化）にしてあるためユニットテストの容易化を意識。
- DB（DuckDB）との互換性考慮
  - DuckDB 0.10 の executemany における空リストバインドの制約への対処（空パラメータは実行しないガードを実装）。
  - 日付の取り扱いやクエリ内のウィンドウ処理は DuckDB との互換性を考えた SQL を採用。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Security
- 必須外部キー（OpenAI / J-Quants / Slack 等）は環境変数経由で安全に注入する設計。パッケージ側でキーをログに出力しないことを旨としている。

Notes / Known behaviors
- OpenAI 呼び出しは gpt-4o-mini を想定した JSON Mode を利用。API の仕様変更や応答フォーマットに対する堅牢化は実装されているが、将来的な SDK 変更で追加の対応が必要になる可能性があります。
- calendar_update_job や pipeline の外部 J-Quants クライアント（kabusys.data.jquants_client）は実行環境で適切に設定されていることが前提です。
- settings による自動 .env ロードはプロジェクトルートの検出に依存するため、配布後やテスト時は KABUSYS_DISABLE_AUTO_ENV_LOAD を使って自動ロードを無効化できます。
- 一部関数は DB のテーブル構成（prices_daily / raw_news / news_symbols / ai_scores / market_regime / raw_financials / market_calendar 等）に依存します。使用前にスキーマを用意してください。

Authors
- 初期実装チーム

─────
将来のリリースでは、ユニットテストカバレッジ、さらに詳細な品質チェック（quality モジュール強化）、監視・アラート連携（Slack/メール等）の具体的実装、strategy / execution モジュールの発展を予定しています。