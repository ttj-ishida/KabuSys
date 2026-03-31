# CHANGELOG

すべての重要な変更をここに記録します。  
このファイルは Keep a Changelog の形式に従います。  

注: 以下のリリースノートは、リポジトリ内のソースコードから実装内容を推測して作成しています。

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回公開リリース。日本株自動売買 / データ基盤向けのコアライブラリを提供します。主な機能・設計方針は以下の通りです。

### 追加（Added）
- パッケージ基盤
  - kabusys パッケージの初期公開。バージョンは 0.1.0。
  - モジュールを公開: data, research, ai, execution, strategy, monitoring（__all__ 経由でエクスポート）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数からの設定読み込みを提供。
  - 自動ロード順序: OS 環境変数 > .env.local > .env。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動ロードを無効化可能（テスト用）。
  - .env パーサーを実装（export プレフィックス、シングル/ダブルクォート、エスケープ、行内コメント処理に対応）。
  - _require / Settings クラスを提供し、必須変数取得時の明確なエラーを発生させる。
  - 設定プロパティ:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID 等の必須取得
    - KABU_API_BASE_URL, DUCKDB_PATH, SQLITE_PATH, PID_FILE_PATH 等の既定値サポート
    - CPU/MEM/ディスク閾値、ログレベル・環境（development/paper_trading/live）検証
    - is_live / is_paper / is_dev の利便性プロパティ

- AI 関連（kabusys.ai）
  - ニュース NLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols を集約し、銘柄ごとのニュースを OpenAI（gpt-4o-mini）へバッチ送信してセンチメント（ai_score）を算出。
    - タイムウィンドウ計算ユーティリティ calc_news_window（JSTベースの前日15:00～当日08:30 -> UTC 変換）を提供。
    - バッチ処理（最大 20 銘柄/呼び出し）、1 銘柄あたりの記事数と文字数上限を導入（トークン肥大化対策）。
    - JSON Mode を用いた厳格なレスポンス検証と、前後ノイズのある JSON の復元処理を実装。
    - レート制限（429）、ネットワーク断、タイムアウト、5xx に対する再試行（指数バックオフ）を実装。
    - API 失敗時やパース失敗時は該当チャンクをスキップし、処理継続（フェイルセーフ）。
    - ai_scores テーブルへは「DELETE（該当 code）→ INSERT」の置換方式で冪等書込み。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321 の 200 日移動平均乖離（重み 70%）とマクロニュース LLM センチメント（重み 30%）を合成して market_regime を日次判定。
    - マクロニュースはニュース NLP 用の calc_news_window と共通ロジックで抽出し、LLM（gpt-4o-mini）から macro_sentiment を取得。
    - OpenAI 呼び出しは独立実装でモジュール結合を避ける設計。
    - API エラー時は macro_sentiment = 0.0 にフォールバック（フェイルセーフ）。
    - 計算結果は market_regime テーブルへ冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
    - ルックアヘッドバイアス防止のため date 引数ベースで動作し、date.today()/datetime.today() を参照しない。

- リサーチ / ファクター（kabusys.research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200 日 MA 乖離（ma200_dev）などを計算。
    - calc_volatility: 20 日 ATR（atr_20）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials から最新財務を取得し PER, ROE を計算（EPS が 0/欠損時は None）。
    - DuckDB SQL を用いた効率的な一括計算を実装。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定 horizon（営業日ベース）後の将来リターン（デフォルト [1,5,21]）。
    - calc_ic: ファクタと将来リターンの Spearman ランク相関（IC）を計算。サンプル数不足時は None を返す。
    - rank: 同順位は平均ランクを付与するランク変換。
    - factor_summary: count/mean/std/min/max/median の統計サマリーを提供。
  - research パッケージはデータ参照のみ（prices_daily / raw_financials）で、発注等の副作用は無し。

- データ基盤（kabusys.data）
  - calendar_management:
    - market_calendar を扱うユーティリティ群（is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day）。
    - DB 登録がない場合の曜日ベース（週末除外）フォールバック実装。
    - calendar_update_job: J-Quants API からカレンダーを差分取得して market_calendar を冪等に更新。バックフィルと健全性チェックを実装。
  - pipeline / ETL:
    - ETLResult データクラスを公開し、ETL 実行時の取得数／保存数／品質問題／エラー一覧を保持可能に。
    - 差分取得、backfill、品質チェック（quality モジュール連携）などの設計方針を反映。
  - etl モジュールは ETLResult を再エクスポート。

### 変更（Changed）
- DuckDB 特性に合わせた堅牢化
  - executemany に空リストを渡せない制約を考慮し、書込み前に params が空でないことを確認する実装（news_nlp / score_news 等）。
  - SQL 実行や日付取り扱いで DuckDB の戻り値型を安全に date に変換するユーティリティを導入。

- エラーハンドリング強化
  - OpenAI API 呼び出しに対する細かな例外分岐（RateLimitError, APIConnectionError, APITimeoutError, APIError など）を実装し、再試行や非再試行の判断を行うことで安定性を向上。
  - JSON パース失敗や未知フォーマットに対する保護ロジックを追加。

- ログ出力の整備
  - 各処理の開始・終了・警告・エラー時に logger を用いて詳細な情報を記録するようにした（デバッグや運用性向上）。

### 修正（Fixed）
- .env 解析の不備に対する改善
  - export プレフィックス、クォート文字内のエスケープ、行内コメントの扱いを正しく処理するように修正。
  - キーが空の行や不正な行を無視する堅牢なパーサーを導入。

- レスポンス検証の強化
  - news_nlp のレスポンス検証で、LLM が整数コードを返すケースや不要なテキストを含むケースを考慮して正規化/復元する処理を追加し、不正なデータによるクラッシュを防止。

### セキュリティ（Security）
- 設定値の必須チェックで明確なエラーメッセージを提供（API キー未設定時に ValueError を送出）し、誤った運用を早期に検出可能に。

### 既知の注意点 / 設計上の決定
- ルックアヘッドバイアス対策のため、全ての「当日基準」処理は date / target_date を引数に取り、内部で date.today() / datetime.today() を参照しない設計になっている。
- OpenAI の呼び出しはレスポンスの不確実性を想定しており、API 失敗時は部分的にスキップして他の処理を継続するフェイルセーフの方針を採用。
- ai_scores / market_regime など DB への書き込みは冪等化（DELETE → INSERT）しているため再実行が安全。

---

貢献者: ソースコード内の実装者（リポジトリ情報から推測）  
注: 実際の変更履歴（コミットログ）に基づく詳細な差分は含まれていません。本ドキュメントはソースコードの現在の実装内容から推測して作成した概要です。