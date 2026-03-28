# CHANGELOG

すべての変更は Keep a Changelog の形式に従って記載しています。  
（初期リリース v0.1.0 — パッケージバージョン: 0.1.0）

## [0.1.0] - 2026-03-28
初期リリース — 日本株自動売買システムのコア機能を実装。

### 追加
- パッケージ基盤
  - パッケージエントリポイントを追加（kabusys.__init__、__version__ = "0.1.0"）。
  - モジュールの公開 API を __all__ で整理（data, strategy, execution, monitoring）。

- 設定 / 環境変数管理（kabusys.config）
  - .env ファイルおよび環境変数から設定を自動ロードする仕組みを実装。
  - プロジェクトルート探索は __file__ を起点に `.git` または `pyproject.toml` を探す方式を採用（CWD 非依存）。
  - .env / .env.local の読み込み順制御（OS 環境変数優先、.env.local は上書き可能）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化を追加（テスト向け）。
  - キー保護（既存 OS 環境変数は protected として上書き防止）対応。
  - .env パーサ実装: export プレフィックス、クォート／エスケープ、インラインコメントの扱いに対応。
  - Settings クラスを提供し、J-Quants / kabu / Slack / DB パス / 環境種別・ログレベル等のプロパティを公開。必須環境変数未設定時は ValueError を送出。

- データ取得・ETL（kabusys.data.pipeline / etl / jquants クライアント想定）
  - ETLResult データクラスを公開して ETL 実行結果（取得数・保存数・品質問題・エラー）を集約。
  - 差分更新・バックフィル・品質チェック方針を実装（API 取得 → 保存 → 品質チェックのフロー / 設計方針を実装）。
  - DuckDB を用いる想定で最大日付取得やテーブル存在確認ユーティリティを実装。

- マーケットカレンダー管理（kabusys.data.calendar_management）
  - JPX カレンダーを扱うユーティリティを実装。
  - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
  - market_calendar の有無に応じた曜日ベースのフォールバック、最大探索日数制限、バックフィル、健全性チェック等を実装。
  - calendar_update_job: J-Quants API からの差分取得 → 保存の夜間バッチ処理を実装（バックフィル含む、例外時は安全に 0 を返して継続）。

- リサーチ用ユーティリティ（kabusys.research）
  - factor_research モジュールを実装:
    - calc_momentum: 1M/3M/6M リターン、200日 MA 乖離の算出。データ不足時の None 処理。
    - calc_volatility: 20日 ATR、相対ATR、20日平均売買代金、出来高比率の算出。
    - calc_value: PER・ROE の算出（raw_financials の最新レコードを結合）。
  - feature_exploration モジュールを実装:
    - calc_forward_returns: 指定ホライズン先の将来リターンを LEAD で一括取得。
    - calc_ic: スピアマンランク相関（IC）計算（結合・欠損除外・最小サンプル検査）。
    - rank: 平均ランク（同順位は平均ランク）計算（丸めによる ties 対策）。
    - factor_summary: 各カラムの count/mean/std/min/max/median を計算。
  - 研究向けに duckdb 接続を受け取り外部 API に依存しない実装。

- AI（自然言語処理）モジュール（kabusys.ai）
  - news_nlp モジュールを実装:
    - score_news: raw_news / news_symbols を集約し、OpenAI（gpt-4o-mini）で銘柄ごとのニュースセンチメントを算出し ai_scores に書き込み。
    - タイムウィンドウは JST 基準（前日 15:00 ～ 当日 08:30）を UTC に変換して処理。
    - バッチ処理（最大 20 銘柄/回）、1銘柄あたりの最大記事数および文字数トリムでトークン肥大を抑制。
    - JSON Mode を利用しレスポンス検証を厳密に行い、不正レスポンスはスキップ（例外を投げずフェイルセーフ）。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフとリトライ。
    - テスト容易性のため _call_openai_api をパッチ可能に設計。
  - regime_detector モジュールを実装:
    - ETF 1321（日経225連動型）の 200 日 MA 乖離（重み 70%）と news_nlp ベースのマクロセンチメント（重み 30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定し market_regime に冪等書き込み。
    - LLM 呼び出しの失敗時は macro_sentiment = 0.0 とするフェイルセーフ。
    - OpenAI 呼び出しは専用実装（news_nlp と内部の private 関数を共有しない設計）。
    - リトライ / バックオフ / JSON パース処理を実装。

- 監視・実行・その他の骨組み
  - data.etl を通じて ETLResult を再エクスポート（kabusys.data.etl）。
  - 各種モジュールでのログ出力と例外ハンドリングを整備（ロールバック / コミット管理、警告ログ）。

### 変更
- （初期リリースのため過去バージョンからの変更はありません）

### 修正
- （初期リリースのため過去バージョンからの修正はありません）

### 注意点 / 既知の挙動
- OpenAI API キーは api_key 引数で注入可能。未指定時は環境変数 OPENAI_API_KEY を参照し、未設定の場合は ValueError を送出する。
- .env の自動ロードはプロジェクトルートが特定できない場合はスキップされる。またテスト時等は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能。
- DuckDB 0.10 の制約（executemany に空リストを渡せない等）を考慮した実装になっている。
- ニュース／LLM 関連はフェイルセーフ優先（API 失敗で例外を投げずスコアをスキップまたは中立にフォールバック）する設計。
- カレンダー情報が未取得の場合、曜日（平日のみを営業日）に基づくフォールバックを使用する。

---

開発・保守にあたっての補足:
- テストしやすさを意識し、外部 API 呼び出し（OpenAI / J-Quants）を差し替え可能な設計になっています（関数レベルで patch/mocking が可能）。
- 将来の拡張点として、ファクター群の追加、モデル運用のための監視/メトリクス、より高度なエラーハンドリング方針の導入を想定しています。

（必要であれば、各モジュールの公開関数・戻り値・例外仕様をより詳細に CHANGELOG またはドキュメントに追記できます。）