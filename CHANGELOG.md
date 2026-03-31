CHANGELOG
=========
この CHANGELOG は Keep a Changelog の形式に準拠しています。  
リリース履歴はコードベース（src/ 以下）の実装内容から推測して作成しています。

[Unreleased]
------------

- なし（初回公開リリースは 0.1.0）

[0.1.0] - 2026-03-31
-------------------

Added
- パッケージ基盤
  - kabusys パッケージを追加。パッケージバージョンを __version__ = "0.1.0" として公開。
  - パッケージ __all__ に data / strategy / execution / monitoring を用意（モジュール分割方針を明示）。

- 環境設定・読み込み機能（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする機能を実装。
  - プロジェクトルートの自動検出（.git または pyproject.toml を起点）に対応し、CWD に依存しないロードを実現。
  - .env のパーサ実装：
    - export KEY=val 形式対応
    - シングル/ダブルクォートとバックスラッシュエスケープの解釈
    - 行コメント（#）の扱い（クォート内は無視、非クォートでは直前が空白/タブの場合にコメントとみなす等）
  - 読み込み優先順位: OS 環境変数 > .env.local > .env。自動読み込みを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD を用意。
  - Settings クラスを提供し、各種必須設定（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティとして取得・バリデート。
  - 環境（KABUSYS_ENV）とログレベル（LOG_LEVEL）値の検証ロジックを実装。
  - データベースパス取得ユーティリティ（DUCKDB_PATH, SQLITE_PATH）を提供。

- データプラットフォーム（kabusys.data）
  - ETL パイプラインインターフェース（pipeline.ETLResult と etl の再エクスポート）。
  - 市場カレンダー管理（calendar_management）:
    - market_calendar テーブルに基づく営業日判定ロジック（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）。
    - DB データ優先、未登録日は曜日ベースでフォールバックする一貫した挙動。
    - calendar_update_job による J-Quants からの差分取得・バックフィル・保存処理と健全性チェックの実装。
  - ETL のユーティリティ（pipeline）:
    - 差分取得ロジック、最終日取得ヘルパ、バックフィル挙動、ETLResult（品質チェック結果やエラーの集約）を実装。
    - quality チェックの結果を ETLResult に保持する構造を用意。

- AI / ニュース NLP（kabusys.ai）
  - ニュースセンチメント解析（news_nlp）
    - raw_news と news_symbols を集約し、銘柄別に記事をトリムして OpenAI (gpt-4o-mini) にバッチ送信。
    - JSON Mode 応答を期待しつつレスポンスの堅牢なバリデーション（前後余分テキストの復元、results リストの検証、スコア数値チェック、既知コードのみ採用）。
    - レート制限(429)、ネットワーク断、タイムアウト、5xx に対する指数バックオフリトライ。
    - 取得スコアは ±1.0 にクリップし、ai_scores テーブルへ部分置換（該当コードのみ DELETE→INSERT）して部分失敗時の保全を行う。
    - タイムウィンドウ計算（JST ベース、UTC 変換）を calc_news_window として実装。
  - 市場レジーム判定（regime_detector）
    - ETF 1321（日経225連動）の 200 日 MA 乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を組合せて日次で 'bull'/'neutral'/'bear' を判定。
    - prices_daily / raw_news からデータ取得、OpenAI 呼び出し（gpt-4o-mini）によるマクロセンチメント評価、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラーやパース失敗時はフォールバック macro_sentiment=0.0 とするフェイルセーフ設計。
    - OpenAI 呼び出しは内部で再試行ロジックを持つ（リトライ・エクスポネンシャルバックオフ）。

- Research（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比を計算。
    - calc_value: raw_financials から最新財務を取得し PER・ROE を計算。
    - 実装は DuckDB SQL を活用し、prices_daily / raw_financials のみ参照（外部 API にはアクセスしない）。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得。horizons 引数にバリデーション。
    - calc_ic: スピアマンランク相関（IC）計算。データ不足時は None を返す。
    - rank, factor_summary: ランク変換（同順位は平均ランク）と基本統計量（count/mean/std/min/max/median）を計算。

Changed
- 設計方針の明示
  - 全ての AI / スコア生成関数は datetime.today() や date.today() を直接参照せず、target_date を引数で受け取ることでルックアヘッドバイアスを防止する設計を採用。
  - DuckDB との組合せでの互換性・空リストバインドの扱い（executemany の空リスト回避）に配慮した実装。

Fixed / Robustness
- .env 読み込み周りの堅牢化
  - ファイル読み込み失敗時に警告を出し処理を継続。
  - 既存 OS 環境変数を保護する protected パラメータを導入して .env.local による上書きを制御。
- AI 呼び出し周りの堅牢化
  - OpenAI API 呼び出しでの一時エラー（ネットワーク/429/タイムアウト/5xx）に対するリトライ、非 5xx の APIError は再試行しない等のハンドリングを実装。
  - レスポンスパース失敗や想定外フォーマット時は警告ログを出し、処理を継続（スコアに対してはフォールバック値を適用）。
- データ不足時のフォールバック
  - MA 等の計算に必要な履歴が不足する場合、明示的に中立値（例: ma200_ratio=1.0）や None を返し、呼び出し側で安全に扱えるよう設計。

Security
- API キーの注入
  - OpenAI API キーは引数で注入可能（テスト容易化）で、未提供時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出して失敗を明示。

Notes / Migration
- 依存:
  - duckdb、openai（OpenAI Python SDK）が必要。
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID, OPENAI_API_KEY（OpenAI は AI 機能を使用する場合）。
- 自動 .env ロードは KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定することで無効化可能。
- データベースファイルのデフォルトパス:
  - DUCKDB_PATH= data/kabusys.duckdb（変更する場合は環境変数で上書き）

Acknowledgements / TODO（推測）
- strategy / execution / monitoring モジュールはパッケージ API に含まれる予定（__all__ に名前あり）が、今回のコードでは具体実装が含まれていないため今後の追加が想定される。
- 将来的に PBR や配当利回りなどのバリューファクター拡張、AI モデルの切替やレート制限緩和のためのキューイング実装などが想定される。

以上。必要であれば各変更点をさらに分割して詳細なリリースノート（例: ファイル/関数単位の変更ログ）を生成します。