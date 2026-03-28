CHANGELOG
=========

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠します。

## [0.1.0] - 2026-03-28

Added
-----
- 初回公開: KabuSys 日本株自動売買システムの基礎モジュール群を追加。
  - パッケージエントリ (src/kabusys/__init__.py)
    - バージョン: 0.1.0
    - 公開サブパッケージ: data, strategy, execution, monitoring（パッケージAPIの意図的な公開）
- 環境設定/ローダ (src/kabusys/config.py)
  - .env / .env.local ファイルおよびOS環境変数から設定を自動読み込み（プロジェクトルートを .git または pyproject.toml から探索）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォートとバックスラッシュエスケープ、インラインコメント扱いの厳密化。
  - .env の読み込みで既存 OS 環境変数を保護する protected 機能（.env と .env.local の読み込み順と override ロジック）。
  - Settings クラスで主要設定をプロパティとして公開:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - DUCKDB_PATH, SQLITE_PATH
    - KABUSYS_ENV（development / paper_trading / live の検証）, LOG_LEVEL（検証）
    - is_live / is_paper / is_dev のユーティリティプロパティ
  - 必須環境変数未設定時は明示的に ValueError を送出する振る舞い。
- AI モジュール (src/kabusys/ai)
  - news_nlp モジュール (src/kabusys/ai/news_nlp.py)
    - raw_news と news_symbols から銘柄毎に記事を集約し、OpenAI (gpt-4o-mini) の JSON モードでセンチメントを取得して ai_scores テーブルへ書き込み。
    - バッチ処理（最大 20 銘柄/回）・記事数/文字数トリム・JSON レスポンスの厳密バリデーション。
    - リトライ戦略（429, ネットワーク断, タイムアウト, 5xx）に対する指数バックオフ。
    - レスポンス検証に失敗した銘柄はスキップし、部分成功時には既存のスコアを消さない（DELETE → INSERT の差分置換）。
    - calc_news_window ユーティリティ（JST のニュース収集ウィンドウ）を提供。
  - regime_detector モジュール (src/kabusys/ai/regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離 (重み 70%) とニュースベースの LLM マクロセンチメント (重み 30%) を合成して市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。
    - API 失敗時のフェイルセーフ（macro_sentiment=0.0）、LLM 呼び出しのリトライ/backoff、5xx の判定対応。
    - ルックアヘッドバイアス防止の設計（内部で datetime.today()/date.today() を参照しない、DB クエリは target_date 未満を使用）。
  - 共通設計: OpenAI 呼び出しはテスト容易性のため差し替え可能な内部ラッパー実装（モジュール間でプライベート関数を共有しない設計）。
- Data モジュール (src/kabusys/data)
  - calendar_management (src/kabusys/data/calendar_management.py)
    - JPX カレンダーデータの夜間差分更新ジョブ calendar_update_job を実装（J-Quants クライアント経由）。
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day といった営業日判定ユーティリティを提供。
    - market_calendar 未取得時に曜日ベースのフォールバックを採用。DB にデータがある場合は DB 値優先。
    - 最大探索日数やバックフィル・健全性チェックを含む堅牢な実装。
  - ETL / pipeline (src/kabusys/data/pipeline.py, src/kabusys/data/etl.py)
    - ETLResult データクラスを公開（ETL 実行の集約結果と品質チェック情報を保持）。
    - 差分取得、バックフィル、保存（idempotent / ON CONFLICT DO UPDATE）、品質チェックのフレームワーク設計に対応。
    - DuckDB との互換性を考慮したテーブル存在チェックや最大日付取得ユーティリティを実装。
- Research モジュール (src/kabusys/research)
  - factor_research (src/kabusys/research/factor_research.py)
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率を計算。
    - calc_value: raw_financials からの EPS/ROE を用いた PER/ROE 計算（target_date 以前の最新財務データを使用）。
    - 各関数は DuckDB SQL を利用し、外部 API に依存しない実装。
  - feature_exploration (src/kabusys/research/feature_exploration.py)
    - calc_forward_returns: 複数ホライズン（デフォルト: 1,5,21）で将来リターンを計算。horizons 入力検証あり。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。データ不足時は None を返す。
    - rank: 同順位は平均ランクを返すランク化ユーティリティ（丸めで ties を安定化）。
    - factor_summary: 各ファクターカラムの count/mean/std/min/max/median を計算。
  - research パッケージ __init__ で主要関数を再エクスポートして使いやすく整理。
- その他
  - DuckDB を用いる全ての DB 書き込みは冪等性とトランザクション（BEGIN/COMMIT/ROLLBACK）を意識した実装。ROLLBACK failure は警告ログで捕捉。
  - ロギングメッセージを多用し、運用時のデバッグ・監査をサポート。

Changed
-------
- 初版のため該当なし。

Fixed
-----
- 初版のため該当なし。

Removed
-------
- 初版のため該当なし。

Security
--------
- 初版のため該当なし。

Notes / Design Decisions
------------------------
- ルックアヘッドバイアス防止: AI スコアリングやレジーム判定関数はいずれも内部で date.today()/datetime.today() を参照しない設計。呼び出し側が target_date を明示的に渡すことで再現性を確保しています。
- フェイルセーフ: 外部 API（OpenAI, J-Quants等）への依存箇所は、API エラー時に処理を継続するか安全なデフォルト値へフォールバックする実装を優先しています（例: macro_sentiment=0.0、スコアスキップ）。
- テスト容易性: OpenAI 呼び出しやファイル読み込みなどは patch / モックで差し替えやすいよう内部ラッパーや明確な抽象化を用意しています。
- DuckDB 互換性: executemany に空リストを渡せない既知の制約（DuckDB 0.10 等）を回避するチェックを実装しています。

今後
----
- strategy / execution / monitoring の具象実装（本リリースではパッケージ名のみ公開）。
- より詳細な品質チェックルールと監視アラートの実装。
- ドキュメント（API リファレンス、運用ガイド、サンプル ETL 実行手順）の拡充。