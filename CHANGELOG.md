Keep a Changelog 準拠 — 変更履歴 (日本語)
=====================================

このファイルは Keep a Changelog の形式に準拠しており、すべての公開された変更点を記録します。  
フォーマット: https://keepachangelog.com/ja/1.0.0/

[Unreleased]
------------

- （なし）

[0.1.0] - 2026-04-04
-------------------

初回リリース。日本株自動売買システムの基本コンポーネントを実装しました。
主にデータ取り込み／品質管理、研究用ファクター計算、AIベースのニュース解析、マーケットカレンダー管理、
および設定管理のユーティリティを含みます。

Added
- パッケージメタ
  - kabusys パッケージ初期化（__version__ = 0.1.0, __all__ 指定）。

- 設定・環境変数管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能（プロジェクトルートは .git または pyproject.toml から探索）。
  - 読み込み優先順位: OS 環境 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動読み込み無効化。
  - シンプルな .env パーサ（コメント、export プレフィックス、クォート・エスケープ対応）。
  - Settings クラスでアプリケーション設定を公開（J-Quants / kabuAPI / LINE / DB パス / 監視閾値 等）。
  - KABUSYS_ENV と LOG_LEVEL の値検証（許容値チェック）。
  - パスは Path オブジェクトで提供、デフォルト値を用意。

- データ関連ユーティリティ (kabusys.data)
  - ETL インターフェース公開 (ETLResult 型の再エクスポート)。
  - pipeline モジュール（ETLResult 等）:
    - ETL 実行結果を表す dataclass (ETLResult) を実装。品質問題やエラー集約、has_errors/has_quality_errors 等を提供。
    - DuckDB を前提とした差分取得・保存・品質チェックパイプラインを想定した設計。
  - calendar_management:
    - JPX カレンダーの夜間バッチ更新ジョブ (calendar_update_job) 実装。
    - 営業日判定ユーティリティ: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - market_calendar が未取得な場合の曜日ベースフォールバック実装。
    - 最大探索日数やバックフィル、健全性チェックの導入。

- 研究（Research）モジュール (kabusys.research)
  - factor_research:
    - モメンタム（1M/3M/6M リターン、200日 MA 乖離）、ボラティリティ（20日 ATR）、流動性（20日平均売買代金・出来高変化率）、バリュー（PER、ROE）を計算する関数群: calc_momentum, calc_volatility, calc_value。
    - DuckDB のウィンドウ関数を活用した実装。データ不足時の None ハンドリング。
  - feature_exploration:
    - 将来リターン計算（calc_forward_returns、任意ホライズン対応、入力検証あり）。
    - IC（Information Coefficient）計算（calc_ic、スピアマンランク相関）。
    - ランク関数（rank）とファクター統計サマリー（factor_summary）を実装。
    - pandas 等に依存しない純 Python 実装。

- AI / NLP 機能 (kabusys.ai)
  - news_nlp:
    - raw_news + news_symbols を集約して銘柄ごとのニュースセンチメントを OpenAI (gpt-4o-mini) の JSON Mode で評価し、ai_scores テーブルへ書き込む score_news を実装。
    - タイムウィンドウ定義（JST 前日15:00〜当日08:30 相当 → UTC 変換済み）。
    - バッチ処理（最大 20 銘柄/リクエスト）、トークン肥大対策（記事数・文字数上限）。
    - レート制限・ネットワーク断・タイムアウト・5xx を対象とした指数バックオフによるリトライ。
    - レスポンスの厳格なバリデーション（JSON 抽出、results フィールド、コード存在チェック、数値チェック）。不正応答はスキップ（例外を上げない）。
    - DuckDB への書き込みは冪等的（BEGIN / DELETE / INSERT / COMMIT）。部分失敗時に他コードの既存スコアを保護する実装。
    - テスト容易性のため _call_openai_api の差し替え（モック）を想定。

  - regime_detector:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、news_nlp ベースのマクロセンチメント（重み 30%）を合成して market_regime テーブルへ書き込む score_regime を実装。
    - OpenAI 呼び出しを独立実装しモジュール結合を避ける設計。
    - API エラー・パースエラーはフェイルセーフで macro_sentiment = 0.0 にフォールバック。
    - DuckDB への冪等書き込みとトランザクション処理（ROLLBACK ハンドリングおよびログ出力）。

- テスト・運用を意識した設計点
  - ルックアヘッドバイアス防止: いずれも datetime.today()/date.today() を直接参照しない API 設計（target_date を明示的に受け取る）。
  - DuckDB を前提とした SQL 実装と互換性配慮（executemany の空リスト回避など）。
  - OpenAI 呼び出しで JSON Mode を利用し、厳密な JSON 応答を期待する実装。レスポンスの前後に余計なテキストが混ざるケースへの復元ロジックを含む。
  - ロギングによるフェイルセーフ行動の通知（警告・情報ログを適切に出力）。

Security
- API キーの取り扱い:
  - OpenAI API キーは api_key 引数または環境変数 OPENAI_API_KEY を想定。未設定時は ValueError を投げることで明示的に扱う。
- 環境変数の自動読み込みで OS 環境変数は保護される（protected set として扱い .env で上書きされない）。
- 秘密情報（API キー等）のログ出力は行わない設計（ログメッセージは状態・エラー情報に限定）。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Notes / 今後の留意点
- DuckDB バージョン差異に起因するバインド挙動（list バインドなど）に配慮した実装を行っていますが、実環境での互換性確認を推奨します。
- OpenAI モデル・API の将来的な SDK 変更に備え、exception の取り扱い（status_code の存在有無など）を安全側で実装しています。
- 外部 API（J-Quants、OpenAI）呼び出しのエラーは基本的にサイレントにし続行するフェイルセーフ方針です。運用ポリシーによってはより厳格に扱う設定が必要となる場合があります。

ライセンス、貢献方法、ドキュメント等は別途 README / docs を参照してください。