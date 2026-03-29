Keep a Changelog 準拠の CHANGELOG.md（日本語）
※以下はリポジトリ内のソースコードから推測して作成した変更履歴です。

All notable changes to this project will be documented in this file.
The format is based on Keep a Changelog and this project adheres to Semantic Versioning.

Unreleased
---------
（なし）

0.1.0 - 2026-03-29
-----------------
Added
- パッケージ初期公開: kabusys v0.1.0
  - パッケージエントリポイント: src/kabusys/__init__.py（__version__ = "0.1.0"）。
- 環境設定・自動 .env ローダー（src/kabusys/config.py）
  - プロジェクトルートを .git または pyproject.toml を基準に探索して .env/.env.local を自動読み込み。
  - .env パーサーを実装（"export KEY=val" 形式、シングル/ダブルクォート、エスケープ、インラインコメント処理に対応）。
  - 読み込み順序: OS 環境変数 > .env.local（上書き） > .env（未設定時にセット）、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 保護された OS 環境変数を上書きしない機能（protected set を使用）。
  - Settings クラスにアプリケーション設定を集約（J-Quants、kabu API、Slack、DB パス、環境・ログレベル検証など）。
  - KABUSYS_ENV と LOG_LEVEL の許容値チェックを実装。is_live/is_paper/is_dev のユーティリティも提供。

- AI モジュール（src/kabusys/ai）
  - ニュース NLP スコアリング（src/kabusys/ai/news_nlp.py）
    - 指定日の前日 15:00 JST ～ 当日 08:30 JST を対象ウィンドウとする時間窓計算（UTC 換算）を実装。
    - raw_news と news_symbols を銘柄単位で集約し、1 銘柄あたり最大記事数・文字数でトリム。
    - OpenAI（gpt-4o-mini）へのバッチ送信を実装（1 API 呼び出しで最大 20 銘柄）。
    - JSON Mode を想定したレスポンス検証ロジックを実装（余計な前後テキストの補正，results リスト・型検査・未知コード無視・数値検証）。
    - API エラー（429/ネットワーク/タイムアウト/5xx）に対する指数バックオフリトライ、非リトライエラーはスキップするフェイルセーフ設計。
    - スコアは ±1.0 にクリップし、取得できた銘柄のみ ai_scores テーブルへ DELETE→INSERT の冪等書き込み（DuckDB executemany の空リスト問題に対処）。
    - テスト容易性のため OpenAI 呼び出し関数を差し替え可能（内部関数を patch できる設計）。
  - 市場レジーム判定（src/kabusys/ai/regime_detector.py）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を算出。
    - prices_daily からの MA200 計算は target_date 未満のデータのみを使用し、ルックアヘッドバイアスを回避。
    - マクロ記事はキーワードフィルタで抽出（デフォルト複数キーワードを設定）。
    - OpenAI（gpt-4o-mini）呼び出しは個別実装で、リトライ・バックオフ・パース失敗時は macro_sentiment=0.0 にフォールバックする堅牢な設計。
    - 最終結果を market_regime テーブルにトランザクション（BEGIN/DELETE/INSERT/COMMIT）で冪等書き込みし、例外時は ROLLBACK を試行。

- データプラットフォーム（src/kabusys/data）
  - カレンダー管理（src/kabusys/data/calendar_management.py）
    - JPX カレンダー用ユーティリティ群を提供：is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day。
    - market_calendar が未登録のときは曜日ベースのフォールバック（週末を非営業日扱い）を行う一貫したフェールバック設計。
    - カレンダー更新バッチ（calendar_update_job）を実装し、J-Quants クライアント経由で差分取得 → 保存（ON CONFLICT 相当）・バックフィル・健全性チェックを実施。
    - 検索範囲の上限（_MAX_SEARCH_DAYS）やバックフィル日数等の安全パラメータを導入。
  - ETL パイプライン（src/kabusys/data/pipeline.py / etl.py）
    - ETLResult データクラスを公開（取得件数・保存件数・品質問題・エラー概要などを集約）。
    - 差分取得ロジック、backfill、品質チェック（quality モジュール）を想定したインターフェース実装。
    - DuckDB のテーブル存在確認、最大日付取得ユーティリティなどを実装。

- リサーチ（src/kabusys/research）
  - ファクター計算（src/kabusys/research/factor_research.py）
    - Momentum（1M/3M/6M リターン、200 日 MA 乖離）、Volatility（20 日 ATR、相対 ATR、平均売買代金、出来高比率）、Value（PER、ROE）を DuckDB の prices_daily/raw_financials を参照して計算。
    - データ不足時は None を返す堅牢な実装。
  - 特徴量探索（src/kabusys/research/feature_exploration.py）
    - 将来リターン計算（任意ホライズン、デフォルト [1,5,21]）を実装。複数ホライズンをまとめて 1 クエリで取得。
    - IC（Spearman の ρ）計算、rank（平均ランク・同順位の平均化）実装。
    - factor_summary により各カラムの基本統計量（count/mean/std/min/max/median）を算出。
  - 研究向けユーティリティをパッケージ公開（__all__ に主要関数をエクスポート）。

Changed
- 設計方針・実装上の注意点を各モジュールに明記
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を参照しない（target_date 引数駆動）。
  - OpenAI 呼び出しは各モジュールで独立実装し、モジュール間でプライベート関数を共有しない（テスト容易性と結合度低減のため）。

Fixed
- API 呼び出し失敗時のフォールバック動作を明確化
  - news_nlp/regime_detector: リトライ失敗・パース失敗時は例外を投げず対象スコアをスキップまたは 0.0 にフォールバックすることで ETL・バッチ処理の安定性を確保。

Notes / Implementation details
- DuckDB を主要なローカル DB として使用。executemany の空リストバインドに注意した実装（DuckDB 0.10 に対処）。
- OpenAI のレスポンスは JSON mode を前提にするが、余計なテキスト混入への復元ロジックを組み込んでいる。
- テスト容易性のため、内部の OpenAI 呼び出し関数へパッチを当てられるように設計されている（unittest.mock.patch が可能）。
- 外部 API クライアント（J-Quants / OpenAI / kabu）への具体的呼び出し部分はクライアントモジュール経由で抽象化されることを想定。

Deprecated
- なし

Removed
- なし

Security
- なし

---- 
補足:
- ここに記載した内容はソースコード（docstrings, 関数、定数、ログメッセージ）から推測したもので、実際のリリースノートや変更履歴は開発者の意図・コミット履歴に基づいて調整してください。