# Changelog

すべての重要な変更は Keep a Changelog の形式に従って記載しています。  
このリポジトリはセマンティックバージョニングに従います。

## [0.1.0] - 2026-03-27

初回リリース

### Added
- パッケージ基盤
  - kabusys パッケージの初期公開（version 0.1.0）。主要サブパッケージを __all__ でエクスポート: data, research, ai, 等。
  - 依存（ランタイム想定）: duckdb, openai を使用するモジュールを含む。

- 環境設定 / 設定管理（kabusys.config）
  - .env ファイルまたは環境変数から設定を自動読み込みする仕組みを実装。
  - プロジェクトルート検出: __file__ を起点に親ディレクトリに .git または pyproject.toml を探し、プロジェクトルートを判定。これにより CWD に依存しない自動ロードを実現。
  - .env 読み込み機能:
    - export KEY=val 形式対応。
    - シングル／ダブルクォート内でのバックスラッシュエスケープ対応。
    - クォートなし行のインラインコメント解析（直前が空白/タブの場合のみ # をコメント扱い）。
    - ファイル存在チェックや読み込み失敗時の警告出力。
    - override / protected オプションにより OS 環境変数を保護して上書きを制御。
  - 自動読み込み無効化フラグ: KABUSYS_DISABLE_AUTO_ENV_LOAD=1。
  - Settings クラスを提供（settings インスタンス）:
    - J-Quants / kabu API / Slack / DB パス等のプロパティを定義。
    - env（development/paper_trading/live）や log_level の検証を実施。
    - Path 型での duckdb/sqlite パス取得。
    - is_live / is_paper / is_dev のヘルパー。

- ニュースNLP（kabusys.ai.news_nlp）
  - raw_news / news_symbols テーブルから記事を収集し、OpenAI（gpt-4o-mini, JSON mode）で銘柄ごとのセンチメントを算出して ai_scores テーブルへ書き込む機能を実装。
  - 処理詳細:
    - JST 基準のニュースウィンドウ計算（前日15:00〜当日08:30、内部は UTC naive datetime）。
    - 1銘柄あたりの記事は最新順で最大 _MAX_ARTICLES_PER_STOCK 件、文字数トリム（_MAX_CHARS_PER_STOCK）。
    - 最大 _BATCH_SIZE 銘柄ずつバッチ送信。
    - 429 / ネットワーク断 / タイムアウト / 5xx を対象とした指数バックオフによるリトライ。
    - レスポンスの堅牢な検証（JSON 抽出、results リスト、code・score の検証、スコアのクリップ）。
    - DuckDB への書き込みは部分失敗を許容するため、取得できたコードのみを DELETE → INSERT で置換（冪等・部分失敗耐性）。
  - テストのために _call_openai_api をパッチ差し替え可能に設計。

- 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み70%）とマクロニュース由来の LLM センチメント（重み30%）を合成して日次レジーム（bull/neutral/bear）を判定し market_regime テーブルへ保存する機能を実装。
  - 処理詳細:
    - prices_daily から 1321 の終値を用いて ma200_ratio を算出（target_date 未満のデータのみを使用しルックアヘッドを防止）。
    - raw_news からマクロキーワードでフィルタしたタイトルを取得、LLM により macro_sentiment を取得（記事なしは LLM 呼び出しを行わない）。
    - OpenAI への呼び出しは専用の内部実装を使用し、リトライ／エラー時は macro_sentiment=0.0 とするフェイルセーフ。
    - 最終的にスコアを合成して market_regime に冪等に書き込む（BEGIN / DELETE / INSERT / COMMIT）。
  - OpenAI API キーは引数優先、未指定時は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

- 研究（kabusys.research）
  - factor_research:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離等を prices_daily から計算。
    - calc_volatility: 20日 ATR、ATR 比率、20日平均売買代金、出来高比率等を計算。
    - calc_value: raw_financials と prices_daily を組み合わせて PER / ROE を計算（EPS=0 や欠損は None）。
    - 全て DuckDB 上の SQL と最小限の Python により実装し、外部 API に依存しない設計。
  - feature_exploration:
    - calc_forward_returns: 任意ホライズン（デフォルト [1,5,21]）の将来リターンを算出（LEAD を使用）。
    - calc_ic: スピアマン（ランク）相関による IC 計算（コードマッチングと None/非有限値フィルタリングを実施）。
    - rank: 同順位は平均ランクで処理（丸めて ties の検出精度を確保）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー。

- データ管理（kabusys.data）
  - calendar_management:
    - market_calendar に基づく営業日判定 / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar 未取得時は曜日ベース（土日非営業）でフォールバックする一貫した動作。
    - calendar_update_job: J-Quants クライアント（jquants_client）を使った差分取得・バックフィル・保存の夜間バッチ処理を実装（健全性チェック、バックフィル、保存結果を返す）。
  - pipeline / ETL:
    - ETLResult データクラスを公開。ETL 実行で取得/保存件数、品質チェック結果、エラー一覧を集約。
    - 差分更新・バックフィル・品質チェックを想定した設計（jquants_client / quality モジュールと連携）。

### Fixed / Robustness / Safety
- DB 書き込み時のトランザクション処理を強化（BEGIN / COMMIT / ROLLBACK の使用、ROLLBACK 失敗時の警告ログ）。
- ニュースやレジームの LLM 呼び出しでの各種例外（RateLimit, APIConnectionError, APITimeoutError, APIError）をハンドリングし、リトライやフェイルセーフ（スコア=0.0）を実装。
- DuckDB executemany の空リストバインド制約に対応して、INSERT/DELETE 前に空チェックを行う。
- 日時の扱いについてルックアヘッドバイアスを防ぐため、datetime.today() / date.today() を直接参照しない設計（target_date を明示的に受け取る API を採用）。
- .env パーサの堅牢化（クォート中のエスケープ、コメント処理、export キーワード対応）。

### Notes / Limitations
- OpenAI 呼び出しは gpt-4o-mini の JSON Mode を想定。API 仕様変更や別モデルを使う場合は内部の _call_openai_api を差し替えるか調整が必要。
- raw_financials の利用は latest report_date を採る仕様のため、財務データのタイミングや報告日扱いに注意が必要。
- 一部の DuckDB バインド（リストや配列）やバージョン差異を考慮した互換性処理を実装しているが、利用する DuckDB のバージョン差異で微妙な挙動差が出る可能性あり。
- calendar_update_job は jquants_client の fetch/save 実装に依存する（実際の API クライアント実装は別モジュール）。

### Security
- .env 自動読み込み時に既存の OS 環境変数を protected として上書きしないデフォルト挙動を採用。必要に応じて override=True により明示的に上書き可能。
- OpenAI API キーの取り扱いは引数優先 → 環境変数で決定。未設定時は明確にエラーを出す設計。

---

今後の予定（例）
- エラーメトリクス・監視統合（Slack 通知等）の追加
- ETL の品質チェックルール追加・可視化
- backtesting / strategy 実装と execution モジュールの統合

（補足）不明点や追加で CHANGELOG に反映したい項目があれば、該当箇所のコミット／ファイル差分情報を提供してください。