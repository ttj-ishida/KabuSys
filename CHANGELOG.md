CHANGELOG
=========

All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠し、セマンティックバージョニングを使用します。

Unreleased
----------

（なし）

0.1.0 - 2026-03-31
-----------------

初回リリース。パッケージの基本機能群を実装しました（日本株自動売買システムのコアライブラリ）。

Added
- パッケージ基盤
  - kabusys パッケージの初期公開（__version__ = 0.1.0）。
  - パッケージ公開 API: data, strategy, execution, monitoring（__all__ に列挙）。

- 環境設定管理（kabusys.config）
  - .env/.env.local ファイルおよび環境変数から設定を自動読み込みする仕組みを実装。
    - プロジェクトルート検出は .git または pyproject.toml を起点に行うため、CWD に依存しない。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動読み込みを無効化可能。
  - .env 行パーサは以下に対応:
    - 空行・コメント行（#）の無視、`export KEY=val` 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い（クォート有無で異なるルール）。
  - OS 環境変数を保護するための protected キーセットを考慮した上書き処理。
  - Settings クラスを提供（プロパティで環境変数を読み取り、必須値未設定時は ValueError を送出）。
    - J-Quants / kabuステーション / Slack / DB パス / 監視閾値 / 環境（development/paper_trading/live）/ログレベル等のプロパティを実装。
    - env / log_level の値検証、is_live/is_paper/is_dev の便利プロパティ。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - 指定日のニュース収集ウィンドウ計算（JST ベース → UTC 変換）を calc_news_window で実装。
    - raw_news と news_symbols を集約して銘柄ごとに記事を結合・トリム（最大記事数・最大文字数制約）。
    - OpenAI（gpt-4o-mini + JSON mode）へのバッチ送信（1リクエストあたり最大 20 銘柄）。
    - 再試行（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。その他エラーはスキップして継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーション実装（JSON 抽出、"results" 配列、code と score の検証、未知コード無視、スコアを ±1.0 にクリップ）。
    - 成功したスコアのみ ai_scores テーブルへ冪等的に置換（DELETE → INSERT、部分失敗時に既存データ保護）。
    - API キー注入対応（api_key 引数または OPENAI_API_KEY 環境変数）。
    - score_news 関数は取得した銘柄数を返す。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して日次でレジーム（bull/neutral/bear）判定。
    - prices_daily からの MA 計算（target_date 未満のデータのみ使用してルックアヘッドを防止）。
    - raw_news からマクロキーワードでタイトルを抽出し、LLM（gpt-4o-mini）でマクロセンチメントを評価（記事が存在する場合のみ）。
    - LLM 呼び出しのリトライ/バックオフ、API 失敗時は macro_sentiment=0.0 で継続（フェイルセーフ）。
    - レジームスコア合成および market_regime テーブルへの冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。エラー発生時は ROLLBACK を行い例外を上位へ伝播。

- データプラットフォーム（kabusys.data）
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーを扱うためのユーティリティを実装。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を提供。
    - 市場カレンダー未取得時は曜日ベース（土日非営業日）でフォールバック。
    - calendar_update_job を実装し、J-Quants API から差分取得して market_calendar を更新（バックフィルと健全性チェックを実装）。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult データクラスを実装（取得件数・保存件数・品質問題・エラー概要を格納）。
      - has_errors / has_quality_errors プロパティ、to_dict メソッドを提供。
    - 差分更新（最終取得日からの新規データ取得）、バックフィル、品質チェックの骨子を実装。
    - DuckDB を前提にしたテーブル存在確認等のユーティリティを含む。
  - ETL の公開インターフェース（kabusys.data.etl）
    - pipeline.ETLResult を再エクスポート。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: 1M/3M/6M リターンと 200 日 MA 乖離（ma200_dev）を計算。データ不足は None を返す。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金（avg_turnover）、出来高比（volume_ratio）を計算。
    - calc_value: raw_financials からの最新財務を使い PER・ROE を計算（EPS が 0/欠損時は None）。
    - いずれも DuckDB の SQL を用いて実装し、(date, code) をキーとする dict リストを返す。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 各ホライズン（デフォルト [1,5,21]）の将来リターンを一括 SQL で取得。horizons の検証あり。
    - calc_ic: スピアマンのランク相関（Information Coefficient）を実装（結合・None 除外・3 件未満は None）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
    - rank: 同順位は平均ランクで扱うランク化ユーティリティ（小さな丸めで ties を確実に扱う）。
  - kabusys.research.__init__ で主要関数や zscore_normalize を再エクスポート。

Changed
- 設計方針・実装上の注意点（全体）
  - ルックアヘッドバイアス防止のため、score_news / score_regime 等の主要関数は内部で datetime.today()/date.today() を参照しない（target_date を明示的に受け取る）。
  - DuckDB を主要な保存・クエリ層として利用する設計を採用。
  - 外部 API（OpenAI, J-Quants 等）呼び出しはリトライ戦略とフォールバック（API 失敗時はスコア 0.0 や処理スキップ）を採ることでフェイルセーフに設計。

Fixed
- トランザクションとロールバックの取り扱いを一貫して実装（DB 書き込み失敗時に ROLLBACK を試行し、失敗ログを出力）。

Notes / Implementation details
- OpenAI 呼び出しは JSON mode（response_format={"type":"json_object"}）を利用し、応答の厳密な JSON パース・復元ロジックを導入している。
- news_nlp と regime_detector は意図的に OpenAI へのラッパー関数を個別に実装し、モジュール間の結合を避けている（テスト時に差し替え可能）。
- AI モジュールはスコアを ±1.0 にクリップして出力する設計。
- DuckDB の executemany に関する互換性問題（空リスト不可）を回避するために条件分岐を追加。
- calendar_update_job はバックフィル、years ahead の健全性チェック、J-Quants からの取得失敗時の例外ハンドリングを備える。

Breaking Changes
- 初回リリースのため、破壊的変更はありません。

Security
- (なし)

今後の予定（例）
- strategy / execution / monitoring モジュールの具体実装（本リリースではパッケージ参照のみ）。
- 単体テスト・統合テストの充実、CI/CD パイプライン整備。
- OpenAI モデルや J-Quants クライアントの抽象化／差し替え容易性向上。

お問い合わせ・貢献
- コード内の docstring や設計メモ（DataPlatform.md / StrategyModel.md 参照箇所）を起点に、機能拡張・バグ修正の PR を歓迎します。