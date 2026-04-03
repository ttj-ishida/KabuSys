Changelog
=========

すべての注記は「Keep a Changelog」形式に準拠します。  
このプロジェクトの安定リリース版はセマンティックバージョニングを使用します。

[Unreleased]
------------

（なし）

[0.1.0] - 2026-04-03
--------------------

Added
- パッケージ初回公開: kabusys v0.1.0
  - パッケージメタ情報:
    - src/kabusys/__init__.py にて __version__ = "0.1.0" を設定し、主要サブパッケージをエクスポート (data, strategy, execution, monitoring)。
- 環境設定 / .env 自動読み込み機能（src/kabusys/config.py）
  - プロジェクトルート（.git または pyproject.toml）を基準に .env/.env.local を自動読み込み。
  - KABUSYS_DISABLE_AUTO_ENV_LOAD により自動ロードを無効化可能。
  - .env パーサ実装:
    - export KEY=val 形式、シングル/ダブルクォート、バックスラッシュエスケープ、インラインコメント扱いをサポート。
    - override / protected オプションで OS 環境変数を保護する挙動を実装。
  - Settings クラスを提供し、J-Quants / kabu ステーション / LINE / DB パス / 監視閾値 / 実行環境（KABUSYS_ENV）などをプロパティで取得。環境値検証（KABUSYS_ENV、LOG_LEVEL）を行う。
- AI（ニュース NLP / レジーム判定）（src/kabusys/ai）
  - news_nlp モジュール:
    - raw_news と news_symbols を銘柄ごとに集約し、OpenAI（gpt-4o-mini）の JSON モードでバッチセンチメント評価。
    - チャンク処理（最大20銘柄/チャンク）、1銘柄あたりの最大記事数・文字数トリム、429/ネットワーク/タイムアウト/5xx に対する指数バックオフリトライを実装。
    - レスポンスの厳密バリデーション（results 配列、code/score の存在、未知コードは無視、数値性と有限性の確認）、スコアを ±1 にクリップ。
    - DuckDB 互換性確保: executemany に空リストを渡さない防御ロジックを追加。
    - calc_news_window 実装（JST 基準の前日 15:00 〜 当日 08:30 を UTC に変換したウィンドウを返す）。
  - regime_detector モジュール:
    - ETF 1321（日経225連動）200日移動平均乖離（70%）とマクロニュース LLM センチメント（30%）を合成して日次で市場レジーム（bull/neutral/bear）を判定。
    - OpenAI 呼び出しは独立実装（news_nlp とは共有しない）で、失敗時は macro_sentiment=0.0 として継続するフェイルセーフを採用。
    - DuckDB への冪等な書き込み（BEGIN/DELETE/INSERT/COMMIT とエラーハンドリングで ROLLBACK を保護）。
    - マクロキーワードリスト、モデル指定（gpt-4o-mini）、リトライと待機（最大リトライ回数・指数バックオフ）を実装。
  - 共通設計方針:
    - LLM 呼び出しに対するリトライ、エラー種別ごとの挙動、JSON パース失敗時のログ & フォールバックの実装。
    - ルックアヘッドバイアス回避: datetime.today()/date.today() を参照せず、target_date ベースで処理を行う。
- Data（ETL / カレンダー / パイプライン）（src/kabusys/data）
  - calendar_management モジュール:
    - JPX カレンダー管理（market_calendar）をサポート。is_trading_day / next_trading_day / prev_trading_day / get_trading_days / is_sq_day を提供。
    - DB にデータがない場合は曜日ベース（土日除外）でフォールバック。DB 登録ありは DB 値を優先。
    - calendar_update_job: J-Quants API からの差分取得、バックフィル（直近日数を再取得）、健全性チェック（将来日付異常の検出）、および save_market_calendar 呼び出しを行い冪等保存。
  - pipeline モジュール:
    - ETLResult dataclass を導入（取得件数・保存件数・品質問題リスト・エラーリストなどを保持）。
    - ETL の設計方針をコードコメントで明示（差分取得、バックフィル、品質チェックは Fail-Fast ではなく収集型）。
    - 内部ユーティリティ: テーブル存在チェック、最大日付取得など。
  - ETL 再利用性・安全性:
    - jquants_client 経由で idempotent に保存する方針を反映。
    - quality モジュールと連携して欠損・スパイク等を検出し、結果を ETLResult に集約。
- Research（因子計算・特徴量探索）（src/kabusys/research）
  - factor_research モジュール:
    - calc_momentum: 1M/3M/6M リターン、200日MA乖離率（ma200_dev）を DuckDB SQL で算出。データ不足時は None を返す。
    - calc_volatility: 20日 ATR、ATR比率（atr_pct）、20日平均売買代金（avg_turnover）、出来高比（volume_ratio）を算出。true_range の NULL 伝播を明確化。
    - calc_value: raw_financials から最新の財務を取得し PER / ROE を計算（EPS 0/欠損は None）。target_date 以前の最新財務レコードを ROW_NUMBER で取得。
    - 設計方針: DuckDB のみを使い、外部 API や発注 API にはアクセスしない。
  - feature_exploration モジュール:
    - calc_forward_returns: 指定ホライズン（デフォルト [1,5,21]）の将来リターンを LEAD を使って一括取得。horizons の検証と上限（<=252）チェックあり。
    - calc_ic: Spearman ランク相関（Information Coefficient）を計算。Tie は平均ランクで扱う。データ不足（<3 件）で None を返す。
    - rank: 値リストをランクに変換（round(..., 12) による tie 回避）。
    - factor_summary: count/mean/std/min/max/median を計算する統計サマリー。
  - すべての research 関数は prices_daily / raw_financials 等の DB テーブルのみ参照し、本番口座との混在を避ける実装。
- テストしやすさ / モック対応
  - OpenAI 呼び出し部分は _call_openai_api を介しているため、unit test で patch して差し替え可能。

Changed
- （初回リリースのため特になし）

Fixed
- （初回リリースのため特になし）

Security / Safety
- LLM 呼び出し失敗時は例外をそのまま上位伝播させず、フェイルセーフ（0.0 やスキップ）で継続する実装を多用。これにより一部機能の停止が全体の停止を招かない設計。
- 環境変数の必須チェック（_require）による早期検出。KABUSYS_ENV / LOG_LEVEL の値検証で誤設定を防止。

Notes / Implementation details
- DuckDB を主要なローカル DB として想定。executemany の空リスト問題等 DuckDB 固有の互換性に対応するガードが含まれる。
- OpenAI API は gpt-4o-mini を想定し、JSON Mode の利用を前提にレスポンスを厳密にパースしている。
- 日時 / 窓の定義は JST をベースに設計し、DB の日付は UTC naive datetime を前提としている（news calc window 等）。
- ルックアヘッドバイアス回避のため、全てのバッチ処理 / スコアリングは target_date を明示して処理する設計を採用。

Acknowledgements
- 初期実装における各モジュールは将来的に微調整（モデル変更、API レスポンス形式の変化、DB スキーマ変更等）される可能性があります。API キーや外部サービスの挙動変更時には該当箇所の更新が必要です。