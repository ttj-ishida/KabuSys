CHANGELOG
=========
All notable changes to this project will be documented in this file.

フォーマットは Keep a Changelog に準拠しています。  
このファイルはコードベースから推測して作成した初期の変更履歴です。

[0.1.0] - 2026-04-04
-------------------

Added
- 基本情報
  - パッケージの初期バージョンを v0.1.0 としてリリース。
  - パッケージルート: src/kabusys。公開 API として data, research, ai, config 等の名前空間を提供。

- 環境設定 / 設定管理 (kabusys.config)
  - .env / .env.local 自動読み込み機能を実装（プロジェクトルートは .git または pyproject.toml で探索）。
  - OS 環境変数を保護する保護セット(protected)を導入し、.env の上書き挙動を制御。
  - .env パーサ実装: export 句対応、シングル/ダブルクォート内のエスケープ処理、コメント処理（クォート外でのみ有効）。
  - 自動読み込みを無効化する環境変数 KABUSYS_DISABLE_AUTO_ENV_LOAD をサポート。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視閾値 / ログレベル 等の設定プロパティを公開。
  - 必須設定取得時に未設定なら ValueError を投げる _require 実装。
  - KABUSYS_ENV / LOG_LEVEL のバリデーションを追加（許容値のチェック）。
  - Path 型での DB/ファイルパス解決（expanduser 対応）。

- AI: ニュース NLP と市場レジーム判定 (kabusys.ai.news_nlp, kabusys.ai.regime_detector)
  - news_nlp:
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）の JSON Mode を使って銘柄別センチメントを取得。
    - タイムウィンドウ計算 (前日15:00 JST ～ 当日08:30 JST を UTC に変換) を calc_news_window として実装。
    - バッチ処理（最大20銘柄/チャンク）、1銘柄あたりの記事数上限・文字数上限を実装（トークン肥大化対策）。
    - リトライ/バックオフロジック（429, ネットワーク断, タイムアウト, 5xx の指数バックオフ）。非再試行のエラーはスキップして継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーションとパース。JSON前後に余計なテキストが混ざる場面も考慮して復元処理を実装。
    - スコアは ±1.0 にクリップ。DuckDB への書き込みは部分失敗対策のため対象コードのみ DELETE→INSERT の冪等更新を実施。
    - テスト容易性のため OpenAI 呼び出し関数をモジュール内でラップしており、unittest.mock.patch による差し替えが可能。
    - 公開 API: score_news(conn, target_date, api_key=None) — 書き込んだ銘柄数を返す。api_key は引数 or 環境変数 OPENAI_API_KEY を利用。未設定時は ValueError。

  - regime_detector:
    - ETF 1321 の 200 日移動平均乖離 (ma200_ratio) とニュース由来マクロセンチメントを重み付け合成して日次の市場レジーム（bull/neutral/bear）を判定。
    - マクロニュースは news_nlp の窓計算を利用して取得、LLM によるセンチメントは独自の呼び出し実装で取得（モジュール結合を低く保つ）。
    - LLM 呼び出しは JSON Mode を用い、3回までのリトライと指数バックオフを実装。API失敗時は macro_sentiment=0.0 として継続（フェイルセーフ）。
    - レジームスコアの合成、閾値によるラベル付け、DuckDB の market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）を実装。
    - 公開 API: score_regime(conn, target_date, api_key=None) — 正常終了で 1 を返す。api_key 未設定時は ValueError。

- Data (kabusys.data)
  - calendar_management:
    - JPX カレンダー管理と営業日判定ロジックを提供（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - market_calendar テーブルが未取得の場合は曜日ベース（土日除外）でフォールバックする一貫した挙動。
    - カレンダー更新ジョブ calendar_update_job(conn, lookahead_days=90) を実装。J-Quants クライアント経由で差分取得し保存。バックフィル / 健全性チェックを実装。
    - 検索上限 (_MAX_SEARCH_DAYS) による無限ループ防止。

  - pipeline / etl:
    - ETLResult データクラスを実装して ETL 結果（取得数・保存数・品質問題・エラー等）を一元管理。
    - ETL の方針: 差分更新、backfill、品質チェック（quality モジュール）を組み込む設計を明示。
    - jquants_client からの保存関数を想定した idempotent な保存ワークフローを前提。

  - etl モジュールは pipeline.ETLResult を再エクスポート。

- Research (kabusys.research)
  - factor_research:
    - モメンタム (calc_momentum)、ボラティリティ・流動性 (calc_volatility)、バリュー (calc_value) の関数を実装。
    - 各ファクターは DuckDB の prices_daily / raw_financials を参照し、(date, code) 単位の dict リストを返す。
    - ma200_dev / mom_1m/3m/6m / atr_20 / atr_pct / avg_turnover / volume_ratio / per / roe 等を計算。データ不足時は None を返す。
    - 実装は SQL ウィンドウ関数と Python を組み合わせて効率的に実行する。

  - feature_exploration:
    - 将来リターン計算 calc_forward_returns(conn, target_date, horizons=None) を実装（デフォルト [1,5,21]）。
    - IC（Information Coefficient）計算 calc_ic（Spearman のランク相関）とランク変換ユーティリティ rank を実装。
    - factor_summary による基本統計量（count/mean/std/min/max/median）計算を実装。外部ライブラリに依存しない純粋 Python 実装。
    - 研究用途の設計方針（本番環境への影響無し）を明確化。

- テスト性 / ロギング / フェイルセーフ
  - OpenAI 呼び出し箇所はモジュール内でラップしており、ユニットテスト時に差し替え可能。
  - API 呼び出しでの一時的な失敗は警告ログを出してフォールバックする実装（例: macro_sentiment=0.0、スコア取得失敗は該当銘柄をスキップ）。
  - DuckDB 操作はトランザクション（BEGIN/COMMIT/ROLLBACK）で保護し、ROLLBACK の失敗時にも警告を出す。

Changed
- 初期リリースのため該当なし。

Fixed
- 初期リリースのため該当なし。

Security
- 環境変数や API キーは Settings / 引数経由で取得。OpenAI API キー未設定時は ValueError を返して明示的な取り扱いを促す。

Notes / 実装上の注意
- 日付/時間の扱い:
  - news ウィンドウは JST 基準で定義され、DB 比較のために UTC naive datetime で返します（ルックアヘッドバイアス回避のため内部で datetime.today() を参照しない設計）。
  - 各種集計クエリは target_date 未満や target_date での明示的フィルタによりルックアヘッドを防止。
- DuckDB のバージョン依存性に配慮（executemany の空リスト禁止や配列バインドの互換性回避）。
- AI レスポンスは厳密な JSON 出力を期待してプロンプト設計しているが、パース失敗時の復元処理も実装している。
- 将来的な拡張点: PBR/配当利回りなどのバリューファクター追加、AI モデルやバッチサイズのパラメタライズ等。

貢献者
- 初期実装（コードベースから推測して記載）

ライセンス
- リポジトリ内のライセンスファイルに従ってください（この CHANGELOG はコードから推測して作成した記録です）。

（以降のリリースはこのフォーマットで追記してください）