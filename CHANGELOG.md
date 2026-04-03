Keep a Changelog
================

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠しています。  

Unreleased
----------

- （現時点の変更はすべて次の初期リリースに含まれます）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリースを追加（kabusys v0.1.0）。
- パッケージ公開情報
  - パッケージ名: kabusys
  - version: 0.1.0
  - メインサブパッケージ: data, research, ai, monitoring, execution, strategy（__all__ を経由して公開）

- 環境/設定管理（kabusys.config）
  - .env ファイルと環境変数の自動ロード機能を実装（プロジェクトルートは .git または pyproject.toml を探索）。
  - .env/.env.local の優先度ロジック（OS 環境 > .env.local > .env）。KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応。
  - 複雑な .env 行パーサを実装（export プレフィックス、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメントの扱い）。
  - protected（既存 OS 環境変数）を考慮した override ロジック。
  - Settings クラスを提供し、J-Quants / kabuステーション / LINE / DB パス / 監視しきい値 / システム設定等のプロパティを型付きで取得。
    - 必須変数取得時のバリデーション (_require) と、env/log_level の許容値検査を実装。
  - デフォルトパス（DuckDB / SQLite / PID 等）や kill-flag の挙動設定（起動時クリアフラグ）を用意。

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を元にニュースを銘柄ごとに集約し、OpenAI（gpt-4o-mini）へバッチで送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ計算（前日 15:00 JST 〜 当日 08:30 JST）を calc_news_window で提供。
    - バッチサイズ、記事数上限、文字トリム（トークン肥大対策）等の保護策を実装。
    - API へのリトライ（429, ネットワーク断, タイムアウト, 5xx）を指数バックオフで実装。失敗時は該当チャンクをスキップして継続（フェイルセーフ）。
    - レスポンスの厳密なバリデーションと JSON 復元（前後余分なテキストが混ざるケースへの対処）。
    - DuckDB 互換性を意識した DB 書き込み（部分成功時に既存スコアを保護する DELETE→INSERT の戦術、executemany 空パラメータへの対応）。
    - テストしやすさのため _call_openai_api を分離して unittest.mock.patch で差し替え可能に。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して market_regime を日次で判定（bull/neutral/bear）。
    - ma200 計算は target_date 未満のデータのみを使用しルックアヘッドを防止。
    - マクロニュースはマクロキーワードでフィルタして LLM に送信。API エラー時は macro_sentiment=0.0 にフォールバック。
    - レジーム判定結果を冪等に DuckDB の market_regime テーブルへ書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）。
    - OpenAI 呼び出しは独立実装として分離（モジュール間結合を低減）。

- Data モジュール（kabusys.data）
  - マーケットカレンダー管理（kabusys.data.calendar_management）
    - market_calendar テーブルに基づく営業日判定 API（is_trading_day, is_sq_day, next_trading_day, prev_trading_day, get_trading_days）を提供。
    - DB にデータがない場合は曜日ベース（週末除外）でフォールバックする一貫した挙動。
    - カレンダー夜間バッチ更新ジョブ calendar_update_job：J-Quants から差分取得・冪等保存、バックフィル、健全性チェックを実装。
    - 最大探索日数制限で無限ループを防止。
  - ETL パイプライン（kabusys.data.pipeline / etl）
    - ETLResult データクラスを公開（取得/保存カウント、品質問題、エラー一覧などを含む）。
    - 差分更新、backfill、品質チェックを行う設計（実装は ETLResult 等の基盤を提供）。
    - DuckDB テーブル存在チェックや最大日付取得ユーティリティ等の内部関数。
  - jquants_client とのインタフェース（実装は参照：fetch/save を呼び出す前提）

- Research モジュール（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - モメンタム: mom_1m, mom_3m, mom_6m と 200 日移動平均乖離（ma200_dev）。
    - ボラティリティ / 流動性: 20 日 ATR（atr_20, atr_pct）、20 日平均売買代金、出来高比率。
    - バリュー: PER（EPS に依存）、ROE（raw_financials から最新レコードを取得）。
    - DuckDB 上の SQL とウィンドウ関数を用いた実装。データ不足時は None を返す方針。
  - 特徴量探索（kabusys.research.feature_exploration）
    - 将来リターン計算（calc_forward_returns）：任意ホライズンの将来リターンを一括取得。
    - IC（Information Coefficient）計算（calc_ic）：スピアマンのランク相関でファクター有効性を評価。データ不足（<3）時は None。
    - rank と factor_summary（count/mean/std/min/max/median）を提供。外部依存（pandas 等）無しで純 Python 実装。

Quality / Reliability
- ルックアヘッドバイアス対策として、AI モジュール・研究モジュールは date.today()/datetime.today() を参照せず、必ず引数の target_date を基準に動作。
- OpenAI API 呼び出しに対して堅牢なリトライ・バックオフ・レスポンス検証を実装。重大な API 障害でもシステム継続（フェイルセーフ）する設計。
- DuckDB の実装制約（executemany に空リスト不可など）に配慮した安全な DB 書き込みロジックを採用。
- 例外発生時に適切にロールバックし、ロールバック失敗時は警告ログを残す。

Security / Configuration
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - OPENAI_API_KEY（AI モジュールで利用; 関数呼び出し時引数で注入可能）
- 環境設定は Settings 経由で型チェック・許容値チェックを行う（例: KABUSYS_ENV, LOG_LEVEL の検証）。

Testing / Extensibility
- OpenAI 呼び出し部分は内部で関数分離されており、unittest.mock.patch 等で差し替えやモックが可能（テスト容易性を考慮）。
- モジュールは DB（DuckDB）接続を注入する設計で、I/O を分離してユニットテストが容易。

Notes
- 本リリースは「データ取得・処理・AI スコアリング・研究用解析基盤」の基礎を提供する初期版です。  
- 発注（execution）や monitoring の詳細実装はパッケージの他モジュールで扱う予定（本 changelog は現行コードベースに基づく記述）。
- 実運用前に環境変数とデータベーススキーマ（prices_daily / raw_news / ai_scores / market_regime / market_calendar / raw_financials 等）の準備が必要です。

Authors
- 初期実装コードに基づく CHANGELOG（自動生成的に推測して作成）

---