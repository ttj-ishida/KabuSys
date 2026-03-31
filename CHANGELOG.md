Changelog
=========
すべての重要な変更点を記録します。本ファイルは Keep a Changelog のフォーマットに準拠します。

フォーマット:
- 変更点はカテゴリ別（Added, Changed, Fixed, Deprecated, Removed, Security）に記載しています。
- 日付はリリース日を示します（YYYY-MM-DD）。

Unreleased
----------
（現在なし）

0.1.0 - 2026-03-31
-----------------

Added
- 初期リリース。本パッケージは日本株の自動売買およびリサーチ向け基盤機能を提供します。主な追加機能:
  - パッケージ公開情報
    - バージョン: 0.1.0（src/kabusys/__init__.py に __version__ を定義）。
    - パッケージ外部公開モジュール: data, strategy, execution, monitoring を __all__ で指定。

  - 環境設定周り（src/kabusys/config.py）
    - .env ファイルまたは OS 環境変数からの自動読み込み機能を実装。プロジェクトルートは .git または pyproject.toml を基準に探索し、CWD に依存しない方式を採用。
    - .env/.env.local の読み込み優先度管理（OS 環境変数 > .env.local > .env）と、既存の OS 環境変数を保護する protected 機能を実装。
    - .env パースの強化:
      - export PREFIX=val 形式に対応
      - シングル/ダブルクォート内のバックスラッシュエスケープ処理
      - クォートなし行のインラインコメント処理（'#' 前にスペース/タブがある場合のみコメント扱い）
      - 無効行のスキップ
    - 自動ロード無効化フラグ KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート（テスト用）。
    - Settings クラスを提供し、J-Quants、kabuステーション、Slack、DBパス、監視設定、システム設定（KABUSYS_ENV, LOG_LEVEL）などのプロパティを型付きで取得。必須環境変数未設定時は ValueError を発生させるバリデーションを実装。

  - AI モジュール（src/kabusys/ai/）
    - ニュースNLP（src/kabusys/ai/news_nlp.py）
      - raw_news と news_symbols を元に銘柄ごとのニューステキストを集約し、OpenAI（gpt-4o-mini）に対してバッチで JSON モードによりセンチメント評価を実行。
      - タイムウィンドウの算出 calc_news_window を提供（JST 基準、前日 15:00 ～ 当日 08:30 を対象、UTC 変換済み）。
      - バッチ処理（最大 20 銘柄/回）、1 銘柄あたりの記事・文字数上限（_MAX_ARTICLES_PER_STOCK/_MAX_CHARS_PER_STOCK）でトリム。
      - API 呼び出しのエラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフとリトライ実装。非リトライ対象エラーはスキップして継続（フェイルセーフ）。
      - レスポンスの堅牢なバリデーション（JSON 抽出、results リスト、code と score の型チェック、未知コードは無視、数値の有限性チェック）。
      - スコアは ±1.0 にクリップし、ai_scores テーブルへトランザクション（DELETE → INSERT）で冪等的に書き込み。DuckDB executemany の空リスト制約を回避するガードを実装。
      - テスト容易性のため _call_openai_api の差し替え（patch）を想定。
    - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
      - ETF 1321（日経225連動型）について 200 日移動平均乖離（重み 70%）と、ニュース NLP によるマクロセンチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）判定。
      - prices_daily からの MA 計算は target_date 未満のデータのみを使用し、ルックアヘッドを防止。
      - raw_news からマクロキーワードでフィルタして記事タイトルを抽出し、LLM に投げて macro_sentiment を算出。記事なし・API 失敗時は macro_sentiment=0.0 にフォールバック。
      - OpenAI 呼び出しに対するリトライ/エラー処理、JSON パース失敗時のフォールバックを実装。
      - 結果は market_regime テーブルへ冪等的に書き込む（BEGIN / DELETE / INSERT / COMMIT with ROLLBACK on error）。
      - 重要: 外部に公開している news_nlp の _call_openai_api と意図的に別実装にして、モジュール間結合を避ける設計。

  - データ基盤（src/kabusys/data/）
    - マーケットカレンダー管理（src/kabusys/data/calendar_management.py）
      - JPX カレンダーの夜間差分更新ジョブ calendar_update_job（J-Quants から差分取得→保存）を実装。バックフィル、先読み、健全性チェック（未来日付の異常検出）を考慮。
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を実装。market_calendar データがない場合は曜日ベース（平日）でフォールバックする一貫した動作。
      - 検索上限 _MAX_SEARCH_DAYS を設け、無限ループ防止。
    - ETL パイプライン基盤（src/kabusys/data/pipeline.py, src/kabusys/data/etl.py）
      - ETLResult データクラスを定義し、ETL の取得数・保存数・品質問題・エラー概要を集約できるように実装。
      - 差分更新、backfill、品質チェック（quality モジュール想定）を行う設計を採用（実装方針・定数を含む）。
      - jquants_client を通じた idempotent 保存（ON CONFLICT DO UPDATE）を想定。
      - etl.py は pipeline.ETLResult を再エクスポート。

  - リサーチ / ファクター（src/kabusys/research/）
    - factor_research.py
      - Momentum, Volatility, Value 等のファクター計算関数を実装:
        - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日移動平均乖離）を計算。データ不足時は None を返す設計。
        - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
        - calc_value: raw_financials から最新の財務データを取得し PER / ROE を計算（EPS が 0/NULL の場合は None）。
      - DuckDB のウィンドウ関数を多用し、prices_daily/raw_financials テーブルのみ参照する安全設計。
    - feature_exploration.py
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括で取得する SQL 実装。horizons のバリデーションを実装。
      - calc_ic: スピアマンランク相関（IC）を実装。3 レコード未満は None を返す。
      - rank: 同順位は平均ランクとする実装（浮動小数丸めを行い ties 判定を安定化）。
      - factor_summary: count/mean/std/min/max/median を返す統計サマリ。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Deprecated
- （初回リリースのため該当なし）

Removed
- （初回リリースのため該当なし）

Security
- OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY から読み込む。設定漏れ時は ValueError を送出して明示的に失敗する設計。

Notes / Implementation choices（実装上の注記）
- ルックアヘッドバイアス防止:
  - 全ての時刻・日付ロジックは内部で date / datetime の引数を明示的に受け取り、datetime.today() / date.today() を参照しない実装方針を採用（分析・トレーニングの再現性確保）。
- DuckDB を主要なデータストアとして前提とし、SQL + Python のハイブリッド実装で高性能に集計処理を実施。
- OpenAI 呼び出し周りは JSON Mode を利用し、レスポンスパースの堅牢化（前後余計テキストの抽出等）を行っている。
- テスト容易性:
  - AI モジュール内の _call_openai_api を patch してモック化できるように設計している（unit test 用フック）。
- 部分失敗に配慮した DB 書き込み:
  - ai_scores 等の書き込みはターゲットの code を限定して DELETE → INSERT することで、部分失敗時の既存データ保護を行う。

Known limitations / TODO
- strategy / execution / monitoring の実装（パッケージに名前はあるが、本コードベース内に詳細実装が含まれていない部分がある可能性があります）。
- jquants_client, quality モジュール等は外部クライアント／補助モジュールとして想定されており、実際の環境での接続確認が必要です。
- 一部ファイル（pipeline の末尾など）でコード断片が途切れているため、ETL の完全実装・例外ハンドリング全体の統合テストが必要。

ライセンス、貢献、連絡先についてはプロジェクトルートのドキュメントを参照してください。