# CHANGELOG

すべての変更は Keep a Changelog 準拠の形式で記載しています。

注: 下記は提示されたソースコードの内容から推測して作成した変更履歴です。実際のコミット履歴ではなく、機能追加・設計上の重要点・既知の振る舞いを整理したものです。

## [Unreleased]
- なし

## [0.1.0] - 2026-03-28
初回リリース。日本株自動売買システムのコアライブラリを公開。

### 追加 (Added)
- パッケージ全体
  - kabusys パッケージ初版を追加。サブパッケージ: data, research, ai, monitoring?, strategy, execution（__all__ で公開）。
  - バージョン: 0.1.0（src/kabusys/__init__.py）。

- 設定・環境変数管理 (kabusys.config)
  - .env ファイルまたは環境変数から設定を読み込む Settings クラスを追加。
  - 自動読み込みの仕様:
    - プロジェクトルートを .git または pyproject.toml で探索して .env/.env.local を自動ロード（KABUSYS_DISABLE_AUTO_ENV_LOAD=1 で無効化可能）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env。OS 環境変数は保護され上書きされない。
  - .env パーサを実装:
    - コメント行/空行を無視。
    - export KEY=val 形式をサポート。
    - 単一・二重クォート内のバックスラッシュエスケープ処理をサポート。
    - 非クォート値では '#' が直前に空白/タブある場合のみコメント扱い。
  - Settings による必須キー取得（_require）と各種プロパティ（J-Quants, kabu API, Slack, DBパス, 環境種別、ログレベル）を提供。
  - KABUSYS_ENV の許容値制約（development, paper_trading, live）および LOG_LEVEL の検証を実装。

- AI モジュール (kabusys.ai)
  - ニュースNLP (news_nlp.py)
    - raw_news / news_symbols を集約して OpenAI（gpt-4o-mini）へバッチ送信し、銘柄ごとの ai_score を ai_scores テーブルへ保存する score_news を実装。
    - 時間ウィンドウ: 前日 15:00 JST 〜 当日 08:30 JST（UTC に変換して DB クエリ）。
    - バッチ処理: 1コールあたり最大 20 銘柄、1銘柄あたり最大 10 記事・3000 文字にトリム。
    - JSON Mode を使用しレスポンスをバリデート（results 配列、code/score 検証）。
    - リトライ/バックオフ: RateLimit / ネットワーク断 / タイムアウト / 5xx を指数バックオフでリトライ（上限あり）。
    - フェイルセーフ: API エラーやパース失敗時は該当チャンクをスキップし、処理を継続。
    - DB 書き込みは冪等を意識（対象コードのみ DELETE → INSERT）して部分失敗時の他コード保護。
    - テスト用に _call_openai_api をパッチ可能（unittest.mock.patch を想定）。
  - 市場レジーム判定 (regime_detector.py)
    - ETF 1321 の 200 日移動平均乖離（重み70%）とマクロニュースの LLM センチメント（重み30%）を合成し、日次で market_regime テーブルへスコアを書き込む score_regime を実装。
    - マクロニュースは news_nlp の calc_news_window により対象ウィンドウを計算し、raw_news からキーワードで抽出。
    - OpenAI 呼び出しは独立実装（news_nlp と private 関数を共有しない設計）。
    - レジームスコアはクリップと閾値判定で "bull"/"neutral"/"bear" を決定。
    - API 失敗時は macro_sentiment=0.0 をフェイルセーフとして採用。
    - DB 書き込みはトランザクション（BEGIN / DELETE / INSERT / COMMIT）で冪等化、失敗時は ROLLBACK。

- 研究（Research）モジュール (kabusys.research)
  - factor_research.py
    - Momentum: mom_1m / mom_3m / mom_6m、200日MA乖離（ma200_dev）を calc_momentum で計算。
    - Volatility: 20日 ATR、相対ATR（atr_pct）、20日平均売買代金、volume_ratio を calc_volatility で計算。
    - Value: PER（EPS が 0 または欠損なら None）、ROE を calc_value で計算（raw_financials と prices_daily を参照）。
    - 全関数は DuckDB を受け取り SQL と組み合わせて結果を返す。
  - feature_exploration.py
    - 将来リターン calc_forward_returns（任意ホライズン、デフォルト [1,5,21]）、効率的に LEAD を用いて取得。
    - IC（Information Coefficient） calc_ic 実装（Spearman の ρ 計算、ランク関数 rank を提供）。
    - factor_summary: 基本統計量（count/mean/std/min/max/median）を計算。
    - 外部依存を避け、標準ライブラリのみで実装。

- データ（Data）モジュール (kabusys.data)
  - calendar_management.py
    - JPX カレンダーを扱うユーティリティ群: is_trading_day, next_trading_day, prev_trading_day, get_trading_days, is_sq_day を実装。
    - market_calendar テーブルがない場合の曜日ベースフォールバック（週末を非営業日扱い）。
    - DB 値優先の一貫した振る舞い（未登録日は曜日フォールバック）と最大探索日数制限を導入。
    - calendar_update_job を実装: J-Quants API（jquants_client）から差分取得し market_calendar を更新、バックフィル・健全性チェックあり。
  - pipeline.py / etl.py
    - ETLResult データクラスを定義（取得件数・保存件数・品質チェック結果・エラーなどを保持）。
    - データ差分取得、保存、品質チェックの実行フローに対応する ETL パイプライン設計方針とユーティリティを実装（jquants_client, quality を参照）。
    - _get_max_date 等のユーティリティを提供。
  - etl モジュールは pipeline.ETLResult を再エクスポート（kabusys.data.etl）。

### 変更 (Changed)
- 該当なし（初回リリース）

### 修正 (Fixed)
- 該当なし（初回リリース）

### セキュリティ / 動作上の注意 (Notes)
- OpenAI API:
  - AI 関連関数 score_news / score_regime は api_key 引数を受け取る。未指定時は環境変数 OPENAI_API_KEY を参照する。未設定の場合は ValueError を送出する。
  - モデルは gpt-4o-mini を想定、JSON mode を利用して厳密な JSON を要求する実装になっている。
  - LLM 呼び出しはリトライ・バックオフを行い、致命的な失敗は部分スキップして継続する（フェイルセーフ）。
- 環境変数:
  - 必須: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, SLACK_BOT_TOKEN, SLACK_CHANNEL_ID（Settings の各プロパティ参照）。
  - .env パーサの仕様に依存するため、.env の書式には注意（クォート・コメントの扱い等）。
- DB（DuckDB）:
  - 多くの処理は DuckDB 接続を前提としている。ai_scores, prices_daily, raw_news, market_regime, raw_financials, market_calendar 等のテーブル存在が前提。
  - DuckDB の executemany に関する注意点（空リストは不可）を考慮した実装になっている。
- ルックアヘッドバイアス防止:
  - AI・研究の各処理は内部で datetime.today()/date.today() を参照しない設計（target_date を明示的に受け取る）。
- テスト支援:
  - OpenAI 呼び出し部分はモック差し替え可能（内部関数を patch してテスト可能）。

### 既知の制約 / 今後の改善候補 (Known issues / TODO)
- news_nlp の出力検証は堅牢だが、LLM の予期しない形式に対する復元ロジック（最外側の {} を抽出する等）は簡易的なため更なる堅牢化の余地あり。
- calc_value では PBR・配当利回りは未実装（注記あり）。
- calendar_update_job の J-Quants クライアント側のエラー処理は current 実装で例外を捕捉するが、詳細リトライやメトリクス計測の拡充が望ましい。
- test coverage の言及はないため、ユニットテスト整備（特に DB クエリと OpenAI 呼び出しのモック化）が推奨される。

---

リリースに関する補足や、実際のコミットログ（著者・コミットハッシュ・詳細な差分）を付加したい場合は、リポジトリの Git 履歴を元に CHANGELOG を拡張してください。