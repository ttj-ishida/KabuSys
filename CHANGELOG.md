Keep a Changelog
=================

すべての注目すべき変更はこのファイルで管理します。
このプロジェクトはセマンティックバージョニングに従います。

0.1.0 - 2026-03-31
------------------

Added
- パッケージ初期リリースとして以下の主要機能を追加しました。
  - core
    - パッケージエントリポイントを追加（kabusys.__version__ = 0.1.0、__all__ に主要サブパッケージを公開）。
  - 設定管理（kabusys.config）
    - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを導入。
      - プロジェクトルートは __file__ 起点で .git または pyproject.toml を探索して特定（CWD 非依存）。
      - 読み込み順は OS 環境変数 > .env.local > .env（.env.local は上書き）。
      - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
    - .env のパースを堅牢化（export プレフィックス対応、クォート内のエスケープ、インラインコメントルール、無効行除外など）。
    - 必須環境変数取得ユーティリティ _require を提供（未設定時は ValueError）。
    - Settings クラスを公開し、J-Quants / kabu / Slack / DB パス / 環境やログレベル等のプロパティを提供。
      - env / log_level の検証（許容値セット）を実装。
      - is_live / is_paper / is_dev 補助プロパティを追加。
  - AI（kabusys.ai）
    - ニュース NLP（kabusys.ai.news_nlp）
      - raw_news / news_symbols を集約して銘柄ごとのニュースを LLM（gpt-4o-mini）でセンチメント評価し、ai_scores テーブルへ書き込む処理を実装。
      - バッチ処理（1 API 呼び出しで最大 20 銘柄）・記事トリム（最大記事数・最大文字数）・チャンク単位の再試行（429/ネットワーク/タイムアウト/5xx）を実装。
      - レスポンスの厳密な JSON モード（"results": [{code, score}, ...]）の検証と冗長テキスト復元処理を実装。
      - スコアは ±1.0 にクリップ。部分失敗時に他銘柄の既存スコアを保持するため、書き込みは対象コードのみ DELETE→INSERT の冪等操作を実行。
      - テスト容易性のため OpenAI 呼び出しを差し替え可能（_call_openai_api を patch）。
      - DuckDB 0.10 の executemany の空リスト制約に対応（空の場合は実行しない）。
    - 市場レジーム判定（kabusys.ai.regime_detector）
      - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して市場レジーム（bull/neutral/bear）を日次判定する処理を実装。
      - prices_daily / raw_news を参照し、計算結果を market_regime テーブルへ冪等書き込み。
      - OpenAI 呼び出しは専用実装でテスト用差し替え可能。API エラー時は macro_sentiment=0.0 のフェイルセーフを採用。
  - Data（kabusys.data）
    - カレンダー管理（kabusys.data.calendar_management）
      - JPX カレンダー（market_calendar）を扱うユーティリティと夜間バッチ更新ジョブ calendar_update_job を実装。
      - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days 等の営業日判定 API を提供。
      - DB にカレンダーがない場合は曜日ベースのフォールバック（平日＝営業日）を一貫して使用。
      - next/prev/get で DB 登録値を優先し、未登録日はフォールバックで補完する設計。
      - 最大探索日数の制限やバックフィル、健全性チェックを実装。
    - ETL（kabusys.data.pipeline / kabusys.data.etl）
      - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラーの集約）。
      - 差分更新 / バックフィル / 品質チェックの設計に基づく ETL パイプラインの基盤を実装（jquants_client 経由での取得・保存、品質チェックの集計など）。
      - DuckDB からの最大日付取得やテーブル存在チェック等のユーティリティを実装。
  - Research（kabusys.research）
    - factor_research
      - Momentum / Volatility / Value 等のファクター計算関数を追加（calc_momentum / calc_volatility / calc_value）。
      - prices_daily / raw_financials のみを参照し、結果を (date, code) ベースの dict リストで返す設計。
    - feature_exploration
      - 将来リターン計算 calc_forward_returns（任意ホライズン）、IC 計算 calc_ic（Spearman ランク相関）、rank、factor_summary（count/mean/std/min/max/median）を実装。
    - data.stats からの zscore_normalize を re-export。
  - 研究／テスト配慮
    - datetime.today()/date.today() によるルックアヘッドバイアスを避ける設計（すべての主要処理は target_date 引数を受ける）。
    - OpenAI 呼び出しの差し替えポイントを用意してユニットテストを容易に。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- OpenAI API キーの解決は引数優先 → 環境変数 OPENAI_API_KEY。未設定時は明確な ValueError を発生させることで安全に失敗。

Notes / Implementation details
- DuckDB 互換性: executemany に空リストを渡すと問題になるバージョンを考慮して、安全に実行するガードを追加（空時はスキップ）。
- LLM 呼び出しのリトライ戦略は指数バックオフを使用し、5xx / レート制限 / ネットワーク断 / タイムアウトをリトライ対象とする設計（最大リトライ回数とベース待機時間は定数化）。
- レスポンスパース失敗や API 異常は例外で上位を壊さずフェイルセーフ動作（スコア=0.0 または当該チャンクスキップ）を行い、ログで警告を残す。
- DB 書き込みは可能な限り冪等に設計（DELETE→INSERT、ON CONFLICT 相当を意識）し、部分失敗時に既存データを不必要に消さないようにしている。
- モジュール間の結合を避けるため、各 AI モジュールは内部で独立した _call_openai_api 実装を持ち、テストで個別に patch できるようにしている。

今後の予定（TODO / Ideas）
- PBR や配当利回りなどバリュー系指標の追加実装。
- pipeline の上位 orchestration（ジョブスケジューラ統合や監視）の追加。
- モデル候補・プロンプト最適化、LLM 応答フォールバック改善。

---- 

（この CHANGELOG はコードの実装内容および埋め込まれた docstring / 設計ノートから推測して作成しています。実際の変更履歴が別にある場合はそちらを優先してください。）