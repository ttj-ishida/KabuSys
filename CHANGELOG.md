CHANGELOG
=========

すべての変更は Keep a Changelog の形式に準拠して記載しています。  
このファイルはコードベース（初期リリース v0.1.0）の実装内容をコードから推測してまとめたものです。

フォーマット:
- "Added" / "Changed" / "Fixed" / "Removed" / "Deprecated" / "Security" を使用しています。

Unreleased
----------

- なし

[0.1.0] - 2026-03-28
--------------------

Added
- パッケージ初期公開
  - kabusys パッケージの公開インターフェースを追加（__version__ = 0.1.0, __all__ に data, strategy, execution, monitoring を定義）。
- 設定・環境変数ロード機能（kabusys.config）
  - .env / .env.local の自動読み込み実装（プロジェクトルートを .git または pyproject.toml から探索）。  
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - .env パーサーは export 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱いなどに対応。
  - OS 環境変数を保護する protected 機能、.env.local による上書き（override）処理を実装。
  - Settings クラスで各種設定プロパティを提供（J-Quants, kabu API, Slack, DB パス, 環境判定, ログレベル 等）。
  - KABUSYS_ENV / LOG_LEVEL の値検証（許容値チェック）と便利な is_live/is_paper/is_dev プロパティ。
- AI 関連（kabusys.ai）
  - news_nlp モジュール: raw_news から銘柄ごとのニュースを集約し OpenAI（gpt-4o-mini JSON mode）でセンチメントを評価して ai_scores テーブルへ書き込み。  
    - タイムウィンドウ計算（JST基準→UTC変換）を提供（calc_news_window）。
    - チャンク処理（最大 20 銘柄/回）、記事トリム、スコアの ±1.0 クリップ、レスポンスバリデーション実装。
    - レート制限・ネットワーク断・タイムアウト・5xx に対する指数バックオフリトライを実装。
    - OpenAI 呼び出しの差し替え（テスト用に patch 可能）。
  - regime_detector モジュール: ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull/neutral/bear）を判定し market_regime テーブルへ冪等書き込み。  
    - マクロキーワードフィルタ／最大記事数の制限、API リトライ・フェイルセーフ（失敗時 macro_sentiment=0.0）を実装。
    - OpenAI 呼び出しは独立した内部実装でモジュール間結合を避ける設計。
- データ基盤（kabusys.data）
  - calendar_management モジュール: market_calendar を使った営業日判定、next/prev/get_trading_days、SQ日判定、夜間バッチ更新ジョブ（calendar_update_job）を実装。  
    - DB に情報がない場合は曜日ベースのフォールバック（週末を非営業日扱い）。
    - カレンダー更新でのバックフィル、健全性チェック（将来日付の異常検出）を実装。
  - pipeline / etl
    - ETLResult データクラスを実装し kabusys.data.etl から再エクスポート。
    - ETL モジュール内ユーティリティ群（テーブル存在チェック、最大日付取得、トレーディング日調整等）を提供。
  - jquants クライアントの呼び出しを想定した差分取得 / 保存フローの下地を実装（説明・設計に準拠）。
- リサーチ（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）を計算。
    - calc_volatility: 20 日 ATR、相対 ATR、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から EPS/ROE を取得して PER/ROE を計算（最新の財務レコードを target_date 以前で取得）。
    - DuckDB を用いた SQL ベースの実装、データ不足時は None を返す方針。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。
    - calc_ic: ファクターと将来リターンのスピアマン（ランク相関）を計算（有効レコード 3 件未満は None）。
    - rank: 同順位は平均ランクを与えるランク化ユーティリティ（丸め処理で ties を安定化）。
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出。
  - research パッケージの __init__ に主要関数を再エクスポート。
- DuckDB 互換性とトランザクション安全
  - ai スコア・market_regime など DB 書き込みは冪等化（DELETE → INSERT の明示的トランザクション）を採用。例外時に ROLLBACK を試みる処理と警告ログを実装。
  - DuckDB の executemany における空リスト禁止の扱い（空チェックしてから executemany）に対応。
- ロギング・設計方針
  - 重要な分岐で logger を多用して状態（info/debug/warning/exception）を出力。
  - すべての時間処理で datetime.today()/date.today() を直接参照しない、target_date を受け取ることでルックアヘッドバイアスを避ける設計。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 環境変数読み込みで OS 環境変数を保護する機構を導入（.env の上書き制御、protected set）。
- OpenAI API キーは引数注入または OPENAI_API_KEY 環境変数から取得する明示的な設計。未設定時は ValueError を発生させる。

Notes / 実装上の注記
- OpenAI 呼び出しは gpt-4o-mini を想定し JSON Mode（response_format={"type": "json_object"}) を利用。レスポンスパースが失敗するケースを考慮し、前後テキスト混入時の復元ロジックを含む。
- API エラーの判定ではステータスコードの有無を安全に扱う（getattr で status_code を参照）。
- テスト容易性のため、_call_openai_api を patch/差し替え可能にしている。news_nlp と regime_detector はそれぞれ独立実装でモジュール間でプライベート関数を共有しない設計。
- news の時間ウィンドウは JST ベースで定義（前日 15:00 JST ～ 当日 08:30 JST を UTC に変換して DB クエリに使用）。
- ファイル読み込みで Unicode を想定（encoding="utf-8"）し、読み込み失敗時は警告を出す実装。
- 一部の振る舞い（例: データ不足時の既定値や API 失敗時のフォールバック）は明確にフェイルセーフを優先する方針。

今後の TODO（コードから推測）
- strategy / execution / monitoring の具体実装の公開（現在はパッケージ公開のみ）。
- ETL 実行フローのエンドツーエンド実装および品質チェックルールの充実（quality モジュール連携）。
- テストカバレッジ拡充（外部 API 呼び出しのモック化、DuckDB ベースの統合テスト等）。
- .env パーサーの追加ケース（特殊文字や改行エスケープ等）の強化。

Referencing
- 実装の主要意図や設計はソース内ドキュメンテーション（docstring）に詳述されているため、追加の背景や仕様は該当モジュールを参照してください。