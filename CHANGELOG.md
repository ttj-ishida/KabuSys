# Changelog

すべての著名な変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」に準拠します。

最新リリース
=============

Unreleased
----------

（なし）

0.1.0 - 2026-03-28
------------------

Added
- パッケージ初期リリース "KabuSys"（バージョン 0.1.0）
  - パッケージエントリポイントを提供（src/kabusys/__init__.py）。
  - モジュール群を論理的に分離:
    - data: データ取得・ETL・カレンダー管理（DuckDB 前提）
    - ai: ニュースNLP / 市場レジーム判定によるAIスコアリング
    - research: ファクター計算・特徴量探索
    - （strategy / execution / monitoring はパッケージ公開シンボルに含める設計）
- 環境設定管理（src/kabusys/config.py）
  - .env /.env.local の自動読み込み（優先順位: OS 環境 > .env.local > .env）。
  - プロジェクトルート検出: .git または pyproject.toml を基準に探索（実行ファイル位置から親ディレクトリを上るため CWD 非依存）。
  - 柔軟な .env パーサ実装:
    - export KEY=val 形式に対応
    - シングル／ダブルクォート内のバックスラッシュエスケープ対応
    - インラインコメントの扱い（クォートあり無しでの差異を考慮）
  - 自動ロード無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD
  - 設定ラッパー Settings を提供（必須値取得や値検証を実装）
    - 必須環境変数: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID
    - デフォルトパス: DUCKDB_PATH（data/kabusys.duckdb）, SQLITE_PATH（data/monitoring.db）
    - 環境 (KABUSYS_ENV) とログレベル (LOG_LEVEL) の検証（許容値定義）
    - is_live / is_paper / is_dev の便宜プロパティ
- AI モジュール（src/kabusys/ai）
  - news_nlp.score_news
    - raw_news / news_symbols を入力に OpenAI（gpt-4o-mini）で銘柄別センチメントを算出し ai_scores に書き込み
    - 前日 15:00 JST 〜 当日 08:30 JST のニュースウィンドウ計算（UTC naive datetime 返却関数 calc_news_window を提供）
    - 銘柄当たり記事数と文字数を制限（トークン肥大化対策）
    - バッチ（最大 20 銘柄）での API 呼び出し、JSON mode を利用
    - 再試行（429/ネットワーク断/タイムアウト/5xx）に対する指数バックオフ
    - レスポンスバリデーション（JSON 抽出、results 配列、code/score の検証、スコアクリップ）
    - DB 書き込みは部分失敗を避けるため該当コードのみ DELETE → INSERT（DuckDB の executemany 空配列回避に配慮）
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）
    - フェイルセーフ: API 失敗時は該当チャンクをスキップして継続
    - テスト容易性: _call_openai_api の差し替えが可能
  - regime_detector.score_regime
    - ETF 1321（日経225連動型）200日移動平均乖離（重み 70%）とニュース（LLM によるマクロセンチメント、重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定
    - MA 計算は target_date 未満のデータのみを利用（ルックアヘッドバイアス回避）
    - マクロ記事抽出（キーワードベース、最大件数制限）
    - OpenAI 呼び出し（gpt-4o-mini）で JSON 出力を期待、リトライ/エラー処理実装
    - レジーム合成ロジックと閾値によるラベリング
    - 市場レジームの DB への冪等書き込み（BEGIN / DELETE / INSERT / COMMIT、失敗時は ROLLBACK）
    - API キー注入可能（api_key 引数または環境変数 OPENAI_API_KEY）
    - フェイルセーフ: API 失敗時は macro_sentiment = 0.0 にフォールバック
- Research モジュール（src/kabusys/research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離を計算（データ不足時は None）
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率を計算
    - calc_value: raw_financials と価格を用いて PER / ROE を計算（EPS 不在/0 の場合 PER=None）
    - 実装は DuckDB SQL を中心に行い、prices_daily/raw_financials のみ参照（外部発注 API にはアクセスしない）
  - feature_exploration
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]営業日）の将来リターンを一括取得
    - calc_ic: スピアマンランク相関（IC）計算を実装（3件未満で None）
    - rank: 同順位は平均ランクを割り当てるランク関数（浮動小数丸め対策あり）
    - factor_summary: count/mean/std/min/max/median 等の統計サマリー集計
  - kabusys.research パッケージは kabusys.data.stats.zscore_normalize を再エクスポート
- Data モジュール（src/kabusys/data）
  - calendar_management
    - JPX カレンダー管理ユーティリティ（market_calendar テーブル連携）
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供
    - DB に値がない場合は曜日ベース（平日=営業日）でフォールバック
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル・健全性チェック実装）
  - pipeline / etl
    - ETLResult データクラス（ETL 実行結果の構造化）
    - ETL パイプラインのユーティリティ（差分取得、backfill、品質チェック呼び出し設計）
    - _get_max_date 等の DB ヘルパーを提供
  - jquants_client を介した外部 API 連携箇所を想定（fetch/save 関数を利用）
- 共通
  - DuckDB を想定したクエリ実装（型変換ユーティリティ等を含む）
  - 詳細なログ出力ポイント（info/debug/warning/exception）
  - ルックアヘッドバイアス対策: 各処理で datetime.today()/date.today() を直接参照せず、target_date ベースで動作

Changed
- 初回リリースのため該当なし

Fixed
- 初回リリースのため該当なし

Deprecated
- 初回リリースのため該当なし

Removed
- 初回リリースのため該当なし

Security
- 初回リリースのため該当なし

Notes / 注意事項
- OpenAI API の利用には OPENAI_API_KEY が必要。news_nlp.score_news / regime_detector.score_regime は引数でもキー注入可能。
- 環境変数の必須項目（Settings のプロパティ参照）を正しく設定する必要があります。未設定時は ValueError を送出します。
- DuckDB 上のスキーマ（prices_daily, raw_news, news_symbols, ai_scores, market_calendar, raw_financials など）を前提としています。実運用前にスキーマ整備が必要です。
- 一部の関数はテスト時にモック可能（例: _call_openai_api の差し替え、KABUSYS_DISABLE_AUTO_ENV_LOAD による自動 env ロード無効化）。
- 現バージョンは主に内部解析・研究用途のロジック実装が中心で、実際の発注/実行ロジック（execution/strategy/monitoring）との統合は別途実装・接続が必要です。

今後の予定（例）
- strategy / execution / monitoring モジュールの実装と統合テスト
- J-Quants / kabu API クライアント実装の強化とサンプル ETL ワークフロー
- ユニット / 統合テストと CI の整備
- ドキュメント（API リファレンス、セットアップ手順、DB スキーマ定義）の追加

---