CHANGELOG
=========

すべての重要な変更は "Keep a Changelog" の形式に従って記載しています。
このプロジェクトはセマンティックバージョニングを採用しています。

Unreleased
----------

（なし）

[0.1.0] - 2026-04-09
--------------------

Added
- パッケージ初期公開:
  - kabusys パッケージの公開モジュール定義（__version__ = "0.1.0"）。
- 環境変数 / 設定管理 (kabusys.config):
  - .env / .env.local の自動読み込み機能を実装。読み込み順は OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加（テスト用）。
  - プロジェクトルート自動検出ロジックを実装（.git または pyproject.toml を基準、__file__ 起点で探索）。
  - .env パーサを独自実装（export プレフィックス、クォート／エスケープ、インラインコメント対応）。
  - 環境変数保護（load 時に既存 OS 環境変数を protected として上書き回避）。
  - Settings クラスを導入し、アプリケーションで使用する設定値をプロパティで提供（J-Quants トークン、kabu API、LINE、DB パス、Paper Trading など）。
  - PAPER_FILL_MODE のバリデーション（"instant" / "partial" / "never" / "reject"）を追加。
  - 環境変数によるログレベル・実行環境（development/paper_trading/live）判定ロジックを追加。

- ニュース NLP / AI モジュール (kabusys.ai):
  - news_nlp.score_news: raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）で銘柄ごとのセンチメントを算出し ai_scores に書き込む処理を実装。
    - タイムウィンドウ計算（前日15:00 JST ～ 当日08:30 JST を UTC に変換）を実装（calc_news_window）。
    - バッチサイズ、トークン肥大化対策（1銘柄あたり記事数上限・文字数トリム）を実装。
    - JSON Mode を利用した厳密レスポンス期待、レスポンスのバリデーション（results 配列、code/score の型チェック等）を実装。
    - リトライ（429 / ネットワーク断 / タイムアウト / 5xx）に対する指数バックオフを実装。非リトライ対象エラーはスキップして継続するフェイルセーフ設計。
    - 部分失敗に備え、取得できた銘柄のみを DELETE → INSERT で置換する冪等的書き込みを実装（DuckDB 互換性考慮）。
  - ai.news_nlp 内部関数群（API 呼出しラッパ、レスポンス検証、チャンクスコア取得）を提供。単体テスト容易性のため _call_openai_api を差し替え可能に設計。
  - ai.regime_detector.score_regime: ETF（1321）の200日 MA 乖離とマクロニュース（LLM）を重み合成して市場レジーム（bull/neutral/bear）を判定し market_regime に保存する機能を実装。
    - ma200_ratio の計算、マクロ記事抽出、OpenAI 呼出し（リトライ / エラー処理）を実装。
    - LLM 呼出し失敗時は macro_sentiment=0.0 にフォールバックするフェイルセーフ動作。
    - レジーム合成ロジック（重み 70%:MA / 30%:マクロセンチメント、スコアクリップ）と閾値に基づくラベル付与を実装。
    - DB への冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - モジュール間の結合を避けるため、news_nlp の内部関数を直接共有しない実装方針を採用。

- データ処理 / ETL (kabusys.data):
  - ETLResult データクラスを公開（kabusys.data.pipeline.ETLResult を再エクスポート）。
  - pipeline モジュール: 差分取得、保存、品質チェックのための骨格を追加（ETLResult、定数、保存 / 品質チェックの設計方針を文書化）。
  - calendar_management:
    - market_calendar を扱うユーティリティ群を実装（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB データ優先、未登録日は曜日ベースのフォールバック、最大探索日数を設け無限ループを防ぐ設計。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得、バックフィル、健全性チェック、冪等保存）。
    - market_calendar の未取得／部分取得ケースへの堅牢な処理とログ出力を実装。
  - jquants_client と quality モジュールとの連携を想定した設計（fetch/save の抽象化）。

- リサーチ / ファクター計算 (kabusys.research):
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算する実装。
    - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算する実装。
    - calc_value: raw_financials から最新財務データを取得して PER / ROE を計算する実装。
    - 全関数は DuckDB 上の prices_daily / raw_financials のみを参照し、ルックアヘッドバイアスを排除する設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを計算。
    - calc_ic: ファクターと将来リターンのスピアマンランク相関（IC）を計算。
    - rank: 同順位は平均ランクとするランク付けユーティリティ。
    - factor_summary: count / mean / std / min / max / median を計算する統計サマリ機能。
  - zscore_normalize を data.stats から再エクスポートするインターフェース整備。

Changed
- 設計方針を明確化:
  - すべての AI / 研究 / ETL モジュールで datetime.today()/date.today() を直接参照しない方針を採用（ルックアヘッドバイアス防止、テスト容易性向上）。
  - DuckDB のバージョンによる制約（executemany に空リスト不可、リスト型バインドの不安定さ等）に配慮した SQL 実装と互換性対策を適用。
  - OpenAI API 呼び出しについてはエラー分類（429/ネットワーク/タイムアウト/5xx 等）ごとにリトライ方針を明確化し、非致命エラーはフェイルセーフで継続するように変更。

Fixed
- 初期公開のための各所の堅牢化（ファイル入出力の例外処理、DB トランザクションの ROLLBACK 保護、ログ出力の追加など）。

Security
- 環境変数の自動読み込みにおいて既存 OS 環境変数を保護する仕組み（protected set）を導入し、意図しない上書きを防止。

Notes / Implementation details
- OpenAI クライアントの生成は各関数内で行う（api_key を引数で注入可能）。テスト時は _call_openai_api をパッチして差し替え可能。
- DuckDB の日付値取り扱い、NULL 管理、行数不足時の挙動（None 返却または中立値使用）について明示的にログ出力を行う。
- 一部の設計・定数（ウィンドウ時刻・バッチサイズ・リトライ回数・モデル名等）は将来的に設定化できるようファイル内定数としてまとめている。

Author: kabusys 開発チーム

注: 上記 CHANGELOG はコードベースの内容から推測してまとめたものであり、実際のリリースノートや公開履歴と差異がある場合があります。必要であれば、各機能ごとにより詳細な変更点や既知の制限事項を追加します。