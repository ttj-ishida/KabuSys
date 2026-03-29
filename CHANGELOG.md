CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/1.0.0/).
Versions are based on semantic versioning.

Unreleased
----------

- （なし）

0.1.0 - 2026-03-29
------------------

初回リリース。以下の主要機能・設計方針・注意点を実装しました。

Added
- パッケージ基礎
  - パッケージ公開情報を追加（kabusys.__version__ = "0.1.0"）。
  - パッケージの公開 API を __all__ で定義（data, strategy, execution, monitoring）。

- 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートを .git / pyproject.toml から探索して決定）。
  - .env 行パーサの強化:
    - コメント行・空行の無視、export プレフィックスの対応。
    - シングル/ダブルクォート内のバックスラッシュエスケープ処理に対応。
    - クォートなし時のインラインコメント判定（直前が空白・タブの場合のみコメントと見なす）。
  - 読み込み順序: OS 環境変数 > .env.local (override) > .env（override フラグと protected set を使用）。
  - 自動ロードの無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、環境変数から以下を取得するプロパティを実装:
    - J-Quants / kabuステーション / Slack / データベースパス（DuckDB / SQLite） / 環境（development/paper_trading/live） / ログレベル
  - 必須環境変数未設定時は ValueError を発生させる _require 実装。

- AI モジュール (kabusys.ai)
  - ニュース N/L P スコアリング (news_nlp.score_news)
    - raw_news / news_symbols を集約して銘柄ごとに記事を連結し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメントを取得。
    - バッチ処理（デフォルト20銘柄）、各銘柄の記事数/文字数トリム（最大記事数・最大文字数）によるトークン制御。
    - JSON Mode を使ったレスポンス検証・復元ロジック（前後の余計なテキストが入るケースのための {} 抽出）。
    - レスポンス検証: results フィールドの存在、各要素の code/score 型検査、未知コードの無視、スコアの数値性確認。
    - スコアを ±1.0 にクリップして ai_scores テーブルへ冪等書き込み（DELETE → INSERT）。部分失敗時に既存スコアを消さない設計。
    - リトライ戦略: 429 / ネットワーク断 / タイムアウト / 5xx を指数バックオフで再試行。非再試行エラーはスキップして継続（フェイルセーフ）。
    - テスト容易性のため _call_openai_api をモック可能に設計。
    - タイムウィンドウ: 前日15:00 JST 〜 当日08:30 JST を UTC に変換して比較（ルックアヘッド防止）。

  - 市場レジーム判定 (regime_detector.score_regime)
    - ETF 1321（日経225連動型）の 200日移動平均乖離（重み70%）と、ニュース由来のマクロセンチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定。
    - マクロセンチメントは news_nlp 側のタイトル集約を用い、OpenAI を呼び出して JSON レスポンスをパース。
    - LLM 呼び出しはリトライ（429/接続/タイムアウト/5xx のハンドリング）、最終的に失敗したら macro_sentiment=0.0 にフォールバック。
    - レジーム判定のスコア合成と閾値処理、market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - datetime.today()/date.today() に依存せず、target_date 引数ベースで処理を行うことでルックアヘッドバイアスを排除。

- Data モジュール (kabusys.data)
  - カレンダー管理 (calendar_management)
    - JPX カレンダー管理ロジックを実装（market_calendar テーブルを元に営業日判定）。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days を提供。
    - DB にデータがある場合は DB 値を優先、未登録日は曜日ベースのフォールバック（週末非営業）で一貫して処理。
    - 夜間バッチ calendar_update_job を実装（J-Quants から差分取得して保存、バックフィルと健全性チェック付き）。
    - 最大探索範囲やバックフィル日数等の保護ロジックを搭載して無限ループや過剰取得を防止。

  - ETL パイプライン (pipeline, etl)
    - ETLResult データクラスを公開（ETL 実行結果の構造化: 取得数/保存数/品質問題/エラー等）。
    - 差分取得・バックフィル・品質チェック（quality モジュール連携）を行う方針を実装。
    - テーブル存在チェック、最大日付取得等の内部ユーティリティを提供。
    - ETL の設計上の方針（部分失敗時の保護、id_token 注入でのテスト容易性等）を明示。

- Research モジュール (kabusys.research)
  - ファクター計算 (factor_research)
    - calc_momentum: mom_1m/mom_3m/mom_6m と ma200_dev（200日 MA 乖離）の計算。
    - calc_volatility: 20日 ATR / ATR% / 20日平均売買代金 / 出来高比の計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（最新報告を target_date 以前から取得）。
    - SQL とウィンドウ関数を用いた高性能な実装。データ不足時の None 扱い。
  - 特徴量探索 (feature_exploration)
    - calc_forward_returns: 指定ホライズン（default [1,5,21]）の将来リターンを計算。horizons のバリデーションあり。
    - calc_ic: Spearman ランク相関（Information Coefficient）の実装（レコード結合と NaN/非有限値除外）。
    - rank: 同順位は平均ランク扱い（丸めで ties 検出の安定化）。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで算出（None 値除外）。

- その他
  - DuckDB を中心に DB 操作（クエリ・executemany を含む）を採用。
  - OpenAI SDK を使用（OpenAI クライアントの生成と chat.completions.create 呼び出しを一元化）。
  - ロギングを広範囲に採用し、失敗時のフォールバック・警告メッセージを充実させてデバッグを容易にする。

Changed
- N/A（初回リリースのため過去バージョンからの変更はなし）

Fixed
- N/A（初回リリース）

Security
- 環境変数の読み込みにおいて OS 環境変数を保護する protected セットを導入（.env の上書きを防ぐ）。自動ロードは明示的に無効化可能（KABUSYS_DISABLE_AUTO_ENV_LOAD）。

Notes / Implementation Decisions
- ルックアヘッドバイアス防止:
  - AI スコアリング・レジーム判定・ETL 等、すべて target_date ベースで処理し、date.today()/datetime.today() への依存を排除。
- フェイルセーフ原則:
  - 外部 API（OpenAI や J-Quants）呼び出しはリトライ・バックオフを行うが、最終的に失敗した場合は処理を続行可能なデフォルト値（例: macro_sentiment=0.0）でフォールバックする設計。
- テスト容易性:
  - OpenAI 呼び出しポイント（_call_openai_api）や環境自動ロードの無効化フラグを用意し、ユニットテスト時に外部依存を差し替え可能。
- DuckDB バージョン互換性対策:
  - executemany に空リストを渡さない等のワークアラウンドを実装。

Known limitations / TODO
- 一部ファクター（PBR・配当利回り）は未実装（calc_value の将来拡張対象）。
- ai_score / sentiment_score が現フェーズで同値となっている点は将来の分離が想定される。
- 監視 / 実行モジュール（strategy / execution / monitoring）はパッケージ定義はあるが、ここに含まれるコードは限定的（詳細実装は継続開発予定）。

もしこの CHANGELOG に追加してほしい詳細（例: 各関数の具体的な SQL や戻り値の例、リリース日付の調整、既知のバグ一覧など）があれば知らせてください。