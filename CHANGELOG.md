# CHANGELOG

すべての変更は「Keep a Changelog」形式に準拠して記載しています。  
（コード内容から実装意図を推測してまとめています）

全体方針・共通設計ノート
- ルックアヘッドバイアス防止のため、各日付処理関数は datetime.today()/date.today() を直接参照しない設計になっています（target_date を明示的に受け取る）。
- DuckDB の実装差異や制約（executemany の空リスト不可など）に配慮した互換性対策が各所に入っています。
- 外部 API 呼び出しはリトライ／バックオフやフェイルセーフ（API失敗時はスキップして続行、デフォルトスコアや 0 を返す等）を備えています。
- DB 書き込みは冪等性・部分障害耐性を重視（DELETE→INSERT、BEGIN/COMMIT/ROLLBACK の明示的制御など）。

## [0.1.0] - 2026-04-04

### 追加
- パッケージ初期リリース（kabusys v0.1.0）
  - __version__ = "0.1.0"

- 環境設定管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を読み込む自動ローダ実装
    - プロジェクトルートは __file__ を起点に .git または pyproject.toml を探索して決定（CWD 非依存）。
    - 読み込み優先順位: OS環境変数 > .env.local > .env。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env のパースは export プレフィックス対応、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメント処理などに対応。
  - Settings クラスを提供し、主要設定項目をプロパティで取得可能：
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, KABU_API_BASE_URL 等
    - DB パス（DUCKDB_PATH, SQLITE_PATH）、監視 PID/フラグパス、閾値（CPU/MEM/DISK）など
    - KABUSYS_ENV の値検証（development / paper_trading / live）
    - LOG_LEVEL の値検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev の利便性プロパティ

- AI ニュース NLP（kabusys.ai.news_nlp）
  - raw_news と news_symbols から銘柄ごとに記事を集約して OpenAI（gpt-4o-mini）へ送信し、銘柄ごとのセンチメント ai_score を ai_scores テーブルへ保存する機能を実装。
  - 特徴:
    - ニュース収集ウィンドウを JST ベースで定義（前日 15:00 JST 〜 当日 08:30 JST を UTC に変換して使用）。
    - 1銘柄あたりの最大記事数（_MAX_ARTICLES_PER_STOCK）と文字数トリム（_MAX_CHARS_PER_STOCK）によるトークン肥大化対策。
    - 1回あたり最大銘柄数（_BATCH_SIZE）を使ったバッチ送信。
    - OpenAI JSON mode を利用して厳密な JSON を期待し、レスポンスの堅牢なパースとバリデーションを実装（レスポンス復元ロジック含む）。
    - レート制限（429）、ネットワーク断、タイムアウト、5xx に対する指数バックオフによるリトライ実装。
    - スコアは ±1.0 にクリップ。部分失敗時に既存スコアを消さないよう、DELETE（コード絞り込み）→INSERT の置換方式で書き込み。
    - APIキーは引数で注入可能（api_key）で、None の場合は環境変数 OPENAI_API_KEY を参照。未設定時は ValueError を送出。

- AI 市場レジーム判定（kabusys.ai.regime_detector）
  - ETF 1321（Nikkei 225 連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジーム（bull / neutral / bear）を判定して market_regime テーブルへ保存。
  - 特徴:
    - ma200_ratio の計算は target_date 未満のデータのみを使用（ルックアヘッド防止）。
    - マクロニュースは news_nlp のウィンドウ計算を利用してタイトルを抽出し、OpenAI（gpt-4o-mini）へ送信して macro_sentiment を算出。
    - API 呼び出しでのリトライ／エラーハンドリングの実装（RateLimitError, APIConnectionError, APITimeoutError, APIError 等）。
    - 合成スコアは clip で -1〜1 に正規化し閾値に基づいて regime_label を決定。
    - DB 書き込みは冪等（BEGIN / DELETE WHERE date = ? / INSERT / COMMIT）で実装。APIキー注入可、未設定時は ValueError。

- データ基盤（kabusys.data）
  - カレンダー管理（calendar_management）
    - JPX の市場カレンダー（market_calendar）を扱うユーティリティを提供。
    - is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - DB にカレンダーがない場合は曜日ベース（土日非営業）でフォールバック。DB 登録ありの場合は DB 値優先、未登録日は曜日フォールバックで一貫した挙動。
    - next/prev の探索に _MAX_SEARCH_DAYS 制限を設けて無限ループを防止。
    - 夜間バッチ calendar_update_job を実装（J-Quants API から差分取得して market_calendar を冪等保存、バックフィル、健全性チェック）。

  - ETL パイプライン（pipeline, etl）
    - ETLResult データクラスを公開（ETL 実行結果の構造化）。
    - pipeline モジュール（ETL の差分取得、保存、品質チェックの設計意図を文書化）。主な方針:
      - 差分更新（最終取得日の自動算出）、バックフィル日数による補正、品質チェックは集約して呼び出し元が判断可能にする（Fail-Fast ではない）。
      - jquants_client 経由の保存は冪等に設計。

- 研究用モジュール（kabusys.research）
  - factor_research:
    - calc_momentum: mom_1m/mom_3m/mom_6m, ma200_dev（200日MA乖離）を計算。
    - calc_volatility: 20日 ATR（atr_20）、相対ATR（atr_pct）、avg_turnover、volume_ratio を計算。
    - calc_value: per（株価/EPS）、roe を raw_financials と prices_daily を組み合わせて計算。
    - 各関数は DuckDB SQL を活用し、必要な行数不足時は None を返す設計。
  - feature_exploration:
    - calc_forward_returns: 将来リターン（デフォルト [1,5,21]）を一括で取得（LEAD を利用）。
    - calc_ic: スピアマンランク相関による IC（Information Coefficient）計算。
    - rank: 同順位の平均ランクを返すヘルパー（丸め誤差対策で round を使用）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算する統計サマリー。

### 改善（設計上の配慮・堅牢化）
- DB 書き込みは部分失敗時の影響を最小化する実装（ai_scores の置換時に処理成功したコードのみ更新する等）。
- OpenAI API とのインタラクションはテスト容易性を考慮し、呼び出し箇所をラップしてモック差し替え可能（unittest.mock.patch による差し替えを想定）。
- JSON レスポンスのパースにおいて、JSON mode でも前後に余計なテキストが混入するケースを考慮し最外の {} を抽出して復元する処理を導入。
- 各所で詳細なログ出力（info/debug/warning/exception）を追加し、運用時のトラブルシュートを容易化。

### 既知の制約 / 注意点
- OpenAI API キーは環境変数 OPENAI_API_KEY から取得可能だが、明示的に api_key を渡すことが可能。未設定の場合は ValueError を送出する箇所あり（AI 関連関数）。
- DuckDB のバージョン差異により一部のバインド表現が不安定なため、executemany を使った個別 DELETE/INSERT の方式を採用している（空リストでの executemany は避ける必要がある）。
- news_nlp / regime_detector は gpt-4o-mini を前提にプロンプトを組んでおり、モデル仕様変更時はパースやレスポンスの取り扱いを見直す必要あり。

### セキュリティ
- 機密情報（API トークン等）は Settings 経由で環境変数管理を想定。自動 .env ロードはプロジェクトルート検出に依存するため、配布後の運用では KABUSYS_DISABLE_AUTO_ENV_LOAD 等で制御してください。

---

この CHANGELOG はコードベースの実装から機能・挙動を推測して作成しています。実際のコミット履歴や設計ドキュメントに基づいて修正・追記することを推奨します。