KEEP A CHANGELOG
=================

すべての変更はこのファイルに記録します。  
このプロジェクトは「Keep a Changelog」仕様に準拠しています。

フォーマット
-----------
- 変更は semantic versioning に従ってバージョンごとに記載します。
- 各リリースでは主な変更点をカテゴリ（Added, Changed, Fixed, Security 等）で整理します。

Unreleased
----------
（現在未リリースの変更はありません）

[0.1.0] - 2026-04-03
--------------------
初回公開リリース。日本株自動売買プラットフォームのコアライブラリを実装しました。
主な追加機能・設計方針は以下の通りです。

Added
- パッケージ基盤
  - kabusys パッケージの初期バージョンを追加。__version__ = 0.1.0。
  - パッケージの公開APIに data, strategy, execution, monitoring を含む。

- 設定・環境変数管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を読み込む自動ロード機能を実装。
  - 読み込み優先順位: OS環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で自動ロードを無効化可能。
  - .env パーサ: export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの扱い等に対応。
  - 設定ラッパー Settings クラスを追加。主なプロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD（必須）
    - KABU_API_BASE_URL（デフォルト http://localhost:18080/kabusapi）
    - LINE_CHANNEL_ACCESS_TOKEN, LINE_USER_ID（通知用）
    - データベースパス（DUCKDB_PATH, SQLITE_PATH）と監視用パス（PID_FILE_PATH, KILL_FLAG_PATH）
    - リソース閾値（CPU/MEMORY/DISK）
    - KABUSYS_ENV 検証（development / paper_trading / live）と LOG_LEVEL 検証
    - is_live / is_paper / is_dev のヘルパー

- AI モジュール（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約して銘柄ごとのニュースセンチメントを算出し、ai_scores テーブルへ書き込む score_news(conn, target_date, api_key=None) を追加。
    - タイムウィンドウは JST 前日 15:00 ～ 当日 08:30（UTC に変換して DB クエリ）。
    - OpenAI（gpt-4o-mini）へのバッチ送信（最大 20 銘柄／チャンク）、JSON Mode を利用。
    - リトライ（429、ネットワーク断、タイムアウト、5xx）に対する指数バックオフと最大リトライ制御。
    - レスポンス検証とスコアの ±1.0 クリップ。部分失敗時にも既存スコアを保護するため、対象コードのみ DELETE → INSERT を実行。
    - 単体テストのため内部 API 呼び出し（_call_openai_api）を差し替え可能に設計。

  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース由来の LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定する score_regime(conn, target_date, api_key=None) を追加。
    - マクロキーワードで raw_news をフィルタし、LLM により macro_sentiment を算出（記事がない場合は LLM 呼び出しをスキップし 0.0 とする）。
    - 冪等な DB 書き込み（BEGIN / DELETE / INSERT / COMMIT）とロールバック処理。
    - API 失敗時フォールバック（macro_sentiment=0.0）やリトライ処理を実装。
    - LLM 呼び出しは独立実装でモジュール結合を避ける設計（news_nlp と共有しない）。

- データ基盤（kabusys.data）
  - ETL パイプライン（kabusys.data.pipeline）
    - 差分更新、バックフィル、品質チェックのための基礎を実装。
    - ETLResult データクラスを公開（kabusys.data.etl で再エクスポート）。ETL 実行結果の集約と品質問題・エラーリスト保持、簡易辞書変換機能を提供。
  - カレンダー管理（kabusys.data.calendar_management）
    - JPX カレンダーの夜間バッチ更新ジョブ（calendar_update_job）を実装。J-Quants クライアント経由で差分取得し market_calendar に冪等保存。
    - 営業日判定 API を提供: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day。
    - DB にカレンダーがない場合の曜日ベースフォールバックや最大探索日数制限、バックフィルや健全性チェックを実装。
    - jquants_client を通じた fetch/save の呼び出し箇所を設ける（実際のクライアント実装は外部）。

- リサーチ（kabusys.research）
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum, calc_value, calc_volatility を実装。prices_daily / raw_financials を用いてモメンタム／バリュー／ボラティリティ系の指標を算出。
    - ATR、MA200 乖離、1M/3M/6M リターン、出来高・売買代金指標等を計算。
    - データ不足時は None を返す仕様。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns（将来リターンの一括取得）、calc_ic（スピアマンランクによる IC 計算）、factor_summary（統計要約）、rank（同順位平均ランク付け）を実装。
    - pandas 等に依存せず標準ライブラリ＋DuckDB SQL で完遂する設計。
  - data.stats の zscore_normalize を再エクスポート。

- ロギング・堅牢性
  - 各所で詳細なログ（info/debug/warning/exception）を追加。
  - DB トランザクションにおける ROLLBACK の失敗を警告ログに落とす等、例外処理を強化。
  - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（関数引数で基準日を渡す形式を基本とする）。

Changed
- （初回リリースのため該当なし）

Fixed
- （初回リリースのため該当なし）

Security
- 秘密情報（OpenAI API キー等）は環境変数での注入を前提。API キー未指定時は明示的に ValueError を発生させる箇所があるため、運用時は環境設定を必ず確認してください。
- .env の自動ロード時、OS 環境変数は保護（protected set）され上書きされないよう実装。

Notes / Requirements / Migration
- 必要ランタイム／依存:
  - Python（typing の union 演算子等を使用）と DuckDB
  - openai SDK（OpenAI クライアント；gpt-4o-mini を使用する想定）
- 環境変数（主要なもの）:
  - OPENAI_API_KEY（AI モジュール利用時に必須）
  - JQUANTS_REFRESH_TOKEN（J-Quants API）
  - KABU_API_PASSWORD（kabuステーション用）
  - KABUSYS_ENV, LOG_LEVEL 等
- データベース:
  - デフォルトで data/kabusys.duckdb（DUCKDB_PATH）および data/monitoring.db（SQLITE_PATH）を使用する設定。
- テストについて:
  - 内部の OpenAI 呼び出しはテスト時に unittest.mock.patch で差し替え可能な設計になっています。

今後の予定（例）
- strategy / execution / monitoring の具体的な実装と統合テスト。
- jquants_client の実実装・認証フローの整備。
- より詳細な品質チェックルールの追加と監視アラートの実装。

----- End of CHANGELOG -----