CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠しています。  
日付はリリース日（推定）です。コードベースの内容から実装・設計意図を推測して記載しています。

Unreleased
----------
- 既知の軽微な問題 / TODO
  - data.pipeline._get_max_date() の末尾が不完全（ソースに "return date.fro" の断片が残っている）。この関数の実装確認と単体テスト追加が必要です。
  - OpenAI モデルやリトライパラメータを外部設定化する改善（現在は定数で固定）。
  - テストカバレッジの強化：DuckDB 接続のモック、OpenAI 呼び出しのモックの整備を推奨。
  - ドキュメント: API エラー・ログの運用ポリシーやサンプル .env.example の明示化を推奨。

[0.1.0] - 2026-04-01
--------------------

Added
- パッケージ初期リリース（kabusys v0.1.0）
  - パッケージ公開用の __init__.py を追加し、バージョンと公開モジュールを定義。
- 環境変数/設定管理
  - .env/.env.local をプロジェクトルート（.git または pyproject.toml）基準で自動読み込みする機能を実装。
  - .env パーサーは export プレフィックス、クォート（シングル/ダブル）、エスケープ、インラインコメントを扱えるよう実装。
  - OS 環境変数を保護する protected 機能、override フラグをサポート。
  - 環境変数自動ロードを無効化する KABUSYS_DISABLE_AUTO_ENV_LOAD フラグを追加。
  - Settings クラスを提供し、必要な環境変数（JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等）をプロパティ経由で取得・検証。
  - KABUSYS_ENV と LOG_LEVEL の検証（許容値チェック）、ログレベルと環境判定用ユーティリティを追加。
  - パス系設定は Path 型で提供（duckdb/sqlite/pid ファイル等の既定値を設定）。
- データプラットフォーム周り（data）
  - calendar_management モジュールを追加
    - market_calendar を元にした営業日判定（is_trading_day）、SQ日判定、次/前営業日取得（next_trading_day / prev_trading_day）、期間内営業日取得（get_trading_days）を実装。
    - DB 登録値優先だが、未登録日は曜日ベース（週末除外）でフォールバックする一貫したロジックを採用。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得して冪等更新、バックフィルと健全性チェックを実施）。
  - ETL パイプライン基盤を実装（pipeline.py / etl.py）
    - ETLResult データクラスを提供し、ETL のフェッチ数・保存数・品質問題・エラーを集約して返却可能に。
    - 差分取得・バックフィル・品質チェックの設計方針を反映（J-Quants クライアント経由での保存は冪等性を想定）。
- AI（自然言語処理）機能（kabusys.ai）
  - news_nlp モジュールを実装
    - raw_news / news_symbols から対象ウィンドウ（前日15:00 JST〜当日08:30 JST）分の記事を銘柄ごとに集約。
    - 1チャンク最大20銘柄、1銘柄あたり最大10記事・最大3000文字にトリムして OpenAI（gpt-4o-mini）へ送信。
    - JSON Mode を利用しレスポンスを厳密にバリデート（results 配列、code/score）、スコアを ±1.0 にクリップ。
    - API 失敗（429/ネットワーク/タイムアウト/5xx）は指数バックオフでリトライし、最終的に失敗したチャンクはスキップして他銘柄を保護。
    - DuckDB への書き込みは部分失敗に備え、スコア取得済みコードのみ DELETE→INSERT の置換を行う（executemany の空リスト問題に対処）。
    - 単体テストのため _call_openai_api の差し替えを想定した設計。
  - regime_detector モジュールを実装
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロ経済ニュースの LLM センチメント（重み30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - prices_daily と raw_news を参照し、ma200_ratio を計算、マクロ記事抽出、OpenAI（gpt-4o-mini）で macro_sentiment を評価（記事なし時は呼び出しを行わず macro_sentiment=0.0）。
    - API 呼び出しはリトライ・エラー分類（5xx はリトライ、非5xx はフォールバック）を行い、フェイルセーフで macro_sentiment=0.0 を使用。
    - レジームスコアはクリップして閾値でラベル化し、market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
    - ルックアヘッドバイアス対策として datetime.today()/date.today() を内部で参照しない設計。
- リサーチ（research）機能
  - factor_research モジュールを実装
    - Momentum（1M/3M/6M リターン、200日MA乖離）、Volatility（20日 ATR 等）、Value（PER/ROE）等を DuckDB の prices_daily / raw_financials から計算する関数群（calc_momentum, calc_volatility, calc_value）。
    - 計算結果を (date, code) キーの辞書リストで返却。
    - データ不足時の None 取り扱いやスキャン範囲バッファの設計を反映。
  - feature_exploration モジュールを実装
    - 将来リターン計算（calc_forward_returns）、IC（calc_ic：Spearman の ρ をランクベースで算出）、ファクター統計サマリー（factor_summary）、ランク化ユーティリティ（rank）を提供。
    - pandas 等に依存せず、標準ライブラリ + DuckDB のみで実装。
- 共通実装・運用改善
  - DuckDB を主要な分析データストアとして利用する設計に一貫性を持たせる。
  - DB 書き込みは可能な限り冪等に（DELETE→INSERT、ON CONFLICT を想定）して部分失敗に強い設計。
  - LLM 呼び出しは JSON Mode を使いレスポンス整合性を重視、パース失敗時は安全にフォールバックする方針。
  - Lookahead バイアスを避けるため、target_date 引数ベースの計算を徹底。

Changed
- N/A（初回リリースのため過去バージョンからの変更はなし）

Fixed
- N/A（初回リリース）

Deprecated
- N/A

Removed
- N/A

Security
- 秘密情報（OpenAI API キー等）は環境変数から取得する設計。キーはコード中にハードコーディングしないことを前提。
- .env ファイル読み込みはデフォルトで自動実行されるが、テスト用途に無効化するための環境変数を提供。

Notes for maintainers / reviewers
- OpenAI クライアント呼び出しはモジュール内でラップされておりユニットテスト用に差し替え可能だが、実運用では API コスト・レート制限に注意してください。
- DuckDB への executemany に関する互換性（空リスト渡し不可）への対応が散見されるため、DuckDB のバージョン依存に注意しつつテストを行ってください。
- calendar_update_job 等は外部 API（J-Quants）依存のため、API レスポンスの変化に対する健全性チェックとログの運用が重要です。
- 今回のコード観察に基づく CHANGELOG です。実際のコミット履歴がある場合はコミット単位での詳細な変更履歴生成を推奨します。