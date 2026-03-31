# Changelog

すべての重要な変更を記録します。本ファイルは Keep a Changelog の形式に準拠しています。  
各リリースは後方互換性や動作に影響する点をわかりやすくまとめています。

フォーマット: https://keepachangelog.com/ja/1.0.0/

## [Unreleased]
（なし）

## [0.1.0] - 2026-03-31
初回公開リリース。

### 追加 (Added)
- パッケージの基礎構成を追加
  - パッケージ名: kabusys
  - version: 0.1.0
  - エクスポート: data, strategy, execution, monitoring

- 環境設定管理 (kabusys.config)
  - .env/.env.local 自動読み込み機能を追加（プロジェクトルート判定は .git または pyproject.toml を基準）
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化対応（テストでの注入を想定）
  - .env パーサ実装:
    - コメント行・空行を無視
    - export KEY=val 形式に対応
    - シングル/ダブルクォート内のバックスラッシュエスケープを考慮したパース
    - クォートなし値でのインラインコメント処理（直前がスペース/タブの場合のみコメントと判断）
  - .env の読み込み動作:
    - OS 環境変数 > .env.local > .env の優先度
    - override/protected オプションにより OS 環境変数を保護
    - 読み込み失敗時は警告（warnings.warn）
  - Settings クラスによる設定参照ユーティリティを追加:
    - JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID を必須チェック
    - KABU_API_BASE_URL、DUCKDB_PATH、SQLITE_PATH のデフォルト値
    - KABUSYS_ENV（development / paper_trading / live）の検証
    - LOG_LEVEL の検証（DEBUG/INFO/WARNING/ERROR/CRITICAL）
    - is_live / is_paper / is_dev のブールプロパティ

- AI モジュール (kabusys.ai)
  - news_nlp.score_news:
    - raw_news と news_symbols を集約して銘柄ごとにニュースをまとめ、OpenAI（gpt-4o-mini）でセンチメントを評価
    - JST 時間ウィンドウ（前日15:00〜当日08:30）を UTC に変換して DB クエリに利用
    - バッチ処理（最大 20 銘柄／チャンク）と銘柄単位の文字数トリム（最大 3000 文字）
    - レスポンスの検証ロジック（JSON パース、results キー、code/score 検証、スコアの有限性チェック）
    - リトライ戦略: 429/ネットワーク断/タイムアウト/5xx に対して指数バックオフ（最大試行回数の制御）
    - 部分成功に備え、ai_scores テーブルへは先に該当 code を DELETE → INSERT で置換（部分失敗時に既存データを保護）
    - API キー注入可能（api_key 引数 or 環境変数 OPENAI_API_KEY）と未設定時の ValueError
    - 失敗時はフェイルセーフで空スコア扱い（処理継続）

  - regime_detector.score_regime:
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）と、マクロニュースの LLM センチメント（重み 30%）を合成して日次の市場レジームを判定（bull/neutral/bear）
    - prices_daily から過去 200 日分を用いて ma200_ratio を計算（ルックアヘッド防止のため target_date 未満のデータのみ使用）
    - マクロニュースは news_nlp.calc_news_window を用いてウィンドウを決定し、キーワードによるフィルタでタイトルを抽出
    - OpenAI 呼び出しは独立実装（news_nlp と内部呼び出しを共有しない設計）
    - OpenAI 呼び出しのリトライ/エラーハンドリング実装（同様にフェイルセーフで macro_sentiment=0.0 を採用）
    - 計算結果は market_regime テーブルへ冪等的に書き込み（BEGIN/DELETE/INSERT/COMMIT、失敗時は ROLLBACK を試行）
    - API キー注入可能（api_key 引数 or 環境変数 OPENAI_API_KEY）と未設定時の ValueError

- Research モジュール (kabusys.research)
  - factor_research:
    - calc_momentum: mom_1m / mom_3m / mom_6m および ma200_dev を DuckDB 上で集合的に計算
      - 200 行未満の場合は ma200_dev を None
      - スキャン範囲にバッファを設けることで週末/祝日を考慮
    - calc_volatility: 20 日 ATR（true_range の厳密な扱い）、相対 ATR（atr_pct）、20 日平均売買代金、出来高比率を計算
      - ATR 計算で high/low/prev_close の NULL 伝播を明示的に管理
    - calc_value: raw_financials から report_date <= target_date の最新財務情報を取り出し PER（EPS が存在し 0 でない場合）と ROE を算出
  - feature_exploration:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD により一度に取得
      - horizons の妥当性チェック（正の整数かつ <= 252）
    - calc_ic: ファクターと将来リターンの Spearman（ランク相関）を計算、データ不足時は None を返す
    - rank: 同順位は平均ランクで処理（丸めによる ties 回避）
    - factor_summary: 各ファクター列の count/mean/std/min/max/median を算出（None 値除外）

  - research パッケージの __all__ に主要関数をエクスポート（zscore_normalize は data.stats からの再利用）

- Data モジュール (kabusys.data)
  - calendar_management:
    - JPX マーケットカレンダーの操作ユーティリティを追加
      - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day
      - DB の market_calendar を優先し、未登録日は曜日ベース（平日）でフォールバック
      - 最大探索日数制限（_MAX_SEARCH_DAYS）や健全性チェック（極端に未来の日付はスキップ）
    - calendar_update_job: J-Quants API から差分取得して market_calendar を更新（バックフィル・オンコンフリクト想定）
  - pipeline (ETL):
    - ETLResult データクラスを追加（取得件数、保存件数、品質問題、エラーリストなどを保持）
    - ETL ヘルパー関数:
      - DB テーブル存在チェック、最大日付取得ロジック
      - 市場カレンダー調整ヘルパー（_adjust_to_trading_day 等）を用意
    - ETL の設計方針:
      - 差分更新、バックフィル、品質チェックを行い、致命的な品質問題でも処理を途中で止めず呼び出し元で判断可能にする
      - id_token 注入可能でテスト容易性に配慮
  - etl モジュールで ETLResult を再エクスポート（kabusys.data.etl）

### 変更 (Changed)
- なし（初回リリースのため）

### 修正 (Fixed)
- なし（初回リリースのため）

### セキュリティ (Security)
- OpenAI API キーは引数注入または環境変数を参照する設計。キー未提供時は ValueError を送出して明示的にエラー化。

### 既知の設計方針（注意点）
- ルックアヘッドバイアス対策として、いずれの処理も datetime.today() / date.today() を内部ロジックの基準に使わず、必ず呼び出し元から target_date を受け取る方式を採用。
- OpenAI 呼び出しに関してはフェイルセーフ設計（API 失敗時はスコアを 0.0 或いはスキップして処理継続）を採用し、例外で全体を停止させない方針。
- DuckDB に対する executemany の互換性（空リスト不可）を考慮した実装を行っている。
- news_nlp と regime_detector は OpenAI 呼び出し関数を意図的に独立実装しており、モジュール間でプライベート関数を共有しない設計になっている。

### ブレイキングチェンジ (Breaking Changes)
- なし（初回リリース）

---

今後のリリースでは、機能追加・最適化・バグ修正をこの形式で記録します。必要であれば特定機能（例：OpenAI モデルの切替、バッチサイズ調整、DB 書き込み最適化など）について詳細を追記します。