Keep a Changelog
=================
すべての重要な変更はこのファイルに記録します。  
フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

[Unreleased]
------------

- （今後のリリースに向けた未反映の変更はここに記載します）

0.1.0 - 2026-03-28
-----------------

Added
- 初回リリース。パッケージ名: kabusys、バージョン: 0.1.0
  - src/kabusys/__init__.py
    - パッケージの公開 API を定義（data, strategy, execution, monitoring）。
  - src/kabusys/config.py
    - 環境変数／.env 管理モジュールを追加。
    - プロジェクトルート自動検出（.git または pyproject.toml）に基づく .env 自動読み込み機能を実装。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
    - .env パーサ実装（コメント、export プレフィックス、クォート＆エスケープ処理対応）。
    - Settings クラスで必須環境変数をラップ（J-Quants, kabu API, Slack, DB パス等）、入力検証（KABUSYS_ENV, LOG_LEVEL）。
  - src/kabusys/ai/news_nlp.py
    - ニュースに基づく銘柄ごとの NLP（LLM）センチメントスコアリングを実装。
    - タイムウィンドウ計算（JST ≒ 前日15:00〜当日08:30）と記事集約ロジックを実装。
    - OpenAI（gpt-4o-mini）とのバッチ呼び出し、レスポンス検証、スコアクリッピング、retry/backoff ロジックを追加。
    - DuckDB へ ai_scores の冪等置換（DELETE → INSERT）を実装。DuckDB 0.10 の executemany 空リスト制約を考慮。
    - テスト向けに _call_openai_api の差し替えが可能（unittest.mock.patch を想定）。
  - src/kabusys/ai/regime_detector.py
    - マクロセンチメント（LLM）と ETF(1321) の 200 日 MA 乖離を合成して市場レジーム（bull/neutral/bear）を日次判定する機能を追加。
    - ma200_ratio 計算、マクロ記事抽出、OpenAI 呼び出し（独立実装）、スコア合成、market_regime テーブルへの冪等書き込みを実装。
    - API エラー時のフェイルセーフ（macro_sentiment=0.0）、リトライ/バックオフを実装。
  - src/kabusys/research/*
    - ファクター計算・研究モジュール群を追加:
      - factor_research.calc_momentum / calc_volatility / calc_value（prices_daily / raw_financials に基づく）
      - feature_exploration.calc_forward_returns / calc_ic / factor_summary / rank
    - StrategyModel.md や Research 用設計に基づいた実装（外部 API に依存せず DuckDB 経由で完結）。
  - src/kabusys/data/*
    - calendar_management.py
      - JPX カレンダー管理と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）を実装。
      - market_calendar 未取得時の曜日ベースフォールバック、最大探索日数制限など堅牢性考慮。
    - pipeline.py / etl.py / __init__.py
      - ETL パイプラインインターフェース（ETLResult dataclass を公開）と差分取得／保存／品質チェックワークフローの基礎を追加。
      - jquants_client / quality モジュールと連携する設計（API 呼び出しの差分フェッチ、idempotent 保存、品質問題の集約）。
    - data エコシステムの設計・定数（バックフィル日数、ルックアヘッド値、スキャン範囲など）を定義。

Changed
- 初版リリースにつき、既存からの変更はなし（新規追加のみ）。

Fixed
- 初版リリースにつき、既存の不具合修正はなし。

Security
- 環境変数に関する扱いを明示:
  - 必須キー未設定時は ValueError を送出して起動時に明確に通知。
  - .env 自動読み込み時に OS 環境変数を保護するため protected セットを使用して上書き制御。
  - OpenAI API キーは引数で注入可能。テストでキーを外部化しやすい設計。

Notes / Known limitations / Design decisions
- LLM 呼び出しに関するフォールバック
  - API の一時的な失敗（429、接続断、タイムアウト、5xx）はリトライ＆エクスポネンシャルバックオフを実施。最終的に失敗した場合は該当処理をスキップし安全側の既定値（macro_sentiment=0.0、スコア取得失敗は無視）を採用して処理を継続する設計。
- ルックアヘッドバイアス対策
  - 全てのスコア／レジーム判定関数は内部で datetime.today() や date.today() を直接参照せず、target_date を明示的に受け取る仕様。
  - DB クエリでは target_date より前のデータのみを参照するなどルックアヘッドを防止する実装。
- DuckDB 互換性
  - executemany に空リストを渡せない（DuckDB 0.10 の挙動）点を考慮してコード内でチェックを行っている。
- テスト支援
  - OpenAI 呼び出し箇所（news_nlp._call_openai_api / regime_detector._call_openai_api）を patch して差し替えられるよう実装済み。
- モデルとバッチ設定（将来の変更要注意）
  - OpenAI モデルは現状 gpt-4o-mini、news_nlp はバッチサイズ 20、1銘柄当たり最大記事数 10、最大文字数 3000 等の定数で設定。
- 部分書き換えの保護
  - ai_scores / market_regime 等への書き込みは、影響対象のコードに限定して DELETE → INSERT を行うことで、部分失敗時に既存データを不必要に削除しないようにしている。

開発者向けメモ
- settings.env / log_level の検証で許容値外は ValueError を投げるため、CI などで環境変数の設定漏れを早期に検出可能。
- calendar_update_job は J-Quants API 呼び出しと保存処理を分離しており、fetch/save の例外はロギングして 0 を返す（安全に夜間バッチが失敗しても停止しない）。
- research モジュールは外部依存を持たず、分析作業で安全に呼べるように設計。

今後の予定（例）
- Strategy / execution / monitoring のコア実装の追加（発注ロジック、実行モジュール、監視＆アラート機能）
- テストカバレッジの拡充（特に OpenAI 呼び出しのモック、DuckDB 結合テスト）
- パフォーマンス最適化（大量銘柄処理時のクエリ最適化、並列化）

問い合わせ
- この CHANGELOG の内容について不明点があれば、リポジトリ内の該当ファイル（上記パス）を参照してください。