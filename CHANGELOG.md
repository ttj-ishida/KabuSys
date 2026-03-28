# Changelog

すべての変更は Keep a Changelog の形式に従います。  
このファイルはコードベースから推測して作成した初回リリースの変更履歴です。

全般的な注意
- 日付・文言はソースコードの設計・定数・コメントから推測して記載しています。
- ライブラリのバージョンはパッケージの __version__（0.1.0）に基づきます。

## [Unreleased]

## [0.1.0] - 初回リリース
初期公開リリース。以下の主要機能・モジュールを実装しています。

### 追加 (Added)
- パッケージ基礎
  - kabusys パッケージ初期化（__version__ = 0.1.0、公開サブパッケージ: data, strategy, execution, monitoring）。
- 設定管理
  - 環境変数/.env 管理モジュール（kabusys.config）を追加。
    - .env/.env.local の自動読み込みを実装（読み込み優先度: OS 環境変数 > .env.local > .env）。
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 により自動読み込みを無効化可能。
    - .git または pyproject.toml を基準にプロジェクトルートを検出するため、CWD に依存しないロードを実現。
    - .env のパース機能を強化（export プレフィックス対応、シングル/ダブルクォート内でのエスケープ処理、コメント扱いの細かなルール）。
    - 必須環境変数取得時に _require() が未設定なら ValueError を送出。
    - 設定項目（JQUANTS_REFRESH_TOKEN / KABU_API_PASSWORD / KABU_API_BASE_URL / SLACK_BOT_TOKEN / SLACK_CHANNEL_ID / DUCKDB_PATH / SQLITE_PATH / KABUSYS_ENV / LOG_LEVEL 等）をプロパティとして提供。
    - KABUSYS_ENV および LOG_LEVEL 値検証（許容値チェック）を実装。
    - is_live / is_paper / is_dev ヘルパープロパティを提供。
- AI（自然言語処理）関連
  - ニュースNLP（kabusys.ai.news_nlp）
    - raw_news と news_symbols から銘柄ごとにニュースを集約し、OpenAI（gpt-4o-mini）でセンチメントを評価して ai_scores テーブルへ書き込み。
    - タイムウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC では前日 06:00 〜 23:30）を対象にする calc_news_window を実装。
    - バッチ処理: 1 API コールあたり最大 _BATCH_SIZE=20 銘柄、1銘柄あたりのトークン肥大化対策として _MAX_ARTICLES_PER_STOCK=10 件・_MAX_CHARS_PER_STOCK=3000 でトリム。
    - OpenAI 呼び出しは JSON mode を利用。レスポンスのバリデーション/パース処理を実装し、不正レスポンスや余計な前後テキストを許容する復元処理を備える。
    - レスポンス検証により未知コードを無視、スコアは ±1.0 にクリップ。
    - レート制限(429)/ネットワーク断/タイムアウト/5xx に対する指数バックオフリトライ実装（初期 wait=1.0 秒、最大リトライ回数設定）。
    - ETL への書き込みは冪等化（DELETE → INSERT）し、部分失敗時に他コードの既存スコアを保護する設計。
  - 市場レジーム判定（kabusys.ai.regime_detector）
    - ETF 1321（日経225連動型）の 200 日移動平均乖離（重み 70%）とマクロニュースの LLM センチメント（重み 30%）を合成して日次で市場レジーム（bull / neutral / bear）を判定。
    - ma200_ratio の計算でルックアヘッドバイアスを防ぐ（target_date 未満のデータのみ使用）。
    - マクロニュースは news_nlp.calc_news_window を利用してウィンドウを決定、上限記事数を設けて LLM に送信。
    - OpenAI（gpt-4o-mini）呼び出し・JSON パースの堅牢化、リトライ/フェイルセーフ（API エラー時 macro_sentiment=0.0）を実装。
    - レジームスコア合成ロジック、閾値（BULL_THRESHOLD / BEAR_THRESHOLD）によるラベリング、結果を market_regime テーブルへ冪等書き込み。
- 研究（Research）モジュール
  - kabusys.research パッケージおよびファクター計算・特徴量探索を実装。
  - ファクター計算（kabusys.research.factor_research）
    - calc_momentum: mom_1m / mom_3m / mom_6m / ma200_dev（200 日 MA 乖離率）を計算。データ不足時の None ハンドリング。
    - calc_volatility: 20 日 ATR（atr_20） / 相対 ATR（atr_pct） / 20 日平均売買代金（avg_turnover） / 出来高比率（volume_ratio）を計算。true_range の NULL 伝播を明確に制御。
    - calc_value: raw_financials から直近の財務データを取得して PER・ROE を計算（EPS が 0 または欠損なら None）。
    - 設計により DuckDB 上の SQL とウィンドウ関数を活用、外部 API にはアクセスしない。
  - 特徴量探索（kabusys.research.feature_exploration）
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを一括クエリで取得。horizons のバリデーション（1..252）を実装。
    - calc_ic: スピアマン（ランク）相関による IC（Information Coefficient）計算。レコード結合・None 排除・3 件未満は None を返す。
    - rank: 同順位は平均ランクを返す実装（float の丸めによる ties 対応）。
    - factor_summary: count/mean/std/min/max/median を算出する統計サマリー関数。
- データプラットフォーム（Data）
  - kabusys.data パッケージの実装（臨時クライアント再エクスポート等）。
  - calendar_management
    - JPX カレンダー管理: is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day 実装。
    - market_calendar が未取得の場合は曜日ベース（週末除外）でフォールバックする一貫した設計。
    - calendar_update_job: jquants_client から差分取得して market_calendar を冪等保存。バックフィル（直近 _BACKFILL_DAYS を再フェッチ）・健全性チェックを実装。
  - ETL パイプライン（kabusys.data.pipeline）
    - ETLResult dataclass を追加（ETL 実行結果の構造化）。
    - 差分更新・backfill・品質チェック（quality モジュール連携）を想定した設計。テーブル最大日付取得や存在チェック等のユーティリティを実装。
  - ETL ユーティリティのエクスポート（kabusys.data.etl: ETLResult を再エクスポート）。

### 変更 (Changed)
- （初回リリースのため過去からの変更はなし）パッケージ設計上の留意点やデフォルト値・既定値をドキュメント化。

### 修正 (Fixed)
- （初回リリースのため過去からの修正はなし）

### 非推奨 (Deprecated)
- なし

### 削除 (Removed)
- なし

### セキュリティ (Security)
- OpenAI / 外部 API キーは引数経由または環境変数 OPENAI_API_KEY で注入する設計。未設定時は ValueError を発生させ明示的に失敗する（安全側の設計）。
- .env ロード時に OS 環境変数を保護するため protected キーセットを扱う（.env.local による上書きや既存環境変数の保護を考慮）。

## 既知の設計方針・制約（要点）
- ルックアヘッドバイアス防止: すべてのバッチ処理 / スコア算出は datetime.today()/date.today() を直接参照せず、呼び出し側から target_date を受け取る設計。
- DuckDB 互換性: 一部実装で DuckDB の挙動（executemany の空リスト不可など）に合わせた防護処理を実装。
- フェイルセーフ: 外部 API 呼び出し失敗時は通常処理を継続し得るようにしており、部分失敗がシステム全体を落とさない設計。
- テスト容易性: OpenAI 呼び出し箇所はモック差し替え（unittest.mock.patch）を想定した構造にしている。

---

（注）この CHANGELOG は提供されたコード断片の内容から推測して作成しています。実際のリリースノートとして公開する場合は、リリース日・著者・追加の変更点・マイグレーション手順などをプロジェクト実態にあわせて補完してください。