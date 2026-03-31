Changelog
=========

すべての注目すべき変更点をここに記録します。  
このファイルは Keep a Changelog のフォーマットに準拠しています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

Unreleased
----------

（現在のところ未リリースの変更はありません）

[0.1.0] - 2026-03-31
-------------------

Added
- 初期リリース: KabuSys — 日本株自動売買／リサーチプラットフォームの基盤実装を追加。
  - パッケージ構成:
    - kabusys.config: 環境変数／.env 管理（自動ロード機能、.env/.env.local の優先度、OS 環境変数保護、KABUSYS_DISABLE_AUTO_ENV_LOAD フラグ）。
    - kabusys.ai: AI を用いたニュース NLP と市場レジーム判定。
      - news_nlp.score_news:
        - raw_news と news_symbols を集約して銘柄ごとのニュースを LLM（gpt-4o-mini）に送信し、銘柄単位のセンチメント（ai_scores テーブル）を書き込む。
        - バッチ処理（最大 20 銘柄/チャンク）、記事数・文字数トリム、JSON Mode を利用したレスポンスバリデーション、429/ネットワーク/5xx に対する指数バックオフリトライ、フェイルセーフで部分失敗を許容。
        - calc_news_window ユーティリティで JST ベースのニュース収集ウィンドウを計算。
      - regime_detector.score_regime:
        - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等的に書き込み。
        - OpenAI 呼び出しのリトライ/バックオフ、API 失敗時の安全フェイル（macro_sentiment = 0.0）。
        - Look-ahead バイアス防止の設計（date.today() を直接参照しない、DB クエリは target_date 未満の排他条件を使用）。
    - kabusys.data: データ関連ユーティリティ
      - calendar_management:
        - JPX カレンダー管理（market_calendar）と営業日判定ユーティリティ（is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day）。
        - DB データを優先、未登録日は曜日ベースでフォールバック。最大探索日数制限、バックフィル、健全性チェックなどを実装。
        - calendar_update_job: J-Quants から差分取得して冪等保存。バックフィルや異常検知を実装。
      - pipeline / etl:
        - ETLResult データクラスの公開（取得数・保存数・品質問題・エラー等の集計）。
        - ETL の方針（差分更新、バックフィル、品質チェックを継続的に収集し呼び出し元へ通知）。
    - kabusys.research:
      - factor_research:
        - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離を計算（営業日ベース）。
        - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比を計算。
        - calc_value: raw_financials から最新の EPS/ROE を取得して PER/ROE を計算。
        - 各関数は DuckDB を使用し prices_daily / raw_financials のみ参照、外部 API に依存しない。
      - feature_exploration:
        - calc_forward_returns: 任意ホライズンの将来リターンを一度のクエリで取得（デフォルト [1,5,21]）。
        - calc_ic: ファクター値と将来リターンのスピアマン ランク相関（IC）を計算。データ不足時には None を返す。
        - rank / factor_summary: ランク化（同順位は平均ランク）と統計サマリー（count/mean/std/min/max/median）。
    - 共通:
      - DuckDB を主要なオンディスク分析 DB として採用（テーブル操作・スキャンは SQL で実装）。
      - OpenAI SDK 経由で gpt-4o-mini を使用、JSON mode（response_format）を活用してレスポンス構造を期待。

Behavior / Design decisions
- ルックアヘッドバイアス防止:
  - AI/リサーチ関数は内部で datetime.today()／date.today() を直接参照しない。すべて target_date を明示的に受け取る設計。
  - DB クエリでは target_date 未満／排他条件を用いることで将来データ参照を防止。
- フェイルセーフ:
  - OpenAI API 呼び出しで失敗した場合は例外を投げずに安全なデフォルト（例: macro_sentiment=0.0）にフォールバックする箇所がある。
  - 部分失敗が発生しても既存データを不必要に削除しない（ai_scores / market_regime 書き込み時は書き込み対象コードを限定）。
- 冪等性:
  - DB への書き込みは冪等性を考慮（BEGIN / DELETE / INSERT / COMMIT 等）。ROLLBACK 処理とログ出力を実装。
- API 呼び出し:
  - 429、ネットワーク断、タイムアウト、5xx に対して指数バックオフでリトライ。非 5xx APIError では即時スキップ。
- .env パーサ:
  - export 形式やクォート／エスケープ、インラインコメント処理などをサポートする堅牢な .env パーサを実装。
  - .env.local は .env 上から上書き可能。ただし OS 環境変数は protected として上書きされない。

Fixed
- （該当なし：初期リリース）

Security
- 機密情報（OpenAI API キー等）は環境変数経由で取得。settings で未設定時は明示的に ValueError を発生させることで運用ミスを検出。

Notes
- 現在のバージョンは 0.1.0。今後は以下のような改善が予定:
  - ai スコアの品質向上（プロンプト改善・アンサンブル手法検討）
  - データ品質チェック機能の拡充と自動修復ルール
  - テストカバレッジ拡充（特に API エラー時の挙動、DuckDB の edge-case）
  - OpenAI SDK のバージョン差異に対応するラッパーの追加

References
- プロジェクトの主要設計文書（StrategyModel.md / DataPlatform.md）に沿って実装されています（ソース内 docstring に要約あり）。