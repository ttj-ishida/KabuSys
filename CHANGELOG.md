# Changelog

すべての注目すべき変更はこのファイルに記録します。  
フォーマットは「Keep a Changelog」（https://keepachangelog.com/ja/1.0.0/）準拠です。

## [Unreleased]

---

## [0.1.0] - 2026-04-02

初期リリース。以下の主要機能・モジュールを追加しました。

### Added
- パッケージ基盤
  - パッケージ名: kabusys、バージョン: 0.1.0 を定義。
  - パッケージの公開 API を __all__（data, strategy, execution, monitoring）で宣言。

- 環境設定 / 設定管理（kabusys.config）
  - .env / .env.local の自動読み込み機能（プロジェクトルートは .git または pyproject.toml を探索して決定）。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD による自動ロード無効化サポート（テスト用途を想定）。
  - .env パーサ: export KEY=val 形式、シングル/ダブルクォート内のバックスラッシュエスケープ、インラインコメントの取り扱い等に対応。
  - _load_env_file にて protected（既存 OS 環境変数）を尊重する上書き制御を実装。
  - Settings クラスを提供: J-Quants / kabuステーション / Slack / DB パス / 監視しきい値 / 環境（development/paper_trading/live）/ログレベルの取得とバリデーションを実施。
  - 必須環境変数未設定時は明示的に ValueError を送出するユーティリティ（_require）。

- AI モジュール（kabusys.ai）
  - news_nlp.score_news
    - raw_news と news_symbols を集約して銘柄毎にニュースをまとめ、OpenAI（デフォルト gpt-4o-mini）の JSON Mode を用いて銘柄ごとのセンチメントを算出。
    - JST基準のニュースウィンドウ（前日15:00 JST〜当日08:30 JST）を UTC naive datetime に変換する calc_news_window を実装。
    - バッチ処理（最大20銘柄／チャンク）、1銘柄あたり記事上限・文字数トリム、スコア ±1.0 クリップ、レスポンスバリデーションを実装。
    - 429 / ネットワーク断 / タイムアウト / 5xx に対する指数バックオフによるリトライ実装。API エラーやパースエラーはフェイルセーフでスキップし、処理を継続。
    - DuckDB への書き込みは部分失敗に強い手順（対象コードのみ DELETE → INSERT）を採用。DuckDB の executemany の空リスト制約への配慮あり。
    - テスト用に _call_openai_api を patch できる設計。
  - regime_detector.score_regime
    - ETF 1321 の 200 日移動平均乖離（MA比率）とマクロニュースの LLM（OpenAI）センチメントを重み合成して日次市場レジーム（bull/neutral/bear）を判定。
    - MA 計算は target_date 未満のデータのみを使用（ルックアヘッドバイアス防止）。データ不足時は中立値を使用。
    - マクロ記事抽出はキーワードベース（複数キーワードリスト）で最大件数制限あり。記事がない場合は LLM 呼び出しを省略して macro_sentiment=0.0。
    - OpenAI 呼び出しはリトライとフェイルセーフ設計（失敗時 macro_sentiment=0.0）。レスポンスは JSON で受け取りパース。
    - market_regime テーブルへの冪等的書き込み（BEGIN / DELETE / INSERT / COMMIT）を実装。
    - OpenAI API 呼び出し用の api_key を引数で注入可能にしてテスト性を向上。

- Data モジュール（kabusys.data）
  - calendar_management
    - JPX カレンダー管理ロジック（market_calendar テーブル）を提供。
    - is_trading_day / is_sq_day / next_trading_day / prev_trading_day / get_trading_days といった営業日判定ユーティリティを実装。DB 登録値を優先し、未登録日は曜日ベースのフォールバック（週末を休み扱い）で補完。
    - calendar_update_job により J-Quants から差分取得→保存（バックフィル・健全性チェック含む）を実装。jquants_client と連携する想定。
  - pipeline / etl
    - ETLResult データクラスを追加。ETL の取得件数／保存件数／品質問題／エラー概況を保持。
    - ETL 実行で想定される差分取得、保存（jquants_client の idempotent save_* を利用）、品質チェック（quality モジュール）に対応する設計方針をドキュメント化。
    - _table_exists / _get_max_date 等の内部ユーティリティを実装。
  - etl モジュールは ETLResult を再エクスポート。

- Research モジュール（kabusys.research）
  - factor_research
    - calc_momentum: 1M/3M/6M リターンと ma200_dev (200日 MA 乖離率) を DuckDB クエリで算出。データ不足時は None を返す設計。
    - calc_volatility: 20日 ATR（true range の扱いに注意）、相対 ATR、20日平均売買代金、出来高比率を算出。NULL の伝播制御に注意。
    - calc_value: raw_financials の最新財務データ（target_date 以下）と当日の株価から PER / ROE を計算。
    - 全関数は prices_daily / raw_financials のみ参照し、本番口座や外部発注 API にはアクセスしない設計。
  - feature_exploration
    - calc_forward_returns: 複数ホライズン（デフォルト [1,5,21]）を一度のクエリで取得。horizons のバリデーションあり。
    - calc_ic: スピアマン（ランク相関）による IC 算出を実装。値が不足すると None を返す。
    - rank: 同順位は平均ランクで扱う実装。浮動小数の丸めで ties を安定判定。
    - factor_summary: count/mean/std/min/max/median を標準ライブラリのみで計算する統計サマリー実装。

- テスト性・安全性・設計上の注意点
  - 主要なスコアリング関数（score_news, score_regime）および ETL 等は datetime.today() / date.today() を直接参照しない（ルックアヘッドバイアス防止）。target_date を明示的に受け取る設計。
  - OpenAI 呼び出し箇所は内部で patch 可能（ユニットテスト容易化のため）。
  - API 呼び出し失敗時は例外を投げずフォールバックする箇所が多く、システム全体のフェイルセーフを重視。
  - DuckDB への書き込みは冪等性を意識（DELETE → INSERT のパターン、トランザクション管理、ROLLBACK のログ出力）。
  - 一部実装は DuckDB のバージョン制約（executemany に空リスト不可等）に配慮。

### Notes / Known limitations
- OpenAI クライアントは現状 gpt-4o-mini を想定。将来的なモデル変更はコード更新が必要。
- news_nlp と regime_detector は JSON mode を期待するため、LLM の出力フォーマットに依存する。出力不整合時はフェイルセーフでスコアをスキップまたは 0.0 にフォールバックする。
- calc_news_window / raw_news.datetime の取り扱いは UTC naive datetime を前提としている（DB 保存形式との整合性に注意）。
- strategy / execution / monitoring モジュール群はパッケージ公開 API に含めているが、本リリースでの実装範囲は上記データ・リサーチ・AI 周りが中心。
- jquants_client / quality モジュールの具象実装は外部依存（本コードではインターフェースを想定・利用）。

---

このリリースは初期の機能実装に焦点を当てており、運用上の堅牢性（リトライ・フェイルセーフ・トランザクション管理）とテスト性（API キー注入、patch 可能な内部呼び出し）を重視しています。今後のリリースでは strategy / execution / monitoring の実装拡充、詳細な品質チェック拡張、ドキュメント・型注釈の強化、テストカバレッジの向上を予定しています。