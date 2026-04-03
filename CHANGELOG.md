CHANGELOG
=========

All notable changes to this project will be documented in this file.
This project adheres to "Keep a Changelog" (https://keepachangelog.com/ja/).
各項目は人為的にコードベースの内容から推測して作成しています。

Unreleased
----------

（なし）

0.1.0 - 2026-04-03
------------------

Added
- パッケージ初期リリース: kabusys 0.1.0
  - package metadata:
    - src/kabusys/__init__.py にて __version__="0.1.0" を設定。

- 環境変数 / 設定管理
  - kabusys.config.Settings を導入し、アプリケーション設定を環境変数から取得。
    - 必須の値は _require() で検証（未設定時は ValueError）。
    - サポート環境変数例: JQUANTS_REFRESH_TOKEN, KABU_API_PASSWORD, OPENAI_API_KEY, LINE_* 系、DUCKDB_PATH, SQLITE_PATH 等。
    - KABUSYS_ENV（development / paper_trading / live）および LOG_LEVEL の入力検証を実装。
    - パス指定は Path.expanduser() を使用して取り扱いを統一。
  - .env 自動読み込み機能を実装（プロジェクトルート検出: .git または pyproject.toml を基準）。
    - 読み込み優先順位: OS 環境変数 > .env.local > .env
    - KABUSYS_DISABLE_AUTO_ENV_LOAD=1 による自動ロード無効化に対応。
    - export KEY=val 形式、シングル/ダブルクォート、エスケープ、行末コメントの取り扱いなどを意識した .env パーサー実装。
    - OS 環境変数保護（protected set）と override フラグ対応。

- データプラットフォーム（DuckDB ベース）
  - データ ETL / パイプライン用ユーティリティ群を追加（kabusys.data.pipeline, etl, jquants_client 連携想定）。
  - ETL 実行結果を表す dataclass ETLResult を公開（kabusys.data. etl で再エクスポート）。
    - 品質チェックの結果（quality_issues）やエラー一覧を含め、辞書化メソッド to_dict を提供。
  - DuckDB 互換性を考慮した実装上の配慮:
    - executemany に空リストを渡せない問題（DuckDB 0.10）を回避するためのガード。
    - テーブル存在確認ユーティリティを多数実装。

- マーケットカレンダー管理
  - kabusys.data.calendar_management を追加:
    - is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - market_calendar テーブルの有無に応じて DB 値優先→未登録日は曜日ベースのフォールバックを行う一貫した判定ロジック。
    - calendar_update_job: J-Quants API から差分取得して market_calendar を冪等更新（バックフィル、サニティチェック付き）。
    - 最大探索日数やバックフィル日数などの安全対策を導入。

- 研究（Research）モジュール
  - kabusys.research パッケージを追加し、ファクター・特徴量解析ツールを提供:
    - factor_research:
      - calc_momentum: 1M/3M/6M リターン、200日移動平均乖離（ma200_dev）を計算。データ不足時は None を返す設計。
      - calc_volatility: 20日 ATR、相対 ATR、20日平均売買代金、出来高比率等を計算。
      - calc_value: raw_financials と prices_daily から PER・ROE を計算（EPS が無効なら None）。
      - DuckDB SQL を活用し高速に集計。結果は (date, code) をキーとする dict のリストで返却。
    - feature_exploration:
      - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを計算。horizons の入力検証あり。
      - calc_ic: ファクターと将来リターンの Spearman ランク相関（IC）を計算。十分なサンプルがなければ None を返す。
      - rank: 同順位は平均ランクを割り当てるランク化関数（丸めによる ties 対策あり）。
      - factor_summary: count/mean/std/min/max/median を計算する統計サマリー関数。
    - 研究用関数群は外部ライブラリに依存せず標準ライブラリ + DuckDB のみで実装。

- AI（LLM）関連
  - kabusys.ai パッケージを追加:
    - news_nlp.score_news:
      - raw_news と news_symbols を集約して銘柄ごとのニュースを整形し、OpenAI（gpt-4o-mini）へバッチ送信して銘柄別センチメント（ai_score）を取得。
      - バッチサイズ、1銘柄あたり記事数上限、文字数トリム等のトークン肥大化対策を実装。
      - レスポンス JSON の堅牢なバリデーション処理（JSON mode でも前後余計なテキストが混在するケースへの対処を含む）。
      - 429 / 通信断 / タイムアウト / 5xx に対する指数バックオフリトライ、非再試行エラーはスキップしてフェイルセーフに継続。
      - スコアは ±1.0 にクリップ。取得成功分のみ ai_scores テーブルを冪等（DELETE→INSERT）で更新。
      - テスト用に _call_openai_api をパッチ差替え可能（ユニットテストを想定）。
    - regime_detector.score_regime:
      - ETF 1321（日経225 連動型）の 200 日 MA 乖離（重み 70%）と、news_nlp 側で抽出したマクロニュースの LLM センチメント（重み 30%）を統合して市場レジーム（bull / neutral / bear）を日次判定。
      - LLM 呼び出しは gpt-4o-mini（JSON 出力）を利用。API エラー時は macro_sentiment=0.0 にフォールバック。
      - レジームスコアを clip して regime_label を決定し market_regime テーブルへ冪等書き込み（BEGIN/DELETE/INSERT/COMMIT）。
      - ルックアヘッドバイアス防止のため datetime.today()/date.today() を直接参照しない設計（target_date を引数で与える）。

- 実装上の堅牢性・運用性向上
  - OpenAI 呼び出しに対する詳細な例外ハンドリング（RateLimitError, APIConnectionError, APITimeoutError, APIError）と再試行戦略を実装。
  - JSON レスポンスパース失敗時の保護（部分的に余計なテキストが混入した JSON の復元試みなど）。
  - DB 書き込みを冪等に設計（DELETE→INSERT）、部分失敗時に既存データを不必要に削除しない工夫。
  - ログレベルとエラー時のログ出力を充実（warning/info/debug/exception を適切に使用）。
  - テスト容易性を考慮した差し替えポイント（_call_openai_api など）を用意。

Changed
- 初回リリースのため該当なし。

Fixed
- 初回リリースのため該当なし。

Deprecated
- 初回リリースのため該当なし。

Removed
- 初回リリースのため該当なし。

Security
- 初回リリースのため該当なし。

Notes / migration / 使用上の注意
- 必須環境変数:
  - JQUANTS_REFRESH_TOKEN（J-Quants API 用）
  - KABU_API_PASSWORD（kabuステーション API 用）
  - OPENAI_API_KEY（news_nlp / regime_detector の実行に必要、関数呼び出し時に引数で上書き可能）
- 自動 .env ロードを無効化したい場合は KABUSYS_DISABLE_AUTO_ENV_LOAD=1 を設定してください。
- DuckDB を用いるため、ai_scores / market_regime / prices_daily / raw_news / raw_financials / market_calendar 等のテーブルスキーマが事前に必要です（DataPlatform.md / StrategyModel.md に記載の想定）。
- OpenAI 呼び出しの振る舞い（リトライや JSON モード）は将来の SDK 変更によって影響を受ける可能性があるため、必要に応じて _call_openai_api の差し替えやラッパーを検討してください。

Acknowledgements / Implementation assumptions
- 本 CHANGELOG は提供されたソースコードを基に機能・設計方針を推測して作成しています。実際のリリース作業・README やドキュメントと差異がある場合は、公式ドキュメントを優先してください。