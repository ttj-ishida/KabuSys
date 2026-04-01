KEEP A CHANGELOG
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
なお、本 CHANGELOG は提示されたコードベースから推測して作成しています（実装/振る舞いの意図・既知問題を含む）。

1.0.0 より前の初回公開として 0.1.0 を作成しています。

## [0.1.0] - 2026-04-01

Added
- パッケージ基盤
  - パッケージ初期バージョンを定義（kabusys.__version__ = "0.1.0"）。
  - 主要サブパッケージを __all__ で公開: data, strategy, execution, monitoring。

- 環境設定 / config
  - Settings クラスを追加し、環境変数経由でアプリケーション設定を取得するプロパティを提供。
    - J-Quants / kabu ステーション / Slack / DB パス / 監視閾値 / 実行環境（development/paper_trading/live）など。
  - .env 自動読み込み機能を実装（プロジェクトルートの判定は .git または pyproject.toml を探索）。
    - 読み込み順序: OS 環境変数 > .env.local > .env（.env.local は上書き、OS 環境変数は保護）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能。
  - .env パースにて export プレフィックスやクォート、インラインコメント、エスケープを考慮した実装。

- AI（自然言語処理）機能
  - kabusys.ai.news_nlp
    - raw_news / news_symbols を集約して銘柄ごとにニュースを結合し、OpenAI（gpt-4o-mini / JSON mode）でセンチメントを算出。
    - バッチ処理（最大 20 銘柄／チャンク）、記事数・文字数上限、JSON レスポンスの厳密検証、スコアの ±1.0 クリップ。
    - API 呼び出しの再試行（RateLimit/ネットワーク/5xx 対応）と指数バックオフ。
    - 結果を ai_scores テーブルへ冪等的に保存（DELETE → INSERT、部分失敗時に既存データを保護）。
    - calc_news_window ユーティリティ（JST の前日 15:00 ～ 当日 08:30 を UTC で扱う窓の算出）。
  - kabusys.ai.regime_detector
    - ETF (1321) の 200 日移動平均乖離（重み 70%）と、ニュース由来のマクロセンチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - DuckDB からのデータ取得、OpenAI（gpt-4o-mini）呼び出し、リトライ/フォールバック、結果を market_regime テーブルへ冪等書込み。
    - API エラーやパース失敗時には macro_sentiment を 0.0 とするフェイルセーフ設計。
    - ルックアヘッドバイアス対策として date 比較は厳格に target_date 未満や排他区間で実装。

- データ / DataPlatform
  - kabusys.data.calendar_management
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants から差分取得して market_calendar を冪等保存。
    - 営業日判定ユーティリティ群を実装: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - calendar が未取得の場合は曜日（平日）ベースのフォールバック、DB の部分登録時にも一貫した動作を確保。
    - 探索上限やバックフィル、健全性チェック（未来日付の異常検知）等を実装。
  - kabusys.data.pipeline / etl
    - ETLResult データクラスを追加（ETL 実行の集約結果・品質問題・エラーメッセージ等を保持）。
    - pipeline モジュールを介した ETL 設計（差分取得、冪等保存、品質チェックの設計方針を実装予定あるいは部分実装）。
    - kabusys.data.etl は ETLResult を公開エクスポート。

- リサーチ機能（研究用ユーティリティ）
  - kabusys.research.factor_research
    - モメンタム（1M/3M/6M）、200 日 MA 乖離、ボラティリティ（20 日 ATR）、流動性指標（20 日平均売買代金・出来高比）、バリュー（PER/ROE）を DuckDB 上で計算する関数を提供。
    - データ不足時の None 処理や、DuckDB 上で SQL ウィンドウ関数を活用した実装。
  - kabusys.research.feature_exploration
    - 将来リターン計算（calc_forward_returns）、IC（情報係数）計算（calc_ic）、rank（同順位は平均ランク）、factor_summary（count/mean/std/min/max/median）を実装。
    - 外部ライブラリに依存しない実装（標準ライブラリ + duckdb）、ルックアヘッド回避の方針を遵守。

Changed
- 全体設計上の決定（明記）
  - ルックアヘッドバイアス対策として各種モジュールは内部で datetime.today()/date.today() を直接参照しない（target_date を明示的に渡す設計）。
  - OpenAI 呼び出しは JSON mode を利用し、レスポンスの堅牢なバリデーションを行うことで LLM 出力のゆらぎに対処。

Fixed
- （初期リリースのため修正履歴はなし。ただし既知の不完全・要対応点あり。下記参照）

Security
- 環境変数の自動読み込みは OS 環境変数を保護する仕組み（protected set）を用いており、.env の一部による意図しない上書きを防止。

Dependencies
- 実行に必要な外部ライブラリ（コードからの推測）:
  - duckdb
  - openai
  - 標準ライブラリ: datetime, json, logging, os, time, math 等

Known issues / Notes (注意)
- src/kabusys/data/pipeline.py の末尾が提示コードで途中（"return date.fro" のような断片）で終わっており、実行時に構文エラー／未定義参照になる可能性が高いです。パイプライン周りの実装・ファイル終端を確認して修正してください。
- テストフックは一部用意（_call_openai_api を patch 可能等）されているものの、ユニットテストや統合テストの整備状況はコードからは不明です。外部 API 呼び出し（OpenAI / J-Quants）は mocking が必須。
- OpenAI API のレスポンス検証は多重防御を行っているが、LLM 出力仕様変更により追加のロバスト化が必要になる場合があります。
- DuckDB の executemany 空リスト制約に対する対処（空チェック）が実装されているが、DuckDB バージョン差異による挙動確認を推奨します。
- この CHANGELOG はコードからの推測に基づき作成しています。実際のリリースノートには実装者による動作確認・追記を行ってください。

---

今後の推奨タスク（開発ロードマップ候補）
- pipeline._get_max_date の残処理とファイル末尾の整備（上記の Known issue を修正）。
- テストケース（DuckDB を用いた integration tests / OpenAI 呼び出しのモックを含む）の作成。
- ドキュメント補完（各関数の公開 API を README / docs に整理）。
- エラーメトリクス / モニタリング（SLACK 通知等）の統合確認。

以上。必要であればこの CHANGELOG を英語版に変換したり、Unreleased セクションを追加したり、より詳細なファイル単位の差分ログを生成します。どの形式/粒度がよいか教えてください。